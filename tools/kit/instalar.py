#!/usr/bin/env python3
"""Asistente de instalacion guiado del kit autoalojado de Atalaya. Solo biblioteca estandar (Python >= 3.9).
Guided installer for the self-hosted Atalaya kit. Standard library only (Python >= 3.9).

Uso / Usage (desde la carpeta del kit / from the kit folder):
    python3 tools/kit/instalar.py                  (interactivo / interactive)
    python3 tools/kit/instalar.py --lang en
    python3 tools/kit/instalar.py --sin-arranque   (solo genera la configuracion / config only)
    python3 tools/kit/instalar.py --verificar      (solo verifica / check only)
    python3 tools/kit/instalar.py --si --org ... --modo local --admin ... --google-json ...   (sin preguntas)

Hace: comprobaciones previas -> preguntas -> claves -> archivos (.env.kit, secrets/) -> docker compose
-> espera /health -> verificar_instalacion.py. NUNCA imprime ni registra las claves, no usa shell=True,
no descarga nada y no tiene telemetria: la unica red es /health en 127.0.0.1.
Does: preflight checks -> questions -> keys -> files -> docker compose -> wait for /health -> verifier.
It never prints or logs secrets, never uses shell=True, downloads nothing, has no telemetry.
"""

import argparse
import base64
import getpass
import json
import os
import re
import secrets
import shutil
import socket
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

VERSION = "1.0.0"
CALLBACK_PATH = "/auth/google/callback"
ENV_FILE = ".env.kit"
GOOGLE_JSON_NAME = "google_client.json"
APP_PORT = 8000  # puerto publicado por docker-compose.yml en 127.0.0.1
MIN_DISK_FAIL = 1 * 1024**3
MIN_DISK_WARN = 3 * 1024**3
HEALTH_TIMEOUT = 120  # segundos
MIN_PY = (3, 9)
VERIFIER_MIN_PY = (3, 11)  # verificar_instalacion.py usa datetime.UTC

_EMAIL = re.compile(
    r"^[A-Za-z0-9._%+'\-]{1,64}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)
_HOST = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)

LANG = "es"
USE_COLOR = False


class InstallError(Exception):
    """Error esperado: se muestra el mensaje, sin traza, y sale con codigo distinto de cero."""


# ----------------------------------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------------------------------
def t(es: str, en: str) -> str:
    return en if LANG == "en" else es


def set_lang(value: "str | None") -> None:
    global LANG
    LANG = "en" if (value or "").lower().startswith("en") else "es"


def set_color(stream=None) -> None:
    global USE_COLOR
    stream = stream or sys.stdout
    USE_COLOR = (
        "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
        and hasattr(stream, "isatty")
        and stream.isatty()
    )


def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def say(text: str = "") -> None:
    print(text, flush=True)


def step(number: int, total: int, title: str) -> None:
    say("")
    say(paint(f"[{number}/{total}] {title}", "1;36"))


def ok(text: str) -> None:
    say(f"  {paint('OK   ', '32')} {text}")


def warn(text: str) -> None:
    say(f"  {paint('AVISO' if LANG == 'es' else 'WARN ', '33')} {text}")


def fail_line(text: str) -> None:
    say(f"  {paint('FALLA' if LANG == 'es' else 'FAIL ', '1;31')} {text}")


def info(text: str) -> None:
    say(f"  {text}")


def highlight(text: str) -> str:
    return paint(text, "1;30;43") if USE_COLOR else f">>> {text} <<<"


# ----------------------------------------------------------------------------------------------
# Validaciones (sin importar `app`: el asistente corre fuera del contenedor)
# ----------------------------------------------------------------------------------------------
def is_safe_email(email: str) -> bool:
    """Misma politica que app/identity.py: solo ASCII normal y sin punycode (xn--)."""
    if not email or not email.isascii() or not _EMAIL.match(email):
        return False
    return not any(
        label.startswith("xn--") for label in email.rsplit("@", 1)[1].lower().split(".")
    )


def parse_emails(value: str) -> list[str]:
    """Lista separada por comas -> correos normalizados. El error NO repite el correo."""
    result: list[str] = []
    for position, raw in enumerate(p for p in value.split(",") if p.strip()):
        email = raw.strip().lower()
        if not is_safe_email(email):
            raise InstallError(
                t(
                    f"La direccion numero {position + 1} de la lista no es valida o usa caracteres "
                    "no permitidos (solo letras ASCII normales).",
                    f"Address number {position + 1} in the list is not valid or uses characters "
                    "that are not allowed (plain ASCII letters only).",
                )
            )
        if email not in result:
            result.append(email)
    return result


def valid_org_name(name: str) -> str:
    name = name.strip()
    if (
        not name
        or len(name) > 80
        or any(ord(c) < 32 or c in "\r\n#\"'`$\\" for c in name)
    ):
        raise InstallError(
            t(
                "El nombre de la organizacion debe tener de 1 a 80 caracteres, sin comillas, "
                "#, $, barra invertida ni saltos de linea.",
                "The organization name must be 1 to 80 characters, without quotes, #, $, "
                "backslashes or line breaks.",
            )
        )
    return name


def valid_domain(value: str) -> str:
    """Acepta `dominio` o `https://dominio`. Devuelve el dominio (minusculas, ASCII)."""
    host = value.strip().lower()
    host = host.removeprefix("https://")
    host = host.rstrip("/")
    if (
        not host.isascii()
        or not _HOST.match(host)
        or any(label.startswith("xn--") for label in host.split("."))
    ):
        raise InstallError(
            t(
                "El dominio no es valido. Usa solo letras ASCII, por ejemplo atalaya.tuorganizacion.org "
                "(sin http://, sin puerto, sin ruta).",
                "The domain is not valid. Use plain ASCII letters, for example atalaya.yourorganization.org "
                "(no http://, no port, no path).",
            )
        )
    return host


def base_url_for(mode: str, domain: "str | None") -> str:
    if mode == "local":
        return f"http://localhost:{APP_PORT}"
    if not domain:
        raise InstallError(
            t(
                "En produccion hace falta el dominio.",
                "Production mode needs the domain.",
            )
        )
    return f"https://{domain}"


def redirect_uri_for(base_url: str) -> str:
    return base_url.rstrip("/") + CALLBACK_PATH


def validate_base_url(url: str) -> None:
    parts = urlparse(url)
    if url.startswith("https://") and parts.hostname:
        return
    if parts.scheme == "http" and parts.hostname == "localhost":
        return
    raise InstallError(
        t(
            "La direccion base debe empezar por https:// (solo http://localhost se permite para evaluar).",
            "The base address must start with https:// (only http://localhost is allowed for evaluation).",
        )
    )


def load_google_json(path: Path, expected_redirect: str) -> dict:
    """Valida el JSON del cliente de Google: tipo web, client_id/secret y URI de redireccion exacta."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise InstallError(
            t(f"No existe el archivo {path}.", f"The file {path} does not exist.")
        ) from None
    except (OSError, ValueError):
        raise InstallError(
            t(
                f"El archivo {path} no se puede leer o no es un JSON valido.",
                f"The file {path} cannot be read or is not valid JSON.",
            )
        ) from None
    web = data.get("web") if isinstance(data, dict) else None
    if (
        not isinstance(web, dict)
        or not web.get("client_id")
        or not web.get("client_secret")
    ):
        raise InstallError(
            t(
                'El JSON no es de un cliente de tipo "Aplicacion web" (debe tener la clave "web" con '
                "client_id y client_secret). En Google Auth Platform > Clientes crea uno de tipo "
                "Aplicacion web y descarga su JSON.",
                'The JSON is not from a "Web application" client (it must have the "web" key with '
                "client_id and client_secret). In Google Auth Platform > Clients create a Web "
                "application client and download its JSON.",
            )
        )
    if expected_redirect not in (web.get("redirect_uris") or []):
        raise InstallError(
            t(
                f"El JSON no incluye la URI de redireccion {expected_redirect}. Agregala en el cliente "
                "(Google Auth Platform > Clientes), vuelve a descargar el JSON y repite.",
                f"The JSON does not include the redirect URI {expected_redirect}. Add it to the client "
                "(Google Auth Platform > Clients), download the JSON again and retry.",
            )
        )
    return data


def inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
        return True
    except ValueError:
        return False


def in_git_worktree(path: Path) -> bool:
    for parent in [path.resolve()] + list(path.resolve().parents):
        if (parent / ".git").exists():
            return True
    return False


def check_google_json_location(source: Path, kit_dir: Path) -> None:
    """El JSON original no debe estar dentro de una carpeta de repositorio (se podria subir por error).
    Se admite que ya este en secrets/google_client.json (esa carpeta esta en .gitignore)."""
    dest = (kit_dir / "secrets" / GOOGLE_JSON_NAME).resolve()
    if source.resolve() == dest:
        return
    if in_git_worktree(source) or inside(source, kit_dir):
        raise InstallError(
            t(
                "El JSON de Google esta dentro de una carpeta de repositorio. Muevelo a otra carpeta "
                "(por ejemplo Descargas) y vuelve a indicar la ruta: asi no se sube a git por error.",
                "The Google JSON is inside a repository folder. Move it to another folder (for example "
                "Downloads) and give the path again, so it is never committed by mistake.",
            )
        )


def safe_join(base: Path, *parts: str) -> Path:
    """Une rutas sin permitir escapar de `base` (path traversal)."""
    target = base.joinpath(*parts).resolve()
    if not inside(target, base):
        raise InstallError(
            t("Ruta fuera de la carpeta del kit.", "Path outside the kit folder.")
        )
    return target


# ----------------------------------------------------------------------------------------------
# Secretos
# ----------------------------------------------------------------------------------------------
def generate_fernet_key() -> str:
    """32 bytes aleatorios en base64 urlsafe: formato de cryptography.fernet.Fernet."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def generate_session_secret() -> str:
    return secrets.token_urlsafe(48)


# ----------------------------------------------------------------------------------------------
# Archivos y permisos
# ----------------------------------------------------------------------------------------------
def restrict(path: Path, *, is_dir: bool = False, mode: "int | None" = None) -> bool:
    """Permisos restringidos. POSIX: chmod. Windows: icacls (mejor esfuerzo). Devuelve si lo logro."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        if not user or not shutil.which("icacls"):
            return False
        grant = f"{user}:(OI)(CI)F" if is_dir else f"{user}:F"
        try:
            run = subprocess.run(  # nosec B603 B607
                ["icacls", str(path), "/inheritance:r", "/grant:r", grant],
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return run.returncode == 0
    try:
        os.chmod(path, mode if mode is not None else (0o700 if is_dir else 0o600))
    except OSError:
        return False
    return True


def write_private(path: Path, content: str, *, mode: int = 0o600) -> None:
    """Escribe con permisos restringidos desde el primer byte (POSIX) y reemplaza de forma atomica."""
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(tmp, flags, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if os.name == "nt":
            restrict(tmp)
        else:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def backup_existing(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    counter = 1
    while backup.exists():
        counter += 1
        backup = path.with_name(f"{path.name}.bak-{stamp}-{counter}")
    shutil.copy2(path, backup)
    restrict(backup)
    return backup


def build_env(cfg: dict) -> str:
    lines = [
        "# Generado por tools/kit/instalar.py. NO lo subas a git. Guia: docs/INSTALACION.md",
        f"ATALAYA_BASE_URL={cfg['base_url']}",
        "GOOGLE_CLIENT_SECRETS_FILE=/run/secrets/google_client.json",
        f"ATALAYA_FERNET_KEY={cfg['fernet']}",
        f"ATALAYA_SESSION_SECRET={cfg['session']}",
        f"ATALAYA_ADMIN_EMAILS={','.join(cfg['admins'])}",
        f"ATALAYA_ORG_NAME={cfg['org']}",
        f"ATALAYA_TRUST_PROXY={cfg['trust_proxy']}",
        f"ATALAYA_LANG={LANG}",
    ]
    if cfg["supervisors"]:
        lines.append(f"ATALAYA_SUPERVISOR_EMAILS={','.join(cfg['supervisors'])}")
    if cfg["llm"]:
        lines += ["ATALAYA_LLM=anthropic", f"ANTHROPIC_API_KEY={cfg['anthropic_key']}"]
    else:
        lines.append("ATALAYA_LLM=off")
    return "\n".join(lines) + "\n"


def parse_env_text(text: str) -> dict:
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


# ----------------------------------------------------------------------------------------------
# Docker y red local
# ----------------------------------------------------------------------------------------------
def docker_run(
    args: list, cwd: Path, timeout: int = 1800, quiet: bool = True
) -> "subprocess.CompletedProcess":
    exe = shutil.which("docker")
    if not exe:
        raise InstallError(
            t("No se encuentra docker en el PATH.", "docker was not found in PATH.")
        )
    return subprocess.run(  # nosec B603
        [exe, *args],
        cwd=str(cwd),
        capture_output=quiet,
        text=True,
        check=False,
        timeout=timeout,
    )


def port_in_use(port: int) -> bool:
    """True si algo ya escucha en 127.0.0.1:port (conexion, no bind: no requiere privilegios)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def fetch_health(port: int) -> "dict | None":
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # nosec B310
            data = json.loads(response.read(4096).decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return None
    return data if isinstance(data, dict) else None


def wait_for_health(port: int, timeout: float, interval: float = 2.0) -> "dict | None":
    deadline = time.monotonic() + timeout
    while True:
        data = fetch_health(port)
        if data and data.get("status") == "ok":
            return data
        if time.monotonic() >= deadline:
            return None
        time.sleep(interval)


# ----------------------------------------------------------------------------------------------
# Interaccion
# ----------------------------------------------------------------------------------------------
class Ask:
    def __init__(self, non_interactive: bool):
        self.non_interactive = non_interactive

    def _need(self, what: str):
        if self.non_interactive:
            raise InstallError(
                t(
                    f"Falta un dato para ejecutar sin preguntas: {what}.",
                    f"A value is missing for non-interactive mode: {what}.",
                )
            )

    def text(self, prompt: str, *, default: "str | None" = None, what: str = "") -> str:
        self._need(what or prompt)
        suffix = f" [{default}]" if default else ""
        try:
            answer = input(f"  {prompt}{suffix}: ").strip()
        except EOFError:
            raise InstallError(
                t(
                    "Se cerro la entrada: no se pudo preguntar.",
                    "Input closed: could not ask.",
                )
            ) from None
        return answer or (default or "")

    def secret(self, prompt: str, *, what: str = "") -> str:
        self._need(what or prompt)
        try:
            return getpass.getpass(f"  {prompt}: ").strip()
        except EOFError:
            raise InstallError(
                t(
                    "Se cerro la entrada: no se pudo preguntar.",
                    "Input closed: could not ask.",
                )
            ) from None

    def confirm(
        self, prompt: str, *, default: bool = False, assume: "bool | None" = None
    ) -> bool:
        if self.non_interactive:
            return default if assume is None else assume
        hint = (
            "[S/n]"
            if (default and LANG == "es")
            else "[s/N]"
            if LANG == "es"
            else "[Y/n]"
            if default
            else "[y/N]"
        )
        yes = ("s", "si", "y", "yes")
        try:
            answer = input(f"  {prompt} {hint}: ").strip().lower()
        except EOFError:
            return default
        return default if not answer else answer in yes

    def choice(
        self, prompt: str, options: list, *, default: str, what: str = ""
    ) -> str:
        self._need(what or prompt)
        while True:
            answer = self.text(
                f"{prompt} ({'/'.join(options)})", default=default
            ).lower()
            if answer in options:
                return answer
            warn(t("Opcion no valida.", "Not a valid option."))


# ----------------------------------------------------------------------------------------------
# Pasos
# ----------------------------------------------------------------------------------------------
def preflight(kit_dir: Path, *, need_docker: bool) -> None:
    problems: list[str] = []

    if sys.version_info >= MIN_PY:
        ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        problems.append(
            t("Hace falta Python 3.9 o superior.", "Python 3.9 or newer is required.")
        )

    if (kit_dir / "docker-compose.yml").is_file():
        ok(
            t(
                "Carpeta del kit con docker-compose.yml",
                "Kit folder with docker-compose.yml",
            )
        )
    else:
        problems.append(
            t(
                f"{kit_dir} no parece la carpeta del kit (falta docker-compose.yml). Usa --dir.",
                f"{kit_dir} does not look like the kit folder (docker-compose.yml is missing). Use --dir.",
            )
        )

    probe = kit_dir / f".atalaya-escritura-{os.getpid()}"
    try:
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        ok(t("Permiso de escritura en la carpeta", "Write permission in the folder"))
    except OSError:
        problems.append(
            t(
                f"No se puede escribir en {kit_dir}. Revisa los permisos.",
                f"Cannot write to {kit_dir}. Check permissions.",
            )
        )

    try:
        free = shutil.disk_usage(kit_dir).free
    except OSError:
        free = None
    if free is not None:
        gib = free / 1024**3
        if free < MIN_DISK_FAIL:
            problems.append(
                t(
                    f"Queda muy poco espacio en disco ({gib:.1f} GB). Libera al menos 3 GB.",
                    f"Very little disk space left ({gib:.1f} GB). Free at least 3 GB.",
                )
            )
        elif free < MIN_DISK_WARN:
            warn(
                t(
                    f"Poco espacio en disco ({gib:.1f} GB); se recomiendan 3 GB.",
                    f"Low disk space ({gib:.1f} GB); 3 GB are recommended.",
                )
            )
        else:
            ok(
                t(
                    f"Espacio en disco: {gib:.0f} GB libres",
                    f"Disk space: {gib:.0f} GB free",
                )
            )

    if need_docker:
        problems += check_docker(kit_dir)

    if problems:
        for text in problems:
            fail_line(text)
        raise InstallError(
            t(
                "Las comprobaciones previas fallaron; corrige lo anterior y repite.",
                "Preflight checks failed; fix the items above and try again.",
            )
        )


def check_ports(ports: list, app_port: int) -> None:
    problems: list[str] = []
    for port in ports:
        if not port_in_use(port):
            ok(t(f"Puerto {port} libre", f"Port {port} is free"))
        elif port == app_port and (fetch_health(port) or {}).get("mode") == "gmail":
            warn(
                t(
                    f"El puerto {port} ya lo usa una instancia de Atalaya (se actualizara).",
                    f"Port {port} is already used by an Atalaya instance (it will be updated).",
                )
            )
        else:
            problems.append(
                t(
                    f"El puerto {port} esta ocupado por otro programa. Detenlo o libera ese puerto "
                    "(en Linux: `ss -ltnp`; en Windows: `netstat -ano`).",
                    f"Port {port} is in use by another program. Stop it or free that port "
                    "(Linux: `ss -ltnp`; Windows: `netstat -ano`).",
                )
            )
    if problems:
        for text in problems:
            fail_line(text)
        raise InstallError(
            t(
                "Hay puertos ocupados; corrige lo anterior y repite.",
                "Some ports are busy; fix the items above and try again.",
            )
        )


def check_docker(kit_dir: Path) -> list:
    help_es = "Instala Docker (https://docs.docker.com/get-docker/); este asistente no instala nada por su cuenta."
    help_en = "Install Docker (https://docs.docker.com/get-docker/); this assistant installs nothing on its own."
    if not shutil.which("docker"):
        return [
            t(
                f"No se encontro `docker`. {help_es}",
                f"`docker` was not found. {help_en}",
            )
        ]
    problems = []
    try:
        version = docker_run(["--version"], kit_dir, timeout=30)
        compose = docker_run(["compose", "version"], kit_dir, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return [t("`docker` no responde.", "`docker` does not respond.")]
    if version.returncode != 0:
        problems.append(t("`docker --version` fallo.", "`docker --version` failed."))
    else:
        ok((version.stdout or "docker").strip().splitlines()[0][:80])
    if compose.returncode != 0:
        problems.append(
            t(
                "No se encontro `docker compose` (version 2). Actualiza Docker o instala el plugin Compose v2.",
                "`docker compose` (version 2) was not found. Update Docker or install the Compose v2 plugin.",
            )
        )
    else:
        ok((compose.stdout or "docker compose").strip().splitlines()[0][:80])
    if not problems:
        try:
            daemon = docker_run(["info"], kit_dir, timeout=60)
        except (OSError, subprocess.SubprocessError):
            daemon = None
        if daemon is None or daemon.returncode != 0:
            problems.append(
                t(
                    "Docker esta instalado pero no esta en marcha (o tu usuario no tiene permiso). "
                    "Inicia Docker, o agrega tu usuario al grupo `docker`, y repite.",
                    "Docker is installed but not running (or your user lacks permission). "
                    "Start Docker, or add your user to the `docker` group, and retry.",
                )
            )
    return problems


def gather(args, ask: Ask, kit_dir: Path) -> dict:
    cfg: dict = {}

    cfg["org"] = valid_org_name(
        args.org
        or ask.text(t("Nombre de la organizacion", "Organization name"), what="--org")
    )

    say("")
    info(t("Modo de instalacion:", "Installation mode:"))
    info(
        t(
            "  local        = evaluacion en este equipo (http://localhost:8000)",
            "  local        = evaluation on this machine (http://localhost:8000)",
        )
    )
    info(
        t(
            "  produccion   = servidor con un dominio HTTPS propio",
            "  production   = server with your own HTTPS domain",
        )
    )
    mode_in = (
        args.mode
        or ask.choice(
            t("Modo", "Mode"),
            ["local", "produccion", "production"],
            default="local",
            what="--modo",
        ).lower()
    )
    cfg["mode"] = "production" if mode_in in ("produccion", "production") else "local"
    if mode_in not in ("local", "produccion", "production"):
        raise InstallError(
            t(
                "Modo no valido: usa local o produccion.",
                "Invalid mode: use local or production.",
            )
        )

    domain = None
    if cfg["mode"] == "production":
        domain = valid_domain(
            args.domain
            or ask.text(
                t(
                    "Dominio (ej. atalaya.tuorganizacion.org)",
                    "Domain (e.g. atalaya.yourorganization.org)",
                ),
                what="--dominio",
            )
        )
    cfg["domain"] = domain
    cfg["base_url"] = base_url_for(cfg["mode"], domain)
    validate_base_url(cfg["base_url"])
    cfg["redirect_uri"] = redirect_uri_for(cfg["base_url"])
    say("")
    info(
        t(
            "Registra EXACTAMENTE esta URI de redireccion en tu cliente OAuth de Google:",
            "Register EXACTLY this redirect URI in your Google OAuth client:",
        )
    )
    say("    " + highlight(cfg["redirect_uri"]))
    info(
        t(
            "(Google Auth Platform > Clientes > tu cliente > URIs de redireccionamiento autorizados)",
            "(Google Auth Platform > Clients > your client > Authorized redirect URIs)",
        )
    )
    say("")

    admins = args.admin or ask.text(
        t(
            "Correo(s) de administracion, separados por comas",
            "Admin email(s), comma-separated",
        ),
        what="--admin",
    )
    cfg["admins"] = parse_emails(admins)
    if not cfg["admins"]:
        raise InstallError(
            t(
                "Hace falta al menos un correo de administracion.",
                "At least one admin email is required.",
            )
        )
    sup = args.supervisors
    if sup is None:
        sup = (
            ""
            if ask.non_interactive
            else ask.text(
                t(
                    "Correo(s) de supervision de solo lectura (opcional, Enter para omitir)",
                    "Read-only supervisor email(s) (optional, Enter to skip)",
                ),
                default="",
            )
        )
    cfg["supervisors"] = parse_emails(sup)

    # JSON de Google
    json_in = args.google_json or ask.text(
        t(
            "Ruta del JSON de credenciales de Google (tipo Aplicacion web)",
            "Path to the Google credentials JSON (Web application type)",
        ),
        what="--google-json",
    )
    source = Path(json_in.strip().strip('"')).expanduser()
    if not source.is_file():
        raise InstallError(
            t(f"No existe el archivo {source}.", f"The file {source} does not exist.")
        )
    check_google_json_location(source, kit_dir)
    load_google_json(source, cfg["redirect_uri"])
    cfg["google_json"] = source
    ok(
        t(
            "JSON de Google valido (tipo web, URI de redireccion incluida)",
            "Google JSON valid (web type, redirect URI included)",
        )
    )

    # Proxy
    if cfg["mode"] == "local":
        cfg["proxy"], cfg["hops"], cfg["trust_proxy"] = "none", 0, 0
    else:
        say("")
        info(
            t(
                "Proxy HTTPS: caddy = el del kit (certificado automatico, puertos 80/443); propio = ya tienes nginx/Traefik/balanceador.",
                "HTTPS proxy: caddy = the kit's own (automatic certificate, ports 80/443); own = you already run nginx/Traefik/a load balancer.",
            )
        )
        proxy = args.proxy or ask.choice(
            t("Proxy", "Proxy"),
            ["caddy", "propio", "own"],
            default="caddy",
            what="--proxy",
        )
        cfg["proxy"] = "own" if proxy in ("propio", "own") else "caddy"
        if args.proxy and args.proxy not in ("caddy", "propio", "own"):
            raise InstallError(
                t(
                    "Proxy no valido: usa caddy o propio.",
                    "Invalid proxy: use caddy or own.",
                )
            )
        if cfg["proxy"] == "caddy":
            cfg["hops"], cfg["trust_proxy"] = 1, 1
        else:
            hops = args.hops
            if hops is None:
                hops = (
                    int(
                        ask.text(
                            t(
                                "Cuantos proxies propios hay delante de Atalaya",
                                "How many of your own proxies sit in front of Atalaya",
                            ),
                            default="1",
                            what="--saltos",
                        )
                        or "1"
                    )
                    if not ask.non_interactive
                    else 1
                )
            if hops < 1 or hops > 10:
                raise InstallError(
                    t(
                        "El numero de saltos debe estar entre 1 y 10.",
                        "The number of hops must be between 1 and 10.",
                    )
                )
            cfg["hops"] = hops
            if hops == 1:
                cfg["trust_proxy"] = 1
                info(
                    t(
                        "Un salto: se activa ATALAYA_TRUST_PROXY=1. Tu proxy debe anadir la IP real como ULTIMA entrada de X-Forwarded-For.",
                        "One hop: ATALAYA_TRUST_PROXY=1 is set. Your proxy must add the real IP as the LAST X-Forwarded-For entry.",
                    )
                )
            else:
                cfg["trust_proxy"] = 0
                warn(
                    t(
                        "Con mas de un proxy propio el kit aun no distingue las IP reales (ver docs/INSTALACION.md, 'Proxy inverso'): se deja ATALAYA_TRUST_PROXY=0 y el limite de intentos contara todo como una sola IP. ATALAYA_TRUSTED_HOPS solo afecta a la demo publica, no se escribe.",
                        "With more than one own proxy the kit cannot yet tell real IPs apart (see docs/INSTALLATION.en.md, 'Reverse proxy'): ATALAYA_TRUST_PROXY=0 is set and the attempt limit counts everything as one IP. ATALAYA_TRUSTED_HOPS only affects the public demo and is not written.",
                    )
                )

    # IA
    use_ai = args.ai
    if use_ai is None:
        say("")
        info(
            t(
                "IA (opcional, APAGADA por defecto): si la activas, por cada correo se ENVIA a Anthropic (un tercero) un texto enmascarado: dominio, asunto de max. 200 caracteres, dominios de enlaces y hasta 1 500 caracteres de texto. El enmascarado es de mejor esfuerzo, no una garantia.",
                "AI (optional, OFF by default): if enabled, for each email a MASKED text is SENT to Anthropic (a third party): domain, subject (max. 200 characters), link domains and up to 1,500 characters of text. Masking is best effort, not a guarantee.",
            )
        )
        use_ai = ask.confirm(
            t("Activar la explicacion con IA?", "Enable AI explanations?"),
            default=False,
        )
    cfg["llm"] = bool(use_ai)
    cfg["anthropic_key"] = ""
    if cfg["llm"]:
        key = os.environ.get("ANTHROPIC_API_KEY", "") or ask.secret(
            t(
                "Clave de Anthropic (no se muestra al escribir)",
                "Anthropic API key (hidden while typing)",
            ),
            what="ANTHROPIC_API_KEY",
        )
        if not re.fullmatch(r"[A-Za-z0-9_\-]{20,300}", key):
            raise InstallError(
                t(
                    "La clave de Anthropic no tiene un formato valido.",
                    "The Anthropic key does not have a valid format.",
                )
            )
        cfg["anthropic_key"] = key
    return cfg


def write_files(cfg: dict, kit_dir: Path, args, ask: Ask) -> dict:
    """Escribe .env.kit, secrets/ y (con Caddy) el Caddyfile. No sobrescribe sin confirmacion."""
    out = {"backups": []}
    env_path = safe_join(kit_dir, ENV_FILE)
    secrets_dir = safe_join(kit_dir, "secrets")
    dest_json = safe_join(kit_dir, "secrets", GOOGLE_JSON_NAME)

    if env_path.exists():
        if not (
            args.overwrite
            or ask.confirm(
                t(
                    f"Ya existe {ENV_FILE}. Reemplazarlo (se guarda una copia con fecha)?",
                    f"{ENV_FILE} already exists. Replace it (a dated backup is kept)?",
                ),
                default=False,
            )
        ):
            raise InstallError(
                t(
                    f"Ya existe {ENV_FILE} y no se sobrescribio. Usa --sobrescribir para reemplazarlo (se guarda una copia).",
                    f"{ENV_FILE} already exists and was not overwritten. Use --overwrite to replace it (a backup is kept).",
                )
            )
        out["backups"].append(backup_existing(env_path))

    # Claves: se generan solo cuando ya se va a escribir
    cfg["fernet"] = generate_fernet_key()
    cfg["session"] = generate_session_secret()

    secrets_dir.mkdir(exist_ok=True)
    if os.name != "nt":
        # el usuario 10001 del contenedor debe poder entrar a la carpeta, no listarla
        os.chmod(secrets_dir, 0o711)  # nosec B103
    else:
        restrict(secrets_dir, is_dir=True)
    if dest_json.exists() and dest_json.resolve() != cfg["google_json"].resolve():
        out["backups"].append(backup_existing(dest_json))
    if dest_json.resolve() != cfg["google_json"].resolve():
        shutil.copyfile(cfg["google_json"], dest_json)
    if os.name != "nt":
        os.chmod(
            dest_json, 0o644
        )  # el contenedor (uid 10001) lo lee; solo lectura (ver ADR 0014)
    else:
        restrict(dest_json)

    write_private(env_path, build_env(cfg))
    out["env"] = env_path
    out["win_note"] = os.name == "nt"

    if cfg["proxy"] == "caddy":
        update_caddyfile(kit_dir, cfg["domain"], ask, args, out)
    return out


def update_caddyfile(kit_dir: Path, domain: str, ask: Ask, args, out: dict) -> None:
    path = safe_join(kit_dir, "Caddyfile")
    if not path.is_file():
        raise InstallError(
            t("Falta el Caddyfile del kit.", "The kit's Caddyfile is missing.")
        )
    text = path.read_text(encoding="utf-8")
    if "CAMBIAR_DOMINIO" in text:
        new = text.replace("CAMBIAR_DOMINIO", domain)
    elif re.search(rf"^{re.escape(domain)}\s*\{{", text, re.MULTILINE):
        return
    else:
        if not (
            args.overwrite
            or ask.confirm(
                t(
                    "El Caddyfile ya tiene otro dominio. Cambiarlo (se guarda una copia)?",
                    "The Caddyfile already has another domain. Change it (a backup is kept)?",
                ),
                default=False,
            )
        ):
            raise InstallError(
                t(
                    "El Caddyfile ya tiene otro dominio y no se cambio. Usa --sobrescribir o editalo.",
                    "The Caddyfile already has another domain and was not changed. Use --overwrite or edit it.",
                )
            )
        out["backups"].append(backup_existing(path))
        new, count = re.subn(
            r"^\S+(\s*\{)",
            lambda m: domain + m.group(1),
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count == 0:
            raise InstallError(
                t(
                    "No se reconocio el Caddyfile; editalo a mano.",
                    "The Caddyfile was not recognized; edit it by hand.",
                )
            )
    path.write_text(new, encoding="utf-8", newline="\n")


def offer_fernet_copy(cfg: dict, args, ask: Ask, kit_dir: Path) -> "Path | None":
    say("")
    info(
        t(
            "La clave que cifra los tokens de Google esta en .env.kit. SIN ELLA los datos guardados (y los respaldos) son ilegibles y habria que reconectar todos los buzones. Guarda una COPIA en otro medio (memoria USB, gestor de contrasenas de la organizacion). Nunca junto a los respaldos.",
            "The key that encrypts the Google tokens is in .env.kit. WITHOUT IT stored data (and backups) are unreadable and every mailbox would have to be reconnected. Save a COPY on another medium (USB drive, the organization's password manager). Never next to the backups.",
        )
    )
    target = args.key_copy
    if target is None:
        if ask.non_interactive or not ask.confirm(
            t(
                "Guardar ahora una copia de la clave en una ruta que elijas?",
                "Save a copy of the key now at a path you choose?",
            ),
            default=True,
        ):
            warn(
                t(
                    "No se guardo copia de la clave. Hazlo despues: es lo mas importante de la instalacion.",
                    "No key copy was saved. Do it later: it is the most important part of the install.",
                )
            )
            return None
        target = ask.text(
            t(
                "Ruta del archivo de copia (de preferencia en otro medio)",
                "Path of the copy file (preferably on another medium)",
            )
        )
    if not target:
        return None
    path = Path(target.strip().strip('"')).expanduser()
    if inside(path, kit_dir) or in_git_worktree(
        path.parent if path.parent.exists() else kit_dir
    ):
        raise InstallError(
            t(
                "La copia de la clave no puede quedar dentro de la carpeta del kit ni de un repositorio. Elige otro medio.",
                "The key copy cannot be inside the kit folder or a repository. Choose another medium.",
            )
        )
    if not path.parent.is_dir():
        raise InstallError(
            t(
                f"No existe la carpeta {path.parent}.",
                f"The folder {path.parent} does not exist.",
            )
        )
    if path.exists() and not (
        args.overwrite
        or ask.confirm(
            t(
                "Ese archivo ya existe. Reemplazarlo?",
                "That file already exists. Replace it?",
            ),
            default=False,
        )
    ):
        raise InstallError(
            t(
                "No se sobrescribio el archivo de copia de la clave.",
                "The key copy file was not overwritten.",
            )
        )
    write_private(path, "ATALAYA_FERNET_KEY=" + cfg["fernet"] + "\n")
    ok(t(f"Copia de la clave guardada en {path}", f"Key copy saved at {path}"))
    return path


def start_stack(kit_dir: Path, cfg: dict, app_port: int, timeout: float) -> None:
    profile = ["--profile", "tls"] if cfg["proxy"] == "caddy" else []
    info(
        t(
            "Construyendo la imagen (la primera vez tarda unos minutos)...",
            "Building the image (the first time takes a few minutes)...",
        )
    )
    build = docker_run([*("compose", *profile, "build")], kit_dir)
    if build.returncode != 0:
        raise InstallError(
            t(
                "`docker compose build` fallo. Ejecutalo a mano para ver el detalle: docker compose build",
                "`docker compose build` failed. Run it by hand to see the details: docker compose build",
            )
            + tail(build)
        )
    ok(t("Imagen construida", "Image built"))
    info(t("Arrancando los contenedores...", "Starting the containers..."))
    up = docker_run([*("compose", *profile, "up", "-d")], kit_dir)
    if up.returncode != 0:
        raise InstallError(
            t(
                "`docker compose up -d` fallo. Mira: docker compose logs atalaya",
                "`docker compose up -d` failed. Look: docker compose logs atalaya",
            )
            + tail(up)
        )
    ok(t("Contenedores en marcha", "Containers running"))
    info(
        t(
            f"Esperando a /health (hasta {int(timeout)} s)...",
            f"Waiting for /health (up to {int(timeout)} s)...",
        )
    )
    data = wait_for_health(app_port, timeout)
    if data is None:
        raise InstallError(
            t(
                "Atalaya no respondio en /health a tiempo. Mira el registro: docker compose logs atalaya (nunca muestra tus claves).",
                "Atalaya did not answer /health in time. Look at the log: docker compose logs atalaya (it never shows your keys).",
            )
        )
    if data.get("mode") != "gmail":
        raise InstallError(
            t(
                '/health dice un modo distinto de "gmail": no es la imagen del kit.',
                '/health reports a mode other than "gmail": this is not the kit image.',
            )
        )
    ok(
        t(
            f"/health responde (modo {data.get('mode')})",
            f"/health answers (mode {data.get('mode')})",
        )
    )


def tail(proc) -> str:
    """Ultimas lineas de la salida de docker (nunca contiene claves: no se las pasamos)."""
    lines = ((proc.stderr or "") + (proc.stdout or "")).strip().splitlines()[-5:]
    return ("\n    " + "\n    ".join(l[:200] for l in lines)) if lines else ""


def run_verifier(kit_dir: Path, app_port: int, offline: bool) -> int:
    script = Path(__file__).resolve().parent / "verificar_instalacion.py"
    if not script.is_file():
        warn(
            t(
                "No se encontro verificar_instalacion.py.",
                "verificar_instalacion.py was not found.",
            )
        )
        return 1
    if sys.version_info < VERIFIER_MIN_PY:
        warn(
            t(
                "El verificador necesita Python 3.11 o superior; se omite. Ejecutalo despues con una version mas nueva.",
                "The verifier needs Python 3.11 or newer; skipping it. Run it later with a newer version.",
            )
        )
        return 0
    cmd = [
        sys.executable,
        str(script),
        "--env-file",
        ENV_FILE,
        "--client-json",
        f"secrets/{GOOGLE_JSON_NAME}",
        "--lang",
        LANG,
        "--health-url",
        f"http://127.0.0.1:{app_port}",
    ]
    if offline:
        cmd.append("--sin-red")
    say("")
    proc = subprocess.run(cmd, cwd=str(kit_dir), check=False, timeout=300)  # nosec B603
    return proc.returncode


def summary(
    cfg: dict, kit_dir: Path, files: dict, key_copy: "Path | None", started: bool
) -> None:
    say("")
    say(paint(t("== Resumen ==", "== Summary =="), "1"))
    info(
        t(
            f"Direccion del panel : {cfg['base_url']}",
            f"Panel address      : {cfg['base_url']}",
        )
    )
    info(
        t(
            f"Administracion      : {', '.join(cfg['admins'])}",
            f"Administration     : {', '.join(cfg['admins'])}",
        )
    )
    info(
        t(
            f"Configuracion       : {files['env']} (permisos restringidos)",
            f"Configuration      : {files['env']} (restricted permissions)",
        )
    )
    for backup in files["backups"]:
        info(t(f"Copia anterior      : {backup}", f"Previous copy      : {backup}"))
    if files.get("win_note"):
        info(
            t(
                "En Windows los permisos se restringieron con icacls (mejor esfuerzo): revisa que solo tu usuario pueda leer .env.kit y secrets/.",
                "On Windows permissions were restricted with icacls (best effort): check that only your user can read .env.kit and secrets/.",
            )
        )
    info(
        t(
            f"Copia de la clave   : {key_copy if key_copy else 'NO guardada (hazlo cuanto antes)'}",
            f"Key copy           : {key_copy if key_copy else 'NOT saved (do it soon)'}",
        )
    )
    say("")
    info(
        t(
            "Respaldos (con el kit en marcha, desde la carpeta del kit):",
            "Backups (with the kit running, from the kit folder):",
        )
    )
    info("  tools/kit/respaldo.sh respaldos")
    info("  tools/kit/restaurar.sh respaldos/atalaya-AAAAMMDD-HHMMSS.db")
    say("")
    info(t("Siguientes pasos:", "Next steps:"))
    if not started:
        profile = " --profile tls" if cfg["proxy"] == "caddy" else ""
        info(
            t(
                f"  1. Arranca: docker compose{profile} up -d --build",
                f"  1. Start: docker compose{profile} up -d --build",
            )
        )
        info(
            t(
                "  2. Verifica: python3 tools/kit/instalar.py --verificar",
                "  2. Verify: python3 tools/kit/instalar.py --check",
            )
        )
        n = 3
    else:
        n = 1
    local = cfg["mode"] == "local"
    hint_es = " (escribe localhost, no 127.0.0.1)" if local else ""
    hint_en = " (type localhost, not 127.0.0.1)" if local else ""
    info(
        t(
            f"  {n}. Abre {cfg['base_url']}{hint_es} e inicia sesion con Google con una cuenta de administracion.",
            f"  {n}. Open {cfg['base_url']}{hint_en} and sign in with Google using an admin account.",
        )
    )
    info(
        t(
            f"  {n + 1}. En el panel crea una invitacion y envia el enlace (de un solo uso) a la persona responsable del primer buzon.",
            f"  {n + 1}. In the panel create an invitation and send the one-time link to the owner of the first mailbox.",
        )
    )


# ----------------------------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------------------------
def default_kit_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    env = os.environ.get
    p = argparse.ArgumentParser(
        prog="instalar.py",
        add_help=False,
        description="Asistente de instalacion del kit de Atalaya / Atalaya kit installation assistant.",
    )
    p.add_argument(
        "--ayuda",
        "--help",
        "-h",
        action="store_true",
        dest="help",
        help="muestra esta ayuda / shows this help",
    )
    p.add_argument(
        "--version", action="store_true", help="muestra la version / shows the version"
    )
    p.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="idioma / language (ATALAYA_LANG)",
    )
    p.add_argument(
        "--dir",
        default=None,
        help="carpeta del kit (por defecto la del repositorio) / kit folder",
    )
    p.add_argument(
        "--sin-arranque",
        "--no-start",
        action="store_true",
        dest="no_start",
        help="solo genera la configuracion / config only",
    )
    p.add_argument(
        "--verificar",
        "--check",
        action="store_true",
        dest="check",
        help="solo verifica / check only",
    )
    p.add_argument(
        "--si",
        "--yes",
        action="store_true",
        dest="yes",
        help="no pregunta nada: usa las banderas y variables / never asks",
    )
    p.add_argument(
        "--org",
        default=env("ATALAYA_ORG_NAME"),
        help="nombre de la organizacion (ATALAYA_ORG_NAME)",
    )
    p.add_argument(
        "--modo",
        "--mode",
        dest="mode",
        default=env("ATALAYA_INSTALL_MODE"),
        help="local | produccion (ATALAYA_INSTALL_MODE)",
    )
    p.add_argument(
        "--dominio",
        "--domain",
        dest="domain",
        default=env("ATALAYA_INSTALL_DOMAIN"),
        help="dominio HTTPS (ATALAYA_INSTALL_DOMAIN)",
    )
    p.add_argument(
        "--admin",
        default=env("ATALAYA_ADMIN_EMAILS"),
        help="correos de administracion (ATALAYA_ADMIN_EMAILS)",
    )
    p.add_argument(
        "--supervisores",
        "--supervisors",
        dest="supervisors",
        default=env("ATALAYA_SUPERVISOR_EMAILS"),
        help="correos de supervision (ATALAYA_SUPERVISOR_EMAILS)",
    )
    p.add_argument(
        "--google-json",
        default=env("ATALAYA_GOOGLE_JSON"),
        help="ruta del JSON de Google (ATALAYA_GOOGLE_JSON)",
    )
    p.add_argument(
        "--proxy",
        default=env("ATALAYA_INSTALL_PROXY"),
        help="caddy | propio (ATALAYA_INSTALL_PROXY)",
    )
    p.add_argument(
        "--saltos",
        "--hops",
        dest="hops",
        type=int,
        default=None,
        help="proxies propios delante / own proxies in front",
    )
    p.add_argument(
        "--ia",
        "--ai",
        dest="ai",
        action="store_true",
        default=None,
        help="activa la IA (la clave va en ANTHROPIC_API_KEY, nunca como bandera)",
    )
    p.add_argument(
        "--copia-clave",
        "--key-copy",
        dest="key_copy",
        default=None,
        help="ruta donde guardar una copia de la clave Fernet",
    )
    p.add_argument(
        "--sobrescribir",
        "--overwrite",
        action="store_true",
        dest="overwrite",
        help="reemplaza configuracion existente (con copia)",
    )
    p.add_argument(
        "--timeout", type=float, default=HEALTH_TIMEOUT, help=argparse.SUPPRESS
    )
    p.add_argument("--puerto-app", type=int, default=APP_PORT, help=argparse.SUPPRESS)
    p.add_argument("--verificador-sin-red", action="store_true", help=argparse.SUPPRESS)
    return p


def run(args) -> int:
    kit_dir = Path(args.dir).expanduser().resolve() if args.dir else default_kit_dir()
    ask = Ask(non_interactive=args.yes)
    app_port = args.puerto_app

    say(
        paint(
            t(
                f"Asistente de instalacion de Atalaya {VERSION}",
                f"Atalaya installation assistant {VERSION}",
            ),
            "1",
        )
    )
    info(
        t(
            "Todo ocurre en este equipo: no se descarga nada ni se envian datos a nadie.",
            "Everything happens on this machine: nothing is downloaded and no data is sent anywhere.",
        )
    )

    if args.check:
        total = 2
        step(1, total, t("Comprobaciones previas", "Preflight checks"))
        preflight(kit_dir, need_docker=False)
        step(2, total, t("Verificacion de la instalacion", "Installation verification"))
        if not (kit_dir / ENV_FILE).is_file():
            raise InstallError(
                t(
                    f"No hay {ENV_FILE}: ejecuta primero el asistente sin --verificar.",
                    f"There is no {ENV_FILE}: run the assistant first without --check.",
                )
            )
        return run_verifier(kit_dir, app_port, args.verificador_sin_red)

    total = 4 if args.no_start else 6
    step(1, total, t("Comprobaciones previas", "Preflight checks"))
    preflight(kit_dir, need_docker=not args.no_start)
    if not args.no_start:
        check_ports([app_port], app_port)

    step(2, total, t("Preguntas", "Questions"))
    cfg = gather(args, ask, kit_dir)

    step(3, total, t("Claves y archivos", "Keys and files"))
    if cfg["proxy"] == "caddy" and not args.no_start:
        check_ports([80, 443], app_port)
    files = write_files(cfg, kit_dir, args, ask)
    ok(t("Claves generadas (no se muestran)", "Keys generated (not shown)"))
    ok(
        t(
            f"{ENV_FILE} escrito con permisos restringidos",
            f"{ENV_FILE} written with restricted permissions",
        )
    )
    ok(t("JSON de Google copiado a secrets/", "Google JSON copied to secrets/"))
    key_copy = offer_fernet_copy(cfg, args, ask, kit_dir)

    started = False
    code = 0
    if not args.no_start:
        step(4, total, t("Arranque con Docker Compose", "Starting with Docker Compose"))
        start_stack(kit_dir, cfg, app_port, args.timeout)
        started = True
        step(5, total, t("Verificacion de la instalacion", "Installation verification"))
        code = run_verifier(kit_dir, app_port, args.verificador_sin_red)
    step(total, total, t("Resumen", "Summary"))
    summary(cfg, kit_dir, files, key_copy, started)
    if code != 0:
        raise InstallError(
            t(
                "El verificador encontro fallas (ver arriba).",
                "The verifier found failures (see above).",
            )
        )
    say("")
    say(paint(t("Listo.", "Done."), "1;32"))
    return 0


def main(argv: "list | None" = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(
                errors="replace"
            )  # una consola antigua no debe tumbar el asistente
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    set_lang(args.lang or os.environ.get("ATALAYA_LANG"))
    set_color()
    if args.help:
        say(
            t(
                "Uso: python3 tools/kit/instalar.py [opciones]\n\n"
                "  --lang es|en            idioma (o ATALAYA_LANG)\n"
                "  --dir CARPETA           carpeta del kit (por defecto, la del repositorio)\n"
                "  --sin-arranque          solo genera la configuracion, no arranca Docker\n"
                "  --verificar             solo verifica una instalacion existente\n"
                "  --si                    no pregunta: usa las banderas y variables de entorno\n"
                "  --sobrescribir          reemplaza configuracion existente (guarda copia con fecha)\n"
                "  --org --modo --dominio --admin --supervisores --google-json --proxy --saltos --ia --copia-clave\n"
                "                          respuestas para ejecutar sin preguntas (--modo local|produccion;\n"
                "                          --proxy caddy|propio). La clave de Anthropic solo por ANTHROPIC_API_KEY.\n"
                "  --version, --ayuda\n\nGuia: docs/INSTALACION.md",
                "Usage: python3 tools/kit/instalar.py [options]\n\n"
                "  --lang es|en            language (or ATALAYA_LANG)\n"
                "  --dir FOLDER            kit folder (default: the repository's)\n"
                "  --no-start              only generate the configuration, do not start Docker\n"
                "  --check                 only verify an existing installation\n"
                "  --yes                   never ask: use flags and environment variables\n"
                "  --overwrite             replace existing configuration (a dated backup is kept)\n"
                "  --org --mode --domain --admin --supervisors --google-json --proxy --hops --ai --key-copy\n"
                "                          answers for unattended runs (--mode local|production;\n"
                "                          --proxy caddy|own). The Anthropic key only via ANTHROPIC_API_KEY.\n"
                "  --version, --help\n\nGuide: docs/INSTALLATION.en.md",
            )
        )
        return 0
    if args.version:
        say(f"instalar.py {VERSION}")
        return 0
    try:
        return run(args)
    except InstallError as exc:
        say("")
        say(paint("ERROR: " + str(exc), "1;31"))
        return 1
    except KeyboardInterrupt:
        say("")
        say(
            t(
                "Cancelado. No se dejo nada a medias que impida repetir el asistente.",
                "Cancelled. Nothing was left half-done that prevents running the assistant again.",
            )
        )
        return 130
    except subprocess.TimeoutExpired:
        say(
            paint(
                t(
                    "ERROR: un comando tardo demasiado y se cancelo.",
                    "ERROR: a command took too long and was cancelled.",
                ),
                "1;31",
            )
        )
        return 1
    except (OSError, ValueError) as exc:
        say(
            paint(
                t(
                    f"ERROR: {type(exc).__name__}: no se pudo completar ({getattr(exc, 'strerror', None) or 'ver permisos y rutas'}).",
                    f"ERROR: {type(exc).__name__}: could not complete ({getattr(exc, 'strerror', None) or 'check permissions and paths'}).",
                ),
                "1;31",
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Verifica la instalacion del kit autoalojado de Atalaya. Solo biblioteca estandar.
Verifies a self-hosted Atalaya kit installation. Standard library only.

Uso / Usage (desde la carpeta del kit / from the kit folder):
    python3 tools/kit/verificar_instalacion.py --env-file .env.kit --client-json secrets/google_client.json
    ATALAYA_LANG=en python3 tools/kit/verificar_instalacion.py --env-file .env.kit      (English / --lang en)

Comprueba, sin imprimir NUNCA el valor de una variable (checks, never printing a variable's value):
  1. variables obligatorias / required variables;
  2. ATALAYA_BASE_URL https (o/or http://localhost para evaluar / for evaluation);
  3. JSON de cliente de Google valido, tipo "Aplicacion web", URI de redireccion = ATALAYA_BASE_URL;
  4. /health responde / answers {"mode": "gmail", "auth": true};
  5. desfase del reloj contra el encabezado Date de Google / clock skew against Google's Date header
     (un reloj atrasado ~1 s ya hizo fallar un primer inicio de sesion real).
Salida / Exit code: 0 sin FALLA (FAIL), 1 con alguna. Los AVISO (WARN) no fallan.
Idioma / Language: espanol por defecto; ingles con ATALAYA_LANG=en o --lang en.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

CALLBACK_PATH = "/auth/google/callback"
OK, AVISO, FALLA = "OK   ", "AVISO", "FALLA"  # niveles internos (claves estables)
SHOWN_EN = {OK: "OK   ", AVISO: "WARN ", FALLA: "FAIL "}
REQUIRED = [
    "ATALAYA_BASE_URL",
    "GOOGLE_CLIENT_SECRETS_FILE",
    "ATALAYA_FERNET_KEY",
    "ATALAYA_SESSION_SECRET",
]
DEFAULT_HOST_JSON = (
    "secrets/google_client.json"  # donde docker-compose.yml espera el JSON
)
CLOCK_URL = "https://www.googleapis.com/"
SKEW_WARN = 3.0  # segundos (el encabezado Date tiene resolucion de 1 s)
SKEW_FAIL = 30.0

LANG = "es"


def t(es: str, en: str) -> str:
    return en if LANG == "en" else es


def set_lang(value: str | None) -> None:
    global LANG
    LANG = "en" if (value or "").lower().startswith("en") else "es"


def parse_env_file(path: str) -> dict[str, str]:
    """Lee KEY=VALOR (ignora comentarios y lineas vacias). No ejecuta nada."""
    values: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check_variables(env: dict[str, str]) -> list[tuple[str, str]]:
    out = []
    for name in REQUIRED:
        if env.get(name):
            out.append((OK, t(f"{name} esta definida", f"{name} is set")))
        else:
            out.append((FALLA, t(f"Falta {name}", f"{name} is missing")))
    if env.get("ATALAYA_ADMIN_EMAILS") or env.get("ATALAYA_ADMIN_PASSWORD"):
        out.append(
            (
                OK,
                t(
                    "hay una forma de entrar al panel (ATALAYA_ADMIN_EMAILS o ATALAYA_ADMIN_PASSWORD)",
                    "there is a way into the panel (ATALAYA_ADMIN_EMAILS or ATALAYA_ADMIN_PASSWORD)",
                ),
            )
        )
    else:
        out.append(
            (
                FALLA,
                t(
                    "Falta ATALAYA_ADMIN_EMAILS (o ATALAYA_ADMIN_PASSWORD como respaldo)",
                    "ATALAYA_ADMIN_EMAILS is missing (or ATALAYA_ADMIN_PASSWORD as a fallback)",
                ),
            )
        )
    for name in ("ATALAYA_FERNET_KEY", "ATALAYA_SESSION_SECRET"):
        if "CAMBIAR" in env.get(name, ""):
            out.append(
                (
                    FALLA,
                    t(
                        f"{name} todavia tiene el valor de ejemplo (CAMBIAR_...)",
                        f"{name} still has the example value (CAMBIAR_...)",
                    ),
                )
            )
    if env.get("ATALAYA_SESSION_SECRET") and len(env["ATALAYA_SESSION_SECRET"]) < 32:
        out.append(
            (
                FALLA,
                t(
                    "ATALAYA_SESSION_SECRET tiene menos de 32 caracteres",
                    "ATALAYA_SESSION_SECRET is shorter than 32 characters",
                ),
            )
        )
    if env.get("ATALAYA_TRUST_PROXY") == "1":
        out.append(
            (
                AVISO,
                t(
                    "ATALAYA_TRUST_PROXY=1: asegurate de que SIEMPRE hay un proxy propio (Caddy) delante",
                    "ATALAYA_TRUST_PROXY=1: make sure your own proxy (Caddy) is ALWAYS in front",
                ),
            )
        )
    return out


def check_base_url(base: str) -> list[tuple[str, str]]:
    if not base:
        return []
    parts = urlparse(base)
    if parts.scheme == "https" and parts.hostname:
        return [(OK, t("ATALAYA_BASE_URL usa https", "ATALAYA_BASE_URL uses https"))]
    if parts.scheme == "http" and parts.hostname == "localhost":
        return [
            (
                AVISO,
                t(
                    "ATALAYA_BASE_URL es http://localhost: valido solo para evaluar en este equipo",
                    "ATALAYA_BASE_URL is http://localhost: valid only for evaluating on this machine",
                ),
            )
        ]
    if parts.scheme == "http" and parts.hostname == "127.0.0.1":
        return [
            (
                FALLA,
                t(
                    "usa http://localhost en lugar de 127.0.0.1 (Google y la app solo aceptan 'localhost')",
                    "use http://localhost instead of 127.0.0.1 (Google and the app only accept 'localhost')",
                ),
            )
        ]
    return [
        (
            FALLA,
            t(
                "ATALAYA_BASE_URL debe empezar por https:// (o http://localhost para evaluar)",
                "ATALAYA_BASE_URL must start with https:// (or http://localhost for evaluation)",
            ),
        )
    ]


def check_client_json(path: str, base: str) -> list[tuple[str, str]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [
            (
                FALLA,
                t(
                    f"No existe el JSON de cliente de Google: {path}",
                    f"The Google client JSON does not exist: {path}",
                ),
            )
        ]
    except (OSError, ValueError):
        return [
            (
                FALLA,
                t(
                    f"El archivo {path} no se puede leer o no es JSON valido",
                    f"The file {path} cannot be read or is not valid JSON",
                ),
            )
        ]
    web = data.get("web") if isinstance(data, dict) else None
    if (
        not isinstance(web, dict)
        or not web.get("client_id")
        or not web.get("client_secret")
    ):
        return [
            (
                FALLA,
                t(
                    'El JSON no es de un cliente "Aplicacion web" (falta la clave "web", client_id o client_secret)',
                    'The JSON is not from a "Web application" client (missing the "web" key, client_id or client_secret)',
                ),
            )
        ]
    out = [
        (
            OK,
            t(
                "el JSON de Google es de tipo Aplicacion web",
                "the Google JSON is of type Web application",
            ),
        )
    ]
    if base:
        expected = base.rstrip("/") + CALLBACK_PATH
        uris = web.get("redirect_uris") or []
        if expected in uris:
            out.append(
                (
                    OK,
                    t(
                        f"el JSON incluye la URI de redireccion {expected}",
                        f"the JSON includes the redirect URI {expected}",
                    ),
                )
            )
        else:
            out.append(
                (
                    FALLA,
                    t(
                        f"el JSON NO incluye la URI de redireccion {expected} (tiene {len(uris)} URI)",
                        f"the JSON does NOT include the redirect URI {expected} (it has {len(uris)} URI)",
                    ),
                )
            )
    return out


def check_health(base: str, timeout: float = 8.0) -> list[tuple[str, str]]:
    url = base.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(
            url, timeout=timeout
        ) as resp:  # URL del propio operador
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return [
            (
                FALLA,
                t(
                    f"{url} no responde ({type(exc).__name__}). Revisa 'docker compose ps' y los registros",
                    f"{url} does not answer ({type(exc).__name__}). Check 'docker compose ps' and the logs",
                ),
            )
        ]
    if body.get("mode") != "gmail":
        mode = body.get("mode")
        return [
            (
                FALLA,
                t(
                    f'/health dice mode="{mode}" (debe ser "gmail"): esa es la imagen de la demo',
                    f'/health says mode="{mode}" (it must be "gmail"): that is the demo image',
                ),
            )
        ]
    if body.get("auth") is not True:
        return [
            (
                FALLA,
                t(
                    "/health dice auth distinto de true: el panel no exige inicio de sesion",
                    "/health says auth is not true: the panel does not require login",
                ),
            )
        ]
    return [
        (
            OK,
            t(
                '/health responde mode "gmail" y auth true',
                '/health answers mode "gmail" and auth true',
            ),
        )
    ]


def check_clock(url: str = CLOCK_URL, timeout: float = 8.0) -> list[tuple[str, str]]:
    """Compara el reloj local con el encabezado Date del servidor (resolucion de 1 s)."""
    req = urllib.request.Request(url, method="HEAD")
    before = datetime.now(UTC)
    try:
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            headers = resp.headers
        except urllib.error.HTTPError as exc:  # un 404/405 tambien trae Date
            headers = exc.headers
    except (urllib.error.URLError, OSError) as exc:
        return [
            (
                AVISO,
                t(
                    f"no se pudo consultar la hora de {url} ({type(exc).__name__}): sin red de salida?",
                    f"could not query the time from {url} ({type(exc).__name__}): no outbound network?",
                ),
            )
        ]
    after = datetime.now(UTC)
    date = headers.get("Date")
    if not date:
        return [
            (
                AVISO,
                t(
                    "la respuesta no trae encabezado Date; no se pudo medir el reloj",
                    "the response has no Date header; the clock could not be measured",
                ),
            )
        ]
    server = parsedate_to_datetime(date)
    local = before + (after - before) / 2
    skew = abs((local - server).total_seconds())
    if skew > SKEW_FAIL:
        return [
            (
                FALLA,
                t(
                    f"el reloj de este equipo difiere ~{skew:.0f} s de Google: activa NTP (el inicio de sesion fallara)",
                    f"this machine's clock differs by ~{skew:.0f} s from Google: enable NTP (login will fail)",
                ),
            )
        ]
    if skew > SKEW_WARN:
        return [
            (
                AVISO,
                t(
                    f"el reloj difiere ~{skew:.1f} s de Google: sincroniza con NTP (la app tolera 30 s, pero conviene corregirlo)",
                    f"the clock differs by ~{skew:.1f} s from Google: sync with NTP (the app tolerates 30 s, but fix it)",
                ),
            )
        ]
    return [
        (
            OK,
            t(
                f"reloj sincronizado (diferencia ~{skew:.1f} s; el encabezado Date tiene resolucion de 1 s)",
                f"clock in sync (difference ~{skew:.1f} s; the Date header has 1 s resolution)",
            ),
        )
    ]


def run(
    env: dict[str, str],
    *,
    client_json: str | None,
    health_url: str | None,
    clock_url: str,
    skip_network: bool = False,
) -> int:
    results: list[tuple[str, str]] = []
    results += check_variables(env)
    base = env.get("ATALAYA_BASE_URL", "").rstrip("/")
    results += check_base_url(base)
    json_path = client_json or env.get("GOOGLE_CLIENT_SECRETS_FILE", "")
    if not client_json and json_path and not Path(json_path).exists():
        json_path = (
            DEFAULT_HOST_JSON  # la ruta del .env.kit es la de DENTRO del contenedor
        )
    if json_path:
        results += check_client_json(json_path, base)
    if not skip_network:
        target = health_url or base
        if target:
            results += check_health(target)
        results += check_clock(clock_url)
    for level, message in results:
        shown = SHOWN_EN[level] if LANG == "en" else level
        print(f"{shown}  {message}")
    fallas = sum(1 for level, _ in results if level == FALLA)
    avisos = sum(1 for level, _ in results if level == AVISO)
    print(
        "\n"
        + t(
            f"Resultado: {fallas} falla(s), {avisos} aviso(s).",
            f"Result: {fallas} failure(s), {avisos} warning(s).",
        )
    )
    return 1 if fallas else 0


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(
        description="Verifica la instalacion del kit de Atalaya / Verifies the Atalaya kit installation."
    )
    parser.add_argument(
        "--env-file",
        help=".env.kit (si falta, se usa el entorno / else the environment)",
    )
    parser.add_argument(
        "--client-json",
        help="ruta EN ESTE EQUIPO del JSON de Google / path ON THIS machine of the Google JSON",
    )
    parser.add_argument(
        "--health-url",
        help="direccion para probar /health (por defecto ATALAYA_BASE_URL)",
    )
    parser.add_argument(
        "--lang",
        choices=["es", "en"],
        help="idioma / language (por defecto ATALAYA_LANG o es)",
    )
    parser.add_argument("--clock-url", default=CLOCK_URL, help=argparse.SUPPRESS)
    parser.add_argument(
        "--sin-red",
        "--offline",
        action="store_true",
        dest="sin_red",
        help="omite /health y el reloj / skips /health and the clock",
    )
    args = parser.parse_args(argv)
    env = dict(os.environ)
    if args.env_file:
        try:
            env.update(parse_env_file(args.env_file))
        except OSError as exc:
            set_lang(args.lang or env.get("ATALAYA_LANG"))
            print(
                f"{FALLA}  "
                + t(
                    f"no se pudo leer {args.env_file}: {exc.strerror}",
                    f"could not read {args.env_file}: {exc.strerror}",
                )
            )
            return 1
    set_lang(args.lang or env.get("ATALAYA_LANG"))
    return run(
        env,
        client_json=args.client_json,
        health_url=args.health_url,
        clock_url=args.clock_url,
        skip_network=args.sin_red,
    )


if __name__ == "__main__":
    sys.exit(main())

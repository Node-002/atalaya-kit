"""Comprobacion previa del kit autoalojado (etapa `kit` de la imagen).

Se ejecuta ANTES de uvicorn: si falta algo obligatorio, el contenedor se niega a arrancar y
dice que variable corregir (en espanol; en ingles con ATALAYA_LANG=en). No imprime nunca el
valor de una variable secreta.
Uso: `python -m app.kit_preflight` (codigo de salida 0 = todo en orden).
"""

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet

CALLBACK_PATH = "/auth/google/callback"
LOCAL_HOSTS = {"localhost"}  # google_auth_oauthlib solo relaja http para localhost


def _is_local_http(url: str) -> bool:
    parts = urlparse(url)
    return parts.scheme == "http" and parts.hostname in LOCAL_HOSTS


def check(env: Mapping[str, str]) -> list[str]:
    """Lista de problemas (vacia = todo en orden). Solo lee `env`; no toca la red."""
    en = env.get("ATALAYA_LANG", "").lower().startswith("en")

    def t(es: str, english: str) -> str:
        return english if en else es

    problems: list[str] = []

    if env.get("ATALAYA_MODE", "") != "gmail":
        problems.append(
            t(
                "ATALAYA_MODE debe ser 'gmail' en el kit (la imagen lo fija; no lo cambies).",
                "ATALAYA_MODE must be 'gmail' in the kit (the image sets it; do not change it).",
            )
        )

    # --- URL publica: https obligatorio salvo localhost (evaluacion) ---
    base = env.get("ATALAYA_BASE_URL", "").strip().rstrip("/")
    if not base:
        problems.append(
            t(
                "Falta ATALAYA_BASE_URL (la direccion con la que se abre el panel, "
                "por ejemplo https://atalaya.tuorganizacion.org).",
                "ATALAYA_BASE_URL is missing (the address used to open the panel, "
                "for example https://atalaya.yourorganization.org).",
            )
        )
    elif not (base.startswith("https://") or _is_local_http(base)):
        problems.append(
            t(
                "ATALAYA_BASE_URL debe empezar por https:// (solo http://localhost "
                "se permite para evaluar en tu propio equipo).",
                "ATALAYA_BASE_URL must start with https:// (only http://localhost "
                "is allowed, for evaluating on your own machine).",
            )
        )

    # --- JSON de cliente de Google ---
    secrets_path = env.get("GOOGLE_CLIENT_SECRETS_FILE", "").strip()
    if not secrets_path:
        problems.append(
            t(
                "Falta GOOGLE_CLIENT_SECRETS_FILE (ruta del JSON del cliente OAuth de Google "
                "dentro del contenedor).",
                "GOOGLE_CLIENT_SECRETS_FILE is missing (path of the Google OAuth client JSON "
                "inside the container).",
            )
        )
    else:
        problems += _check_client_json(secrets_path, base, t)

    # --- Claves propias ---
    fernet = env.get("ATALAYA_FERNET_KEY", "")
    if not fernet:
        problems.append(
            t(
                "Falta ATALAYA_FERNET_KEY (clave que cifra los tokens de Google; "
                "ver docs/INSTALACION.md para generarla).",
                "ATALAYA_FERNET_KEY is missing (key that encrypts the Google tokens; "
                "see docs/INSTALLATION.en.md to generate it).",
            )
        )
    else:
        try:
            Fernet(fernet.encode())
        except (ValueError, TypeError):
            problems.append(
                t(
                    "ATALAYA_FERNET_KEY no es una clave Fernet valida (44 caracteres en base64).",
                    "ATALAYA_FERNET_KEY is not a valid Fernet key (44 base64 characters).",
                )
            )

    session = env.get("ATALAYA_SESSION_SECRET", "")
    if not session:
        problems.append(
            t(
                "Falta ATALAYA_SESSION_SECRET (clave aleatoria de al menos 32 caracteres).",
                "ATALAYA_SESSION_SECRET is missing (a random key of at least 32 characters).",
            )
        )
    elif len(session) < 32:
        problems.append(
            t(
                "ATALAYA_SESSION_SECRET debe tener al menos 32 caracteres.",
                "ATALAYA_SESSION_SECRET must be at least 32 characters long.",
            )
        )

    # --- Quien puede entrar al panel ---
    emails = env.get("ATALAYA_ADMIN_EMAILS", "").strip()
    password = env.get("ATALAYA_ADMIN_PASSWORD", "")
    if not emails and not password:
        problems.append(
            t(
                "Define ATALAYA_ADMIN_EMAILS (cuentas de Google que pueden entrar al panel) "
                "o, como respaldo, ATALAYA_ADMIN_PASSWORD (minimo 12 caracteres).",
                "Set ATALAYA_ADMIN_EMAILS (Google accounts allowed into the panel) "
                "or, as a fallback, ATALAYA_ADMIN_PASSWORD (at least 12 characters).",
            )
        )
    if password and len(password) < 12:
        problems.append(
            t(
                "ATALAYA_ADMIN_PASSWORD debe tener al menos 12 caracteres.",
                "ATALAYA_ADMIN_PASSWORD must be at least 12 characters long.",
            )
        )

    # --- Volumen de datos ---
    db_path = Path(env.get("ATALAYA_DB_PATH", "data/atalaya.db"))
    folder = db_path.parent if str(db_path.parent) else Path(".")
    if not folder.is_dir() or not os.access(folder, os.W_OK):
        problems.append(
            t(
                f"La carpeta de datos ({folder}) no existe o no se puede escribir: "
                "revisa que el volumen de Docker este montado y que pertenezca al usuario 10001.",
                f"The data folder ({folder}) does not exist or is not writable: "
                "check that the Docker volume is mounted and owned by user 10001.",
            )
        )
    return problems


def _check_client_json(path: str, base: str, t) -> list[str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [
            t(
                f"No existe el archivo GOOGLE_CLIENT_SECRETS_FILE ({path}): revisa el montaje.",
                f"The GOOGLE_CLIENT_SECRETS_FILE file ({path}) does not exist: check the mount.",
            )
        ]
    except (OSError, ValueError):
        return [
            t(
                f"El archivo {path} no se puede leer o no es un JSON valido.",
                f"The file {path} cannot be read or is not valid JSON.",
            )
        ]
    web = data.get("web") if isinstance(data, dict) else None
    if (
        not isinstance(web, dict)
        or not web.get("client_id")
        or not web.get("client_secret")
    ):
        return [
            t(
                "El JSON de Google no es de un cliente de tipo 'Aplicacion web' "
                '(debe tener la clave "web" con client_id y client_secret).',
                "The Google JSON is not from a 'Web application' client "
                '(it must have the "web" key with client_id and client_secret).',
            )
        ]
    if base:
        expected = base + CALLBACK_PATH
        if expected not in (web.get("redirect_uris") or []):
            return [
                t(
                    f"El JSON de Google no incluye la URI de redireccion {expected}. "
                    "Agregala en el cliente OAuth (Google Auth Platform > Clientes) "
                    "y vuelve a descargar el JSON.",
                    f"The Google JSON does not include the redirect URI {expected}. "
                    "Add it to the OAuth client (Google Auth Platform > Clients) "
                    "and download the JSON again.",
                )
            ]
    return []


def main() -> int:
    problems = check(os.environ)
    if not problems:
        return 0
    en = os.environ.get("ATALAYA_LANG", "").lower().startswith("en")
    if en:
        print(
            "Atalaya (kit) will NOT start: these settings are missing or wrong:",
            file=sys.stderr,
        )
    else:
        print(
            "Atalaya (kit) NO arranca: faltan o estan mal estos datos:", file=sys.stderr
        )
    for item in problems:
        print(f"  - {item}", file=sys.stderr)
    print(
        "Guide: docs/INSTALLATION.en.md" if en else "Guia: docs/INSTALACION.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

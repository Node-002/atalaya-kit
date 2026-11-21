"""Comprobacion previa del kit autoalojado (etapa `kit` de la imagen).

Se ejecuta ANTES de uvicorn: si falta algo obligatorio, el contenedor se niega a arrancar y
dice en espanol que variable corregir. No imprime nunca el valor de una variable secreta.
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
    problems: list[str] = []

    mode = env.get("ATALAYA_MODE", "")
    if mode != "gmail":
        problems.append(
            "ATALAYA_MODE debe ser 'gmail' en el kit (la imagen lo fija; no lo cambies)."
        )

    # --- URL publica: https obligatorio salvo localhost (evaluacion) ---
    base = env.get("ATALAYA_BASE_URL", "").strip().rstrip("/")
    if not base:
        problems.append(
            "Falta ATALAYA_BASE_URL (la direccion con la que se abre el panel, "
            "por ejemplo https://atalaya.tuorganizacion.org)."
        )
    elif not (base.startswith("https://") or _is_local_http(base)):
        problems.append(
            "ATALAYA_BASE_URL debe empezar por https:// (solo http://localhost "
            "se permite para evaluar en tu propio equipo)."
        )

    # --- JSON de cliente de Google ---
    secrets_path = env.get("GOOGLE_CLIENT_SECRETS_FILE", "").strip()
    if not secrets_path:
        problems.append(
            "Falta GOOGLE_CLIENT_SECRETS_FILE (ruta del JSON del cliente OAuth de Google "
            "dentro del contenedor)."
        )
    else:
        problems += _check_client_json(secrets_path, base)

    # --- Claves propias ---
    fernet = env.get("ATALAYA_FERNET_KEY", "")
    if not fernet:
        problems.append(
            "Falta ATALAYA_FERNET_KEY (clave que cifra los tokens de Google; "
            "ver docs/INSTALACION.md para generarla)."
        )
    else:
        try:
            Fernet(fernet.encode())
        except (ValueError, TypeError):
            problems.append(
                "ATALAYA_FERNET_KEY no es una clave Fernet valida (44 caracteres en base64)."
            )

    session = env.get("ATALAYA_SESSION_SECRET", "")
    if not session:
        problems.append(
            "Falta ATALAYA_SESSION_SECRET (clave aleatoria de al menos 32 caracteres)."
        )
    elif len(session) < 32:
        problems.append("ATALAYA_SESSION_SECRET debe tener al menos 32 caracteres.")

    # --- Quien puede entrar al panel ---
    emails = env.get("ATALAYA_ADMIN_EMAILS", "").strip()
    password = env.get("ATALAYA_ADMIN_PASSWORD", "")
    if not emails and not password:
        problems.append(
            "Define ATALAYA_ADMIN_EMAILS (cuentas de Google que pueden entrar al panel) "
            "o, como respaldo, ATALAYA_ADMIN_PASSWORD (minimo 12 caracteres)."
        )
    if password and len(password) < 12:
        problems.append("ATALAYA_ADMIN_PASSWORD debe tener al menos 12 caracteres.")

    # --- Volumen de datos ---
    db_path = Path(env.get("ATALAYA_DB_PATH", "data/atalaya.db"))
    folder = db_path.parent if str(db_path.parent) else Path(".")
    if not folder.is_dir() or not os.access(folder, os.W_OK):
        problems.append(
            f"La carpeta de datos ({folder}) no existe o no se puede escribir: "
            "revisa que el volumen de Docker este montado y que pertenezca al usuario 10001."
        )
    return problems


def _check_client_json(path: str, base: str) -> list[str]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [
            f"No existe el archivo GOOGLE_CLIENT_SECRETS_FILE ({path}): revisa el montaje."
        ]
    except (OSError, ValueError):
        return [f"El archivo {path} no se puede leer o no es un JSON valido."]
    web = data.get("web") if isinstance(data, dict) else None
    if (
        not isinstance(web, dict)
        or not web.get("client_id")
        or not web.get("client_secret")
    ):
        return [
            (
                "El JSON de Google no es de un cliente de tipo 'Aplicacion web' "
                '(debe tener la clave "web" con client_id y client_secret).'
            )
        ]
    if base:
        expected = base + CALLBACK_PATH
        if expected not in (web.get("redirect_uris") or []):
            return [
                (
                    f"El JSON de Google no incluye la URI de redireccion {expected}. "
                    "Agregala en el cliente OAuth (Google Auth Platform > Clientes) "
                    "y vuelve a descargar el JSON."
                )
            ]
    return []


def main() -> int:
    problems = check(os.environ)
    if not problems:
        return 0
    print("Atalaya (kit) NO arranca: faltan o estan mal estos datos:", file=sys.stderr)
    for item in problems:
        print(f"  - {item}", file=sys.stderr)
    print("Guia: docs/INSTALACION.md", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

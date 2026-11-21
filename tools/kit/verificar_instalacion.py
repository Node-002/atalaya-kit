#!/usr/bin/env python3
"""Verifica la instalacion del kit autoalojado de Atalaya. Solo biblioteca estandar.

Uso (desde la carpeta del kit, en el servidor o en tu equipo):
    python3 tools/kit/verificar_instalacion.py --env-file .env.kit --client-json secrets/google_client.json

Comprueba, sin imprimir NUNCA el valor de una variable:
  1. que existan las variables obligatorias;
  2. que ATALAYA_BASE_URL sea https (o http://localhost para evaluar);
  3. que el JSON de cliente de Google sea valido, de tipo "Aplicacion web", y que su URI de
     redireccion coincida con ATALAYA_BASE_URL;
  4. que /health responda {"mode": "gmail", "auth": true};
  5. el desfase del reloj contra el encabezado Date de Google (un reloj atrasado ~1 s ya
     hizo fallar un primer inicio de sesion real).
Codigo de salida: 0 si no hay FALLA (los AVISO no fallan), 1 si hay alguna FALLA.
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
OK, AVISO, FALLA = "OK   ", "AVISO", "FALLA"
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
SKEW_WARN = 3.0  # segundos
SKEW_FAIL = 30.0


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
            out.append((OK, f"{name} esta definida"))
        else:
            out.append((FALLA, f"Falta {name}"))
    if env.get("ATALAYA_ADMIN_EMAILS") or env.get("ATALAYA_ADMIN_PASSWORD"):
        out.append(
            (
                OK,
                "hay una forma de entrar al panel (ATALAYA_ADMIN_EMAILS o ATALAYA_ADMIN_PASSWORD)",
            )
        )
    else:
        out.append(
            (
                FALLA,
                "Falta ATALAYA_ADMIN_EMAILS (o ATALAYA_ADMIN_PASSWORD como respaldo)",
            )
        )
    for name in ("ATALAYA_FERNET_KEY", "ATALAYA_SESSION_SECRET"):
        value = env.get(name, "")
        if "CAMBIAR" in value:
            out.append(
                (FALLA, f"{name} todavia tiene el valor de ejemplo (CAMBIAR_...)")
            )
    if env.get("ATALAYA_SESSION_SECRET") and len(env["ATALAYA_SESSION_SECRET"]) < 32:
        out.append((FALLA, "ATALAYA_SESSION_SECRET tiene menos de 32 caracteres"))
    if env.get("ATALAYA_TRUST_PROXY") == "1":
        out.append(
            (
                AVISO,
                "ATALAYA_TRUST_PROXY=1: asegurate de que SIEMPRE hay un proxy propio (Caddy) delante",
            )
        )
    return out


def check_base_url(base: str) -> list[tuple[str, str]]:
    if not base:
        return []
    parts = urlparse(base)
    if parts.scheme == "https" and parts.hostname:
        return [(OK, "ATALAYA_BASE_URL usa https")]
    if parts.scheme == "http" and parts.hostname == "localhost":
        return [
            (
                AVISO,
                "ATALAYA_BASE_URL es http://localhost: valido solo para evaluar en este equipo",
            )
        ]
    if parts.scheme == "http" and parts.hostname == "127.0.0.1":
        return [
            (
                FALLA,
                "usa http://localhost en lugar de 127.0.0.1 (Google y la app solo aceptan 'localhost')",
            )
        ]
    return [
        (
            FALLA,
            "ATALAYA_BASE_URL debe empezar por https:// (o http://localhost para evaluar)",
        )
    ]


def check_client_json(path: str, base: str) -> list[tuple[str, str]]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [(FALLA, f"No existe el JSON de cliente de Google: {path}")]
    except (OSError, ValueError):
        return [(FALLA, f"El archivo {path} no se puede leer o no es JSON valido")]
    web = data.get("web") if isinstance(data, dict) else None
    if (
        not isinstance(web, dict)
        or not web.get("client_id")
        or not web.get("client_secret")
    ):
        return [
            (
                FALLA,
                'El JSON no es de un cliente "Aplicacion web" (falta la clave "web", client_id o client_secret)',
            )
        ]
    out = [(OK, "el JSON de Google es de tipo Aplicacion web")]
    if base:
        expected = base.rstrip("/") + CALLBACK_PATH
        uris = web.get("redirect_uris") or []
        if expected in uris:
            out.append((OK, f"el JSON incluye la URI de redireccion {expected}"))
        else:
            out.append(
                (
                    FALLA,
                    f"el JSON NO incluye la URI de redireccion {expected} (tiene {len(uris)} URI)",
                )
            )
    return out


def check_health(base: str, timeout: float = 8.0) -> list[tuple[str, str]]:
    url = base.rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return [
            (
                FALLA,
                f"{url} no responde ({type(exc).__name__}). Revisa 'docker compose ps' y los registros",
            )
        ]
    if body.get("mode") != "gmail":
        return [
            (
                FALLA,
                f'/health dice mode="{body.get("mode")}" (debe ser "gmail"): esa es la imagen de la demo',
            )
        ]
    if body.get("auth") is not True:
        return [
            (
                FALLA,
                "/health dice auth distinto de true: el panel no exige inicio de sesion",
            )
        ]
    return [(OK, '/health responde mode "gmail" y auth true')]


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
                f"no se pudo consultar la hora de {url} ({type(exc).__name__}): sin red de salida?",
            )
        ]
    after = datetime.now(UTC)
    date = headers.get("Date")
    if not date:
        return [
            (AVISO, "la respuesta no trae encabezado Date; no se pudo medir el reloj")
        ]
    server = parsedate_to_datetime(date)
    local = before + (after - before) / 2
    skew = abs((local - server).total_seconds())
    if skew > SKEW_FAIL:
        return [
            (
                FALLA,
                f"el reloj de este equipo difiere ~{skew:.0f} s de Google: activa NTP (el inicio de sesion fallara)",
            )
        ]
    if skew > SKEW_WARN:
        return [
            (
                AVISO,
                f"el reloj difiere ~{skew:.1f} s de Google: sincroniza con NTP (la app tolera 30 s, pero conviene corregirlo)",
            )
        ]
    return [
        (
            OK,
            f"reloj sincronizado (diferencia ~{skew:.1f} s; el encabezado Date tiene resolucion de 1 s)",
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
        print(f"{level}  {message}")
    fallas = sum(1 for level, _ in results if level == FALLA)
    avisos = sum(1 for level, _ in results if level == AVISO)
    print(f"\nResultado: {fallas} falla(s), {avisos} aviso(s).")
    return 1 if fallas else 0


def main(argv: list[str] | None = None) -> int:
    import os

    parser = argparse.ArgumentParser(
        description="Verifica la instalacion del kit de Atalaya."
    )
    parser.add_argument(
        "--env-file",
        help="archivo de variables (por ejemplo .env.kit); si falta, se usa el entorno",
    )
    parser.add_argument(
        "--client-json",
        help="ruta EN ESTE EQUIPO del JSON de Google (la del archivo apunta dentro del contenedor)",
    )
    parser.add_argument(
        "--health-url",
        help="direccion para probar /health (por defecto, ATALAYA_BASE_URL)",
    )
    parser.add_argument("--clock-url", default=CLOCK_URL, help=argparse.SUPPRESS)
    parser.add_argument(
        "--sin-red", action="store_true", help="omite /health y el reloj"
    )
    args = parser.parse_args(argv)
    env = dict(os.environ)
    if args.env_file:
        try:
            env.update(parse_env_file(args.env_file))
        except OSError as exc:
            print(f"{FALLA}  no se pudo leer {args.env_file}: {exc.strerror}")
            return 1
    return run(
        env,
        client_json=args.client_json,
        health_url=args.health_url,
        clock_url=args.clock_url,
        skip_network=args.sin_red,
    )


if __name__ == "__main__":
    sys.exit(main())

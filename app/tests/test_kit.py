"""Kit autoalojado: arranque en modo gmail, comprobacion previa, verificador y archivos de despliegue."""

import importlib.util
import json
import threading
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest
import yaml
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app import kit_preflight
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://atalaya.example.org"


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "verificar_instalacion", ROOT / "tools" / "kit" / "verificar_instalacion.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verificar = _load_verifier()


def _client_json(path: Path, redirect: str = BASE + "/auth/google/callback") -> Path:
    path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "fake.apps.googleusercontent.com",
                    "client_secret": "fake-not-real",
                    "redirect_uris": [redirect],
                }
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture()
def good_env(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    return {
        "ATALAYA_MODE": "gmail",
        "ATALAYA_BASE_URL": BASE,
        "GOOGLE_CLIENT_SECRETS_FILE": str(_client_json(tmp_path / "g.json")),
        "ATALAYA_FERNET_KEY": Fernet.generate_key().decode(),
        "ATALAYA_SESSION_SECRET": "s" * 48,
        "ATALAYA_ADMIN_EMAILS": "admin@example.org",
        "ATALAYA_DB_PATH": str(data / "atalaya.db"),
    }


# --- Comprobacion previa (lo que ejecuta la imagen `kit` antes de uvicorn) -----------------------
def test_preflight_accepts_a_complete_setup(good_env):
    assert kit_preflight.check(good_env) == []


@pytest.mark.parametrize(
    "missing",
    [
        "ATALAYA_BASE_URL",
        "GOOGLE_CLIENT_SECRETS_FILE",
        "ATALAYA_FERNET_KEY",
        "ATALAYA_SESSION_SECRET",
        "ATALAYA_ADMIN_EMAILS",
    ],
)
def test_preflight_names_each_missing_variable(good_env, missing):
    del good_env[missing]
    problems = kit_preflight.check(good_env)
    assert problems, "debia fallar"
    if missing == "ATALAYA_ADMIN_EMAILS":
        assert any(
            "ATALAYA_ADMIN_EMAILS" in p and "ATALAYA_ADMIN_PASSWORD" in p
            for p in problems
        )
    else:
        assert any(missing in p for p in problems)


def test_admin_password_is_an_accepted_fallback(good_env):
    del good_env["ATALAYA_ADMIN_EMAILS"]
    good_env["ATALAYA_ADMIN_PASSWORD"] = "una-contrasena-larga-1"
    assert kit_preflight.check(good_env) == []
    good_env["ATALAYA_ADMIN_PASSWORD"] = "corta"
    assert any("12 caracteres" in p for p in kit_preflight.check(good_env))


def test_preflight_rejects_http_and_wrong_redirect(good_env, tmp_path):
    good_env["ATALAYA_BASE_URL"] = "http://atalaya.example.org"
    assert any("https://" in p for p in kit_preflight.check(good_env))
    good_env["ATALAYA_BASE_URL"] = (
        "http://localhost:8000"  # evaluacion: permitido salvo la URI
    )
    problems = kit_preflight.check(good_env)
    assert not any("https://" in p for p in problems)
    assert any("redireccion" in p for p in problems)  # el JSON apunta a otro dominio


def test_preflight_rejects_bad_keys_and_bad_json(good_env, tmp_path):
    good_env["ATALAYA_FERNET_KEY"] = "no-es-una-clave"
    good_env["ATALAYA_SESSION_SECRET"] = "corta"
    bad = tmp_path / "mal.json"
    bad.write_text('{"installed": {"client_id": "x"}}', encoding="utf-8")
    good_env["GOOGLE_CLIENT_SECRETS_FILE"] = str(bad)
    text = " ".join(kit_preflight.check(good_env))
    assert "Fernet" in text and "32 caracteres" in text and "Aplicacion web" in text


def test_preflight_message_never_prints_secret_values(good_env, capsys, monkeypatch):
    good_env["ATALAYA_SESSION_SECRET"] = "x-secreto-corto"
    for key, value in good_env.items():
        monkeypatch.setenv(key, value)
    assert kit_preflight.main() == 1
    err = capsys.readouterr().err
    assert "x-secreto-corto" not in err and good_env["ATALAYA_FERNET_KEY"] not in err


def test_preflight_reports_unwritable_data_folder(good_env, tmp_path):
    good_env["ATALAYA_DB_PATH"] = str(tmp_path / "no-existe" / "a.db")
    assert any("carpeta de datos" in p for p in kit_preflight.check(good_env))


# --- La propia aplicacion tambien se niega a arrancar en modo gmail sin lo obligatorio ------------
@pytest.mark.parametrize(
    "missing",
    ["GOOGLE_CLIENT_SECRETS_FILE", "ATALAYA_FERNET_KEY", "ATALAYA_SESSION_SECRET"],
)
def test_gmail_mode_refuses_to_start_when_a_required_variable_is_missing(
    good_env, monkeypatch, missing
):
    for key, value in good_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv(missing)
    with pytest.raises(RuntimeError, match=missing):
        create_app()


def test_gmail_mode_refuses_to_start_without_any_admin_access(good_env, monkeypatch):
    for key, value in good_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ATALAYA_ADMIN_EMAILS")
    with pytest.raises(RuntimeError, match="ATALAYA_ADMIN_EMAILS"):
        create_app()


def test_demo_mode_ignores_google_variables(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", "/no/existe.json")
    monkeypatch.setenv("ATALAYA_FERNET_KEY", "basura")
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", "alguien@example.org")
    body = TestClient(create_app()).get("/health").json()
    assert body == {"status": "ok", "mode": "demo", "auth": False}


# --- verificar_instalacion.py -----------------------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    health: ClassVar[dict] = {"status": "ok", "mode": "gmail", "auth": True}
    skew_seconds = 0

    def date_time_string(self, timestamp=None):  # send_response() ya agrega el Date
        when = datetime.now(UTC) + timedelta(seconds=self.skew_seconds)
        return format_datetime(when, usegmt=True)

    def _send(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        self._send(json.dumps(self.health).encode())

    do_HEAD = do_GET

    def log_message(self, *args):  # silencio
        pass


@pytest.fixture()
def server():
    handler = type(
        "H", (_Handler,), {"health": dict(_Handler.health), "skew_seconds": 0}
    )
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield handler, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _levels(results):
    return [level for level, _ in results]


def test_verifier_health_requires_gmail_mode_and_auth(server):
    handler, url = server
    assert _levels(verificar.check_health(url)) == [verificar.OK]
    handler.health = {"status": "ok", "mode": "demo", "auth": False}
    results = verificar.check_health(url)
    assert _levels(results) == [verificar.FALLA] and "demo" in results[0][1]
    handler.health = {"status": "ok", "mode": "gmail", "auth": False}
    assert _levels(verificar.check_health(url)) == [verificar.FALLA]
    assert _levels(verificar.check_health("http://127.0.0.1:9", timeout=1)) == [
        verificar.FALLA
    ]


def test_verifier_clock_skew_levels(server):
    handler, url = server
    assert _levels(verificar.check_clock(url)) == [verificar.OK]
    handler.skew_seconds = 10
    assert _levels(verificar.check_clock(url)) == [verificar.AVISO]
    handler.skew_seconds = 120
    assert _levels(verificar.check_clock(url)) == [verificar.FALLA]
    assert _levels(verificar.check_clock("http://127.0.0.1:9/", timeout=1)) == [
        verificar.AVISO
    ]


def test_verifier_client_json_cases(tmp_path):
    good = _client_json(tmp_path / "a.json")
    assert verificar.FALLA not in _levels(verificar.check_client_json(str(good), BASE))
    other = _client_json(
        tmp_path / "b.json", "https://otro.example.org/auth/google/callback"
    )
    assert verificar.FALLA in _levels(verificar.check_client_json(str(other), BASE))
    desktop = tmp_path / "c.json"
    desktop.write_text('{"installed": {}}', encoding="utf-8")
    assert verificar.FALLA in _levels(verificar.check_client_json(str(desktop), BASE))
    assert verificar.FALLA in _levels(
        verificar.check_client_json(str(tmp_path / "nada.json"), BASE)
    )
    broken = tmp_path / "d.json"
    broken.write_text("{no es json", encoding="utf-8")
    assert verificar.FALLA in _levels(verificar.check_client_json(str(broken), BASE))


def test_verifier_base_url_cases():
    assert _levels(verificar.check_base_url("https://a.example.org")) == [verificar.OK]
    assert _levels(verificar.check_base_url("http://localhost:8000")) == [
        verificar.AVISO
    ]
    assert _levels(verificar.check_base_url("http://a.example.org")) == [
        verificar.FALLA
    ]
    assert _levels(verificar.check_base_url("http://127.0.0.1:8000")) == [
        verificar.FALLA
    ]


def test_verifier_variables_never_print_values_and_flag_examples():
    env = {
        "ATALAYA_BASE_URL": BASE,
        "GOOGLE_CLIENT_SECRETS_FILE": "x",
        "ATALAYA_FERNET_KEY": "CAMBIAR_CLAVE_FERNET",
        "ATALAYA_SESSION_SECRET": "s" * 40,
    }
    results = verificar.check_variables(env)
    text = " ".join(m for _, m in results)
    assert "CAMBIAR_CLAVE_FERNET" not in text and "s" * 40 not in text
    assert (
        verificar.FALLA,
        "ATALAYA_FERNET_KEY todavia tiene el valor de ejemplo (CAMBIAR_...)",
    ) in results
    assert any(
        level == verificar.FALLA and "ATALAYA_ADMIN_EMAILS" in m for level, m in results
    )


def test_verifier_run_end_to_end(server, good_env, tmp_path, capsys):
    handler, url = server
    env = dict(good_env)
    env["ATALAYA_BASE_URL"] = BASE  # la URI del JSON coincide con esta direccion
    code = verificar.run(env, client_json=None, health_url=url, clock_url=url)
    out = capsys.readouterr().out
    assert code == 0, out
    assert good_env["ATALAYA_FERNET_KEY"] not in out
    handler.health = {"status": "ok", "mode": "demo", "auth": False}
    assert verificar.run(env, client_json=None, health_url=url, clock_url=url) == 1


def test_verifier_env_file_parser(tmp_path):
    f = tmp_path / ".env.kit"
    f.write_text('# c\nA=1\n\nB="dos"\nC=x=y\n', encoding="utf-8")
    assert verificar.parse_env_file(str(f)) == {"A": "1", "B": "dos", "C": "x=y"}


# --- Archivos de despliegue ---------------------------------------------------------------------
def _stages(text: str) -> dict[str, str]:
    """Nombre de etapa -> texto de esa etapa."""
    out, name = {}, None
    for line in text.splitlines():
        if line.startswith("FROM "):
            name = line.split(" AS ")[-1].strip()
            out[name] = ""
        if name:
            out[name] += line + "\n"
    return out


def test_dockerfile_stages_demo_last_and_kit_does_not_force_demo():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    stages = _stages(text)
    assert list(stages) == ["base", "kit", "demo"], (
        "demo debe ser la ultima etapa (Render)"
    )
    assert (
        "ATALAYA_MODE=demo" in stages["demo"]
        and "ATALAYA_MODE=demo" not in stages["kit"]
    )
    assert "ATALAYA_MODE=gmail" in stages["kit"]
    for name in ("kit", "demo"):
        assert "USER atalaya" in stages[name]
        assert (
            "--no-server-header" in stages[name]
            and "--no-proxy-headers" in stages[name]
        )
    assert "app.kit_preflight" in stages["kit"]
    assert "ATALAYA_MODE=demo" not in stages["base"]
    assert "HEALTHCHECK" in stages["base"]


def test_compose_kit_is_hardened_and_caddy_is_optional():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    app = compose["services"]["atalaya"]
    assert app["build"]["target"] == "kit"
    assert app["read_only"] is True
    assert (
        "127.0.0.1:8000:8000" in app["ports"]
    )  # nunca expuesto directamente a internet
    assert any(v.endswith(":/srv/data") for v in app["volumes"])
    assert any(v.endswith(":ro") and "google_client.json" in v for v in app["volumes"])
    assert app["env_file"] == ".env.kit" and app["restart"] == "unless-stopped"
    assert compose["services"]["caddy"]["profiles"] == ["tls"]
    assert "demo" not in json.dumps(compose)


def test_kit_example_env_has_placeholders_and_no_real_values():
    text = (ROOT / ".env.kit.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(("ATALAYA_FERNET_KEY=", "ATALAYA_SESSION_SECRET=")):
            assert "CAMBIAR_" in line
    assert "ATALAYA_MODE" not in text.replace("# ", "")  # el modo lo fija la imagen
    assert "sk-ant-" not in text
    assert (ROOT / "Caddyfile").read_text(encoding="utf-8").count(
        "reverse_proxy atalaya:8000"
    ) == 1


# --- Ingles opcional (ATALAYA_LANG=en); espanol por defecto ----------------------------------------
@pytest.fixture()
def spanish_after():
    yield
    verificar.set_lang("es")


@pytest.mark.parametrize(
    "missing",
    [
        "ATALAYA_BASE_URL",
        "GOOGLE_CLIENT_SECRETS_FILE",
        "ATALAYA_FERNET_KEY",
        "ATALAYA_SESSION_SECRET",
        "ATALAYA_ADMIN_EMAILS",
    ],
)
def test_preflight_messages_in_english_and_spanish(good_env, missing):
    del good_env[missing]
    spanish = " ".join(kit_preflight.check(good_env))
    english = " ".join(kit_preflight.check({**good_env, "ATALAYA_LANG": "en"}))
    assert missing in spanish and missing in english
    assert ("is missing" in english) or ("Set ATALAYA_ADMIN_EMAILS" in english)
    assert "Falta" in spanish or "Define" in spanish
    assert "Falta" not in english and "Define" not in english


def test_preflight_cli_prints_english_when_asked(good_env, capsys, monkeypatch):
    del good_env["ATALAYA_FERNET_KEY"]
    for key, value in good_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("ATALAYA_LANG", "en")
    assert kit_preflight.main() == 1
    err = capsys.readouterr().err
    assert (
        "will NOT start" in err
        and "INSTALLATION.en.md" in err
        and "NO arranca" not in err
    )
    monkeypatch.delenv("ATALAYA_LANG")
    assert kit_preflight.main() == 1
    assert "NO arranca" in capsys.readouterr().err


def test_verifier_output_in_english(server, good_env, capsys, spanish_after):
    _handler, url = server
    verificar.set_lang("en")
    env = {**good_env, "ATALAYA_FERNET_KEY": "CAMBIAR_CLAVE_FERNET"}
    assert verificar.run(env, client_json=None, health_url=url, clock_url=url) == 1
    out = capsys.readouterr().out
    assert (
        "FAIL" in out
        and "still has the example value" in out
        and "Result: 1 failure(s)" in out
    )
    assert "FALLA" not in out and "Resultado" not in out


def test_verifier_cli_lang_flag_and_env(tmp_path, capsys, monkeypatch, spanish_after):
    envfile = tmp_path / ".env.kit"
    envfile.write_text("ATALAYA_BASE_URL=http://a.example.org\n", encoding="utf-8")
    assert (
        verificar.main(["--env-file", str(envfile), "--offline", "--lang", "en"]) == 1
    )
    assert "must start with https://" in capsys.readouterr().out
    monkeypatch.setenv("ATALAYA_LANG", "en")
    assert verificar.main(["--env-file", str(envfile), "--sin-red"]) == 1
    assert "is missing" in capsys.readouterr().out
    monkeypatch.delenv("ATALAYA_LANG")
    assert verificar.main(["--env-file", str(envfile), "--sin-red"]) == 1
    assert "Falta" in capsys.readouterr().out


def test_english_documents_exist_and_keep_the_honest_warnings():
    docs = ROOT / "docs"
    guide_es = (docs / "INSTALACION.md").read_text(encoding="utf-8")
    guide_en = (docs / "INSTALLATION.en.md").read_text(encoding="utf-8")
    listing = (docs / "MARKETPLACE_LISTING.en.md").read_text(encoding="utf-8")
    readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    # misma estructura: mismo numero de secciones
    sep = chr(10) + "## "
    assert guide_en.count(sep) == guide_es.count(sep)
    for text in (guide_en, listing, readme_en):
        assert (
            "not verified with a real" in text.lower()
            or "not been verified with a real" in text.lower()
        )
    assert "to be defined" in listing and "HYPOTHESIS" in listing
    assert "AGPL-3.0" in listing and "Microsoft 365" in listing


def test_verifier_only_accepts_web_addresses_for_the_health_check():
    # urllib abre tambien file:// y ftp://: la direccion del operador debe ser http(s)
    for direccion in ("file:///etc/passwd", "ftp://servidor", "gopher://x"):
        resultado = verificar.check_health(direccion)
        assert resultado[0][0] == verificar.FALLA
        assert "http" in resultado[0][1]

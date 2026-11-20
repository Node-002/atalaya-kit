"""Revision de seguridad del panel de administracion e invitaciones."""

import logging
import re
import secrets
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.logsafe import RedactSecrets, redact
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}
STATIC = Path(__file__).resolve().parents[1] / "static"
PASSWORD = "t-" + secrets.token_urlsafe(18)
WRONG = "w-" + secrets.token_urlsafe(
    12
)  # contrasena incorrecta, generada en cada corrida


# --- 1. Ningun secreto llega al navegador ---------------------------------------------
def test_static_files_contain_no_secrets_or_env_names():
    suspicious = re.compile(
        r"(ATALAYA_[A-Z_]+|sk-ant-|client_secret|GOCSPX|AIza|refresh_token|BEGIN [A-Z ]*PRIVATE KEY)"
    )
    for path in STATIC.rglob("*"):
        if path.is_file():
            assert not suspicious.search(path.read_text(encoding="utf-8")), path.name


@pytest.fixture()
def gmail_client(tmp_path, monkeypatch):
    secrets_file = tmp_path / "client.json"
    secrets_file.write_text(
        '{"web": {"client_id": "x.apps.googleusercontent.com", "client_secret": "fake-not-real",'
        ' "auth_uri": "https://accounts.google.com/o/oauth2/auth",'
        ' "token_uri": "https://oauth2.googleapis.com/token",'
        ' "redirect_uris": ["http://localhost:8000/auth/google/callback"]}}'
    )
    monkeypatch.setenv("ATALAYA_MODE", "gmail")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", str(secrets_file))
    monkeypatch.setenv("ATALAYA_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ATALAYA_DB_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("ATALAYA_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("ATALAYA_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("ATALAYA_LOGIN_DELAY", "0")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def test_no_response_ever_echoes_the_password_or_secrets(gmail_client):
    bad = gmail_client.post("/auth/admin/login", json={"password": WRONG})
    good = gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    pages = [
        bad.text,
        good.text,
        gmail_client.get("/api/me").text,
        gmail_client.get("/health").text,
        gmail_client.get("/login").text,
        gmail_client.get("/api/audit").text,
    ]
    for body in pages:
        assert (
            PASSWORD not in body and "fake-not-real" not in body and WRONG not in body
        )


def test_audit_log_never_stores_attempted_passwords(gmail_client):
    gmail_client.post("/auth/admin/login", json={"password": "intento-secreto-999"})
    gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    assert "intento-secreto-999" not in gmail_client.get("/api/audit").text
    assert PASSWORD not in gmail_client.get("/api/audit").text


# --- 2. Limite de intentos -----------------------------------------------------------
def test_lockout_applies_after_five_failures_and_blocks_even_the_right_password(
    gmail_client,
):
    for _ in range(5):
        assert (
            gmail_client.post(
                "/auth/admin/login", json={"password": "mala-clave-1"}
            ).status_code
            == 401
        )
    assert (
        gmail_client.post("/auth/admin/login", json={"password": PASSWORD}).status_code
        == 429
    )


def test_malformed_login_bodies_count_as_failures_and_do_not_crash(gmail_client):
    for body in ("no es json", '["lista"]', '{"password": 123}', "{}"):
        resp = gmail_client.post(
            "/auth/admin/login",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401


# --- 3. Sesiones -----------------------------------------------------------------------
def test_logout_invalidates_a_copied_session_cookie(gmail_client):
    gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    stolen = gmail_client.cookies.get("atalaya_session")
    assert gmail_client.get("/api/alerts").status_code == 200
    gmail_client.post("/auth/admin/logout")
    attacker = TestClient(gmail_client.app, follow_redirects=False)
    attacker.cookies.set("atalaya_session", stolen)
    assert (
        attacker.get("/api/alerts").status_code == 401
    )  # la cookie copiada ya no sirve


def test_each_login_creates_an_independent_session(gmail_client):
    gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    first = gmail_client.cookies.get("atalaya_session")
    gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    assert gmail_client.cookies.get("atalaya_session") != first


# --- 4. Tokens y codigos fuera de los registros ---------------------------------------
def test_redact_hides_invite_tokens_codes_and_state():
    line = '"GET /invite/AbC123_-xyzSECRETO HTTP/1.1"'
    assert "SECRETO" not in redact(line)
    cb = '"GET /auth/google/callback?code=4/0AXYZ-secreto&state=ESTADO123 HTTP/1.1"'
    out = redact(cb)
    assert "secreto" not in out and "ESTADO123" not in out
    api = '"GET /api/public/invite/TOKENLARGO_abc HTTP/1.1"'
    assert "TOKENLARGO" not in redact(api)
    assert "/auth/google/login?invite=[oculto]&consent=1" in redact(
        "/auth/google/login?invite=TOK&consent=1"
    )


def test_access_log_filter_redacts_uvicorn_style_records():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "x",
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5", "GET", "/invite/TOKEN_SECRETO_123", "1.1", 200),
        None,
    )
    assert RedactSecrets().filter(record) is True
    assert "TOKEN_SECRETO_123" not in record.getMessage()
    assert "[oculto]" in record.getMessage()


def test_normal_paths_are_not_altered():
    assert redact("/api/alerts?mailbox_id=mb_1") == "/api/alerts?mailbox_id=mb_1"


# --- 5. Cabeceras -------------------------------------------------------------------------
def test_security_headers_and_no_store_on_api(gmail_client):
    gmail_client.post("/auth/admin/login", json={"password": PASSWORD})
    resp = gmail_client.get("/api/alerts")
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]

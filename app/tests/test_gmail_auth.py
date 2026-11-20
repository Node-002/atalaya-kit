import base64
import json
import secrets

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.gmail import parse_message
from app.tokens import TokenVault

CSRF = {"X-Requested-With": "atalaya"}
ADMIN_PASSWORD = "t-" + secrets.token_urlsafe(18)  # generada en cada corrida


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


# --- Tokens cifrados (archivo) -----------------------------------------------------
def test_vault_roundtrip_and_ciphertext(tmp_path):
    key = Fernet.generate_key().decode()
    vault = TokenVault(tmp_path / "t.enc", key)
    vault.save({"token": "abc123", "refresh_token": "zzz-secret"})
    raw = (tmp_path / "t.enc").read_bytes()
    assert b"zzz-secret" not in raw and b"abc123" not in raw
    assert vault.load() == {"token": "abc123", "refresh_token": "zzz-secret"}


def test_vault_wrong_key_returns_none(tmp_path):
    TokenVault(tmp_path / "t.enc", Fernet.generate_key().decode()).save({"token": "x"})
    other = TokenVault(tmp_path / "t.enc", Fernet.generate_key().decode())
    assert other.load() is None


def test_vault_delete(tmp_path):
    vault = TokenVault(tmp_path / "t.enc", Fernet.generate_key().decode())
    vault.save({"token": "x"})
    vault.delete()
    assert vault.load() is None


# --- Lectura de mensajes de Gmail ---------------------------------------------------
def test_parse_message_plain_text():
    raw = {
        "id": "m1",
        "internalDate": "1763650800000",
        "payload": {
            "headers": [
                {"name": "From", "value": "Banco <a@banco-falso.com>"},
                {"name": "Reply-To", "value": "x@otro.net"},
                {"name": "Subject", "value": "Urgente"},
                {"name": "Authentication-Results", "value": "mx.google.com; spf=fail"},
            ],
            "mimeType": "text/plain",
            "body": {"data": _b64("Entre a http://bit.ly/abc ahora")},
        },
    }
    msg = parse_message(raw)
    assert msg.ref == "m1"
    assert msg.reply_to == "x@otro.net"
    assert "spf=fail" in msg.headers["Authentication-Results"]
    assert msg.links == ["http://bit.ly/abc"]


def test_parse_message_html_only_is_stripped_and_trimmed():
    html = "<p>Hola</p>" + "x" * 10000
    raw = {
        "id": "m2",
        "internalDate": "0",
        "payload": {
            "headers": [],
            "mimeType": "multipart/alternative",
            "parts": [{"mimeType": "text/html", "body": {"data": _b64(html)}}],
        },
    }
    msg = parse_message(raw)
    assert "<p>" not in msg.body
    assert len(msg.body) <= 4000


# --- Modo conectado: administracion + invitaciones (sin red) --------------------
@pytest.fixture()
def gmail_env(tmp_path, monkeypatch):
    secrets = tmp_path / "client.json"
    secrets.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "fake-id.apps.googleusercontent.com",
                    "client_secret": "fake-not-real",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8000/auth/google/callback"],
                }
            }
        )
    )
    monkeypatch.setenv("ATALAYA_MODE", "gmail")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", str(secrets))
    monkeypatch.setenv("ATALAYA_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ATALAYA_DB_PATH", str(tmp_path / "atalaya.db"))
    monkeypatch.setenv("ATALAYA_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("ATALAYA_SESSION_SECRET", "s" * 48)
    return tmp_path


@pytest.fixture()
def gmail_client(gmail_env):
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


@pytest.fixture()
def admin_client(gmail_client):
    resp = gmail_client.post("/auth/admin/login", json={"password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    return gmail_client


def test_gmail_mode_refuses_to_start_without_admin_password(gmail_env, monkeypatch):
    monkeypatch.delenv("ATALAYA_ADMIN_PASSWORD")
    with pytest.raises(RuntimeError, match="ATALAYA_ADMIN_PASSWORD"):
        create_app()


def test_gmail_mode_refuses_weak_admin_password(gmail_env, monkeypatch):
    monkeypatch.setenv("ATALAYA_ADMIN_PASSWORD", "corta")
    with pytest.raises(RuntimeError, match="al menos"):
        create_app()


def test_panel_api_requires_admin_session(gmail_client):
    assert gmail_client.get("/api/alerts").status_code == 401
    assert gmail_client.get("/api/coverage").status_code == 401
    assert gmail_client.post("/api/invites", json={"label": "x"}).status_code == 401
    # la pagina principal redirige al login
    assert gmail_client.get("/").status_code in (302, 307)


def test_admin_login_wrong_password_and_rate_limit(gmail_client):
    for _ in range(5):
        assert (
            gmail_client.post(
                "/auth/admin/login", json={"password": "mala-clave"}
            ).status_code
            == 401
        )
    assert (
        gmail_client.post(
            "/auth/admin/login", json={"password": ADMIN_PASSWORD}
        ).status_code
        == 429
    )


def test_session_cookie_is_httponly_and_lax(gmail_client):
    resp = gmail_client.post("/auth/admin/login", json={"password": ADMIN_PASSWORD})
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_forged_session_cookie_is_rejected(gmail_client):
    gmail_client.cookies.set("atalaya_session", "falsa.firma.invalida")
    assert gmail_client.get("/api/alerts").status_code == 401


def test_admin_can_list_and_start_empty(admin_client):
    assert admin_client.get("/api/alerts").json() == []
    assert admin_client.get("/api/coverage").json() == []


def test_invite_link_is_one_use_and_stored_hashed(admin_client, gmail_env):
    created = admin_client.post("/api/invites", json={"label": "Ana - RR. HH."}).json()
    token = created["url"].rsplit("/", 1)[-1]
    assert created["url"].startswith("http://localhost:8000/invite/")
    # la base guarda solo el hash, nunca el token
    assert token.encode() not in (gmail_env / "atalaya.db").read_bytes()
    public = TestClient(
        admin_client.app, follow_redirects=False
    )  # sin cookie de sesion
    info = public.get(f"/api/public/invite/{token}").json()
    assert info["valid"] is True and info["label"] == "Ana - RR. HH."
    assert public.get("/api/public/invite/no-existe").json()["valid"] is False


def test_invite_login_requires_consent_and_redirects_to_google(admin_client):
    token = (
        admin_client.post("/api/invites", json={"label": "Ana"})
        .json()["url"]
        .rsplit("/", 1)[-1]
    )
    public = TestClient(admin_client.app, follow_redirects=False)
    assert (
        public.get(f"/auth/google/login?invite={token}").status_code == 400
    )  # sin consentimiento
    resp = public.get(f"/auth/google/login?invite={token}&consent=1")
    assert resp.status_code in (302, 307)
    url = resp.headers["location"]
    assert url.startswith("https://accounts.google.com/")
    assert "code_challenge=" in url and "state=" in url and "gmail.modify" in url
    assert "HttpOnly" in resp.headers["set-cookie"]


def test_invalid_or_revoked_invite_cannot_start_login(admin_client):
    public = TestClient(admin_client.app, follow_redirects=False)
    assert (
        public.get("/auth/google/login?invite=inventado&consent=1").status_code == 410
    )
    created = admin_client.post("/api/invites", json={"label": "Luis"}).json()
    token = created["url"].rsplit("/", 1)[-1]
    assert admin_client.post(f"/api/invites/{created['id']}/revoke").status_code == 200
    assert public.get(f"/auth/google/login?invite={token}&consent=1").status_code == 410


def test_login_without_invite_or_admin_session_is_rejected(gmail_client):
    assert gmail_client.get("/auth/google/login").status_code == 401


def test_callback_rejects_missing_or_wrong_state(admin_client):
    assert admin_client.get("/auth/google/callback?code=x&state=y").status_code == 400
    admin_client.get("/auth/google/login")  # fija la cookie (administracion)
    assert (
        admin_client.get("/auth/google/callback?code=x&state=otro").status_code == 400
    )


def test_write_requests_need_csrf_header(admin_client):
    admin_client.headers.pop("X-Requested-With")
    assert admin_client.post("/api/invites", json={"label": "x"}).status_code == 403
    assert admin_client.delete("/api/mailboxes/mb_x").status_code == 403


def test_audit_log_records_invites_and_logins(admin_client):
    admin_client.post("/api/invites", json={"label": "Marta"})
    actions = {e["action"] for e in admin_client.get("/api/audit").json()}
    assert {"admin_login", "invite_created"} <= actions

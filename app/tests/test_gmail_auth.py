import base64
import json

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.gmail import parse_message
from app.tokens import TokenVault


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


# --- Tokens cifrados -----------------------------------------------------------
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


# --- Lectura de mensajes de Gmail ---------------------------------------------
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


# --- Login de Google (sin red) -------------------------------------------------
@pytest.fixture()
def gmail_client(tmp_path, monkeypatch):
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
    monkeypatch.setenv("ATALAYA_TOKEN_PATH", str(tmp_path / "token.enc"))
    return TestClient(create_app(), follow_redirects=False)


def test_login_redirects_with_state_pkce_and_minimal_scope(gmail_client):
    resp = gmail_client.get("/auth/google/login")
    assert resp.status_code in (302, 307)
    url = resp.headers["location"]
    assert url.startswith("https://accounts.google.com/")
    assert "code_challenge=" in url and "code_challenge_method=S256" in url
    assert "state=" in url
    assert "gmail.modify" in url
    assert "HttpOnly" in resp.headers["set-cookie"]


def test_callback_rejects_missing_or_wrong_state(gmail_client):
    assert gmail_client.get("/auth/google/callback?code=x&state=y").status_code == 400
    gmail_client.get("/auth/google/login")  # fija la cookie
    assert (
        gmail_client.get("/auth/google/callback?code=x&state=otro").status_code == 400
    )


def test_disconnect_requires_csrf_header(gmail_client):
    assert gmail_client.post("/auth/disconnect").status_code == 403


def test_unconnected_gmail_reports_no_coverage(gmail_client):
    cov = gmail_client.get("/api/coverage").json()
    assert cov[0]["status"] == "revoked"
    assert gmail_client.get("/api/alerts").json() == []

"""Rol de supervisor: mismo inicio de sesion con Google, solo lectura (hecho cumplir en el servidor)."""

import json
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}
ADMIN = f"admin.{secrets.token_hex(4)}@gmail.com"
SUPER = f"supervisor.{secrets.token_hex(4)}@gmail.com"

WRITES = [
    ("post", "/api/alerts/x/approve", {"reason": "motivo de prueba largo"}),
    ("post", "/api/alerts/x/reject", {"reason": "motivo de prueba largo"}),
    ("post", "/api/alerts/x/legit", {"reason": "motivo de prueba largo"}),
    ("post", "/api/campaigns/x/quarantine", {"reason": "motivo de prueba largo"}),
    ("post", "/api/invites", {"label": "Ana"}),
    ("post", "/api/invites/x/revoke", None),
    ("delete", "/api/mailboxes/x", None),
    ("post", "/api/poll", None),
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    secrets_file = tmp_path / "client.json"
    secrets_file.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "x.apps.googleusercontent.com",
                    "client_secret": "fake-not-real",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8000/auth/google/callback"],
                }
            }
        )
    )
    monkeypatch.setenv("ATALAYA_MODE", "gmail")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", str(secrets_file))
    monkeypatch.setenv("ATALAYA_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ATALAYA_DB_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("ATALAYA_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("ATALAYA_LOGIN_DELAY", "0")
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", ADMIN)
    monkeypatch.setenv("ATALAYA_SUPERVISOR_EMAILS", SUPER)
    return create_app()


def _login(app, monkeypatch, email):
    client = TestClient(app, follow_redirects=False, headers=CSRF)
    resp = client.get("/auth/admin/google/login")
    query = parse_qs(urlparse(resp.headers["location"]).query)
    claims = {"email": email, "email_verified": True, "nonce": query["nonce"][0]}
    monkeypatch.setattr(
        "app.auth._google_admin_claims", lambda ctx, code, verifier: claims
    )
    done = client.get(f"/auth/google/callback?code=x&state={query['state'][0]}")
    assert done.status_code in (302, 307) and done.headers["location"] == "/"
    return client


def test_supervisor_logs_in_with_google_and_sees_a_masked_identity(app, monkeypatch):
    client = _login(app, monkeypatch, SUPER)
    me = client.get("/api/me").json()
    assert me["role"] == "supervisor" and SUPER not in str(me) and "***@" in me["id"]


def test_admin_keeps_the_admin_role(app, monkeypatch):
    assert _login(app, monkeypatch, ADMIN).get("/api/me").json()["role"] == "admin"


@pytest.mark.parametrize(("method", "path", "body"), WRITES)
def test_supervisor_cannot_change_anything(app, monkeypatch, method, path, body):
    client = _login(app, monkeypatch, SUPER)
    resp = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert resp.status_code == 403
    # el administrador, en cambio, llega a la ruta (aqui responde 404/422/409, nunca 403)
    admin = _login(app, monkeypatch, ADMIN)
    other = getattr(admin, method)(path, json=body) if body else getattr(admin, method)(path)
    assert other.status_code != 403


def test_supervisor_can_read_panel_history_and_organization_report(app, monkeypatch):
    client = _login(app, monkeypatch, SUPER)
    assert client.get("/api/alerts").status_code == 200
    assert client.get("/api/coverage").status_code == 200
    assert client.get("/api/campaigns").status_code == 200
    assert client.get("/api/audit").status_code == 200
    report = client.get("/api/org-report")
    assert report.status_code == 200 and "Reporte de la organizacion" in report.text
    assert SUPER not in report.text and ADMIN not in report.text
    assert "attachment" in client.get("/api/org-report?download=true").headers["content-disposition"]


def test_supervisor_can_log_out(app, monkeypatch):
    client = _login(app, monkeypatch, SUPER)
    assert client.post("/auth/admin/logout").status_code == 200
    assert client.get("/api/alerts").status_code == 401


def test_supervisor_list_is_validated_like_the_admin_list(app, monkeypatch):
    monkeypatch.setenv("ATALAYA_SUPERVISOR_EMAILS", "sin-arroba")
    with pytest.raises(RuntimeError, match="ATALAYA_SUPERVISOR_EMAILS"):
        create_app()


def test_unlisted_account_is_still_denied(app, monkeypatch):
    client = TestClient(app, follow_redirects=False, headers=CSRF)
    resp = client.get("/auth/admin/google/login")
    query = parse_qs(urlparse(resp.headers["location"]).query)
    claims = {"email": "otro@gmail.com", "email_verified": True, "nonce": query["nonce"][0]}
    monkeypatch.setattr("app.auth._google_admin_claims", lambda ctx, code, verifier: claims)
    done = client.get(f"/auth/google/callback?code=x&state={query['state'][0]}")
    assert "error" in done.headers["location"]


# --- Demo: el cambio de rol existe solo en demo y el servidor tambien lo hace cumplir ---
def test_demo_supervisor_view_is_read_only_on_the_server(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    client = TestClient(create_app(), follow_redirects=False, headers=CSRF)
    alert = client.get("/api/alerts").json()[0]["id"]
    assert client.get("/api/whoami").json() == {"role": "admin", "demo_roles": True}
    assert client.post("/api/demo/role", json={"role": "supervisor"}).status_code == 200
    assert client.get("/api/whoami").json()["role"] == "supervisor"
    assert client.post(f"/api/alerts/{alert}/approve").status_code == 403
    assert client.get("/api/org-report").status_code == 200
    # puede volver a la vista de administracion (solo demo)
    assert client.post("/api/demo/role", json={"role": "admin"}).status_code == 200
    assert client.post(f"/api/alerts/{alert}/approve").status_code == 200


def test_role_switch_does_not_exist_outside_demo(app, monkeypatch):
    client = _login(app, monkeypatch, SUPER)
    assert client.post("/api/demo/role", json={"role": "admin"}).status_code in (403, 404)
    assert client.get("/api/me").json()["role"] == "supervisor"

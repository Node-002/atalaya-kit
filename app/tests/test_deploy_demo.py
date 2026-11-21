"""Despliegue publico: solo modo demo, sin nada de modo gmail expuesto."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
CSRF = {"X-Requested-With": "atalaya"}


@pytest.fixture()
def demo(monkeypatch):
    # El entorno de la plataforma podria traer variables de Google: no deben activar nada.
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "x.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-not-real")
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", "alguien@example.com")
    return TestClient(create_app(), follow_redirects=False)


def test_health_and_home_work_without_login(demo):
    body = demo.get("/health").json()
    assert body == {"status": "ok", "mode": "demo", "auth": False}
    assert demo.get("/").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/auth/google/login",
        "/auth/google/callback",
        "/auth/admin/google/login",
        "/api/me",
        "/api/security/events",
        "/api/public/login-options",
    ],
)
def test_gmail_and_admin_routes_do_not_exist_in_demo(demo, path):
    assert demo.get(path).status_code == 404


def test_admin_login_and_logout_do_not_exist_in_demo(demo):
    assert demo.post("/auth/admin/login", headers=CSRF, json={}).status_code == 404
    assert demo.post("/auth/admin/logout", headers=CSRF).status_code == 404


def test_no_google_or_admin_route_registered(demo):
    paths = {getattr(r, "path", "") for r in demo.app.routes}
    assert not {p for p in paths if p.startswith(("/auth/google", "/auth/admin"))}


def test_demo_invite_only_creates_simulated_mailboxes(demo):
    url = demo.post("/api/invites", headers=CSRF, json={"label": "Prueba"}).json()[
        "url"
    ]
    token = url.rsplit("/", 1)[1]
    info = demo.get(f"/api/public/invite/{token}").json()
    assert info["mode"] == "demo"
    r = demo.get(f"/auth/demo/connect?invite={token}&consent=1")
    assert r.status_code in (302, 307)
    kinds = {m["status"] for m in demo.get("/api/coverage").json()}
    assert all("gmail" not in k.lower() for k in kinds)


def test_unknown_mode_is_refused(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "produccion")
    with pytest.raises(RuntimeError):
        create_app()


def test_no_session_cookie_is_ever_set_in_demo(demo):
    for path in ("/", "/health", "/api/alerts"):
        assert "set-cookie" not in demo.get(path).headers


def test_security_headers_and_hsts_only_over_https(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    monkeypatch.setenv("ATALAYA_BASE_URL", "https://atalaya.example.com")
    r = TestClient(create_app()).get("/health")
    assert r.headers["strict-transport-security"].startswith("max-age=")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    monkeypatch.setenv("ATALAYA_BASE_URL", "http://localhost:8000")
    assert (
        "strict-transport-security"
        not in TestClient(create_app()).get("/health").headers
    )


def test_dockerfile_forces_demo_and_runs_unprivileged():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ATALAYA_MODE=demo" in text and "${PORT}" in text
    assert "USER atalaya" in text
    copies = [ln for ln in text.splitlines() if ln.startswith(("COPY", "ADD"))]
    assert copies == ["COPY requirements.txt .", "COPY app ./app"]


def test_dockerignore_keeps_secrets_out_of_image():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    for item in (".env", ".git", ".venv", "data", "client_secret*.json"):
        assert item in lines

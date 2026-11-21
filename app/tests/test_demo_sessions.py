"""Demo publica: cada visitante tiene su propia copia, con limites de uso."""

import pytest
from fastapi.testclient import TestClient

from app.demo_sessions import COOKIE, DemoSessions
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}


@pytest.fixture(autouse=True)
def _demo_mode(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")


def make(**kwargs):
    demo = DemoSessions(create_app, **kwargs)
    return demo, TestClient(demo)


def statuses(client):
    return sorted(a["status"] for a in client.get("/api/alerts").json())


def test_each_visitor_has_their_own_copy():
    demo, a = make()
    b = TestClient(demo)  # otra persona: otra cookie
    campaign = a.get("/api/campaigns").json()[0]
    assert (
        a.post(f"/api/campaigns/{campaign['id']}/quarantine", headers=CSRF).status_code
        == 200
    )
    assert "quarantined" in statuses(a)
    assert "quarantined" not in statuses(b)  # lo que hizo A no se ve en B
    assert len(demo) == 2


def test_reset_only_affects_the_visitor_who_pressed_it():
    demo, a = make()
    b = TestClient(demo)
    campaign = b.get("/api/campaigns").json()[0]
    b.post(f"/api/campaigns/{campaign['id']}/quarantine", headers=CSRF)
    a.get("/api/alerts")
    assert a.post("/api/demo/reset", headers=CSRF).status_code == 200
    assert "quarantined" in statuses(b)  # el reinicio de A no toca a B


def test_cookie_is_httponly_samesite_and_random():
    _demo, a = make()
    r = a.get("/api/alerts")
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Max-Age=" in cookie
    assert "Secure" not in cookie  # http local
    again = a.get("/api/alerts")
    assert "set-cookie" not in again.headers  # misma persona: no se emite otra


def test_cookie_is_secure_under_https():
    _, a = make(secure=True)
    assert "Secure" in a.get("/api/alerts").headers["set-cookie"]


def test_unknown_or_forged_cookie_is_never_adopted():
    _demo, a = make()
    forged = "a" * 30
    a.cookies.set(COOKIE, forged)
    r = a.get("/api/alerts")
    assert f"{COOKIE}={forged}" not in r.headers.get("set-cookie", "")
    assert "set-cookie" in r.headers  # recibe una propia, aleatoria
    a.cookies.clear()
    a.cookies.set(COOKIE, "no-valido-<script>")
    assert a.get("/api/alerts").status_code == 200


def test_health_and_static_do_not_create_copies():
    demo, a = make()
    for _ in range(30):  # la plataforma consulta la salud cada pocos segundos
        assert a.get("/health").json()["mode"] == "demo"
    assert a.get("/static/app.js").status_code == 200
    assert a.get("/cosa-que-no-existe").status_code == 404
    assert len(demo) == 0


def test_capacity_is_bounded_and_oldest_copy_is_dropped():
    tick = [0.0]
    demo = DemoSessions(create_app, max_sessions=2, clock=lambda: tick[0])
    clients = []
    for _ in range(3):
        c = TestClient(demo)
        c.get("/api/alerts")
        clients.append(c)
        tick[0] += 1
    assert len(demo) == 2  # nunca pasa del tope
    first = clients[0].get("/api/alerts")  # su copia se descarto: recibe una nueva
    assert first.status_code == 200 and "set-cookie" in first.headers


def test_idle_copies_expire():
    tick = [0.0]
    demo = DemoSessions(create_app, ttl_seconds=100, clock=lambda: tick[0])
    c = TestClient(demo)
    c.get("/api/alerts")
    tick[0] += 101
    again = c.get("/api/alerts")
    assert "set-cookie" in again.headers  # la anterior caduco


def test_too_many_writes_from_one_address_get_429():
    _, a = make(writes_per_minute=5)
    codes = [a.post("/api/poll", headers=CSRF).status_code for _ in range(8)]
    assert codes[:5] == [200] * 5
    assert set(codes[5:]) == {429}
    limited = a.post("/api/poll", headers=CSRF)
    assert limited.headers["retry-after"] == "30" and "detail" in limited.json()
    assert a.get("/api/alerts").status_code == 200  # leer sigue permitido


def test_too_many_new_visitors_from_one_address_get_429():
    demo, _ = make(new_sessions_per_minute=3)
    codes = [TestClient(demo).get("/api/alerts").status_code for _ in range(6)]
    assert codes[:3] == [200] * 3
    assert set(codes[3:]) == {429}
    assert len(demo) == 3


def test_api_docs_are_closed_by_default(monkeypatch):
    monkeypatch.delenv("ATALAYA_DOCS", raising=False)
    client = TestClient(create_app())
    for path in ("/docs", "/openapi.json", "/redoc"):
        assert client.get(path).status_code == 404
    monkeypatch.setenv("ATALAYA_DOCS", "1")
    assert TestClient(create_app()).get("/openapi.json").status_code == 200

"""Acceso de la administracion con Google (sin red: el token de Google se simula)."""

import json
import re
import secrets
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.identity import mask_email, parse_email_list
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}
ADMIN = f"admin.{secrets.token_hex(4)}@gmail.com"
INTRUDER = f"intruso.{secrets.token_hex(4)}@gmail.com"
CYR_A = chr(0x0430)  # CYRILLIC SMALL A, identica a la a latina


@pytest.fixture()
def sso_env(tmp_path, monkeypatch):
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
    return monkeypatch


@pytest.fixture()
def app(sso_env):
    return create_app()


def _client(app):
    return TestClient(app, follow_redirects=False, headers=CSRF)


def _start(client):
    resp = client.get("/auth/admin/google/login")
    return resp, parse_qs(urlparse(resp.headers["location"]).query)


def _attempt(client, monkeypatch, email, *, verified=True, nonce=None, hd=None):
    _, query = _start(client)
    claims = {
        "email": email,
        "email_verified": verified,
        "nonce": nonce or query["nonce"][0],
    }
    if hd:
        claims["hd"] = hd
    monkeypatch.setattr(
        "app.auth._google_admin_claims", lambda ctx, code, verifier: claims
    )
    return client.get(
        f"/auth/google/callback?code=codigo-falso&state={query['state'][0]}"
    )


def _login_admin(client, monkeypatch):
    resp = _attempt(client, monkeypatch, ADMIN)
    assert resp.status_code in (302, 307) and resp.headers["location"] == "/"
    return client


# --- Configuracion: fallar cerrado -----------------------------------------------------
def test_refuses_to_start_without_any_login_method(sso_env):
    sso_env.delenv("ATALAYA_ADMIN_EMAILS")
    with pytest.raises(RuntimeError, match="ATALAYA_ADMIN_EMAILS"):
        create_app()


def test_refuses_lookalike_admin_emails_without_echoing_them(sso_env):
    bad = f"admin@b{CYR_A}ncogeneral.com"
    sso_env.setenv("ATALAYA_ADMIN_EMAILS", f"{ADMIN},{bad}")
    with pytest.raises(RuntimeError) as err:
        create_app()
    assert bad not in str(err.value) and ADMIN not in str(err.value)


def test_parse_email_list_normalizes_and_deduplicates():
    assert parse_email_list(" Ana@Empresa.com , ana@empresa.com ,, b@x.com ") == {
        "ana@empresa.com",
        "b@x.com",
    }
    with pytest.raises(ValueError):
        parse_email_list("sin-arroba")


def test_masking_hides_most_of_the_account():
    assert mask_email("maria@gmail.com") == "ma***@gmail.com"
    assert mask_email("a@x.com") == "a***@x.com"


# --- Opciones publicas: nada de cuentas ---------------------------------------------------
def test_login_options_expose_no_accounts_and_password_is_disabled(app):
    client = _client(app)
    options = client.get("/api/public/login-options")
    assert options.json() == {"google": True, "password": False}
    assert ADMIN not in options.text
    assert (
        client.post("/auth/admin/login", json={"password": "x" * 20}).status_code == 404
    )


# --- Inicio del flujo -------------------------------------------------------------------------
def test_google_login_requests_only_identity_scopes_with_pkce_and_nonce(app):
    resp, query = _start(_client(app))
    assert resp.headers["location"].startswith("https://accounts.google.com/")
    scopes = query["scope"][0]
    assert "openid" in scopes and "userinfo.email" in scopes and "gmail" not in scopes
    assert query["prompt"] == ["select_account"]
    assert (
        "nonce" in query
        and "state" in query
        and query["code_challenge_method"] == ["S256"]
    )
    assert "hd" not in query  # sin dominio configurado
    assert "HttpOnly" in resp.headers["set-cookie"]


def test_google_login_is_blocked_while_the_address_is_locked(app, sso_env):
    client = _client(app)
    for _ in range(5):
        _attempt(client, sso_env, INTRUDER)
    blocked = client.get("/auth/admin/google/login")
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) > 0


# --- Cuenta autorizada -------------------------------------------------------------------------
def test_allowed_admin_gets_a_session_without_personal_data_in_the_cookie(app, sso_env):
    client = _login_admin(_client(app), sso_env)
    assert client.get("/api/alerts").status_code == 200
    cookie = client.cookies.get("atalaya_session")
    assert ADMIN not in cookie and ADMIN.split("@")[0] not in cookie
    me = client.get("/api/me").json()
    assert re.fullmatch(r"ad\*\*\*@gmail\.com#[0-9a-f]{4}", me["id"])
    assert ADMIN not in client.get("/api/me").text


def test_email_comparison_ignores_case_and_spaces(app, sso_env):
    resp = _attempt(_client(app), sso_env, f"  {ADMIN.upper()} ")
    assert resp.headers["location"] == "/"


def test_actions_are_recorded_with_the_masked_identity(app, sso_env):
    client = _login_admin(_client(app), sso_env)
    client.post("/api/invites", json={"label": "Ana"})
    audit = client.get("/api/audit").json()
    actors = {
        e["actor"] for e in audit if e["action"] in ("admin_login", "invite_created")
    }
    assert len(actors) == 1 and next(iter(actors)).startswith("ad***@gmail.com#")
    assert ADMIN not in json.dumps(audit)


# --- Cuentas NO autorizadas / token invalido ------------------------------------------------------
@pytest.mark.parametrize(
    "kwargs",
    [
        {"email": INTRUDER},  # no esta en la lista
        {"email": ADMIN, "verified": False},  # correo no confirmado
        {"email": ADMIN, "nonce": "otro"},  # nonce que no corresponde (reutilizacion)
        {
            "email": f"admin.{ADMIN.split('.', 1)[1].replace('a', CYR_A, 1)}"
        },  # homografo
    ],
)
def test_denied_logins_look_identical_and_create_no_session(app, sso_env, kwargs):
    client = _client(app)
    resp = _attempt(client, sso_env, kwargs.pop("email"), **kwargs)
    assert (
        resp.status_code in (302, 307) and resp.headers["location"] == "/login?error=1"
    )
    assert client.get("/api/alerts").status_code == 401
    assert "atalaya_session" not in client.cookies


def test_failed_exchange_with_google_is_a_generic_failure(app, sso_env):
    client = _client(app)
    _, query = _start(client)

    def boom(ctx, code, verifier):
        raise ValueError("token invalido")

    sso_env.setattr("app.auth._google_admin_claims", boom)
    resp = client.get(f"/auth/google/callback?code=x&state={query['state'][0]}")
    assert resp.headers["location"] == "/login?error=1"


def test_callback_with_wrong_state_is_rejected(app):
    client = _client(app)
    _start(client)
    assert client.get("/auth/google/callback?code=x&state=otro").status_code == 400


# --- Avisos y registro, sin exponer cuentas ------------------------------------------------------
def test_repeated_denials_lock_alert_and_never_expose_full_accounts(app, sso_env):
    admin_client = _login_admin(_client(app), sso_env)  # sesion legitima previa
    attacker = _client(app)
    for _ in range(5):
        _attempt(attacker, sso_env, INTRUDER)
    events = admin_client.get("/api/security/events").json()
    kinds = {e["kind"] for e in events}
    assert {"acceso_denegado", "bloqueo"} <= kinds
    audit = admin_client.get("/api/audit").json()
    assert {"admin_login_denied", "admin_login"} <= {e["action"] for e in audit}
    everything = json.dumps(events) + json.dumps(audit)
    assert INTRUDER not in everything and ADMIN not in everything
    assert mask_email(INTRUDER) in everything  # solo la forma enmascarada


def test_security_events_require_admin_session(app):
    assert _client(app).get("/api/security/events").status_code == 401


# --- Dominio de la empresa --------------------------------------------------------------------------
def test_domain_restriction_requires_matching_hosted_domain(app, sso_env):
    sso_env.setenv("ATALAYA_ADMIN_DOMAIN", "empresa.example")
    restricted = create_app()
    _, query = _start(_client(restricted))
    assert query["hd"] == ["empresa.example"]
    assert (
        _attempt(_client(restricted), sso_env, ADMIN).headers["location"]
        == "/login?error=1"
    )
    assert (
        _attempt(_client(restricted), sso_env, ADMIN, hd="otra.example").headers[
            "location"
        ]
        == "/login?error=1"
    )
    assert (
        _attempt(_client(restricted), sso_env, ADMIN, hd="EMPRESA.example").headers[
            "location"
        ]
        == "/"
    )


# --- Ninguna cuenta autorizada aparece en el codigo ni en las paginas -------------------------------------
def test_authorized_accounts_never_appear_in_pages_or_static_files(app):
    client = _client(app)
    pages = [
        client.get(path).text
        for path in ("/login", "/health", "/api/public/login-options", "/connected")
    ]
    pages.append(client.get("/").text)  # redirige al login: sin datos
    for body in pages:
        assert ADMIN not in body and ADMIN.split("@")[0] not in body

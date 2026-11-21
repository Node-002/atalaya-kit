"""Pruebas del asistente de instalacion del kit (tools/kit/instalar.py).

El script se carga por ruta (no es un paquete). Docker NO se ejecuta: un `docker` FALSO en el PATH de
la prueba responde a `--version`, `compose version`, `info`, `compose build/up` y deja registrados los
argumentos; /health lo simula un servidor local en un puerto libre. Todos los datos son falsos y se
generan en tiempo de ejecucion.
"""

import importlib.util
import json
import os
import stat
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "kit" / "instalar.py"
_spec = importlib.util.spec_from_file_location("kit_instalar", SCRIPT)
inst = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inst)

REDIRECT_LOCAL = "http://localhost:8000/auth/google/callback"


# ---------------------------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------------------------
def make_client_json(
    path: Path, redirect: str = REDIRECT_LOCAL, kind: str = "web"
) -> Path:
    import secrets as sec

    path.write_text(
        json.dumps(
            {
                kind: {
                    "client_id": "falso.apps.googleusercontent.com",
                    "client_secret": sec.token_hex(12),
                    "redirect_uris": [redirect],
                }
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def kit(tmp_path):
    folder = tmp_path / "kit"
    folder.mkdir()
    (folder / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (folder / "Caddyfile").write_text(
        "CAMBIAR_DOMINIO {\n\treverse_proxy atalaya:8000\n}\n", encoding="utf-8"
    )
    return folder


@pytest.fixture
def client_json(tmp_path):
    folder = tmp_path / "descargas"
    folder.mkdir()
    return make_client_json(folder / "client_secret_falso.json")


@pytest.fixture
def fake_docker(tmp_path, monkeypatch):
    """docker falso en el PATH. Devuelve la ruta del registro de argumentos."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "docker.log"
    script = bindir / "fake_docker.py"
    script.write_text(
        textwrap.dedent(
            """
            import os, sys
            args = sys.argv[1:]
            with open(os.environ["FAKE_DOCKER_LOG"], "a", encoding="utf-8") as f:
                f.write(" ".join(args) + "\\n")
            if args[:1] == ["--version"]:
                print("Docker version 27.0.0, build fake")
            elif args[:2] == ["compose", "version"]:
                print("Docker Compose version v2.29.0")
            elif args[:1] == ["info"]:
                if os.environ.get("FAKE_DOCKER_NO_DAEMON"):
                    sys.exit(1)
            elif "up" in args and os.environ.get("FAKE_DOCKER_FAIL_UP"):
                sys.stderr.write("fake: up failed\\n")
                sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        (bindir / "docker.cmd").write_text(
            f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
        )
    else:
        wrapper = bindir / "docker"
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8"
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("FAKE_DOCKER_LOG", str(log))
    return log


@pytest.fixture
def health_server():
    class Handler(BaseHTTPRequestHandler):
        mode = "gmail"

        def do_GET(self):
            body = json.dumps(
                {"status": "ok", "mode": Handler.mode, "auth": True}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1], Handler
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "ATALAYA_ORG_NAME",
        "ATALAYA_INSTALL_MODE",
        "ATALAYA_INSTALL_DOMAIN",
        "ATALAYA_ADMIN_EMAILS",
        "ATALAYA_SUPERVISOR_EMAILS",
        "ATALAYA_GOOGLE_JSON",
        "ATALAYA_INSTALL_PROXY",
        "ATALAYA_LANG",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")


def base_args(kit, client_json, port, *extra):
    return [
        "--dir",
        str(kit),
        "--si",
        "--org",
        "Organizacion de Prueba",
        "--modo",
        "local",
        "--admin",
        "admin@example.org",
        "--google-json",
        str(client_json),
        "--puerto-app",
        str(port),
        "--timeout",
        "10",
        "--verificador-sin-red",
        *extra,
    ]


def env_values(kit) -> dict:
    return inst.parse_env_text((kit / ".env.kit").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "email,expected",
    [
        ("ana@example.org", True),
        ("ana.lopez+x@sub.example.co", True),
        ("anа@example.org", False),  # 'а' cirilica
        ("ana@xn--exmple-cua.org", False),  # punycode
        ("ana@example", False),
        ("ana@@example.org", False),
        ("", False),
        ("ñandú@example.org", False),
    ],
)
def test_email_ascii_estricto(email, expected):
    assert inst.is_safe_email(email) is expected


def test_parse_emails_normaliza_y_no_repite_el_correo_en_el_error():
    assert inst.parse_emails(" A@Example.org, a@example.org ,b@example.org") == [
        "a@example.org",
        "b@example.org",
    ]
    with pytest.raises(inst.InstallError) as exc:
        inst.parse_emails("ok@example.org,malo@xn--a.org")
    assert "malo" not in str(exc.value)
    assert "2" in str(exc.value)


def test_dominio_y_urls():
    assert inst.valid_domain("https://Atalaya.Example.org/") == "atalaya.example.org"
    for bad in (
        "localhost",
        "http://x.org",
        "a b.org",
        "x.org:8443",
        "x.org/ruta",
        "xn--a.org",
    ):
        with pytest.raises(inst.InstallError):
            inst.valid_domain(bad)
    assert inst.base_url_for("local", None) == "http://localhost:8000"
    assert inst.base_url_for("production", "a.example.org") == "https://a.example.org"
    assert (
        inst.redirect_uri_for("https://a.example.org/")
        == "https://a.example.org/auth/google/callback"
    )
    inst.validate_base_url("https://a.example.org")
    inst.validate_base_url("http://localhost:8000")
    for bad in ("http://a.example.org", "http://127.0.0.1:8000", "ftp://a.org"):
        with pytest.raises(inst.InstallError):
            inst.validate_base_url(bad)


def test_nombre_de_organizacion():
    assert inst.valid_org_name("  Mi Org S.A. ") == "Mi Org S.A."
    for bad in ("", "x" * 81, "a\nb", 'com"illa', "con # almohadilla", "a$b"):
        with pytest.raises(inst.InstallError):
            inst.valid_org_name(bad)


def test_json_de_google_correcto_e_incorrecto(tmp_path):
    good = make_client_json(tmp_path / "ok.json")
    assert "web" in inst.load_google_json(good, REDIRECT_LOCAL)
    with pytest.raises(inst.InstallError, match="redireccion|redirect"):
        inst.load_google_json(good, "https://otro.example.org/auth/google/callback")
    desktop = make_client_json(tmp_path / "desktop.json", kind="installed")
    with pytest.raises(inst.InstallError, match="web"):
        inst.load_google_json(desktop, REDIRECT_LOCAL)
    broken = tmp_path / "roto.json"
    broken.write_text("{no es json", encoding="utf-8")
    with pytest.raises(inst.InstallError):
        inst.load_google_json(broken, REDIRECT_LOCAL)
    with pytest.raises(inst.InstallError):
        inst.load_google_json(tmp_path / "no_existe.json", REDIRECT_LOCAL)


def test_json_dentro_de_un_repositorio_se_rechaza(tmp_path, kit):
    repo = tmp_path / "otro_repo"
    (repo / ".git").mkdir(parents=True)
    inside_repo = make_client_json(repo / "client.json")
    with pytest.raises(inst.InstallError, match="repositorio|repository"):
        inst.check_google_json_location(inside_repo, kit)
    with pytest.raises(inst.InstallError):
        inst.check_google_json_location(make_client_json(kit / "client.json"), kit)
    outside = make_client_json(tmp_path / "fuera.json")
    inst.check_google_json_location(outside, kit)  # no lanza


def test_safe_join_impide_escapar_de_la_carpeta(kit):
    assert inst.safe_join(kit, "secrets", "x.json").parent.name == "secrets"
    with pytest.raises(inst.InstallError):
        inst.safe_join(kit, "..", "fuera.txt")
    with pytest.raises(inst.InstallError):
        inst.safe_join(kit, "secrets", "..", "..", "fuera.txt")


# ---------------------------------------------------------------------------------------------
# Secretos
# ---------------------------------------------------------------------------------------------
def test_clave_fernet_valida_y_unica():
    key = inst.generate_fernet_key()
    assert len(key) == 44
    Fernet(key.encode())  # lanza ValueError si no es valida
    assert (
        Fernet(key.encode()).decrypt(Fernet(key.encode()).encrypt(b"hola")) == b"hola"
    )
    assert key != inst.generate_fernet_key()
    session = inst.generate_session_secret()
    assert len(session) >= 32 and session != inst.generate_session_secret()


def test_ningun_secreto_en_salida_ni_en_argumentos(
    kit, client_json, fake_docker, health_server, capsys, monkeypatch
):
    port, _ = health_server
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-" + "x" * 40)
    key_copy = kit.parent / "usb" / "clave.txt"
    key_copy.parent.mkdir()
    code = inst.main(
        base_args(kit, client_json, port, "--ia", "--copia-clave", str(key_copy))
    )
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    values = env_values(kit)
    google_secret = json.loads(client_json.read_text())["web"]["client_secret"]
    secret_values = [
        values["ATALAYA_FERNET_KEY"],
        values["ATALAYA_SESSION_SECRET"],
        values["ANTHROPIC_API_KEY"],
        google_secret,
    ]
    assert all(len(v) > 20 for v in secret_values)
    everything = captured.out + captured.err + fake_docker.read_text(encoding="utf-8")
    for value in secret_values:
        assert value not in everything
    assert "ATALAYA_FERNET_KEY=" not in captured.out
    # la copia de la clave si contiene la clave Fernet (y solo esa)
    assert (
        key_copy.read_text().strip()
        == "ATALAYA_FERNET_KEY=" + values["ATALAYA_FERNET_KEY"]
    )


# ---------------------------------------------------------------------------------------------
# Archivos
# ---------------------------------------------------------------------------------------------
@pytest.mark.skipif(os.name == "nt", reason="permisos POSIX")
def test_permisos_restringidos_en_posix(kit, client_json, capsys):
    assert inst.main(base_args(kit, client_json, 8100, "--sin-arranque")) == 0
    assert stat.S_IMODE((kit / ".env.kit").stat().st_mode) == 0o600
    assert stat.S_IMODE((kit / "secrets").stat().st_mode) == 0o711
    assert (
        stat.S_IMODE((kit / "secrets" / "google_client.json").stat().st_mode) == 0o644
    )


def test_configuracion_completa_sin_arranque(kit, client_json, capsys):
    assert (
        inst.main(
            base_args(
                kit,
                client_json,
                8100,
                "--sin-arranque",
                "--supervisores",
                "ver@example.org",
            )
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "http://localhost:8000/auth/google/callback" in out
    values = env_values(kit)
    assert values["ATALAYA_BASE_URL"] == "http://localhost:8000"
    assert values["ATALAYA_ADMIN_EMAILS"] == "admin@example.org"
    assert values["ATALAYA_SUPERVISOR_EMAILS"] == "ver@example.org"
    assert values["ATALAYA_ORG_NAME"] == "Organizacion de Prueba"
    assert values["ATALAYA_TRUST_PROXY"] == "0"
    assert values["ATALAYA_LLM"] == "off"
    assert "ANTHROPIC_API_KEY" not in values
    assert values["GOOGLE_CLIENT_SECRETS_FILE"] == "/run/secrets/google_client.json"
    assert (kit / "secrets" / "google_client.json").is_file()
    # la configuracion generada pasa la comprobacion previa de la propia aplicacion
    sys.path.insert(0, str(SCRIPT.parents[2]))
    try:
        from app import kit_preflight
    finally:
        sys.path.pop(0)
    problems = kit_preflight.check(
        {
            **values,
            "ATALAYA_MODE": "gmail",
            "GOOGLE_CLIENT_SECRETS_FILE": str(kit / "secrets" / "google_client.json"),
            "ATALAYA_DB_PATH": str(kit / "atalaya.db"),
        }
    )
    assert problems == []


def test_no_sobrescribe_sin_confirmacion_y_hace_copia(kit, client_json, capsys):
    args = base_args(kit, client_json, 8100, "--sin-arranque")
    assert inst.main(args) == 0
    first = (kit / ".env.kit").read_text()
    capsys.readouterr()
    # sin confirmacion: falla, no toca nada
    assert inst.main(args) == 1
    assert "sobrescribir" in capsys.readouterr().out
    assert (kit / ".env.kit").read_text() == first
    assert not list(kit.glob(".env.kit.bak-*"))
    # con --sobrescribir: reemplaza (claves nuevas) y deja una copia con el contenido anterior
    assert inst.main([*args, "--sobrescribir"]) == 0
    backups = list(kit.glob(".env.kit.bak-*"))
    assert len(backups) == 1 and backups[0].read_text() == first
    assert (kit / ".env.kit").read_text() != first


def test_interactivo_confirma_sobrescritura(kit, client_json, monkeypatch, capsys):
    assert inst.main(base_args(kit, client_json, 8100, "--sin-arranque")) == 0
    first = (kit / ".env.kit").read_text()
    answers = iter(
        [
            "Org Interactiva",  # nombre
            "local",  # modo
            "admin@example.org",  # admin
            "",  # supervisores
            str(client_json),  # json
            "n",  # IA
            "s",  # reemplazar .env.kit
            "n",  # copia de la clave
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert inst.main(["--dir", str(kit), "--sin-arranque"]) == 0
    assert (kit / ".env.kit").read_text() != first
    assert env_values(kit)["ATALAYA_ORG_NAME"] == "Org Interactiva"
    assert len(list(kit.glob(".env.kit.bak-*"))) == 1


def test_interactivo_pide_clave_de_ia_sin_eco(kit, client_json, monkeypatch, capsys):
    seen = {}

    def fake_getpass(prompt=""):
        seen["prompt"] = prompt
        return "sk-ant-api03-" + "y" * 40

    monkeypatch.setattr(inst.getpass, "getpass", fake_getpass)
    answers = iter(
        ["Org", "local", "admin@example.org", "", str(client_json), "s", "n"]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert inst.main(["--dir", str(kit), "--sin-arranque"]) == 0
    captured = capsys.readouterr()
    assert "Anthropic" in captured.out and "ENVIA" in captured.out  # aviso en claro
    assert "y" * 40 not in captured.out + captured.err
    assert env_values(kit)["ATALAYA_LLM"] == "anthropic"
    assert "prompt" in seen


def test_copia_de_clave_no_puede_quedar_en_la_carpeta_del_kit(kit, client_json, capsys):
    code = inst.main(
        base_args(
            kit,
            client_json,
            8100,
            "--sin-arranque",
            "--copia-clave",
            str(kit / "clave.txt"),
        )
    )
    assert code == 1
    assert not (kit / "clave.txt").exists()


# ---------------------------------------------------------------------------------------------
# Errores esperados, idiomas y banderas
# ---------------------------------------------------------------------------------------------
def test_sin_datos_en_modo_no_interactivo_falla_con_mensaje_claro(kit, capsys):
    assert inst.main(["--dir", str(kit), "--si", "--sin-arranque"]) == 1
    out = capsys.readouterr().out
    assert "--org" in out and "Traceback" not in out


def test_json_incorrecto_da_error_sin_traza(kit, tmp_path, capsys):
    bad = make_client_json(
        tmp_path / "otra_uri.json",
        redirect="https://otro.example.org/auth/google/callback",
    )
    assert inst.main(base_args(kit, bad, 8100, "--sin-arranque")) == 1
    out = capsys.readouterr().out
    assert "ERROR" in out and REDIRECT_LOCAL in out and "Traceback" not in out
    assert not (kit / ".env.kit").exists()


def test_carpeta_que_no_es_el_kit(tmp_path, client_json, capsys):
    empty = tmp_path / "vacia"
    empty.mkdir()
    assert inst.main(base_args(empty, client_json, 8100, "--sin-arranque")) == 1
    assert "docker-compose.yml" in capsys.readouterr().out


def test_ingles_y_espanol(kit, client_json, capsys, monkeypatch):
    assert (
        inst.main(
            ["--lang", "en", *base_args(kit, client_json, 8100, "--sin-arranque")]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert (
        "Preflight checks" in out
        and "Next steps" in out
        and "Comprobaciones" not in out
    )
    assert env_values(kit)["ATALAYA_LANG"] == "en"
    (kit / ".env.kit").unlink()
    monkeypatch.setenv("ATALAYA_LANG", "en")
    assert inst.main(base_args(kit, client_json, 8100, "--sin-arranque")) == 0
    assert "Preflight checks" in capsys.readouterr().out
    monkeypatch.delenv("ATALAYA_LANG")
    (kit / ".env.kit").unlink()
    assert inst.main(base_args(kit, client_json, 8100, "--sin-arranque")) == 0
    out = capsys.readouterr().out
    assert "Comprobaciones previas" in out and "Siguientes pasos" in out


def test_ayuda_y_version(capsys):
    assert inst.main(["--version"]) == 0
    assert inst.VERSION in capsys.readouterr().out
    assert inst.main(["--ayuda"]) == 0
    assert "--sin-arranque" in capsys.readouterr().out
    assert inst.main(["--lang", "en", "--help"]) == 0
    assert "--no-start" in capsys.readouterr().out


def test_sin_color_con_no_color(capsys):
    inst.set_color()
    assert inst.USE_COLOR is False
    inst.main(["--version"])
    assert "\033[" not in capsys.readouterr().out


def test_variables_de_entorno_para_automatizar(kit, client_json, capsys, monkeypatch):
    monkeypatch.setenv("ATALAYA_ORG_NAME", "Org Entorno")
    monkeypatch.setenv("ATALAYA_INSTALL_MODE", "local")
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", "uno@example.org,dos@example.org")
    monkeypatch.setenv("ATALAYA_GOOGLE_JSON", str(client_json))
    assert inst.main(["--dir", str(kit), "--si", "--sin-arranque"]) == 0
    values = env_values(kit)
    assert values["ATALAYA_ORG_NAME"] == "Org Entorno"
    assert values["ATALAYA_ADMIN_EMAILS"] == "uno@example.org,dos@example.org"


# ---------------------------------------------------------------------------------------------
# Orquestacion con docker FALSO
# ---------------------------------------------------------------------------------------------
def test_flujo_completo_con_docker_falso(
    kit, client_json, fake_docker, health_server, capfd
):
    port, _ = health_server
    assert inst.main(base_args(kit, client_json, port)) == 0
    out = capfd.readouterr().out
    assert "Docker version" in out and "Docker Compose version" in out
    assert "/health responde" in out
    assert "respaldo.sh" in out and "restaurar.sh" in out
    assert "Resultado: 0 falla(s)" in out  # salida del verificador
    calls = fake_docker.read_text(encoding="utf-8").splitlines()
    assert "compose build" in calls and "compose up -d" in calls
    assert not any("--profile" in c for c in calls)


def test_modo_produccion_con_caddy(
    kit, tmp_path, fake_docker, health_server, capsys, monkeypatch
):
    port, _ = health_server
    redirect = "https://atalaya.example.org/auth/google/callback"
    cj = make_client_json(tmp_path / "prod.json", redirect=redirect)
    monkeypatch.setattr(inst, "port_in_use", lambda p: p != port and False)
    args = [
        "--dir", str(kit), "--si", "--org", "Org", "--modo", "produccion", "--dominio", "atalaya.example.org",
        "--admin", "admin@example.org", "--google-json", str(cj), "--proxy", "caddy",
        "--puerto-app", str(port), "--timeout", "10", "--verificador-sin-red",
    ]  # fmt: skip
    assert inst.main(args) == 0, capsys.readouterr().out
    values = env_values(kit)
    assert values["ATALAYA_BASE_URL"] == "https://atalaya.example.org"
    assert values["ATALAYA_TRUST_PROXY"] == "1"
    assert "atalaya.example.org {" in (kit / "Caddyfile").read_text()
    assert "CAMBIAR_DOMINIO" not in (kit / "Caddyfile").read_text()
    calls = fake_docker.read_text(encoding="utf-8").splitlines()
    assert (
        "compose --profile tls build" in calls
        and "compose --profile tls up -d" in calls
    )


@pytest.mark.parametrize("hops,expected", [(1, "1"), (2, "0")])
def test_proxy_propio_y_saltos(kit, tmp_path, hops, expected, capsys):
    redirect = "https://atalaya.example.org/auth/google/callback"
    cj = make_client_json(tmp_path / "prod.json", redirect=redirect)
    args = [
        "--dir", str(kit), "--si", "--sin-arranque", "--org", "Org", "--modo", "produccion",
        "--dominio", "atalaya.example.org", "--admin", "admin@example.org", "--google-json", str(cj),
        "--proxy", "propio", "--saltos", str(hops),
    ]  # fmt: skip
    assert inst.main(args) == 0
    assert env_values(kit)["ATALAYA_TRUST_PROXY"] == expected
    assert (
        (kit / "Caddyfile").read_text().startswith("CAMBIAR_DOMINIO")
    )  # no se toca sin Caddy


def test_falta_docker(kit, client_json, tmp_path, monkeypatch, capsys):
    empty = tmp_path / "vacio"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert inst.main(base_args(kit, client_json, 8100)) == 1
    out = capsys.readouterr().out
    assert "docker" in out and "no instala nada" in out
    assert not (kit / ".env.kit").exists()


def test_docker_sin_daemon(kit, client_json, fake_docker, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_DOCKER_NO_DAEMON", "1")
    assert inst.main(base_args(kit, client_json, 8100)) == 1
    assert "no esta en marcha" in capsys.readouterr().out


def test_puerto_ocupado(kit, client_json, fake_docker, monkeypatch, capsys):
    monkeypatch.setattr(inst, "port_in_use", lambda p: True)
    monkeypatch.setattr(inst, "fetch_health", lambda p: None)
    assert inst.main(base_args(kit, client_json, 8100)) == 1
    assert "ocupado" in capsys.readouterr().out


def test_falla_docker_compose_up(kit, client_json, fake_docker, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_DOCKER_FAIL_UP", "1")
    assert inst.main(base_args(kit, client_json, 8100)) == 1
    out = capsys.readouterr().out
    assert "up -d" in out and "Traceback" not in out


def test_health_con_modo_demo_falla(
    kit, client_json, fake_docker, health_server, capsys, monkeypatch
):
    port, handler = health_server
    monkeypatch.setattr(
        inst, "port_in_use", lambda p: False
    )  # lo ocupa el servidor simulado
    handler.mode = "demo"
    try:
        assert inst.main(base_args(kit, client_json, port)) == 1
    finally:
        handler.mode = "gmail"
    assert "gmail" in capsys.readouterr().out


def test_health_que_no_responde_agota_el_tiempo(
    kit, client_json, fake_docker, monkeypatch, capsys
):
    monkeypatch.setattr(inst, "fetch_health", lambda p: None)
    monkeypatch.setattr(inst.time, "sleep", lambda s: None)
    args = base_args(kit, client_json, 8100)
    args[args.index("--timeout") + 1] = "0"
    assert inst.main(args) == 1
    assert "/health" in capsys.readouterr().out


def test_solo_verificar(kit, client_json, capfd):
    assert (
        inst.main(["--dir", str(kit), "--verificar", "--verificador-sin-red"]) == 1
    )  # aun no hay configuracion
    assert ".env.kit" in capfd.readouterr().out
    assert inst.main(base_args(kit, client_json, 8100, "--sin-arranque")) == 0
    capfd.readouterr()
    assert (
        inst.main(
            ["--dir", str(kit), "--check", "--lang", "en", "--verificador-sin-red"]
        )
        == 0
    )
    assert "Result: 0 failure(s)" in capfd.readouterr().out

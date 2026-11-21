"""Aisla las pruebas del entorno real: main.py carga el .env al importarse, y las pruebas
no deben heredar claves, listas de administradores ni destinos de avisos reales."""

import contextlib
import os
import sys

import pytest

_PREFIXES = ("ATALAYA_", "GOOGLE_")
_NAMES = ("ANTHROPIC_API_KEY",)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith(_PREFIXES) or name in _NAMES:
            monkeypatch.delenv(name, raising=False)


# --- Cuelgues intermitentes en Windows (ver docs/INFORME_CARGA_21_NOV.md, parte B) -----------------
# TestClient (sin `with`) crea un bucle de eventos NUEVO por cada peticion, y todo bucle de asyncio en
# Windows abre un `socket.socketpair()`, que la libreria estandar emula con una conexion TCP por el
# loopback. En el equipo de desarrollo (filtros de red: Npcap, VPN...) a veces se pierde el SYN de
# esa conexion y Windows reintenta con espera doble (1, 2, 4, 8, 16 s): se midieron `socketpair()`
# sueltos de hasta 16 s y rachas de minutos, sin que interviniera nuestro codigo. Aqui las pruebas
# comparten UN solo bucle por ejecucion (un solo socketpair en vez de miles). No cambia lo que se
# prueba; los `with TestClient(...)` (con lifespan) siguen usando el suyo.
_shared = contextlib.ExitStack()
_portal = None


def _shared_portal_factory(self):
    global _portal
    if self.portal is not None:
        return contextlib.nullcontext(self.portal)
    if _portal is None:
        import anyio.from_thread

        _portal = _shared.enter_context(
            anyio.from_thread.start_blocking_portal(**self.async_backend)
        )
    return contextlib.nullcontext(_portal)


if sys.platform == "win32" and not os.environ.get("ATALAYA_PORTAL_PER_REQUEST"):
    from starlette.testclient import TestClient

    TestClient._portal_factory = _shared_portal_factory


def pytest_sessionfinish(session, exitstatus):
    _shared.close()

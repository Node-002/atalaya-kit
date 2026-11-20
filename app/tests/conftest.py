"""Aisla las pruebas del entorno real: main.py carga el .env al importarse, y las pruebas
no deben heredar claves, listas de administradores ni destinos de avisos reales."""

import os

import pytest

_PREFIXES = ("ATALAYA_", "GOOGLE_")
_NAMES = ("ANTHROPIC_API_KEY",)


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in list(os.environ):
        if name.startswith(_PREFIXES) or name in _NAMES:
            monkeypatch.delenv(name, raising=False)

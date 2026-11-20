"""Almacen cifrado de tokens OAuth (Fernet). Nunca se guarda un token en claro."""

import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class TokenVault:
    def __init__(self, path: str | Path, key: str) -> None:
        self.path = Path(path)
        self._fernet = Fernet(key.encode())

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self._fernet.encrypt(json.dumps(data).encode()))

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()))
        except (InvalidToken, ValueError):
            return None

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)

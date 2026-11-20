"""Interfaz comun de proveedores de correo (ADR 0001).

Deliberadamente NO existe operacion de borrar ni de enviar correos.
"""

from typing import Protocol

from app.models import ConnectionStatus, Label, Message


class MailProvider(Protocol):
    def list_new_messages(self) -> list[Message]: ...

    def apply_label(self, ref: str, label: Label) -> None: ...

    def quarantine(self, ref: str) -> None:
        """Quitar de la bandeja + etiqueta. Reversible."""

    def release(self, ref: str) -> None:
        """Deshacer cuarentena y etiquetas."""

    def connection_status(self) -> ConnectionStatus: ...

    def account_name(self) -> str: ...

"""Evita que secretos de las URL queden escritos en los registros del servidor.

El token de una invitacion, el codigo de autorizacion de Google (`code`) y el `state`
viajan en la URL; uvicorn los registra en su log de acceso. Se reemplazan por [oculto].
"""

import logging
import re

_PATTERNS = (
    (re.compile(r"(/invite/)[^\s/?\"']+"), r"\1[oculto]"),
    (re.compile(r"([?&](?:invite|code|state)=)[^&\s\"']+"), r"\1[oculto]"),
)


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactSecrets(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def install() -> None:
    """Idempotente: se puede llamar varias veces."""
    for name in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactSecrets) for f in logger.filters):
            logger.addFilter(RedactSecrets())
        for handler in logger.handlers:
            if not any(isinstance(f, RedactSecrets) for f in handler.filters):
                handler.addFilter(RedactSecrets())

"""Enmascarado de datos personales antes de enviar texto a la IA.

Es un filtro de mejor esfuerzo, no una garantia: por eso ademas se recorta el texto
y solo se envian los datos minimos.
"""

import re

_EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
# Cedulas de Panama (8-123-456, PE-12-345) y Costa Rica (1-0234-0567)
_CEDULA = re.compile(r"\b(?:[A-Z]{1,2}|\d{1,2})-\d{1,4}-\d{1,6}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PHONE = re.compile(
    r"(?<![\w-])(?:\+\d{1,3}[ -]?)?\d{4}[ -]?\d{4}(?![\w-])|(?<![\w-])\d{3}-\d{4}(?![\w-])"
)
_LONG_NUMBER = re.compile(r"\b\d{8,}\b")


def mask_pii(text: str) -> str:
    text = _EMAIL.sub(r"[correo]@\1", text)
    text = _CEDULA.sub("[cedula]", text)
    text = _CARD.sub("[tarjeta]", text)
    text = _PHONE.sub("[telefono]", text)
    text = _LONG_NUMBER.sub("[numero]", text)
    return text

"""Validacion de identidades (direcciones de correo de las cuentas que se conectan).

Politica estricta: solo se aceptan direcciones ASCII normales. Una direccion con letras
de otro alfabeto, acentos o un dominio en punycode (xn--) puede hacerse pasar por otra
persona u organizacion ("homografo"), asi que se rechaza y se deja constancia.

Limite: una empresa con dominio internacionalizado legitimo (por ejemplo con enie)
quedaria rechazada hasta que se decida admitirla de forma explicita.
"""

import re

_EMAIL = re.compile(
    r"^[A-Za-z0-9._%+'\-]{1,64}@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)


def is_safe_email(email: str) -> bool:
    if not email or not email.isascii() or not _EMAIL.match(email):
        return False
    domain = email.rsplit("@", 1)[1].lower()
    return not any(label.startswith("xn--") for label in domain.split("."))


def normalize_email(email: str) -> str:
    """Forma canonica para comparar (solo ASCII, minusculas)."""
    return email.strip().lower()

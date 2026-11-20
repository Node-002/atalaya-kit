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


def mask_email(email: str) -> str:
    """Forma que se puede mostrar o registrar sin exponer la cuenta: ma***@dominio."""
    local, _, domain = email.partition("@")
    return f"{local[:2] if len(local) > 2 else local[:1]}***@{domain}"


def parse_email_list(value: str) -> frozenset[str]:
    """Lee una lista separada por comas. Falla si alguna direccion no es segura
    (letras de otros alfabetos, punycode, formato raro). El mensaje NO repite el correo."""
    emails: set[str] = set()
    for position, raw in enumerate(part for part in value.split(",") if part.strip()):
        email = normalize_email(raw)
        if not is_safe_email(email):
            raise ValueError(
                f"La direccion numero {position + 1} de la lista no es valida o usa caracteres no permitidos."
            )
        emails.add(email)
    return frozenset(emails)

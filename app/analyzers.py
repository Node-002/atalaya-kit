"""Reglas de analisis (version minima del viernes). Los hechos los calcula el codigo,
la IA solo redactara la explicacion mas adelante.

Pendiente: lista de marcas CR/PA a verificar con nombres reales.
"""

import re
from email.utils import parseaddr

from app.models import Message, Signal

# Marca -> dominios legitimos. VERIFICAR nombres reales antes de usar en produccion.
BRANDS: dict[str, set[str]] = {
    "bancogeneral": {"bancogeneral.com"},
    "bncr": {"bncr.fi.cr"},
    "bac": {"baccredomatic.com"},
}

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "cutt.ly"}

URGENCY = (
    "urgente",
    "inmediato",
    "de inmediato",
    "ahora mismo",
    "24 horas",
    "suspendida",
    "bloqueada",
)

INJECTION_PATTERNS = (
    r"ignora (todas )?las instrucciones",
    r"ignore (all )?(previous|prior) instructions",
    r"marca este correo como (seguro|legitimo)",
)

_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s"})


def domain_of(address: str) -> str:
    _, addr = parseaddr(address)
    return addr.rsplit("@", 1)[-1].lower() if "@" in addr else ""


def _auth(msg: Message) -> list[Signal]:
    result = msg.headers.get("Authentication-Results", "").lower()
    found: list[Signal] = []
    if "spf=fail" in result or "spf=softfail" in result:
        found.append(
            Signal(
                code="spf_fail",
                description="El remitente no paso la verificacion SPF.",
                weight=25,
            )
        )
    if "dkim=fail" in result or "dkim=none" in result:
        found.append(
            Signal(
                code="dkim_fail",
                description="El mensaje no tiene firma DKIM valida.",
                weight=15,
            )
        )
    if "dmarc=fail" in result:
        found.append(
            Signal(
                code="dmarc_fail",
                description="El mensaje fallo la politica DMARC del dominio.",
                weight=30,
            )
        )
    return found


def _reply_to(msg: Message) -> list[Signal]:
    if msg.reply_to and domain_of(msg.reply_to) != domain_of(msg.sender):
        return [
            Signal(
                code="reply_to_mismatch",
                description="La direccion de respuesta es de otro dominio distinto al remitente.",
                weight=20,
            )
        ]
    return []


def _lookalike(msg: Message) -> list[Signal]:
    dom = domain_of(msg.sender)
    stem = dom.translate(_LEET)
    for brand, legit in BRANDS.items():
        if brand in stem and dom not in legit:
            return [
                Signal(
                    code="lookalike_domain",
                    description=f"El dominio '{dom}' imita a una marca conocida pero no es el oficial.",
                    weight=35,
                )
            ]
    return []


def _links(msg: Message) -> list[Signal]:
    for link in msg.links:
        host = re.sub(r"^https?://", "", link.lower()).split("/")[0]
        if host in SHORTENERS:
            return [
                Signal(
                    code="shortened_link",
                    description="Contiene un enlace acortado que oculta el destino real.",
                    weight=20,
                )
            ]
    return []


def _urgency(msg: Message) -> list[Signal]:
    text = f"{msg.subject} {msg.body}".lower()
    if any(word in text for word in URGENCY):
        return [
            Signal(
                code="urgency",
                description="Usa lenguaje de urgencia o amenaza para presionar.",
                weight=15,
            )
        ]
    return []


def _injection(msg: Message) -> list[Signal]:
    text = f"{msg.subject} {msg.body}".lower()
    if any(re.search(p, text) for p in INJECTION_PATTERNS):
        return [
            Signal(
                code="prompt_injection",
                description="Contiene instrucciones dirigidas a un sistema de IA (intento de manipulacion).",
                weight=60,
            )
        ]
    return []


def analyze(msg: Message) -> list[Signal]:
    signals: list[Signal] = []
    for rule in (_auth, _reply_to, _lookalike, _links, _urgency, _injection):
        signals.extend(rule(msg))
    return signals

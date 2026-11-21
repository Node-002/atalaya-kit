"""Reglas de analisis (version minima del viernes). Los hechos los calcula el codigo,
la IA solo redactara la explicacion mas adelante.

Pendiente: verificar con nombres reales los dominios oficiales de la lista de marcas.
"""

import re
from email.utils import parseaddr

from app import lookalike
from app.models import Message, Signal

_GOOGLE = {"google.com", "gmail.com", "googlemail.com", "google.com.pa", "google.co.cr"}
_MICROSOFT = {
    "microsoft.com",
    "microsoftonline.com",
    "outlook.com",
    "office.com",
    "office365.com",
    "live.com",
    "hotmail.com",
}
_APPLE = {"apple.com", "icloud.com"}
_AMAZON = {"amazon.com", "amazon.es", "amazon.com.mx", "amazon.co.uk", "amazon.de"}
_FACEBOOK = {"facebook.com", "facebookmail.com", "fb.com", "meta.com", "messenger.com"}
_DAVIVIENDA = {"davivienda.com", "davivienda.com.pa", "davivienda.cr"}
_CW = {"cwpanama.com", "cwpanama.net"}

# Marca (palabra que aparece en el dominio) -> dominios legitimos. Los subdominios de
# un dominio oficial tambien son oficiales. VERIFICAR nombres reales antes de produccion.
# Una misma empresa puede tener varias palabras (google y gmail comparten dominios).
BRANDS: dict[str, set[str]] = {
    "bancogeneral": {"bancogeneral.com"},
    "bncr": {"bncr.fi.cr"},
    "bac": {"baccredomatic.com"},
    "banistmo": {"banistmo.com"},
    "banconal": {"banconal.com.pa"},
    "davivienda": _DAVIVIENDA,
    "yappy": {"yappy.com.pa"},
    "tigo": {"tigo.com.pa", "tigo.com", "tigo.cr"},
    "cwpanama": _CW,
    "google": _GOOGLE,
    "gmail": _GOOGLE,
    "microsoft": _MICROSOFT,
    "outlook": _MICROSOFT,
    "office365": _MICROSOFT,
    "netflix": {"netflix.com"},
    "dropbox": {"dropbox.com", "dropboxmail.com"},
    "paypal": {"paypal.com", "paypal.me"},
    "apple": _APPLE,
    "icloud": _APPLE,
    "amazon": _AMAZON,
    "facebook": _FACEBOOK,
    "dhl": {"dhl.com", "dhl.de", "dhl.es", "dhl.co.uk"},
}

# Nombres con los que una marca se muestra a la gente (VERIFICAR). No se usa "meta"
# sola porque en espanol es una palabra comun.
BRAND_NAMES: dict[str, tuple[str, ...]] = {
    "bancogeneral": ("banco general", "bancogeneral"),
    "bncr": ("bncr", "banco nacional de costa rica"),
    "bac": ("bac credomatic", "credomatic", "bac"),
    "banistmo": ("banistmo",),
    "banconal": ("banco nacional de panama", "banconal"),
    "davivienda": ("davivienda",),
    "yappy": ("yappy",),
    "tigo": ("tigo",),
    "cwpanama": ("cable & wireless", "cable and wireless", "cwpanama"),
    "google": ("google",),
    "gmail": ("gmail",),
    "microsoft": ("microsoft",),
    "outlook": ("outlook",),
    "office365": ("office 365", "office365"),
    "netflix": ("netflix",),
    "dropbox": ("dropbox",),
    "paypal": ("paypal",),
    "apple": ("apple",),
    "icloud": ("icloud",),
    "amazon": ("amazon",),
    "facebook": ("facebook", "meta platforms"),
    "dhl": ("dhl",),
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


def _candidate_hosts(msg: Message) -> list[str]:
    """Dominios que una persona veria: remitente, respuesta y enlaces."""
    hosts = [domain_of(msg.sender)]
    if msg.reply_to:
        hosts.append(domain_of(msg.reply_to))
    for link in msg.links:
        hosts.append(
            re.sub(r"^https?://", "", link.lower()).split("/")[0].split(":")[0]
        )
    return [h for h in hosts if h]


def _impersonation(msg: Message) -> list[Signal]:
    """Dominios que imitan una marca, con o sin trucos de caracteres (homografos)."""
    lookalike_dom: str | None = None
    trick = False
    mixed_dom: str | None = None
    for dom in _candidate_hosts(msg):
        ascii_dom = lookalike.to_ascii(dom)
        stem = lookalike.fold(lookalike.to_unicode(dom))
        for brand, official in BRANDS.items():
            if lookalike.mentions_brand(stem, brand) and not lookalike.is_official(
                ascii_dom, official
            ):
                lookalike_dom = lookalike_dom or ascii_dom
                trick = trick or lookalike.uses_special_characters(dom)
        if mixed_dom is None and lookalike.is_mixed_script(dom):
            mixed_dom = ascii_dom
    signals: list[Signal] = []
    if lookalike_dom:
        signals.append(
            Signal(
                code="lookalike_domain",
                description=f"El dominio '{lookalike_dom}' imita a una marca conocida pero no es el oficial.",
                weight=35,
            )
        )
    if trick:
        signals.append(
            Signal(
                code="homograph_domain",
                description="Usa letras de otro alfabeto o con marcas especiales que se ven iguales a las normales para hacerse pasar por la marca.",
                weight=30,
            )
        )
    if mixed_dom:
        signals.append(
            Signal(
                code="mixed_script_domain",
                description=f"El dominio '{mixed_dom}' mezcla alfabetos distintos (por ejemplo latino y cirilico), una tecnica comun de suplantacion.",
                weight=40,
            )
        )
    return signals


def _display_name(msg: Message) -> list[Signal]:
    """El nombre visible aparenta ser una marca, pero la direccion es de otro dominio."""
    name, _ = parseaddr(msg.sender)
    folded = lookalike.fold(name)
    sender_ascii = lookalike.to_ascii(domain_of(msg.sender))
    for brand, aliases in BRAND_NAMES.items():
        if lookalike.mentions_brand_name(folded, aliases) and not lookalike.is_official(
            sender_ascii, BRANDS[brand]
        ):
            return [
                Signal(
                    code="display_name_brand",
                    description="El nombre del remitente aparenta ser de una marca conocida, pero la direccion es de otro dominio.",
                    weight=30,
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
    for rule in (
        _auth,
        _reply_to,
        _impersonation,
        _display_name,
        _links,
        _urgency,
        _injection,
    ):
        signals.extend(rule(msg))
    return signals

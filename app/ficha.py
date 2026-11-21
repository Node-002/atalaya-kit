"""Ficha tecnica de un correo: lista BLANCA de metadatos de cabeceras.

Se guarda solo lo necesario para explicar el veredicto: resultado de SPF/DKIM/DMARC, la IP de
origen, el Return-Path con la parte local enmascarada, el host de cada enlace neutralizado, el
dominio de Reply-To, el vector de ataque y un subconjunto saneado de cabeceras SMTP.

NUNCA se guarda el asunto, el cuerpo, los adjuntos ni una direccion de correo completa. El texto
sale de cabeceras ajenas (dato hostil): aqui se limpia y se acota, y la interfaz lo muestra con
textContent.
"""

import ipaddress
import re
from email.utils import parseaddr

from app.analyzers import link_parts
from app.models import Ficha, Message, Signal

MAX_HEADER_LINES = 12
MAX_RECEIVED = 5
MAX_LINK_HOSTS = 5
MAX_LINE = 240
MAX_BYTES = 2048  # tope de la ficha entera, ya serializada

_EMAIL = re.compile(r"[\w.+'-]+@([\w-]+(?:\.[\w-]+)+)")
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f<>]")
_AUTH = re.compile(
    r"\b(spf|dkim|dmarc)\s*=\s*(pass|fail|none|softfail|neutral|temperror|permerror)",
    re.IGNORECASE,
)
_IPV4 = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
_IPV6 = re.compile(
    r"(?<![\w:])((?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4})(?![\w:])", re.IGNORECASE
)
_BY = re.compile(r"\bby\s+([A-Za-z0-9.-]{1,80})", re.IGNORECASE)
_FROM = re.compile(r"\bfrom\s+([A-Za-z0-9.-]{1,80})", re.IGNORECASE)
_TAG = re.compile(r"\b([ds])=([A-Za-z0-9.-]{1,80})", re.IGNORECASE)
_DOMAIN = re.compile(r"[A-Za-z0-9.-]{1,120}")

# Las redes de documentacion no son "publicas" para Python, pero la demo las usa a proposito
# (son direcciones que nunca existen en internet).
_DOC_NETS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
]

# codigo de senal -> (texto del vector de ataque). El orden de VECTOR_PRIORITY decide el principal.
SIGNAL_VECTOR = {
    "prompt_injection": "Instrucciones a la IA (manipulación)",
    "mixed_script_domain": "Dominio con letras engañosas (homógrafo)",
    "homograph_domain": "Dominio con letras engañosas (homógrafo)",
    "lookalike_domain": "Suplantación de marca / dominio parecido",
    "display_name_brand": "Suplantación de marca / dominio parecido",
    "reply_to_mismatch": "Respuesta desviada a otro dominio",
    "shortened_link": "Enlace acortado",
    "urgency": "Presión de urgencia",
    "spf_fail": "Autenticación fallida (SPF/DKIM/DMARC)",
    "dkim_fail": "Autenticación fallida (SPF/DKIM/DMARC)",
    "dmarc_fail": "Autenticación fallida (SPF/DKIM/DMARC)",
}
OTHER_VECTOR = "Otro"
NO_VECTOR = "Ninguno"


def vector_of_code(code: str) -> str:
    if code in SIGNAL_VECTOR:
        return SIGNAL_VECTOR[code]
    return "Análisis semántico (IA)" if code.startswith("ai_") else OTHER_VECTOR


def vector_of(signals: list[Signal]) -> str:
    """Vector principal: el de la senal con mas peso. Lo calcula el codigo, no la IA."""
    if not signals:
        return NO_VECTOR
    top = max(signals, key=lambda s: s.weight)
    return vector_of_code(top.code)


def _clean(text: str, limit: int = MAX_LINE) -> str:
    """Una linea, sin caracteres de control ni '<>', sin direcciones de correo completas."""
    text = _CTRL.sub(" ", str(text))
    text = _EMAIL.sub(r"***@\1", text)
    return " ".join(text.split())[:limit]


def _domain(text: str) -> str:
    m = _DOMAIN.search(text or "")
    return m.group(0).strip(".").lower()[:120] if m else ""


def mask_address(value: str | None) -> str | None:
    """ab***@dominio: del usuario solo quedan sus dos primeras letras."""
    _, addr = parseaddr(value or "")
    if "@" not in addr:
        return None
    local, _, host = addr.rpartition("@")
    host = _domain(host)
    if not host:
        return None
    return f"{_CTRL.sub('', local)[:2]}***@{host}"


def neutralize(link: str) -> str | None:
    """https://host.tld/ruta?x=1 -> hxxps://host[.]tld  (sin ruta ni parametros)."""
    _, host = link_parts(link)
    host = _domain(host)
    if not host or "." not in host:
        return None
    scheme = "hxxps" if link.strip().lower().startswith("https") else "hxxp"
    return f"{scheme}://{host.replace('.', '[.]')}"


def _public(text: str) -> bool:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return False
    return ip.is_global or any(ip in net for net in _DOC_NETS if ip.version == 4)


def _ips(line: str) -> list[str]:
    found = _IPV4.findall(line) + _IPV6.findall(line)
    return [i for i in found if _public(i)]


def _received_summary(line: str) -> str:
    """'from host (ip) by host' de una cabecera Received, sin direcciones de correo."""
    frm = _FROM.search(line)
    by = _BY.search(line)
    ips = _ips(line)
    parts = []
    if frm:
        parts.append(f"from {frm.group(1).lower()}")
    if ips:
        parts.append(f"[{ips[0]}]")
    if by:
        parts.append(f"by {by.group(1).lower()}")
    return " ".join(parts) or "(sin datos legibles)"


def _lines(msg: Message, name: str) -> list[str]:
    return [v for k, v in msg.header_lines if k.lower() == name]


def _auth_results(msg: Message) -> dict[str, str]:
    text = " ".join(_lines(msg, "authentication-results")) or msg.headers.get(
        "Authentication-Results", ""
    )
    out: dict[str, str] = {}
    for key, value in _AUTH.findall(text):
        out.setdefault(key.lower(), value.lower())
    return out


def build_ficha(msg: Message, signals: list[Signal]) -> Ficha:
    auth = _auth_results(msg)
    received = _lines(msg, "received")  # de la mas nueva a la mas vieja
    # Origen = la IP publica mas antigua de la cadena (el primer salto desde el remitente)
    source_ip = next(
        (ips[0] for line in reversed(received) if (ips := _ips(line))), None
    )
    if source_ip is None:
        source_ip = next(
            (
                ips[0]
                for line in msg.header_lines
                if line[0].lower() == "x-originating-ip" and (ips := _ips(line[1]))
            ),
            None,
        )
    return_path = mask_address((_lines(msg, "return-path") or [""])[0])
    hosts: list[str] = []
    for link in msg.links:
        n = neutralize(link)
        if n and n not in hosts:
            hosts.append(n)
    smtp: list[str] = []
    if return_path:
        smtp.append(f"Return-Path: {return_path}")
    for line in received[:MAX_RECEIVED]:
        smtp.append(f"Received: {_received_summary(line)}")
    for name, label in (
        ("authentication-results", "Authentication-Results"),
        ("received-spf", "Received-SPF"),
    ):
        for value in _lines(msg, name)[:1]:
            smtp.append(f"{label}: {_clean(value)}")
    for value in _lines(msg, "dkim-signature")[:1]:
        tags = {k.lower(): v.lower() for k, v in _TAG.findall(value)}
        smtp.append(
            "DKIM-Signature: "
            + "; ".join(f"{k}={tags[k]}" for k in ("d", "s") if k in tags)
        )
    for value in _lines(msg, "message-id")[:1]:
        m = re.search(r"@([A-Za-z0-9.-]{1,120})", value)
        if m:
            smtp.append(f"Message-ID: @{m.group(1).lower()}")
    ficha = Ficha(
        spf=auth.get("spf"),
        dkim=auth.get("dkim"),
        dmarc=auth.get("dmarc"),
        source_ip=source_ip,
        return_path=return_path,
        reply_to_domain=_domain(parseaddr(msg.reply_to or "")[1].rpartition("@")[2])
        or None,
        link_hosts=hosts[:MAX_LINK_HOSTS],
        vector=vector_of(signals),
        smtp=[_clean(s) for s in smtp[:MAX_HEADER_LINES]],
    )
    return _fit(ficha)


def _fit(ficha: Ficha) -> Ficha:
    """Tope de tamano: si la ficha serializada pasa de MAX_BYTES se recortan las cabeceras."""
    while ficha.smtp and len(ficha.model_dump_json().encode()) > MAX_BYTES:
        ficha.smtp.pop()
    while ficha.link_hosts and len(ficha.model_dump_json().encode()) > MAX_BYTES:
        ficha.link_hosts.pop()
    return ficha

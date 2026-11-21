"""Reglas de analisis (version minima del viernes). Los hechos los calcula el codigo,
la IA solo redactara la explicacion mas adelante.

Los dominios oficiales de cada marca se verificaron con fuentes publicas (ver
docs/VERIFICACION_MARCAS.md).
"""

import re
from email.utils import parseaddr

from app import lookalike
from app.models import Message, Signal


def _tlds(prefix: str, suffixes: str, sep: str = ".") -> set[str]:
    """prefix + cada sufijo ('google' + 'de' -> 'google.de'; con sep='-': 'paypal-mktg.com')."""
    return {f"{prefix}{sep}{s}" for s in suffixes.split()}


# Dominios oficiales verificados el 21 nov 2026. Fuentes y dominios dejados fuera a
# proposito (alojamiento de terceros, sin confirmar): docs/VERIFICACION_MARCAS.md.
# Google: lista publica de Google https://www.google.com/supported_domains
_GOOGLE = {"google.com", "gmail.com", "googlemail.com", "google-analytics.com"} | _tlds(
    "google",
    """
    ad ae al am as at az ba be bf bg bi bj bs bt by ca cat cd cf cg ch ci cl cm cn
    co.ao co.bw co.ck co.cr co.id co.il co.in co.jp co.ke co.kr co.ls co.ma co.mz
    co.nz co.th co.tz co.ug co.uk co.uz co.ve co.vi co.za co.zm co.zw com.af com.ag
    com.ar com.au com.bd com.bh com.bn com.bo com.br com.bz com.co com.cu com.cy
    com.do com.ec com.eg com.et com.fj com.gh com.gi com.gt com.hk com.jm com.kh
    com.kw com.lb com.ly com.mm com.mt com.mx com.my com.na com.ng com.ni com.np
    com.om com.pa com.pe com.pg com.ph com.pk com.pr com.py com.qa com.sa com.sb
    com.sg com.sl com.sv com.tj com.tr com.tw com.ua com.uy com.vc com.vn cv cz de dj
    dk dm dz ee es fi fm fr ga ge gg gl gm gr gy hn hr ht hu ie im iq is it je jo kg
    ki kz la li lk lt lu lv md me mg mk ml mn mu mv mw ne nl no nr nu pl pn ps pt ro
    rs ru rw sc se sh si sk sm sn so sr st td tg tl tm tn to tt vu ws
    """,
)
_MICROSOFT = {
    "microsoft.com",
    "microsoft365.com",
    "microsoftstore.com",
    "microsoftonline.com",
    "outlook.com",
    "office.com",
    "office365.com",
    "live.com",
    "hotmail.com",
}
_APPLE = {
    "apple.com",
    "apple.com.cn",
    "apple.co",
    "apple.news",
    "icloud.com",
    "icloud.com.cn",
}
_AMAZON = _tlds(
    "amazon",
    "com es com.mx co.uk de fr it ca com.br co.jp jp in co.in com.au nl se pl sg ae sa com.tr com.be eg",
)
_FACEBOOK = {
    "facebook.com",
    "facebook.net",
    "facebookmail.com",
    "fb.com",
    "meta.com",
    "messenger.com",
}
_WHATSAPP = {"whatsapp.com", "whatsapp.net", "wa.me"}
_DAVIVIENDA = {
    "davivienda.com",
    "davivienda.com.pa",
    "davivienda.cr",
    "davivienda.hn",
    "davivienda.com.hn",
    "davivienda.com.sv",
}
_CW = {"cwpanama.com", "cwpanama.net"}
_BANCOGENERAL = {
    "bancogeneral.com",
    "bgeneral.com",
    "banco-general.com",
    "bgeneral.fi.cr",
    "bgeneralcr.com",
}
_PAYPAL = (
    {"paypal.com", "paypal.me"}
    | _tlds(
        "paypal",
        "at be biz ca ch cl co.id co.il co.in co.nz co.th co.uk co.za com com.ar com.au com.br com.cn com.hk com.mx com.pe com.sa com.sg com.tr com.tw com.ve de dk es eu fi fr ie in it jp lu me nl no ph pl pt se vn ai",
    )
    | _tlds(
        "paypal",
        "australia.com.au business.co.uk business.com.au businesscenter.com communications.com corp.com danmark.dk donations.co.uk donations.com experience.com gifts.com globalshops.com information.com knowledge.com latam.com marketing.ca marketing.co.uk media.com mena.com mktg.com nakit.com norge.no optimizer.com partners.com passport.com prepagata.com promo.es support.com sverige.se turkiye.com workplace.com",
        sep="-",
    )
)
_DHL = _tlds(
    "dhl",
    """
    ae af al at ba be bg ch cl co.bw co.il co.in co.ir co.jp co.ke co.ls co.mu co.mw
    co.nz co.rs co.tz co.ug co.uk co.za co.zm co.zw com com.af com.au com.bb com.bd
    com.bh com.bm com.bn com.bs com.co com.cy com.ge com.gh com.jm com.kh com.kw
    com.la com.lb com.lk com.mk com.mt com.my com.na com.ng com.np com.om com.pe
    com.pg com.pk com.qa com.sa com.sg com.tr com.tt com.ua cz de dk ee es fi fr gr hr
    hu ie in is it jo kz lt lu lv mk nl no pt ro se si sk vg
    """,
) | {"dhl-usa.com", "dhlegypt.com"}
_SCOTIABANK = {
    "scotiabank.com",
    "scotiabank.ca",
    "scotiabank.com.pa",
    "scotiabankfc.com",
}
_DOCUSIGN = _tlds(
    "docusign", "com net ca co.uk com.au com.br com.es de fr in it jp mx nl sg"
)

# Marca (palabra que aparece en el dominio) -> dominios legitimos. Los subdominios de
# un dominio oficial tambien son oficiales. Verificados (ver arriba); lo dudoso quedo fuera.
# Una misma empresa puede tener varias palabras (google y gmail comparten dominios).
BRANDS: dict[str, set[str]] = {
    "bancogeneral": _BANCOGENERAL,
    "bgeneral": _BANCOGENERAL,
    "bncr": {"bncr.fi.cr"},
    "bac": {"baccredomatic.com", "baccredomatic.cr", "baccredomatic.sv", "bac.net"},
    "banistmo": {"banistmo.com", "banistmo.com.pa"},
    "banconal": {"banconal.com.pa"},
    "davivienda": _DAVIVIENDA,
    "yappy": {"yappy.com.pa"},
    "tigo": {"tigo.com.pa", "tigo.com", "tigo.cr"},
    "cwpanama": _CW,
    "bancolombia": {"bancolombia.com"},
    "scotiabank": _SCOTIABANK,
    "google": _GOOGLE,
    "gmail": _GOOGLE,
    "microsoft": _MICROSOFT,
    "outlook": _MICROSOFT,
    "office365": _MICROSOFT,
    "netflix": {"netflix.com", "netflix.ca"},
    "dropbox": {"dropbox.com", "dropboxmail.com"},
    "paypal": _PAYPAL,
    "apple": _APPLE,
    "icloud": _APPLE,
    "amazon": _AMAZON,
    "facebook": _FACEBOOK,
    "instagram": {"instagram.com"},
    "whatsapp": _WHATSAPP,
    "linkedin": {"linkedin.com"},
    "docusign": _DOCUSIGN,
    "dhl": _DHL,
}

# Nombres con los que una marca se muestra a la gente. No se usa "meta"
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
    "bancolombia": ("bancolombia",),
    "scotiabank": ("scotiabank",),
    "instagram": ("instagram",),
    "whatsapp": ("whatsapp",),
    "linkedin": ("linkedin",),
    "docusign": ("docusign",),
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
    return addr.rsplit("@", 1)[-1].lower().rstrip(".") if "@" in addr else ""


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
    if msg.reply_to and not _same_org(domain_of(msg.reply_to), domain_of(msg.sender)):
        return [
            Signal(
                code="reply_to_mismatch",
                description="La direccion de respuesta es de otro dominio distinto al remitente.",
                weight=20,
            )
        ]
    return []


def link_parts(link: str) -> tuple[str, str]:
    """(texto antes de '@', host real) de un enlace. El host real es lo que hay DESPUES
    de la arroba ('http://paypal.com@evil.example' va a evil.example), sin puerto ni
    punto final. Entiende 'hxxp://' y '//'."""
    rest = re.sub(r"^[a-z][a-z0-9+.-]*:(?://)?|^//", "", link.strip().lower())
    authority = re.split(r"[/?#\\]", rest, maxsplit=1)[0]
    userinfo, _, hostport = authority.rpartition("@")
    host = hostport if hostport.startswith("[") else hostport.split(":")[0]
    return userinfo, host.rstrip(".")


def _same_org(a: str, b: str) -> bool:
    """Mismo dominio o uno es subdominio del otro (mail.empresa.com / empresa.com)."""
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _candidate_hosts(msg: Message) -> list[tuple[str, str]]:
    """(lo que una persona leeria, host real): remitente, respuesta y enlaces."""
    hosts = [(domain_of(msg.sender),) * 2]
    if msg.reply_to:
        hosts.append((domain_of(msg.reply_to),) * 2)
    for link in msg.links:
        userinfo, host = link_parts(link)
        hosts.append((f"{userinfo}.{host}" if userinfo else host, host))
    return [(shown, real) for shown, real in hosts if real]


def _impersonation(msg: Message) -> list[Signal]:
    """Dominios que imitan una marca, con o sin trucos de caracteres (homografos)."""
    lookalike_dom: str | None = None
    trick = False
    mixed_dom: str | None = None
    for shown, dom in _candidate_hosts(msg):
        ascii_dom = lookalike.to_ascii(dom)
        stem = lookalike.fold(lookalike.to_unicode(shown))
        for brand, official in BRANDS.items():
            if lookalike.mentions_brand(stem, brand) and not lookalike.is_official(
                ascii_dom, official
            ):
                lookalike_dom = lookalike_dom or ascii_dom
                trick = trick or lookalike.uses_special_characters(shown)
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
        if link_parts(link)[1] in SHORTENERS:
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

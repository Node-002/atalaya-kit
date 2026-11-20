"""Deteccion de dominios y nombres que imitan a una marca, incluidos los ataques
homografos (letras de otros alfabetos que se ven iguales).

La tabla de confusables es PARCIAL (cirilico y griego frecuentes). Lo ideal en
produccion es la lista oficial de Unicode (UTS #39). Aqui se cubre lo mas usado.
Se escribe con codigos numericos (no con las letras) para que sea legible y auditable.
"""

import re
import unicodedata

# codigo Unicode -> letra latina con la que se confunde
_CONFUSABLES = str.maketrans(
    {
        # cirilico
        0x0430: "a",  # CYRILLIC SMALL A
        0x0435: "e",  # CYRILLIC SMALL IE
        0x043E: "o",  # CYRILLIC SMALL O
        0x0440: "p",  # CYRILLIC SMALL ER
        0x0441: "c",  # CYRILLIC SMALL ES
        0x0443: "y",  # CYRILLIC SMALL U
        0x0445: "x",  # CYRILLIC SMALL HA
        0x0456: "i",  # CYRILLIC SMALL BYELORUSSIAN-UKRAINIAN I
        0x0458: "j",  # CYRILLIC SMALL JE
        0x04BB: "h",  # CYRILLIC SMALL SHHA
        0x0501: "d",  # CYRILLIC SMALL KOMI DE
        0x043A: "k",  # CYRILLIC SMALL KA
        0x043C: "m",  # CYRILLIC SMALL EM
        0x043D: "h",  # CYRILLIC SMALL EN
        0x0442: "t",  # CYRILLIC SMALL TE
        0x0455: "s",  # CYRILLIC SMALL DZE
        0x04CF: "l",  # CYRILLIC SMALL PALOCHKA
        0x0432: "b",  # CYRILLIC SMALL VE
        # griego
        0x03BF: "o",  # GREEK SMALL OMICRON
        0x03B1: "a",  # GREEK SMALL ALPHA
        0x03BD: "v",  # GREEK SMALL NU
        0x03C1: "p",  # GREEK SMALL RHO
        0x03B9: "i",  # GREEK SMALL IOTA
        0x03BA: "k",  # GREEK SMALL KAPPA
        0x03C4: "t",  # GREEK SMALL TAU
        0x03C5: "u",  # GREEK SMALL UPSILON
        0x03B5: "e",  # GREEK SMALL EPSILON
        # latinas especiales
        0x0251: "a",  # LATIN SMALL ALPHA
        0x0261: "g",  # LATIN SMALL SCRIPT G
        0x0131: "i",  # LATIN SMALL DOTLESS I
        0x2113: "l",  # SCRIPT SMALL L
    }
)
_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s"})


def to_ascii(domain: str) -> str:
    """Forma segura para mostrar: punycode (xn--...) si el dominio usa caracteres especiales."""
    try:
        return domain.encode("idna").decode("ascii")
    except UnicodeError:
        return domain


def to_unicode(domain: str) -> str:
    """Decodifica punycode (xn--...) a lo que veria una persona en pantalla."""
    try:
        return domain.encode("ascii").decode("idna")
    except UnicodeError:
        return domain


def fold(text: str) -> str:
    """Reduce un texto a su 'apariencia' latina simple: sin acentos, sin letras
    de otros alfabetos parecidas, minusculas y sin sustituciones numericas."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().translate(_CONFUSABLES).translate(_LEET)


def _scripts(label: str) -> set[str]:
    return {unicodedata.name(ch, "?").split(" ")[0] for ch in label if ch.isalpha()}


def is_mixed_script(domain: str) -> bool:
    """True si alguna parte del dominio mezcla alfabetos (p. ej. latino + cirilico)."""
    return any(len(_scripts(label)) > 1 for label in to_unicode(domain).split("."))


def uses_special_characters(domain: str) -> bool:
    """True si el dominio tiene caracteres no ASCII (o esta en punycode)."""
    return any(ord(ch) > 127 for ch in to_unicode(domain))


def is_official(ascii_domain: str, official: set[str]) -> bool:
    """Dominio oficial o subdominio suyo (mail.bancogeneral.com). Compara en ASCII."""
    return any(ascii_domain == d or ascii_domain.endswith("." + d) for d in official)


def mentions_brand(stem: str, brand: str) -> bool:
    """Marcas cortas (bac, bncr) solo cuentan como palabra completa del dominio,
    para no marcar 'backups-empresa'. Marcas largas y distintivas tambien como parte."""
    tokens = re.split(r"[^a-z0-9]+", stem)
    return brand in tokens or (len(brand) >= 8 and brand in stem)


def mentions_brand_name(folded_name: str, aliases: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(a)}\b", folded_name) for a in aliases)

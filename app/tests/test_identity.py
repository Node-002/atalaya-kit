from app.identity import is_safe_email, normalize_email

CYR_A = chr(0x0430)  # CYRILLIC SMALL A, identica a la a latina
GREEK_O = chr(0x03BF)  # GREEK SMALL OMICRON


def test_normal_addresses_are_accepted():
    for email in (
        "ana@gmail.com",
        "maria.lopez+rrhh@empresa.com.pa",
        "o'brien@empresa.co.cr",
        "a_b-c@mail.sub.empresa.org",
    ):
        assert is_safe_email(email), email


def test_lookalike_letters_are_rejected():
    assert not is_safe_email(f"ana@b{CYR_A}ncogeneral.com")
    assert not is_safe_email(f"an{CYR_A}@gmail.com")
    assert not is_safe_email(f"ana@empresa.c{GREEK_O}m")


def test_accents_and_fullwidth_letters_are_rejected():
    assert not is_safe_email("ana@bancógeneral.com")
    assert not is_safe_email("ana@empresa.com".replace("a", "ａ", 1))


def test_punycode_domains_are_rejected():
    puny = f"b{CYR_A}ncogeneral.com".encode("idna").decode("ascii")
    assert puny.startswith("xn--") and not is_safe_email(f"ana@{puny}")


def test_malformed_values_are_rejected():
    for bad in (
        "",
        "sin-arroba",
        "a@b",
        "a b@empresa.com",
        "a@@empresa.com",
        "@empresa.com",
    ):
        assert not is_safe_email(bad), bad


def test_normalization_is_case_and_space_insensitive():
    assert normalize_email("  Ana@Empresa.COM ") == "ana@empresa.com"

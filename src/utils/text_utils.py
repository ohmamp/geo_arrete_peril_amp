"""Fonctions utilitaires génériques pour le texte.

"""

import re
import unicodedata


# graphies de "n°"
RE_NO = r"n[°º]"

# numéraux: ordinaux et cardinaux
RE_ORDINAUX = (  # jusqu'à 15 devrait suffire?
    r"(?:premier|deuxi[èe]me|second|troisi[èe]me|quatri[èe]me|cinqui[èe]me|sixi[èe]me|septi[èe]me|huiti[èe]me|neuvi[èe]me|dixi[èe]me"
    + r"|onzi[èe]me|douzi[èe]me|treizi[èe]me|quatorzi[èe]me|quinzi[èe]me)"
)
RE_CARDINAUX = r"un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze"

# normalisation des tirets, apostrophes
# <https://github.com/gorgitko/molminer/blob/master/molminer/normalize.py>
# <https://github.com/mcs07/ChemDataExtractor/blob/master/chemdataextractor/text/__init__.py>
# alternative: utiliser la lib regex <https://stackoverflow.com/a/48923796>
#
#: Hyphen and dash characters.
HYPHENS = {
    # "-",  # \u002d Hyphen-minus
    "‐",  # \u2010 Hyphen
    "‑",  # \u2011 Non-breaking hyphen
    "⁃",  # \u2043 Hyphen bullet
    "‒",  # \u2012 figure dash
    "–",  # \u2013 en dash
    "—",  # \u2014 em dash
    "―",  # \u2015 horizontal bar
}

#: Minus characters.
MINUSES = {
    "-",  # \u002d Hyphen-minus
    "−",  # \u2212 Minus
    "－",  # \uff0d Full-width Hyphen-minus
    "⁻",  # \u207b Superscript minus
}

#: Apostrophe characters.
APOSTROPHES = {
    "'",  # \u0027
    "’",  # \u2019
    "՚",  # \u055a
    "Ꞌ",  # \ua78b
    "ꞌ",  # \ua78c
    "＇",  # \uff07
}


# motif pour capturer tout le texte sauf les espaces initiaux et finaux
RE_STRIP = (
    r"(?:\s*)"  # espaces initiaux
    + r"(?P<outstrip>\S[\s\S]*?)"  # texte à capturer
    + r"(?:\s*)"  # espaces finaux
)
P_STRIP = re.compile(RE_STRIP, re.IGNORECASE | re.MULTILINE)

# motif pour capturer les lignes (pour ne pas les confondre avec du vrai texte, en garde-fou avant STRIP)
RE_LINE = (
    r"(?:\s*)"  # espaces initiaux
    + r"(?:_{3,})"  # capturer les traits/lignes "_______"
    + r"(?:\s*)"  # espaces finaux
)
P_LINE = re.compile(RE_LINE, re.IGNORECASE | re.MULTILINE)


# suppression des accents, cédilles etc
def remove_accents(str_in: str) -> str:
    """Enlève les accents d'une chaîne de caractères.

    cf. <https://stackoverflow.com/a/517974>

    Parameters
    ----------
    str_in: string
        Chaîne de caractères pouvant contenir des caractères combinants
        (accents, cédille etc.).

    Returns
    -------
    str_out: string
        Chaîne de caractères sans caractère combinant.
    """
    nfkd_form = unicodedata.normalize("NFKD", str_in)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def normalize_string(
    raw_str: str,
    num: bool = False,
    apos: bool = False,
    hyph: bool = False,
    spaces: bool = False,
) -> str:
    """Normaliser une chaîne de caractères.

    Remplacer les séquences d'espaces par une unique espace.

    Parameters
    ----------
    raw_str: str
        Chaîne de caractères à normaliser

    Returns
    -------
    nor_str: str
        Chaîne de caractères normalisée
    """
    nor_str = raw_str
    if num:
        # graphies de "numéro"
        nor_str = re.sub(RE_NO, "n°", nor_str, flags=re.MULTILINE | re.IGNORECASE)
    if hyph:
        # remplace les tirets (hyphens) par un "en dash" et les moins (minus) par un simple "-"
        # observation sur le stock: les PDF texte contiennent généralement des "en dash" (\u2013),
        # les PDF OCRisés contiennent "em dash" (\u2014)
        for hyphen in HYPHENS:
            nor_str = nor_str.replace(hyphen, "-")  # was: "–")  # \u2013 en dash
        for minus in MINUSES:
            nor_str = nor_str.replace(minus, "-")
        # supprimer les "soft hyphen" (qui sont invisibles au rendu)
        nor_str = nor_str.replace("\u00ad", "")
    if apos:
        # apostrophes
        for single_quote in APOSTROPHES:
            nor_str = nor_str.replace(single_quote, "'")  # \u0027
        # et supprimer les éventuels espaces inutiles après une apostrophe
        nor_str = re.sub(r"[']\s*", "'", nor_str, flags=re.MULTILINE)
    # end TODO
    if spaces:
        # remplacer toutes les suites d'espaces (de tous types) par une espace simple
        nor_str = re.sub(r"\s+", " ", nor_str, flags=re.MULTILINE).strip()
    return nor_str

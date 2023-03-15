"""Fonctions utilitaires génériques pour le texte.

"""

import re
import unicodedata


# graphies de "n°"
RE_NO = r"n[°º]"

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


def normalize_string(raw_str: str) -> str:
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
    nor_str = re.sub(r"\s+", " ", raw_str, flags=re.MULTILINE).strip()
    return nor_str

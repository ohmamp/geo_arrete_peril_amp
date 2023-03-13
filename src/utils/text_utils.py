"""Fonctions utilitaires génériques pour le texte.

"""

import re

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


# normalisation des strings
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

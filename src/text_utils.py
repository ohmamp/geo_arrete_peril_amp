"""Fonctions utilitaires génériques pour le texte.

"""

import re


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

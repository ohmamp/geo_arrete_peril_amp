"""Reconnaissance et mise en forme des dates.

"""

import re
from typing import Dict


# liste des mois et de leurs abréviations
RE_MOIS = (
    r"(?:"
    + r"janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
    + r"|jan|f[ée]v|mars|avr|mai|juin|juil|aou|sep|oct|nov|d[ée]c"
    + r")"
)

# table associative: nom du mois => numéro (sur 2 chiffres)
MAP_MOIS = {
    "janvier": "01",
    "jan": "01",
    "fevrier": "02",
    "fev": "02",
    "mars": "03",
    # "mar": "03",
    "avril": "04",
    "avr": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "juil": "07",  # jul?
    "aout": "08",
    "aou": "08",
    "septembre": "09",
    "sept": "09",  # sep?
    "octobre": "10",
    "oct": "10",
    "novembre": "11",
    "nov": "11",
    "decembre": "12",
    "dec": "12",
}


# FIXME harmoniser/fusionner RE_DATE, RE_DATE_PREC
RE_DATE = (
    r"(?:"
    + r"\d{2}[.]\d{2}[.]\d{4}"  # Peyrolles-en-Provence (en-tête)
    + r"|\d{2}/\d{2}/\d{4}"  # ?
    + r"|\d{1,2} "
    + RE_MOIS
    + r" \d{4}"  # Roquevaire (fin), Martigues (fin)
    + r")"
)

# date: extraction précise des champs
RE_DATE_PREC = (
    r"(?P<dd>\d{1,2})"  # jour
    + r"[\s./-]"
    + r"(?P<mm>\d{2}"  # moi en nombre
    + rf"|{RE_MOIS})"  # ou en lettres (toutes ou abrégées)
    + r"[\s./-]"
    + r"(?P<yyyy>\d{4})"  # Peyrolles-en-Provence (en-tête)
)
P_DATE_PREC = re.compile(RE_DATE_PREC, re.MULTILINE | re.IGNORECASE)


def process_date_brute(arr_date: str) -> Dict:
    """Extraire les différents champs d'une date brute et la normaliser.

    Parameters
    ----------
    arr_date: str
        Date brute

    Returns
    -------
    arr_date_norm: str
        Date normalisée dd/mm/yyyy
    """
    if m_date_p := P_DATE_PREC.search(arr_date):
        m_dict = m_date_p.groupdict()
        # traitement spécifique pour le mois, qui peut être écrit en lettres
        mm_norm = MAP_MOIS.get(
            m_dict["mm"].lower().replace("é", "e").replace("û", "u"), m_dict["mm"]
        )
        return f"{m_dict['dd']:>02}/{mm_norm:>02}/{m_dict['yyyy']}"
    else:
        return None

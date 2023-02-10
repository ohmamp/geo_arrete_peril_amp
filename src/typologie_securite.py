"""Typologie des arrêtés de mise en sécurité.

"""

import re

# - classification des arrêtés
RE_CLASS_PS_PO = r"""Arrêté\s+de\s+péril\s+(simple|ordinaire)"""
M_CLASS_PS_PO = re.compile(RE_CLASS_PS_PO, re.MULTILINE | re.IGNORECASE)
RE_CLASS_PS_PO_MOD = r"""Arrêté\s+de\s+péril\s+(simple|ordinaire)\s+modificatif"""
M_CLASS_PS_PO_MOD = re.compile(RE_CLASS_PS_PO_MOD, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MS = r"""Arrêté\s+de\s+mise\s+en\s+sécurité\s+-\s+procédure\s+ordinaire"""
M_CLASS_MS = re.compile(RE_CLASS_MS, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MS_MOD = (
    r"""Arrêté\s+de\s+mise\s+en\s+sécurité\s+modificatif\s+-\s+procédure\s+ordinaire"""
)
M_CLASS_MS_MOD = re.compile(RE_CLASS_MS_MOD, re.MULTILINE | re.IGNORECASE)
RE_CLASS_PGI = (
    r"""(?:"""
    + r"""Arr[êe]t[ée]\s+de\s+p[ée]ril\s+grave\s+et\s+imminent|"""
    + r"""Arr[êe]t[ée]\s+portant\s+proc[ée]dure\s+de\s+p[ée]ril(?:\s+grave\s+et)?\s+imminent"""
    + r""")"""
)
M_CLASS_PGI = re.compile(RE_CLASS_PGI, re.MULTILINE | re.IGNORECASE)
RE_CLASS_PGI_MOD = (
    r"""("""
    + r"""Arrêté\s+de\s+péril\s+grave\s+et\s+imminent\s+modificatif"""
    + r"""|"""
    + r"""Modification\s+de\s+l'\s+arrêté\s+de\s+péril\s+grave\s+et\s+imminent"""
    + r""")"""
)
M_CLASS_PGI_MOD = re.compile(RE_CLASS_PGI_MOD, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MSU = r"""Arrêté\s+de\s+mise\s+en\s+sécurité\s+-\s+procédure\s+urgente"""
M_CLASS_MSU = re.compile(RE_CLASS_MSU, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MSU_MOD = (
    r"""Arrêté\s+de\s+mise\s+en\s+sécurité\s+modificatif\s+-\s+procédure\s+urgente"""
)
M_CLASS_MSU_MOD = re.compile(RE_CLASS_MSU_MOD, re.MULTILINE | re.IGNORECASE)
RE_CLASS_ML = r"""Arrêté(?:\s+de)?\s+mainlevée"""
M_CLASS_ML = re.compile(RE_CLASS_ML, re.MULTILINE | re.IGNORECASE)
RE_CLASS_ML_PA = r"""Arrêté(?:\s+de)?\s+mainlevée\s+partielle"""
M_CLASS_ML_PA = re.compile(RE_CLASS_ML_PA, re.MULTILINE | re.IGNORECASE)
RE_CLASS_DE = r"""Arrêté\s+de\s+(déconstruction|démolition)"""
M_CLASS_DE = re.compile(RE_CLASS_DE, re.MULTILINE | re.IGNORECASE)
RE_CLASS_ABRO_DE = r"""Abrogation\s+de\s+l'arrêté\s+de\s+(déconstruction|démolition)"""
M_CLASS_ABRO_DE = re.compile(RE_CLASS_ABRO_DE, re.MULTILINE | re.IGNORECASE)
RE_CLASS_INS = r"""Arrêté\s+d'\s*insécurité\s+des\s+équipements\s+communs"""
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)
RE_CLASS_INT = r"""Arrêté\s+d'\s*interdiction\s+d'\s*occuper"""
M_CLASS_INT = re.compile(RE_CLASS_INT, re.MULTILINE | re.IGNORECASE)
RE_CLASS_ABRO_INT = (
    r"""Arrêté\s+d'\s*abrogation\s+de\s+l'\s*interdiction\s+d'\s*occuper"""
)
M_CLASS_ABRO_INT = re.compile(RE_CLASS_ABRO_INT, re.MULTILINE | re.IGNORECASE)
# toutes classes
RE_CLASS_ALL = r"|".join(
    [
        RE_CLASS_PGI_MOD,
        RE_CLASS_PGI,
        RE_CLASS_PS_PO_MOD,
        RE_CLASS_PS_PO,
        RE_CLASS_MSU_MOD,
        RE_CLASS_MSU,
        RE_CLASS_MS_MOD,
        RE_CLASS_MS,
        RE_CLASS_ML_PA,
        RE_CLASS_ML,
        RE_CLASS_ABRO_DE,
        RE_CLASS_DE,
        RE_CLASS_ABRO_INT,
        RE_CLASS_INT,
        RE_CLASS_INS,
    ]
)
M_CLASS_ALL = re.compile(RE_CLASS_ALL, re.MULTILINE | re.IGNORECASE)

# interdiction d'habiter
RE_INTERDICT_HABIT = (
    r"""(?:"""
    + r"""interdiction\s+d'habiter\s+et\s+d'occuper"""
    + r"""|interdiction\s+d'habiter\s+l'appartement"""
    + r""")"""
)
M_INTERDICT_HABIT = re.compile(RE_INTERDICT_HABIT, re.MULTILINE | re.IGNORECASE)

# démolition / déconstruction
# TODO à affiner: démolition d'un mur? déconstruction et reconstruction? etc
# TODO filtrer les pages copiées des textes réglementaires
RE_DEMOL_DECONST = (
    r"""(?:""" + r"""démolir""" + r"""|démolition""" + r"""|déconstruction""" + r""")"""
)
M_DEMOL_DECONST = re.compile(RE_DEMOL_DECONST, re.MULTILINE | re.IGNORECASE)

# (insécurité des) équipements communs
RE_EQUIPEMENTS_COMMUNS = r"""sécurité(?:\s+imminente)\s+des\s+équipements\s+communs"""
M_EQUIPEMENTS_COMMUNS = re.compile(RE_EQUIPEMENTS_COMMUNS, re.MULTILINE | re.IGNORECASE)

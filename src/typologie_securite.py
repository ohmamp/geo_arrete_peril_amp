"""Typologie des arrêtés de mise en sécurité.

"""

# TODO interdiction partielle d'occupation? interdiction d'occuper partielle?
# TODO abrogation d'interdiction partielle d'occupation?
# TODO interdiction d'accès et d'occupation du fond de parcelle => interdiction partielle?
# TODO modification de l'interdiction d'occuper
# TODO mise en demeure de réaliser des travaux

import re

# "arrếté" et ses variantes de graphies
RE_ARRETE = r"Arr[êeé]t[ée](?:\s+municipal)?"
# procédures: orginaire et urgente
RE_PROCEDURE_ORDINAIRE = r"(?:\s*-)?\s+proc[ée]dure\s+ordinaire"
RE_PROCEDURE_URGENTE = (
    r"(?:"
    + r"(?:(?:\s*-)?\s+proc[ée]dure\s+(?:urgente|d['’]\s*urgence))"
    + r"|(?:\s+d['’]\s*urgence)"  # "mise en sécurité d'urgence"
    + r")"
)

# - classification des arrêtés
# péril simple/ordinaire (terminologie précédente)
RE_PS_PO = r"p[ée]ril\s+(?:simple|ordinaire|non\s+imminent)"
RE_CLASS_PS_PO = RE_ARRETE + r"\s+de\s+" + RE_PS_PO
M_CLASS_PS_PO = re.compile(RE_CLASS_PS_PO, re.MULTILINE | re.IGNORECASE)
RE_CLASS_PS_PO_MOD = (
    r"(?:"  # arrêté de péril simple|ordinaire modificatif
    + RE_CLASS_PS_PO
    + r"\s+modificatif"
    + rf"|{RE_ARRETE}"  # arrêté modificatif de l'arrêté de péril simple|ordinaire
    + r"\s+modificatif\s+de\s+l['’]\s*"
    + RE_CLASS_PS_PO
    + rf"|{RE_ARRETE}"  # arrêté modificatif de|du péril simple|ordinaire
    + r"\s+modificatif\s+d[eu]\s+"
    + RE_PS_PO
    + r")"
)
M_CLASS_PS_PO_MOD = re.compile(RE_CLASS_PS_PO_MOD, re.MULTILINE | re.IGNORECASE)

# mise en sécurité (terminologie actuelle)
RE_MISE_EN_SECURITE = r"mise\s+en\s+s[ée]curit[ée]"
RE_ARR_DE_MISE_EN_SECURITE = rf"{RE_ARRETE}" + r"\s+de\s+" + rf"{RE_MISE_EN_SECURITE}"
RE_CLASS_MS = (
    r"(?:"
    + RE_ARR_DE_MISE_EN_SECURITE
    + RE_PROCEDURE_ORDINAIRE
    + rf"|{RE_ARR_DE_MISE_EN_SECURITE}"
    + r"(?!"  # arrêté de mise en sécurité, sauf si suivi de "modificatif" ou "procédure urgente"
    + r"\s+modificatif"
    + rf"|{RE_PROCEDURE_URGENTE}"
    + r")"
    + r")"
)
M_CLASS_MS = re.compile(RE_CLASS_MS, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MS_MOD = (
    r"(?:"
    + RE_ARR_DE_MISE_EN_SECURITE
    + r"\s+modificatif"
    + RE_PROCEDURE_ORDINAIRE
    + rf"|{RE_ARRETE}"
    + r"\s+modificatif\s+de\s+l['’]\s*"
    + RE_ARR_DE_MISE_EN_SECURITE
    + rf"|{RE_ARRETE}"
    + r"\s+modificatif\s+de\s+"
    + RE_MISE_EN_SECURITE
    + r")"
)
M_CLASS_MS_MOD = re.compile(RE_CLASS_MS_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_PGI = r"p[ée]ril" + r"(?:\s+grave(?:\s+et)?)?" + r"\s+imminent"
RE_CLASS_PGI = (
    r"(?:"
    + rf"{RE_ARRETE}"
    + r"""(?:\s+portant\s+proc[ée]dure)?"""
    + r"\s+de\s+"
    + rf"{RE_PGI}"
    + r")"
)
M_CLASS_PGI = re.compile(RE_CLASS_PGI, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_PGI_MOD = (
    r"(?:"
    + RE_CLASS_PGI  # arrêté de péril grave et imminent modificatif
    + r"\s+modificatif"
    + r"|(?:"  # (arrêté modificatif | modification) de l'arrêté de péril grave et imminent
    + rf"{RE_ARRETE}"
    + r"\s+modificatif"
    + r"|Modification"
    + r")"
    + r"\s+de\s+l['’]\s*"
    + RE_CLASS_PGI
    + rf"|{RE_ARRETE}"
    + r"\s+modificatif"
    + r"\s+de\s+"
    + rf"{RE_PGI}"
    + r")"
)
M_CLASS_PGI_MOD = re.compile(RE_CLASS_PGI_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_MSU = RE_ARR_DE_MISE_EN_SECURITE + RE_PROCEDURE_URGENTE
M_CLASS_MSU = re.compile(RE_CLASS_MSU, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_MSU_MOD = (
    r"(?:"  # arrêté de mise en sécurité modificatif - procédure urgente
    + RE_ARR_DE_MISE_EN_SECURITE
    + r"""\s+modificatif"""
    + RE_PROCEDURE_URGENTE
    + rf"|{RE_ARRETE}"  # arrêté modificatif de l'arrêté de mise en sécurité - procédure urgente
    + r"\s+modificatif\s+de\s+l['’]\s*"
    + RE_ARR_DE_MISE_EN_SECURITE
    + RE_PROCEDURE_URGENTE
    + rf"|{RE_ARRETE}"  # arrêté modificatif de mise en sécurité - procédure urgente
    + r"\s+modificatif\s+de\s+"
    + RE_MISE_EN_SECURITE
    + RE_PROCEDURE_URGENTE
    + r")"
)
M_CLASS_MSU_MOD = re.compile(RE_CLASS_MSU_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_ML = r"main[-]?\s*lev[ée]e"
RE_CLASS_ML = (
    r"(?:"
    + r"(?:"  # arrêté de mainlevée
    + RE_ARRETE
    + r"(?:\s+de)?\s+"
    + RE_ML
    + r"(?!\s+partielle)"  # sauf si la suite est "partielle" (negative lookahead)
    + r")"
    + r"|(?:"  # mainlevée de l'arrêté
    + RE_ML
    + r"\s+(?:de\s+l['’]|d['’])\s*"
    + RE_ARRETE
    + r")"
    + r")"
)
M_CLASS_ML = re.compile(RE_CLASS_ML, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ML_PA = (
    r"(?:"
    + r"(?:"
    + rf"{RE_ARRETE}"
    + r"\s+(?:de\s+)?"
    + rf"{RE_ML}"
    + r"\s+partielle"
    + r")"
    + r"|(?:"
    + rf"{RE_ML}"
    + r"\s+partielle"
    + r"\s+de"
    + r")"
    + r")"
)
M_CLASS_ML_PA = re.compile(RE_CLASS_ML_PA, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_DE = (
    r"(?:"
    + rf"{RE_ARRETE}"
    + r"""\s+"""
    + r"""(?:de\s+"""
    + r"""|portant\s+sur\s+"""
    + r"""(?:l['’]installation\s+d['’]un\s+périmètre\s+de\s+sécurité\s+et\s+)?"""
    + r"""la)"""
    + r"""(?:déconstruction|démolition)"""
    + r")"
)
M_CLASS_DE = re.compile(RE_CLASS_DE, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ABRO_DE = (
    r"(?:"
    + r"Abrogation\s+de\s+l['’]"
    + RE_ARRETE
    + r"\s+de\s+(?:d[ée]construction|d[ée]molition)"
    + r")"
)
M_CLASS_ABRO_DE = re.compile(RE_CLASS_ABRO_DE, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_INS = (
    rf"{RE_ARRETE}" + r"""\s+d'\s*ins[ée]curit[ée]\s+des\s+[ée]quipements\s+communs"""
)
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)
#
RE_INTERD_OCCUP = r"interdiction\s+d['’]\s*(?:occuper|occupation)"
RE_CLASS_INT = (
    RE_ARRETE + r"\s+" + r"(?:portant\s+(?:l['’]\s*)?|d['’]\s*)" + RE_INTERD_OCCUP
)
M_CLASS_INT = re.compile(RE_CLASS_INT, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ABRO_INT = (
    r"(?:"
    + rf"{RE_ARRETE}"  # arrêté d'abrogation de l'interdiction d'occuper
    + r"\s+d['’]\s*abrogation\s+de\s+l['’]\s*"
    + RE_INTERD_OCCUP
    + rf"|{RE_ARRETE}"  # arrêté d'abrogation d'arrêté portant interdiction d'occuper
    + r"\s+d['’]\s*abrogation\s+d['’]\s*"
    + RE_ARRETE
    + r"\s+portant\s+(?:(?:sur\s+)?l['’]\s*)?"
    + RE_INTERD_OCCUP
    + r"|abrogation\s+de\s+l['’]\s*"  # abrogation de l'arrêté ... portant sur l'interdiction d'occuper
    + RE_ARRETE
    + r"\s+[\S\s]+?"
    + r"portant\s+(?:(?:sur\s+)?l['’]\s*)?"
    + RE_INTERD_OCCUP
    + rf"|{RE_ARRETE}"  # arrêté portant abrogation de l'arrêté ... portant l'interdiction
    + r"\s+portant\s+abrogation\s+de\s+l['’]\s*"
    + RE_ARRETE
    + r"\s+[\S\s]+?"
    + r"portant\s+(?:(?:sur\s+)?l['’]\s*)?"
    + RE_INTERD_OCCUP
    + r"|abrogation\s+d['’]\s*"  # abrogation d'interdiction d'occupation
    + RE_INTERD_OCCUP
    + r")"
)
M_CLASS_ABRO_INT = re.compile(RE_CLASS_ABRO_INT, re.MULTILINE | re.IGNORECASE)
# toutes classes
RE_CLASSE = (
    r"(?:"
    + r"|".join(
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
    + r")"
)
P_CLASSE = re.compile(RE_CLASSE, re.MULTILINE | re.IGNORECASE)

# interdiction d'habiter
RE_INT_HAB = (
    r"""(?:"""
    + r"""interdiction\s+d['’]habiter\s+et\s+d['’]occuper"""
    + r"""|interdiction\s+d['’]habiter\s+l['’]appartement"""
    + r""")"""
)
P_INT_HAB = re.compile(RE_INT_HAB, re.MULTILINE | re.IGNORECASE)

# démolition / déconstruction
# TODO à affiner: démolition d'un mur? déconstruction et reconstruction? etc
# TODO filtrer les pages copiées des textes réglementaires
RE_DEMO = (
    r"""(?:"""
    + r"""d[ée]molir"""
    + r"""|d[ée]molition"""
    + r"""|d[ée]construction"""
    + r""")"""
)
P_DEMO = re.compile(RE_DEMO, re.MULTILINE | re.IGNORECASE)

# (insécurité des) équipements communs
RE_EQU_COM = r"""s[ée]curit[ée](?:\s+imminente)\s+des\s+[ée]quipements\s+communs"""
P_EQU_COM = re.compile(RE_EQU_COM, re.MULTILINE | re.IGNORECASE)

# TODO exclure les arrêtés de mise en place d'un périmètre de sécurité
# (sauf s'ils ont un autre motif conjoint, eg. périmètre + interdiction d'occuper)
# "ARRÊTE DE MISE EN PLACE D’UN PÉRIMÈTRE DE SÉCURITÉ"
RE_CLASS_PERIM = (
    rf"{RE_ARRETE}"
    + r"""\s+(?:de|portant\s+(?:sur\s+))"""
    + r"""(?:la\s+mise\s+en\s+place|l['’]installation)\s+"""
    + r"""d['’]un\s+p[ée]rim[èe]tre\s+de\s+s[ée]curit[ée]"""
)
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)

# "MODIFICATIF DE L'ARRÊTÉ N°xxxx": exclure? classe?
# ex: "10 place Jean Jaures-Modif 27.01.21.pdf": rectification erreur sur propriétaires

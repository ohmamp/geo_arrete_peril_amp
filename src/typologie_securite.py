"""Typologie des arrêtés de mise en sécurité.

"""

import re

# - classification des arrêtés
# péril simple/ordinaire (terminologie précédente)
RE_CLASS_PS_PO = r"""Arr[êe]t[ée]\s+de\s+p[ée]ril\s+(simple|ordinaire)"""
M_CLASS_PS_PO = re.compile(RE_CLASS_PS_PO, re.MULTILINE | re.IGNORECASE)
RE_CLASS_PS_PO_MOD = (
    r"""(?:"""
    + RE_CLASS_PS_PO
    + r"""\s+modificatif"""
    + r"""|Arr[êe]t[ée]\s+modificatif\s+de\s+l['’]\s*"""
    + RE_CLASS_PS_PO
    + r""")"""
)
M_CLASS_PS_PO_MOD = re.compile(RE_CLASS_PS_PO_MOD, re.MULTILINE | re.IGNORECASE)
# mise en sécurité (terminologie actuelle)
RE_MISE_EN_SECURITE = r"""Arr[êe]t[ée]\s+de\s+mise\s+en\s+s[ée]curit[ée]"""
RE_PROCEDURE_ORDINAIRE = r"""(?:\s*-)?\s+proc[ée]dure\s+ordinaire"""
RE_CLASS_MS = RE_MISE_EN_SECURITE + RE_PROCEDURE_ORDINAIRE
M_CLASS_MS = re.compile(RE_CLASS_MS, re.MULTILINE | re.IGNORECASE)
RE_CLASS_MS_MOD = (
    r"""(?:"""
    + RE_MISE_EN_SECURITE
    + r"""\s+modificatif"""
    + RE_PROCEDURE_ORDINAIRE
    + r"""|Arr[êe]t[ée]\s+modificatif\s+de\s+l['’]\s*"""
    + RE_MISE_EN_SECURITE
    + r""")"""
)
M_CLASS_MS_MOD = re.compile(RE_CLASS_MS_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_PGI = (
    r"""(?:"""
    + r"""Arr[êe]t[ée]"""
    + r"""(?:\s+portant\s+proc[ée]dure)?"""
    + r"""\s+de\s+p[ée]ril"""
    + r"""(?:\s+grave(?:\s+et)?)?"""
    + r"""\s+imminent"""
    + r""")"""
)
M_CLASS_PGI = re.compile(RE_CLASS_PGI, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_PGI_MOD = (
    RE_CLASS_PGI
    + r"""\s+modificatif"""
    + r"""|(?:"""
    + r"""Arr[êe]t[ée]\s+modificatif"""
    + r"""|Modification"""
    + r""")"""
    + r"""\s+de\s+l['’]\s*"""
    + RE_CLASS_PGI
)
M_CLASS_PGI_MOD = re.compile(RE_CLASS_PGI_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_PROCEDURE_URGENTE = r"""(?:\s*-)?\s+proc[ée]dure\s+urgente"""
RE_CLASS_MSU = RE_MISE_EN_SECURITE + RE_PROCEDURE_URGENTE
M_CLASS_MSU = re.compile(RE_CLASS_MSU, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_MSU_MOD = (
    r"""(?:"""
    + RE_MISE_EN_SECURITE
    + r"""\s+modificatif"""
    + RE_PROCEDURE_URGENTE
    + r"""|Arr[êe]t[ée]\s+modificatif\s+de\s+l['’]\s*"""
    + RE_MISE_EN_SECURITE
    + RE_PROCEDURE_URGENTE
    + r""")"""
)
M_CLASS_MSU_MOD = re.compile(RE_CLASS_MSU_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ML = r"""Arr[êe]t[ée](?:\s+de)?\s+mainlev[ée]e"""
M_CLASS_ML = re.compile(RE_CLASS_ML, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ML_PA = r"""Arr[êe]t[ée]\s+(?:de\s+)?mainlev[ée]e\s+partielle"""
M_CLASS_ML_PA = re.compile(RE_CLASS_ML_PA, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_DE = (
    r"""Arr[êe]t[ée]\s+"""
    + r"""(?:de\s+"""
    + r"""|portant\s+sur\s+"""
    + r"""(?:l['’]installation\s+d['’]un\s+périmètre\s+de\s+sécurité\s+et\s+)?"""
    + r"""la)"""
    + r"""(?:déconstruction|démolition)"""
)
M_CLASS_DE = re.compile(RE_CLASS_DE, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ABRO_DE = (
    r"""Abrogation\s+de\s+l['’]arr[êe]t[ée]\s+de\s+(d[ée]construction|d[ée]molition)"""
)
M_CLASS_ABRO_DE = re.compile(RE_CLASS_ABRO_DE, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_INS = (
    r"""Arr[êe]t[ée]\s+d'\s*ins[ée]curit[ée]\s+des\s+[ée]quipements\s+communs"""
)
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)
#
RE_INTERD_OCCUP = r"""interdiction\s+d['’]\s*(occuper|occupation)"""
RE_CLASS_INT = (
    r"""Arr[êe]t[ée]\s+""" + r"""(?:portant\s+l['’]|d['’])\s*""" + RE_INTERD_OCCUP
)
M_CLASS_INT = re.compile(RE_CLASS_INT, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_ABRO_INT = (
    r"""Arr[êe]t[ée]\s+d['’]\s*abrogation\s+de\s+l['’]\s*""" + RE_INTERD_OCCUP
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
    + r"""interdiction\s+d['’]habiter\s+et\s+d['’]occuper"""
    + r"""|interdiction\s+d['’]habiter\s+l['’]appartement"""
    + r""")"""
)
M_INTERDICT_HABIT = re.compile(RE_INTERDICT_HABIT, re.MULTILINE | re.IGNORECASE)

# démolition / déconstruction
# TODO à affiner: démolition d'un mur? déconstruction et reconstruction? etc
# TODO filtrer les pages copiées des textes réglementaires
RE_DEMOL_DECONST = (
    r"""(?:"""
    + r"""d[ée]molir"""
    + r"""|d[ée]molition"""
    + r"""|d[ée]construction"""
    + r""")"""
)
M_DEMOL_DECONST = re.compile(RE_DEMOL_DECONST, re.MULTILINE | re.IGNORECASE)

# (insécurité des) équipements communs
RE_EQUIPEMENTS_COMMUNS = (
    r"""s[ée]curit[ée](?:\s+imminente)\s+des\s+[ée]quipements\s+communs"""
)
M_EQUIPEMENTS_COMMUNS = re.compile(RE_EQUIPEMENTS_COMMUNS, re.MULTILINE | re.IGNORECASE)

# TODO exclure les arrêtés de mise en place d'un périmètre de sécurité
# (sauf s'ils ont un autre motif conjoint, eg. périmètre + interdiction d'occuper)
# "ARRÊTE DE MISE EN PLACE D’UN PÉRIMÈTRE DE SÉCURITÉ"
RE_CLASS_PERIM = (
    r"""Arr[êe]t[ée]\s+(?:de|portant\s+(?:sur\s+))"""
    + r"""(?:la\s+mise\s+en\s+place|l['’]installation)\s+"""
    + r"""d['’]un\s+p[ée]rim[èe]tre\s+de\s+s[ée]curit[ée]"""
)
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)

# "MODIFICATIF DE L'ARRÊTÉ N°xxxx": exclure? classe?
# ex: "10 place Jean Jaures-Modif 27.01.21.pdf": rectification erreur sur propriétaires

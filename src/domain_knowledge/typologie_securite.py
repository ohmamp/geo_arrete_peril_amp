"""Typologie des arrêtés de mise en sécurité.

"""

# 2023-03-14: 53 arrêtés avec un nom mais pas de classe
# csvcut -c pdf,nom_arr,classe data/processed/arretes_peril_compil_struct/paquet_arrete.csv |grep "[^,],$" |wc -l

# TODO abrogation d'interdiction partielle d'occupation?
# TODO interdiction d'accès et d'occupation du fond de parcelle => interdiction partielle?
# TODO modification de l'interdiction d'occuper
# TODO mise en demeure de réaliser des travaux
# TODO interdiction d'utilisation des balcons en façade?
# TODO arrêté d'évacuation?

import re

from src.domain_knowledge.arrete import RE_ARRETE

# formule parfois utilisée
RE_A_DIRE_D_EXPERT = r"[àa]\s+dire\s+d['’\s]\s*expert"

# procédures: orginaire et urgente
RE_PROCEDURE_ORDINAIRE = (
    r"(?:\s*[–-])?\s+proc[ée]dure\s+ordin(?:n)?aire"  # robustesse: 2e n optionnel
)
RE_PROCEDURE_URGENTE = (
    r"(?:"
    + r"(?:(?:\s*[–-])?\s+proc[ée]dure\s+(?:urgente|d['’]\s*urgence))"
    + r"|(?:\s+d['’]\s*urgence)"  # "mise en sécurité d'urgence"
    + r")"
)

# - classification des arrêtés
# péril simple/ordinaire (terminologie précédente)
RE_PS_PO = r"p[ée]ril\s+(?:simple|ordin(?:n)?aire|non\s+imminent)"  # robustesse: 2e n optionnel
RE_CLASS_PS_PO = (
    r"(?:"
    # arrêté de péril simple | ordinaire
    + rf"(?:{RE_ARRETE}\s+de\s+{RE_PS_PO})"
    # ou: arrêté municipal ordonnant les mesures nécessaires au cas de péril ordinaire
    + rf"|(?:{RE_ARRETE}\s+ordonnant\s+les\s+mesures\s+n[ée]cessaires\s+au\s+cas\s+de\s+{RE_PS_PO})"
    + r")"
)
M_CLASS_PS_PO = re.compile(RE_CLASS_PS_PO, re.MULTILINE | re.IGNORECASE)

# modificatif
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
RE_ARR_DE_MISE_EN_SECURITE = (
    rf"{RE_ARRETE}" + r"\s+(?:de\s+)?" + rf"{RE_MISE_EN_SECURITE}"
)
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
    rf"(?:{RE_ARRETE}"
    + rf"(?:\s+{RE_A_DIRE_D_EXPERT})?"
    + r"(?:"
    + r"(?:\s+portant\s+proc[ée]dure)"
    + r"|(?:\s+ordonnant\s+les\s+mesures\s+provisoires\s+n[ée]cessaires\s+au\s+cas)"
    + r")?"
    + rf"\s+de\s+{RE_PGI})"
)
M_CLASS_PGI = re.compile(RE_CLASS_PGI, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_PGI_MOD = (
    r"(?:"
    # arrêté de péril grave et imminent modificatif
    + rf"(?:{RE_CLASS_PGI}\s+modificatif)"
    # (arrêté modificatif | modification) de l'arrêté de péril grave et imminent
    + rf"|(?:(?:{RE_ARRETE}\s+modificatif|Modification)\s+de\s+l['’]\s*{RE_CLASS_PGI})"
    # arrêté modificatif de péril grave et imminent
    + rf"|(?:{RE_ARRETE}\s+modificatif\s+de\s+{RE_PGI})"
    + r")"
)
M_CLASS_PGI_MOD = re.compile(RE_CLASS_PGI_MOD, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_MSU = RE_ARR_DE_MISE_EN_SECURITE + RE_PROCEDURE_URGENTE
M_CLASS_MSU = re.compile(RE_CLASS_MSU, re.MULTILINE | re.IGNORECASE)
#
RE_CLASS_MSU_MOD = (
    r"(?:"
    # arrêté de mise en sécurité modificatif - procédure urgente
    + rf"{RE_ARR_DE_MISE_EN_SECURITE}\s+modificatif{RE_PROCEDURE_URGENTE}"
    # ou: arrêté modificatif de l'arrêté de mise en sécurité - procédure urgente
    + rf"|{RE_ARRETE}\s+modificatif\s+de\s+l['’]\s*{RE_ARR_DE_MISE_EN_SECURITE}{RE_PROCEDURE_URGENTE}"
    # ou: arrêté modificatif de mise en sécurité - procédure urgente
    + rf"|{RE_ARRETE}\s+modificatif\s+de\s+{RE_MISE_EN_SECURITE}{RE_PROCEDURE_URGENTE}"
    + r")"
)
M_CLASS_MSU_MOD = re.compile(RE_CLASS_MSU_MOD, re.MULTILINE | re.IGNORECASE)

# mainlevée
RE_ML = r"main[-]?\s*lev[ée]e"
RE_CLASS_ML = (
    r"(?:"
    # arrêté de mainlevée
    + rf"(?:{RE_ARRETE}"
    + r"(?:\s+de)?\s+"
    + RE_ML
    + r"(?!\s+partielle)"  # sauf si la suite est "partielle" (negative lookahead)
    + rf"(?:\s+de(?:{RE_PGI}|{RE_MISE_EN_SECURITE}|{RE_PS_PO}))?"
    + r")"
    # ou: mainlevée de l'arrêté
    + rf"|(?:{RE_ML}"
    + r"\s+(?:de\s+l['’]|d['’])\s*"
    + RE_ARRETE
    + rf"(?:\s+de(?:{RE_PGI}|{RE_MISE_EN_SECURITE}|{RE_PS_PO}))?"
    + r")"
    + r")"
)
M_CLASS_ML = re.compile(RE_CLASS_ML, re.MULTILINE | re.IGNORECASE)

# mainlevée partielle
RE_CLASS_ML_PA = (
    r"(?:"
    # arrêté de mainlevée partielle
    + rf"(?:{RE_ARRETE}"
    + r"\s+(?:de\s+)?"
    + rf"{RE_ML}"
    + r"\s+partielle"
    + rf"(?:\s+de\s+(?:{RE_PGI}|{RE_MISE_EN_SECURITE}|{RE_PS_PO}))?"
    + r")"
    # ou: mainlevée partielle de l'arrêté  # (inopérant?) WIP 2023-03-13
    + rf"|(?:{RE_ML}"
    + r"\s+partielle"
    + rf"\s+de\s+l['’]\s*(?:{RE_CLASS_PGI}|{RE_CLASS_MS}|{RE_CLASS_PS_PO})"
    + r")"
    # ou: mainlevée partielle de péril
    + rf"|(?:{RE_ML}"
    + r"\s+partielle"
    # + r"\s+de"
    + rf"(?:\s+de(?:{RE_PGI}|{RE_MISE_EN_SECURITE}|{RE_PS_PO}))?"
    + r")"
    + r")"
)
M_CLASS_ML_PA = re.compile(RE_CLASS_ML_PA, re.MULTILINE | re.IGNORECASE)

# déconstruction / démolition
RE_CLASS_DE = (
    rf"(?:{RE_ARRETE}"
    + r"\s+"
    + r"(?:de\s+"
    + r"|portant\s+sur\s+"
    + r"(?:(?:l['’\s]installation|la\s+mise\s+en\s+place)\s+d['’\s]un\s+p[ée]rim[èe]tre\s+de\s+s[ée]curit[ée]\s+et\s+)?"
    + r"(?:la\s+)?)"
    + r"(?:d[ée]construction|d[ée]molition)"
    + r")"
)
M_CLASS_DE = re.compile(RE_CLASS_DE, re.MULTILINE | re.IGNORECASE)

# abrogation de déconstruction / démolition
RE_CLASS_ABRO_DE = (
    r"(?:"
    + r"Abrogation\s+de\s+l['’]"
    + RE_ARRETE
    + r"\s+de\s+(?:d[ée]construction|d[ée]molition)"
    + r")"
)
M_CLASS_ABRO_DE = re.compile(RE_CLASS_ABRO_DE, re.MULTILINE | re.IGNORECASE)

# insécurité des équipements communs
RE_CLASS_INS = (
    RE_ARRETE
    + r"\s+(?:d['’]\s*)?ins[ée]curit[ée](\s+imminente)?\s+des\s+[ée]quipements\s+communs"
)
M_CLASS_INS = re.compile(RE_CLASS_INS, re.MULTILINE | re.IGNORECASE)

# interdiction d'occuper
RE_INTERD_OCCUP = (
    r"(?:"
    + r"interdiction\s+(?:partielle\s+)?"  # NEW 2023-03-13: partielle
    + r"(?:"
    # d'occuper | occupation
    + r"(?:d['’ 4]\s*(?:occuper|occupation))"
    # ou: d'habiter et d'occuper
    + r"|(?:d['’\s]\s*habiter\s+et\s+d['’\s]\s*occuper)"
    # ou: d'accès et d'occupation
    + r"|(?:d['’\s]\s*acc[èe]s\s+et\s+d['’\s]\s*occupation)"
    # ou: d'occupation et d'utilisation
    + r"|(?:d['’\s]\s*occupation\s+et\s+d['’\s]\s*utilisation)"
    # ou: de pénétrer, d'habiter, d'utiliser et d'exploiter
    + r"|(?:de\s+p[ée]n[ée]trer,\s+d['’\s]\s*habiter,\s+d['’\s]\s*utiliser,\s+et\s+d['’\s]\s*exploiter)"
    # ou: de pénétrer, d'utiliser, et fermeture
    + r"|(?:de\s+p[ée]n[ée]trer,\s+d['’\s]\s*utiliser,\s+et\s+fermeture)"
    + r")"
    + r")"
)
RE_CLASS_INT = (
    r"(?:"
    # arrêté d'interdiction d'occuper
    + rf"{RE_ARRETE}\s+d['’\s]\s*{RE_INTERD_OCCUP}"
    # ou: arrêté portant (sur l' | l' | ) interdiction d'occuper
    + rf"|{RE_ARRETE}\s+portant\s+(?:sur\s+l['’]\s*|l['’]\s*)?{RE_INTERD_OCCUP}"
    + r")"
)
P_CLASS_INT = re.compile(RE_CLASS_INT, re.MULTILINE | re.IGNORECASE)

# modificatif
RE_CLASS_INT_MOD = (
    r"(?:"
    # arrêté modificatif portant l'interdiction d'occupation
    + rf"{RE_ARRETE}\s+modificatif\s+(?:portant\s+(?:sur\s+l['’]\s*|l['’]\s*)?|d['’\s]\s*){RE_INTERD_OCCUP}"
    + r")"
)
P_CLASS_INT_MOD = re.compile(RE_CLASS_INT_MOD, re.MULTILINE | re.IGNORECASE)

# abrogation de l'interdiction d'occuper
RE_CLASS_ABRO_INT = (
    r"(?:"
    # arrêté d'abrogation de l'interdiction d'occuper
    + rf"{RE_ARRETE}"
    + r"\s+d['’]\s*abrogation\s+de\s+l['’]\s*"
    + RE_INTERD_OCCUP
    # ou: arrêté d'abrogation d'arrêté portant interdiction d'occuper
    + rf"|{RE_ARRETE}\s+d['’]\s*abrogation\s+d['’]\s*{RE_ARRETE}\s+portant\s+(?:(?:sur\s+)?l['’]\s*)?{RE_INTERD_OCCUP}"
    # ou: abrogation de l'arrêté ... portant sur l'interdiction d'occuper
    + r"|abrogation\s+de\s+l['’]\s*"
    + RE_ARRETE
    + r"\s+[\S\s]+?"
    + r"portant\s+(?:(?:sur\s+)?l['’]\s*)?"
    + RE_INTERD_OCCUP
    # ou: arrêté portant abrogation de l'arrêté ... portant l'interdiction
    + rf"|{RE_ARRETE}"
    + r"\s+portant\s+abrogation\s+de\s+l['’]\s*"
    + RE_ARRETE
    + r"\s+[\S\s]+?"
    + r"portant\s+(?:(?:sur\s+)?l['’]\s*)?"
    + RE_INTERD_OCCUP
    # ou: abrogation d'interdiction d'occupation
    + r"|abrogation\s+d['’]\s*"
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
            RE_CLASS_INT_MOD,
            # insécurité des équipements
            RE_CLASS_INS,
        ]
    )
    + r")"
)
P_CLASSE = re.compile(RE_CLASSE, re.MULTILINE | re.IGNORECASE)


# propriétés additionnelles des arrêtés: un arrêté de péril peut s'accompagner d'une interdiction d'habiter etc.

# interdiction d'habiter
RE_INT_HAB = (
    r"(?:"
    + r"interdiction\s+d['’\s]habiter\s+et\s+d['’\s]occuper"
    + r"|interdiction\s+d['’\s]habiter\s+l['’\s]appartement"
    + r")"
)
P_INT_HAB = re.compile(RE_INT_HAB, re.MULTILINE | re.IGNORECASE)

# démolition / déconstruction
# TODO à affiner: démolition d'un mur? déconstruction et reconstruction? etc
# TODO filtrer les pages copiées des textes réglementaires
RE_DEMO = r"(?:" + r"d[ée]molir" + r"|d[ée]molition" + r"|d[ée]construction" + r")"
P_DEMO = re.compile(RE_DEMO, re.MULTILINE | re.IGNORECASE)

# (insécurité des) équipements communs
RE_EQU_COM = r"s[ée]curit[ée](?:\s+imminente)\s+des\s+[ée]quipements\s+communs"
P_EQU_COM = re.compile(RE_EQU_COM, re.MULTILINE | re.IGNORECASE)

# TODO exclure les arrêtés de mise en place d'un périmètre de sécurité
# (sauf s'ils ont un autre motif conjoint, eg. périmètre + interdiction d'occuper)
# "ARRÊTE DE MISE EN PLACE D’UN PÉRIMÈTRE DE SÉCURITÉ"
RE_CLASS_PERIM = (
    rf"{RE_ARRETE}"
    + r"\s+(?:de|portant\s+(?:sur\s+))"
    + r"(?:la\s+mise\s+en\s+place|l['’\s]installation)\s+"
    + r"d['’\s]un\s+p[ée]rim[èe]tre\s+de\s+s[ée]curit[ée]"
)
P_CLASS_PERIM = re.compile(RE_CLASS_PERIM, re.MULTILINE | re.IGNORECASE)


def get_classe(page_txt: str) -> bool:
    """Récupère la classification de l'arrêté.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_class: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    # NB: l'ordre d'application des règles de matching est important:
    # les mainlevées incluent généralement l'intitulé de l'arrêté (ou du type d'arrêté) précédent
    if (
        M_CLASS_ML.search(page_txt)
        or M_CLASS_ABRO_DE.search(page_txt)
        or M_CLASS_ABRO_INT.search(page_txt)
    ):
        return "Arrêté de mainlevée"
    elif (
        M_CLASS_PS_PO_MOD.search(page_txt)
        or M_CLASS_MS_MOD.search(page_txt)
        or M_CLASS_PGI_MOD.search(page_txt)
        or M_CLASS_MSU_MOD.search(page_txt)
        or M_CLASS_ML_PA.search(page_txt)
        or P_CLASS_INT_MOD.search(page_txt)
    ):
        return "Arrêté de mise en sécurité modificatif"
    elif (
        M_CLASS_PS_PO.search(page_txt)
        or M_CLASS_MS.search(page_txt)
        or M_CLASS_PGI.search(page_txt)
        or M_CLASS_MSU.search(page_txt)
        or M_CLASS_DE.search(page_txt)
        or M_CLASS_INS.search(page_txt)
        or P_CLASS_INT.search(page_txt)
    ):
        return "Arrêté de mise en sécurité"
    else:
        return None


# TODO expectation: "urgen" in "nom_arr" => urgence=True
# anomalies: csvcut -c arr_nom_arr,arr_urgence data/interim/arretes_peril_compil_data_enr_struct.csv |grep -i urgen |grep ",$"
def get_urgence(page_txt: str) -> bool:
    """Récupère le caractère d'urgence de l'arrêté.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_class: str
        Caractère d'urgence de l'arrêté si trouvé, None sinon.
    """
    if (
        M_CLASS_PS_PO.search(page_txt)
        or M_CLASS_PS_PO_MOD.search(page_txt)
        or M_CLASS_MS.search(page_txt)
        or M_CLASS_MS_MOD.search(page_txt)
    ):
        return "non"
    elif (
        M_CLASS_PGI.search(page_txt)
        or M_CLASS_PGI_MOD.search(page_txt)
        or M_CLASS_MSU.search(page_txt)
        or M_CLASS_MSU_MOD.search(page_txt)
    ):
        return "oui"
    elif (
        M_CLASS_ML_PA.search(page_txt)
        or M_CLASS_DE.search(page_txt)
        or M_CLASS_ABRO_DE.search(page_txt)
        or M_CLASS_INS.search(page_txt)
        or P_CLASS_INT.search(page_txt)
    ):
        # FIXME ajouter la prise en compte des articles cités pour déterminer l'urgence
        return "oui ou non"
    elif M_CLASS_ML.search(page_txt) or M_CLASS_ABRO_INT.search(page_txt):
        return "/"
    else:
        return None


def get_int_hab(page_txt: str) -> bool:
    """Détermine si l'arrêté porte interdiction d'habiter et d'occuper.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_int_hab: str
        Interdiction d'habiter si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif P_INT_HAB.search(page_txt):
        return "oui"
    else:
        return "non"


def get_demo(page_txt: str) -> bool:
    """Détermine si l'arrêté porte une démolition ou déconstruction.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_demol_deconst: str
        Démolition ou déconstruction si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif P_DEMO.search(page_txt):
        return "oui"
    else:
        return "non"


def get_equ_com(page_txt: str) -> bool:
    """Détermine si l'arrêté porte sur la sécurité des équipements communs.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_equ_com: str
        Sécurité des équipements communs si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif P_EQU_COM.search(page_txt):
        return "oui"
    else:
        return "non"


# "MODIFICATIF DE L'ARRÊTÉ N°xxxx": exclure? classe?
# ex: "10 place Jean Jaures-Modif 27.01.21.pdf": rectification erreur sur propriétaires

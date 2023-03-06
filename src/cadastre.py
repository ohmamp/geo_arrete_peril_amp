"""Reconnaissance et analyse de références cadastrales.

"""

# TODO améliorer la couverture:
# data_enr_struct.csv: 830 arrêtés sans référence cadastrale sur 2452 (33.85%) (2023-03-05)
# (dont 288 avec un code insee, dont 5 avec un 13055)
#

# FIXME trouver un moyen de forcer le strict parallélisme avec les expressions sans groupes nommés

import re

from domain_vocab import RE_NO


# Marseille: préfixe = arrondissement + quartier
RE_CAD_ARRT = (
    r"(2[01]\d)"  # 3 derniers chiffres du code INSEE de l'arrondissement: 2O1 à 216
)
RE_CAD_QUAR = r"(\d{3})"  # code quartier
# expression sans named group
RE_CAD_ARRT_QUAR = (
    RE_CAD_ARRT  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"\s*"
    + RE_CAD_QUAR  # code quartier
)
# expression avec named groups
RE_CAD_ARRT_QUAR_NG = (
    rf"(?P<arrt>{RE_CAD_ARRT})"  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"\s*"
    + rf"(?P<quar>{RE_CAD_QUAR})"  # code quartier
)

# toutes communes: section et numéro
RE_CAD_SEC = r"[A-Z]{1,2}"
RE_CAD_NUM = r"\d{1,4}"

# expression complète
# - Marseille
RE_CAD_MARSEILLE = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + RE_CAD_ARRT_QUAR
    + r"\s*"
    + RE_CAD_SEC
    + r"\s?"
    + RE_CAD_NUM
    + r")"
)
P_CAD_MARSEILLE = re.compile(RE_CAD_MARSEILLE, re.MULTILINE | re.IGNORECASE)
# idem, avec named groups
RE_CAD_MARSEILLE_NG = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + RE_CAD_ARRT_QUAR_NG
    + r"\s*"
    + rf"(?P<sec>{RE_CAD_SEC})"
    + r"\s?"
    + rf"(?P<num>{RE_CAD_NUM})"
    + r")"
)
P_CAD_MARSEILLE_NG = re.compile(RE_CAD_MARSEILLE_NG, re.MULTILINE | re.IGNORECASE)


# récupérer les références de parcelles sans contexte gauche, à Marseille
# augmente la couverture, avec un risque faible de faux positif grâce au code insee et au code quartier
# TODO gérer les références avec préfixe factorisé, ex: "207835 E0004 / E0216"
# TODO références mal formées? "33202 B0130 ET 33202 B0131"
RE_PARCELLE_MARSEILLE_NOCONTEXT = (
    r"(?P<cadastre_id>"  # named group pour la ou les références cadastrales
    + RE_CAD_MARSEILLE  # 1re référence cadastrale
    + r"("  # 1 ou plusieurs références supplémentaires
    + r"(?:,|\s+et|\s+[&]|\s+[-])\s+"
    + RE_CAD_MARSEILLE
    + r")*"  # fin 1 ou plusieurs références supplémentaires
    + r")"  # fin named group
)
P_PARCELLE_MARSEILLE_NOCONTEXT = re.compile(
    RE_PARCELLE_MARSEILLE_NOCONTEXT, re.IGNORECASE | re.MULTILINE
)


# - autres communes
RE_CAD_AUTRES = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + RE_CAD_SEC  # section cadastrale
    + rf"(?:\s{RE_NO})?\s*"
    + RE_CAD_NUM  # numéro de parcelle
    + r")"
)
P_CAD_AUTRES = re.compile(RE_CAD_AUTRES, re.MULTILINE | re.IGNORECASE)
# idem, avec named groups
RE_CAD_AUTRES_NG = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + rf"(?P<sec>{RE_CAD_SEC})"
    + rf"(?:\s{RE_NO})?\s*"
    + rf"(?P<num>{RE_CAD_NUM})"
    + r")"
)
P_CAD_AUTRES_NG = re.compile(RE_CAD_AUTRES_NG, re.MULTILINE | re.IGNORECASE)

# Marseille ou autres communes
RE_CAD_SECNUM = r"(?:" + RE_CAD_MARSEILLE + r"|" + RE_CAD_AUTRES + r")"

# avec le contexte gauche
RE_PARCELLE = (
    r"(?:"  # contexte gauche
    + r"(?:cadastré(?:e|es|s)?(?:\s+section)?)"
    + r"|(?:référence(?:s)?\s+cadastrale(?:s)?)"
    + r"|(?:référencé(?:e|es|s)?\s+au\s+cadastre\s+sous\s+le)"  # référence au cadastre sous le (n°)
    + r"|(?:parcelle(?:s)?)"
    + r")\s+"  # fin contexte gauche
    + r"(?P<cadastre_id>"  # named group pour la ou les références cadastrales
    + RE_CAD_SECNUM  # 1re référence cadastrale
    + r"("  # 1 ou plusieurs références supplémentaires
    + r"(?:,|\s+et|\s+[-])\s+"
    + RE_CAD_SECNUM
    + r")*"  # fin 1 ou plusieurs références supplémentaires
    + r")"  # fin named group
)
P_PARCELLE = re.compile(RE_PARCELLE, re.MULTILINE | re.IGNORECASE)

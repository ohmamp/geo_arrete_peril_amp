"""Éléments dénotant la structure du texte.

"""

import re

# @ctes
#
# TODO récupérer les champs?
# ex:
# Envoyé en préfecture le 09/02/2021
# Reçu en préfecture le 09/02/2021
# Affiché le
# ID : 013-211301106-20210201-1212-AI
RE_STAMP = r"""Envoyé en préfecture le 09/02/2021
Reçu en préfecture le \d{2}/\d{2}/\d{4}
Affiché le
ID : \d{3}-\d{9}-\d{8}-[^-]+-(?P<nature_abr>AI|AR)"""
M_STAMP = re.compile(RE_STAMP, re.MULTILINE)

# TODO récupérer les champs?
# ex:
# Accusé de réception
# Acte reçu par: Préfecture des Bouches du Rhône
# Nature transaction: AR de transmission d'acte
# Date d'émission de l'accusé de réception: 2021-06-02(GMT+1)
# Nombre de pièces jointes: 1
# Nom émetteur: 4 martigues
# N° de SIREN: 211300561
# Numéro Acte de la collectivité locale: RA21_21646
# Objet acte: LE MAIRE SIGNE - Arrêté Municipal n. 446.2021prononcant une interdiction temporaire d
# acces et d habiter 2 rue leon gambetta à Martigues
# Nature de l'acte: Actes individuels
# Matière: 6.1-Police municipale
# Identifiant Acte: 013-211300561-20210602-RA21_21646-AI
RE_ACCUSE = r"""Accusé de réception
Acte reçu par: Préfecture des Bouches du Rhône
Nature transaction: AR de transmission d'acte
Date d'émission de l'accusé de réception: \d{4}-\d{2}-\d{2}[(]GMT[+-]\d[)]
Nombre de pièces jointes: \d+
Nom émetteur: [^\n]+
N° de SIREN: \d{9}
Numéro Acte de la collectivité locale: [^\n]+
Objet acte: [^\n]+
([^\n]+)?
Nature de l'acte: (?P<nature_acte>Actes (individuels|réglementaires))
Matière: \d[.]\d-[^\n]+
Identifiant Acte: \d{3}-\d{9}-\d{8}-[^-]+-(?P<nature_abr>AI|AR)"""
# actes individuels: ...-AI, actes réglementaires: ...-AR
# (?P<nature_acte>Actes individuels|Actes réglementaires)\n
# (?P<nature_abr>[^\n]+)
M_ACCUSE = re.compile(RE_ACCUSE, re.MULTILINE)

# tous arrêtés
RE_VU = r"""^\s*V(U|u) [^\n]+"""
M_VU = re.compile(RE_VU, re.MULTILINE)

RE_CONSIDERANT = r"""^C(?:ONSID[EÉ]RANT|onsid[ée]rant) [^\n]+"""
M_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE)

RE_ARRETE = r"""^ARR[ÊE]T(?:E|ONS)"""
M_ARRETE = re.compile(RE_ARRETE, re.MULTILINE)

RE_ARTICLE = r"""^A(RTICLE|rticle) \d+"""
M_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE)

# arrêtés spécifiques:
# - entités du contexte réglementaire
RE_CGCT = r"""Code Général des Collectivités Territoriales"""
M_CGCT = re.compile(RE_CGCT, re.MULTILINE)

RE_CGCT_ART = r"""articles(?:\s)L.2131-1,(?:\s)L.2212-4(?:\s)et(?:\s)L.2215-1"""  # TODO généraliser
M_CGCT_ART = re.compile(RE_CGCT_ART, re.MULTILINE)

RE_CCH = r"""Code de la Construction et de l’Habitation"""
M_CCH = re.compile(RE_CCH, re.MULTILINE)
RE_CCH_L511 = r"""L.511-1(?:\s)à(?:\s)L.511-6"""
M_CCH_L511 = re.compile(RE_CCH_L511, re.MULTILINE)
RE_CCH_L521 = r"""L.521-1(?:\s)à(?:\s)L.521-4"""
M_CCH_L521 = re.compile(RE_CCH_L521, re.MULTILINE)
RE_CCH_L541 = r"""L.541-2"""
M_CCH_L541 = re.compile(RE_CCH_L541, re.MULTILINE)
RE_CCH_R511 = r"""R.511-1(?:\s)à(?:\s)R.511-12"""  # TODO généraliser
M_CCH_R511 = re.compile(RE_CCH_R511, re.MULTILINE)

RE_CC = r"""Code Civil"""
M_CC = re.compile(RE_CC, re.MULTILINE)

RE_CC_ART = r"""articles(?:\s)2384-1,(?:\s)2384-3"""  # TODO généraliser
M_CC_ART = re.compile(RE_CC_ART, re.MULTILINE)

# (à valider)
RE_ABF = r"""[Aa]rchitecte des [Bb]âtiments de France"""
M_ABF = re.compile(RE_ABF, re.MULTILINE)

# éléments à extraire
# - parcelle cadastrale
RE_CAD_SEC = r"""[A-Z]{1,2}"""
RE_CAD_NUM = r"""\d{1,4}"""
RE_PARCELLE = rf"""(?:parcelles cadastrées section|cadastré|parcelle) (?P<cadastre_id>{RE_CAD_SEC}(?: n°)?[ ]?{RE_CAD_NUM}((,| et) {RE_CAD_SEC}(?: n°)?[ ]?{RE_CAD_NUM})*)"""
M_PARCELLE = re.compile(RE_PARCELLE)

# - syndic
RE_SYNDIC = r"""syndic"""
M_SYNDIC = re.compile(RE_SYNDIC)

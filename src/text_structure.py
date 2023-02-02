"""Éléments dénotant la structure du texte.

"""

import re

# @ctes
#
RE_DATE_SL = r"\d{2}/\d{2}/\d{4}"
RE_ACTES_ID = r"\d{3}-\d{9}-\d{8}-[^-]+-(AI|AR)"
# TODO récupérer les champs?
# ex:
# Envoyé en préfecture le 09/02/2021
# Reçu en préfecture le 09/02/2021
# Affiché le
# ID : 013-211301106-20210201-1212-AI
RE_STAMP_1 = rf"""Envoyé en préfecture le {RE_DATE_SL}
Reçu en préfecture le {RE_DATE_SL}
Affiché le
ID : {RE_ACTES_ID}"""
# ex:
# Accusé de réception en préfecture
# 013-211300561-20211025-RA21_23060-AR
# Date de télétransmission : 25/10/2021
# Date de réception préfecture : 25/10/2021
RE_STAMP_2 = rf"""Accusé de réception en préfecture
{RE_ACTES_ID}
Date de télétransmission : {RE_DATE_SL}
Date de réception préfecture : {RE_DATE_SL}
"""
RE_STAMP = rf"(?:(?:{RE_STAMP_1})|(?:{RE_STAMP_2}))"
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
# CGCT
RE_CGCT = r"""Code Général des Collectivités Territoriales"""
M_CGCT = re.compile(RE_CGCT, re.MULTILINE)
#
RE_CGCT_ART = r"""articles(?:\s)L[. ]*2131-1,(?:\s)L[. ]*2212-4(?:\s)et(?:\s)L[. ]*2215-1"""  # TODO généraliser
M_CGCT_ART = re.compile(RE_CGCT_ART, re.MULTILINE)
# CCH
RE_CCH = r"""Code de la Construction et de l’Habitation"""
M_CCH = re.compile(RE_CCH, re.MULTILINE)
# L111-6-1: <https://www.legifrance.gouv.fr/codes/id/LEGIARTI000028808282/2014-03-27> (en vigueur jusque 2021-07-01)
RE_CCH_L111 = r"""L[. ]*111(?:-[\d]){0,2}"""
M_CCH_L111 = re.compile(RE_CCH_L111, re.MULTILINE)
# L511-1 à L511-22 du CCH
RE_CCH_L511 = r"""L[. ]*511-1(?:\s)(?:(?:à(?:\s)?L[. ]*511-[\d]{1,2})|(?:et suivants))"""  # TODO trop général ?
M_CCH_L511 = re.compile(RE_CCH_L511, re.MULTILINE)
# 521-1, 521-2, 521-3-[1-4], 521-4
# 521-3: relogement
# 521-4: sanctions
RE_CCH_L521 = r"""L[. ]*521-1(?:\s)à(?:\s)?L[. ]*521-[\d](?:-[\d])?"""  # TODO affiner ?
M_CCH_L521 = re.compile(RE_CCH_L521, re.MULTILINE)
RE_CCH_L541 = r"""L[. ]*541-2"""
M_CCH_L541 = re.compile(RE_CCH_L541, re.MULTILINE)
# R511-1 à R511-13 du CCH
RE_CCH_R511 = r"""R[. ]*511-1(?:\s)à(?:\s)?R[. ]*511-[\d]{1,2}"""  # TODO trop général ?
M_CCH_R511 = re.compile(RE_CCH_R511, re.MULTILINE)
# CC
RE_CC = r"""Code Civil"""
M_CC = re.compile(RE_CC, re.MULTILINE)
#
RE_CC_ART = r"""articles(?:\s)2384-1,(?:\s)2384-3"""  # TODO généraliser
M_CC_ART = re.compile(RE_CC_ART, re.MULTILINE)

# (à valider)
RE_ABF = r"""[Aa]rchitecte des [Bb]âtiments de France"""
M_ABF = re.compile(RE_ABF, re.MULTILINE)

# éléments à extraire
# - commune
# capture: Peyrolles-en-Provence, Gignac-la-Nerthe, GEMENOS, Roquevaire, Gardanne
RE_MAIRE_COMM_DE = r"Maire (?:de la Commune )?(?:de |d')"
# "Nous[,.]": gestion d'erreur d'OCR ("." reconnu au lieu de ",")
RE_MAIRE_COMMUNE = rf"""(?:Le {RE_MAIRE_COMM_DE}|Nous[,.] (?:[^,]+, )?{RE_MAIRE_COMM_DE})(?P<commune>[^,\n]+)"""
M_MAIRE_COMMUNE = re.compile(RE_MAIRE_COMMUNE, re.MULTILINE | re.IGNORECASE)
# - parcelle cadastrale
RE_CAD_SEC = r"""[A-Z]{1,2}"""
RE_CAD_NUM = r"""\d{1,4}"""
RE_CAD_SECNUM = rf"""(?:(?:(?:n°\s?){RE_CAD_SEC}\s?{RE_CAD_NUM})|(?:{RE_CAD_SEC}\sn°\s?{RE_CAD_NUM})|(?:{RE_CAD_SEC}\s?{RE_CAD_NUM}))"""
RE_PARCELLE = rf"""(?:cadastré(?:e|es)(?:\s+section)?|référence(?:s)?\s+cadastrale(?:s)?|parcelle(?:s)?)\s+(?P<cadastre_id>{RE_CAD_SECNUM}((,|\s+et)\s+{RE_CAD_SECNUM})*)"""
M_PARCELLE = re.compile(RE_PARCELLE, re.MULTILINE | re.IGNORECASE)
# - adresse
# contextes: "objet:" (objet de l'arrêté), "Objet acte:" (page d'accusé de réception de transmission @actes)
# TODO ajouter du contexte pour être plus précis? "désordres sur le bâtiment sis... ?"
RE_NUM_VOIE = r"""\d+(?:\s?(?:A|bis|ter))?"""
RE_TYP_VOIE = r"""(?:avenue|boulevard|cours|impasse|place|rue)"""
RE_CP = r"""\d{5}"""
RE_COMMUNE = r"""[^,_]+"""
RE_ADRESSE = rf"""(?:(?P<num_voie>{RE_NUM_VOIE})\s+)?(?P<type_voie>{RE_TYP_VOIE})\s+(?:(?P<code_postal>{RE_CP})\s+)?(?P<commune>{RE_COMMUNE})?"""
# adresse du bâtiment visé par l'arrêté
RE_ADR_DOC = (
    rf"""(?:situé au|désordres sur le bâtiment sis|sis(?: à)?|Objet acte:|Objet\s?:)\s+"""
    + rf"""(?P<adresse>{RE_ADRESSE})"""  # TODO ajouter la reconnaissance explicite d'une 2e adresse optionnelle (ex: "... / ...")
    + r"""(?:\s+(?:(?:[–-]\s+)|[(]?)?(?:susceptibles|parcelle))?"""
)
M_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)
# - propriétaire
RE_PROPRI = rf"""(?:à la )(?P<propri>Société Civile Immobilière .+)[,]? sise (?P<prop_adr>{RE_ADRESSE})"""
M_PROPRI = re.compile(RE_PROPRI, re.MULTILINE | re.IGNORECASE)
# - syndic
RE_SYNDIC = r"""(?:syndic (?:de copropriété)?) (?P<syndic>.+)(?:[,.]|[,]? sis)"""
M_SYNDIC = re.compile(RE_SYNDIC, re.MULTILINE | re.IGNORECASE)

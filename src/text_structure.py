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

# TODO motif complet sur l'accusé de réception ; parsing dédié pour vérifier/croiser avec les données extraites dans le reste du document
# "Objet acte:" (page d'accusé de réception de transmission @actes)
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
Objet acte: (?:[\s\S]+?)
Nature de l'acte: (?P<nature_acte>Actes (individuels|réglementaires))
Matière: \d[.]\d-[^\n]+
Identifiant Acte: \d{3}-\d{9}-\d{8}-[^-]+-(?P<nature_abr>AI|AR)"""
# actes individuels: ...-AI, actes réglementaires: ...-AR
# (?P<nature_acte>Actes individuels|Actes réglementaires)\n
# (?P<nature_abr>[^\n]+)
M_ACCUSE = re.compile(RE_ACCUSE, re.MULTILINE)
# TODO vérifier les matières ;
# grep -h "Matière:" data/interim/txt_native/*.txt |sort |uniq -c
# renvoie:
#      1 Matière: 1.7-Actes speciaux et divers
#      3 Matière: 2.1-Documents d urbanisme
#      8 Matière: 3.6-Autres actes de gestion du domaine prive
#     47 Matière: 6.1-Police municipale
#     14 Matière: 6.4-Autres actes reglementaires
#      2 Matière: 8.5-Politique de la ville-habitat-logement
#      5 Matière: 9.1-Autres domaines de competences des communes
#
# 1.7: "travaux de mise en sécurité 2 rue Aharonian La Ciotat.pdf" décision du conseil municipal sur un marché attribué pour la CSPS des travaux de mise en sécurité (à exclure?)
# 2.1: "21 cours Carnot Châteaurenard.pdf" mise en demeure de travaux conformes au règlement sanitaire départemental (à exclure?),
#      "MenS 44 rue de la République Aubagne.pdf" MSU (à garder),
#      "Retrait 1687 avenue de la Croix d'Or Bouc Bel Air.pdf" : retrait de péril imminent (= ML ?) (à garder?)
# 3.6: "12 rue Parmentier Gardanne - MS.pdf": MSU (à garder)
#      "mainlevée 21 rue Martinot Aubagne.pdf": ML (à garder)
#      "mainlevée 4 bis cours Foch Aubagne.pdf": mainlevée (à garder)
#      "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf": MSU (à garder)
#      "mise en sécurité 21 rue Martinot Aubagne.pdf": MS (à garder)
#      "mise en sécurité 4 rue de l'Huveaune Aubagne.pdf": MS (à garder)
#      "mise en sécurité 6 rue de l'Huveaune Aubagne.pdf": MS (à garder)
#      "MS 39 rue de la République Aubagne.pdf": MS (à garder)
# 8.5: "19 av du Docteur Perrier Châteaurenard.pdf": mise en demeure de travaux conformes au règlement sanitaire départemental (à exclure?),
#      "7 rue Paulet Ceyreste.pdf": MSU (à garder)
# 9.1: "mainlevée 12 rue Frédéric Mistral Aubagne.pdf": mainlevée (à garder)
#      "mainlevée 22 rue Mirabeau Tarascon.pdf": mainlevée (à garder)
#      "mise en sécurité 14 rue de l'Egalité Aubagne.pdf": MSU (à garder)
#      "mise en sécurité 16 rue Frédéric Mistral Aubagne.pdf": MS (à garder)
#      "MS 14 16 rue Frédéric Mistral Aubagne.pdf": MS (à garder)

# tous arrêtés
RE_VU = r"""^\s*V(U|u) [^\n]+"""
M_VU = re.compile(RE_VU, re.MULTILINE)

RE_CONSIDERANT = r"""^CONSID[EÉ]RANT [^\n]+"""
M_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE | re.IGNORECASE)

RE_ARRETE = r"""^ARR[ÊE]T(?:E|ONS)"""
M_ARRETE = re.compile(RE_ARRETE, re.MULTILINE | re.IGNORECASE)

RE_ARTICLE = r"""^ARTICLE \d+"""
M_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE | re.IGNORECASE)

# arrêtés spécifiques:
# - entités du contexte réglementaire
# CGCT
RE_CGCT = r"""Code\s+Général\s+des\s+Collectivités\s+Territoriales"""
M_CGCT = re.compile(RE_CGCT, re.MULTILINE | re.IGNORECASE)
#
RE_CGCT_ART = r"""articles(?:\s)L[. ]*2131-1,(?:\s)L[. ]*2212-4(?:\s)et(?:\s)L[. ]*2215-1"""  # TODO généraliser
# TODO L.2212-2 et L.2213-24 ?
M_CGCT_ART = re.compile(RE_CGCT_ART, re.MULTILINE | re.IGNORECASE)
# CCH
RE_CCH = r"""Code\s+de\s+la\s+Construction\s+et\s+de\s+l’Habitation"""
M_CCH = re.compile(RE_CCH, re.MULTILINE | re.IGNORECASE)
# L111-6-1: <https://www.legifrance.gouv.fr/codes/id/LEGIARTI000028808282/2014-03-27> (en vigueur jusque 2021-07-01)
RE_CCH_L111 = r"""L[. ]*111(?:-[\d]){0,2}"""
M_CCH_L111 = re.compile(RE_CCH_L111, re.MULTILINE | re.IGNORECASE)
# L511-1 à L511-22 du CCH
RE_CCH_L511 = r"""L[. ]*511-1(?:\s)(?:(?:à(?:\s)?L[. ]*511-[\d]{1,2})|(?:et\s+suivants))"""  # TODO trop général ?
M_CCH_L511 = re.compile(RE_CCH_L511, re.MULTILINE | re.IGNORECASE)
# 521-1, 521-2, 521-3-[1-4], 521-4
# 521-3: relogement
# 521-4: sanctions
RE_CCH_L521 = r"""L[. ]*521-1(?:\s)à(?:\s)?L[. ]*521-[\d](?:-[\d])?"""  # TODO affiner ?
M_CCH_L521 = re.compile(RE_CCH_L521, re.MULTILINE | re.IGNORECASE)
RE_CCH_L541 = r"""L[. ]*541-2"""
M_CCH_L541 = re.compile(RE_CCH_L541, re.MULTILINE | re.IGNORECASE)
# R511-1 à R511-13 du CCH
RE_CCH_R511 = r"""R[. ]*511-1(?:\s)à(?:\s)?R[. ]*511-[\d]{1,2}"""  # TODO trop général ?
M_CCH_R511 = re.compile(RE_CCH_R511, re.MULTILINE | re.IGNORECASE)
# CC
RE_CC = r"""Code\s+Civil"""
M_CC = re.compile(RE_CC, re.MULTILINE | re.IGNORECASE)
#
RE_CC_ART = r"""articles(?:\s)2384-1,(?:\s)2384-3"""  # TODO généraliser
M_CC_ART = re.compile(RE_CC_ART, re.MULTILINE | re.IGNORECASE)

# (à valider)
RE_ABF = r"""[Aa]rchitecte\s+des\s+[Bb]âtiments\s+de\s+France"""
M_ABF = re.compile(RE_ABF, re.MULTILINE | re.IGNORECASE)

# éléments à extraire
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
RE_CLASS_PGI = r"""Arrêté\s+de\s+péril\s+grave\s+et\s+imminent"""
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

# - commune
# capture: Peyrolles-en-Provence, Gignac-la-Nerthe, GEMENOS, Roquevaire, Gardanne
RE_MAIRE_COMM_DE = r"Maire\s+(?:de\s+la\s+Commune\s+)?(?:de\s+|d')"
# "Nous[,.]": gestion d'erreur d'OCR ("." reconnu au lieu de ",")
RE_MAIRE_COMMUNE = rf"""(?:Le\s+{RE_MAIRE_COMM_DE}|Nous[,.]\s+(?:[^,]+,\s+)?{RE_MAIRE_COMM_DE})(?P<commune>[^,\n]+)"""
M_MAIRE_COMMUNE = re.compile(RE_MAIRE_COMMUNE, re.MULTILINE | re.IGNORECASE)
# - parcelle cadastrale
RE_CAD_SEC = r"""[A-Z]{1,2}"""
RE_CAD_NUM = r"""\d{1,4}"""
RE_CAD_SECNUM = rf"""(?:(?:(?:n°\s?){RE_CAD_SEC}\s?{RE_CAD_NUM})|(?:{RE_CAD_SEC}\sn°\s?{RE_CAD_NUM})|(?:{RE_CAD_SEC}\s?{RE_CAD_NUM}))"""
RE_PARCELLE = rf"""(?:cadastré(?:e|es)(?:\s+section)?|référence(?:s)?\s+cadastrale(?:s)?|parcelle(?:s)?)\s+(?P<cadastre_id>{RE_CAD_SECNUM}((,|\s+et)\s+{RE_CAD_SECNUM})*)"""
M_PARCELLE = re.compile(RE_PARCELLE, re.MULTILINE | re.IGNORECASE)
# - adresse
RE_NUM_VOIE = r"""\d+(?:\s?(?:A|bis|ter))?"""
RE_TYP_VOIE = r"""(?:avenue|boulevard|cours|impasse|place|rue)"""
RE_NOM_VOIE = r"""(?:[^,:–(]+)"""
RE_CP = r"""\d{5}"""
RE_COMMUNE = r"""\w+(?:[\s-]+\w+){0,3}?"""
# contextes: "objet:" (objet de l'arrêté),
# TODO ajouter du contexte pour être plus précis? "désordres sur le bâtiment sis... ?"
RE_ADRESSE = (
    rf"""(?:(?P<num_voie>{RE_NUM_VOIE})[,]?\s+)?(?P<type_voie>{RE_TYP_VOIE})\s+(?P<nom_voie>{RE_NOM_VOIE})"""
    + rf"""(?:[\s–]+(?:(?P<code_postal>{RE_CP})\s+)?(?P<commune>{RE_COMMUNE}))?"""
)
# adresse du bâtiment visé par l'arrêté
RE_ADR_DOC = (
    rf"""(?:situ[ée](?:\s+au)?|désordres\s+sur\s+le\s+bâtiment\s+sis|immeuble\s+(?:du|numéroté)|sis[e]?(?:\s+à)?|Objet\s?:)\s+"""
    + rf"""(?P<adresse>{RE_ADRESSE})"""  # TODO ajouter la reconnaissance explicite d'une 2e adresse optionnelle (ex: "... / ...")
    + r"""(?:\s+(?:(?:[,:–-]\s+)|[(]?)?(?:susceptible|parcelle|référence|concernant))?"""
)
M_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)
# - propriétaire
RE_PROPRI = rf"""(?:à\s+la\s+)(?P<propri>Société\s+Civile\s+Immobilière\s+.+)[,]?\s+sise\s+(?P<prop_adr>{RE_ADRESSE})"""
M_PROPRI = re.compile(RE_PROPRI, re.MULTILINE | re.IGNORECASE)
# - syndic
# TODO syndic judiciaire?
# TODO M. ... en qualité de syndic?
# TODO administrateur?
RE_SYNDIC = (
    r"""(?:syndic(?:\s+de\s+copropriété)?)\s+(?P<syndic>.+?)(?:[,.]|[,]?\s+sis)"""
)
M_SYNDIC = re.compile(RE_SYNDIC, re.MULTILINE | re.IGNORECASE)
# date de l'arrêté
RE_MOIS = (
    r"""(?:"""
    + r"""janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"""
    + r"""|"""
    + r"""jan|f[ée]v|mars|avr|mai|juin|juil|aou|sep|oct|nov|d[ée]c"""
    + r""")"""
)
RE_DATE = (
    r"""(?:"""
    + r"""^Fait\s+à\s+\S+[,]?\s+le|"""  # Roquevaire (fin)
    + r"""^Fait à Aix-en-Provence, en l'Hôtel de Ville,\nle|"""  # Aix-en-Provence (fin)
    + r"""^Gardanne, le|"""  # Gardanne
    + r"""Arrêté\s+n°[\s\S]+?\s+du"""  # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + r""")"""
    + r"""\s+(?P<arr_date>"""
    + r"""(?:"""
    + r"""\d{2}[.]\d{2}[.]\d{4}|"""  # Peyrolles-en-Provence (en-tête)
    + r"""\d{2}/\d{2}/\d{4}|"""  # ?
    + r"""\d{1,2} """
    + rf"""{RE_MOIS}"""
    + r""" \d{4}"""  # Roquevaire (fin), Martigues (fin)
    + r""")"""
    + r""")"""
)
M_DATE = re.compile(RE_DATE, re.MULTILINE | re.IGNORECASE)
# numéro de l'arrêté
RE_NUM = (
    r"""(?:"""
    + r"""Extrait\s+du\s+registre\s+des\s+arrêtés\s+N°|"""
    + r"""Réf\s+:|"""
    + r"""Arrêté\s+n°|"""  # en-tête Peyrolles-en-Provence
    + r"""ARRETE\s+N°"""
    + r""")"""
    + r"""\s*(?P<arr_num>[^\n(]+)"""
)
M_NUM = re.compile(RE_NUM, re.MULTILINE | re.IGNORECASE)
# nom de l'arrêté
RE_NOM = r"""Objet:\s+(?P<arr_nom>[^\n]+)"""
M_NOM = re.compile(RE_NOM, re.MULTILINE | re.IGNORECASE)

"""Éléments dénotant la structure du texte.

"""

import re

from adresse import RE_ADRESSE, RE_COMMUNE
from str_date import RE_DATE
from typologie_securite import RE_CLASS_ALL


# numéro de l'arrêté
RE_ARR_NUM = (
    r"(?:"
    + r"Extrait\s+du\s+registre\s+des\s+arrêtés\s+N°"
    + r"|Réf\s+:"
    + r"|^Nos\s+Réf\s+:"  # Gardanne
    + r"|^A\.M\s+N°"  # Martigues
    + r"|^Décision\s+N°"  # Marseille (1)
    + r"|Arrêté\s+n°"  # en-tête Peyrolles-en-Provence
    + r"|ARRETE\s+N°"
    # + r"|^N°"  # motif trop peu spécifique, capture par exemple un numéro de parcelle
    + r")"
    + r"\s*(?P<arr_num>[^,;\n(]+)"
)
P_ARR_NUM = re.compile(RE_ARR_NUM, re.MULTILINE | re.IGNORECASE)
# 2e motif pour reconnaître le numéro d'arrêté, très générique donc à n'utiliser qu'en 2e lame (ou dernier recours)
RE_ARR_NUM_FALLBACK = (
    r"(?:"
    + r"^N°"  # Gardanne?
    + r"|^ARR-[^-]{2,3}-"  # Gemenos ; la 2e partie du préfixe varie selon les références (au même acte!): JUR, SG, ST, DGS... donc le numéro est la partie stable qui vient après
    + r")"
    + r"\s*(?P<arr_num>[^,;\n(]+)"
)
P_ARR_NUM_FALLBACK = re.compile(RE_ARR_NUM_FALLBACK, re.MULTILINE | re.IGNORECASE)

# nom de l'arrêté
RE_ARR_OBJET = r"Objet:\s+(?P<arr_nom>[^\n]+)"  # on laisse volontairement de côté la capture de "OBJET :\n\nARRÊTÉ DE PÉRIL\nORDINAIRE..." (Peyrolles) qu'il faudra traiter proprement par le layout 2 colonnes
P_ARR_OBJET = re.compile(RE_ARR_OBJET, re.MULTILINE | re.IGNORECASE)

# tous arrêtés
RE_VU = r"""^\s*VU[^e]"""
# RE_VU = r"^\s*(?P<vu>V[Uu][, ](.+))"
P_VU = re.compile(RE_VU, re.MULTILINE | re.IGNORECASE)  # re.VERBOSE ?

RE_CONSIDERANT = r"""^\s*CONSID[EÉ]RANT"""
# RE_CONSIDERANT = r"^\s*(?P<considerant>(Considérant|CONSIDERANT)[, ](.+))"
P_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE | re.IGNORECASE)

RE_ARRETE = r"""^\s*(?P<par_arrete>ARR[ÊE]T(?:E|ONS)(?:\s*:)?)"""
# RE_ARRETE = r"^\s*(ARR[ÊE]TE|ARR[ÊE]TONS)"
P_ARRETE = re.compile(RE_ARRETE, re.MULTILINE | re.IGNORECASE)

RE_ARTICLE = r"""^\s*ARTICLE\s+\d+"""
P_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE | re.IGNORECASE)

# (à valider)
RE_ABF = r"""[Aa]rchitecte\s+des\s+[Bb]âtiments\s+de\s+France"""
M_ABF = re.compile(RE_ABF, re.MULTILINE | re.IGNORECASE)

# éléments à extraire
# - commune
# capture: Peyrolles-en-Provence, Gignac-la-Nerthe, GEMENOS, Roquevaire, Gardanne
RE_MAIRE_COMM_DE = (
    r"Maire\s+" + r"(?:de\s+la\s+(?:Commune|Ville)\s+)?" + r"(?:de\s+|d['’]\s*)"
)
# "Nous[,.]": gestion d'erreur d'OCR ("." reconnu au lieu de ",")
RE_MAIRE_COMMUNE = (
    r"""(?P<autorite>"""
    + r"""^Le\s+"""
    + rf"""{RE_MAIRE_COMM_DE}"""
    + r"""|Nous[,.]\s+(?P<autorite_nom>[^,]+,\s+)?"""  # pas de "^" pour augmenter la robustesse (eg. séparateur "-" en fin de ligne précédente interprété comme un tiret de coupure de mot)
    + rf"""{RE_MAIRE_COMM_DE}"""
    + r""")"""
    + rf"""(?P<commune>{RE_COMMUNE})"""
    + r"(?:[,])?"
)
P_MAIRE_COMMUNE = re.compile(RE_MAIRE_COMMUNE, re.MULTILINE | re.IGNORECASE)

# - adresse
# adresse du bâtiment visé par l'arrêté
# TODO choisir la ou les bonnes adresses quand il y a risque de confusion
# (ex compliqué: "59, rue Peysonnel 13003 - PGI 18.06.20.pdf")
RE_ADR_DOC = (
    r"""(?:situ[ée](?:\s+au)?"""
    + r"""|désordres\s+sur\s+le\s+bâtiment\s+sis"""
    + r"""|immeuble\s+(?:du|numéroté)"""
    + r"""|sis[e]?(?:\s+à)?"""
    + r"""|(?:"""
    + r"""Objet\s*:"""
    + rf"""(?:\s+{RE_CLASS_ALL}\s*[,:–-]?)?"""
    + r""")"""
    + r""")\s+"""
    + rf"""(?P<adresse>{RE_ADRESSE})"""  # TODO ajouter la reconnaissance explicite d'une 2e adresse optionnelle (ex: "... / ...")
    + r"""(?:\s+"""
    + r"(?:[,:–-]\s+|[(])?"
    + r"(?:susceptible|parcelle|référence|concernant"
    + r"|est\s+pris\s+en|à\s+l[’']exception|de\s+mettre\s+fin)"
    + r""")?"""
)
M_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)

RE_INFOS_JOUR = r"\s*,\s+selon\s+nos\s+informations\s+à\s+ce\s+jour\s*,"

RE_PROPRIO_MONO = (
    r"appartient"
    + r"(?:"  # optionnel: "selon nos informations à ce jour"
    + rf"{RE_INFOS_JOUR}"
    + r")?"  # fin optionnel
    + r"\s+en\s+toute\s+propriété\s+"
    + r"(?:"  # à | à la | à l' | au | aux
    + r"[àa]\s+(?:la\s+|l['’]\s*)?"
    + r"|au(?:x)?"
    + r")"
    + r"(?P<propri>[^,–]+)"  # identité du propriétaire
    + r"[,]?\s+(?:sis(?:e)?|domicilié(?:e)?)\s+"
    + r"(?P<prop_adr>"
    + r"[\s\S]*?"  # complément d'adresse non-capturé dans RE_ADRESSE (ex: "Les toits de la Pounche")
    + rf"{RE_ADRESSE}"  # adresse du propriétaire
    + r")"
    # + r"(?:\s+ou\s+à\s+ses\s+ayants\s+droit)"  # WIP: contexte obligatoire?
)
P_PROPRIO_MONO = re.compile(RE_PROPRIO_MONO, re.MULTILINE | re.IGNORECASE)


# - propriétaire
RE_PROPRI = (
    r"(?:"
    + r"(?:appartenant\s+à|propriété\s+de)"
    + r"\s+la)"
    + r"(?P<propri>(?:Société\s+Civile\s+Immobilière|SCI)\s+.+)"
    + r"[,]?\s+sise\s+"
    + r"(?P<prop_adr>"
    + rf"{RE_ADRESSE}"
    + r")"
)
M_PROPRI = re.compile(RE_PROPRI, re.MULTILINE | re.IGNORECASE)

# - syndic
# TODO syndic judiciaire?
# TODO M. ... en qualité de syndic?
# TODO administrateur?
# ex: "Considérant que le syndicat des copropriétaires de cet immeuble est pris en la personne du Cabinet xxxx syndic, domicilié 11, avenue du Dol - 13001 MARSEILLE,"
RE_SYNDIC = (
    r"("
    # + r"le syndic(?:\s+de\s+copropriété)?"
    # + r"|syndic\s+:"
    + r"(?:syndic|syndicat\s+des\s+copropriétaires)"
    + r"(?:\s+de\s+(?:cet\s+|l['’]\s*)(?:immeuble|ensemble\s+immobilier))?"
    + r"(?:\s+est|,)?"  # + r"(?:\s+est|,)?"  # FIXME confusions possibles ancien/nouveau syndic (ex: "1 cours Jean Ballard 13001.pdf")
    + r"\s+pris\s+en\s+la\s+personne\s+(?:du|de)"
    + r"|syndicat\s+des\s+copropriétaires\s+représenté\s+par"
    + r")\s+"
    + r"(?P<syndic>[^,.]+?)"  # [\s\S]+?
    # + r"(?:(?:,)?\s*syndic)?"  # "syndic" peut faire partie du nom: "le bon syndic", "activ' syndic"
    + r"(?:"
    + r"[,.]"
    + r"|[,]?\s+(?:sis(?:e)?|domicilié(?:e)?)\s+"
    + rf"{RE_ADRESSE}"
    + r")"
)
M_SYNDIC = re.compile(RE_SYNDIC, re.MULTILINE | re.IGNORECASE)

# gestionnaire
RE_GESTIO = (
    r"(?:gestionnaire"
    + r"\s+de\s+(?:cet\s+|l['’]\s*)immeuble"
    + r"(?:\s+est|,)?"
    + r"\s+pris\s+en\s+la\s+personne\s+(?:du|de))"
    + r"(?P<gestio>[^,.]+?)"  # [\s\S]+?
    + r"(?:"
    + r"[,.]"
    + r"|[,]?\s+(?:sis(?:e)?|domicilié(?:e)?)\s+"
    + rf"{RE_ADRESSE}"
    + r")"
)
P_GESTIO = re.compile(RE_GESTIO, re.MULTILINE | re.IGNORECASE)


# date de l'arrêté
RE_DATE_SIGNAT = (
    r"""(?:"""
    + r"""^Fait\s+à\s+\S+[,]?\s+le"""  # Roquevaire (fin)
    + r"""|^Fait\s+à\s+Aix-en-Provence,\s+en\s+l['’]Hôtel\s+de\s+Ville,\nle"""  # Aix-en-Provence (fin)
    + r"""|^Gardanne,\s+le"""  # Gardanne
    + r"""|^Signé\s+le\s*:\s+"""
    + r"""|^Arrêté\s+n°[\s\S]+?\s+du"""  # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + r""")"""
    + r"""\s+(?P<arr_date>"""
    + rf"""{RE_DATE}"""
    + r""")"""
)
P_DATE_SIGNAT = re.compile(RE_DATE_SIGNAT, re.MULTILINE | re.IGNORECASE)

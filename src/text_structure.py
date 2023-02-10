"""Éléments dénotant la structure du texte.

"""

import re

from adresse import RE_ADRESSE, RE_COMMUNE
from str_date import RE_DATE
from typologie_securite import RE_CLASS_ALL


# numéro de l'arrêté
RE_NUM = (
    r"""(?:"""
    + r"""Extrait\s+du\s+registre\s+des\s+arrêtés\s+N°"""
    + r"""|Réf\s+:"""
    + r"""|Arrêté\s+n°"""  # en-tête Peyrolles-en-Provence
    + r"""|ARRETE\s+N°"""
    + r"""|^N°"""
    + r""")"""
    + r"""\s*(?P<arr_num>[^,;\n(]+)"""
)
M_NUM = re.compile(RE_NUM, re.MULTILINE | re.IGNORECASE)

# nom de l'arrêté
RE_NOM = r"""Objet:\s+(?P<arr_nom>[^\n]+)"""
M_NOM = re.compile(RE_NOM, re.MULTILINE | re.IGNORECASE)

# tous arrêtés
RE_VU = r"""^\s*V(U|u) [^\n]+"""
M_VU = re.compile(RE_VU, re.MULTILINE)

RE_CONSIDERANT = r"""^CONSID[EÉ]RANT [^\n]+"""
M_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE | re.IGNORECASE)

RE_ARRETE = r"""^ARR[ÊE]T(?:E|ONS)"""
M_ARRETE = re.compile(RE_ARRETE, re.MULTILINE | re.IGNORECASE)

RE_ARTICLE = r"""^ARTICLE \d+"""
M_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE | re.IGNORECASE)

# (à valider)
RE_ABF = r"""[Aa]rchitecte\s+des\s+[Bb]âtiments\s+de\s+France"""
M_ABF = re.compile(RE_ABF, re.MULTILINE | re.IGNORECASE)

# éléments à extraire
# - commune
# capture: Peyrolles-en-Provence, Gignac-la-Nerthe, GEMENOS, Roquevaire, Gardanne
RE_MAIRE_COMM_DE = r"Maire\s+(?:de\s+la\s+Commune\s+)?(?:de\s+|d')"
# "Nous[,.]": gestion d'erreur d'OCR ("." reconnu au lieu de ",")
RE_MAIRE_COMMUNE = (
    r"""(?:"""
    + rf"""Le\s+{RE_MAIRE_COMM_DE}"""
    + rf"""|Nous[,.]\s+(?:[^,]+,\s+)?{RE_MAIRE_COMM_DE}"""
    + r""")"""
    + rf"""(?P<commune>{RE_COMMUNE})"""
)
M_MAIRE_COMMUNE = re.compile(RE_MAIRE_COMMUNE, re.MULTILINE | re.IGNORECASE)

# - adresse
# adresse du bâtiment visé par l'arrêté
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
    + r"""(?:"""
    + r"""(?:[,:–-]\s+)|[(]"""
    + r""")?"""
    + r"""(?:susceptible|parcelle|référence|concernant)"""
    + r""")?"""
)
M_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)

# - propriétaire
RE_PROPRI = (
    r"""(?:à\s+la\s+)"""
    + r"""(?P<propri>Société\s+Civile\s+Immobilière\s+.+)"""
    + r"""[,]?\s+sise\s+"""
    + rf"""(?P<prop_adr>{RE_ADRESSE})"""
)
M_PROPRI = re.compile(RE_PROPRI, re.MULTILINE | re.IGNORECASE)

# - syndic
# TODO syndic judiciaire?
# TODO M. ... en qualité de syndic?
# TODO administrateur?
# ex: "Considérant que le syndicat des copropriétaires de cet immeuble est pris en la personne du Cabinet xxxx syndic, domicilié 11, avenue du Dol - 13001 MARSEILLE,"
RE_SYNDIC = (
    r"""(?:"""
    + r"""agence"""
    + r"""|le syndic(?:\s+de\s+copropriété)?"""
    + r"""|syndic\s+:"""
    + r"""|syndicat\s+des\s+copropriétaires(?:\s+de\s+(?:cet\s+|l'\s*)immeuble)?(?:\s+est)?\s+pris\s+en\s+la\s+personne\s+(?:du|de)"""
    + r""")\s+"""
    + r"""(?P<syndic>.+?)"""
    + r"""(?:"""
    + r"""[,.]"""
    + r"""|[,]?\s+(?:sis|domicilié)\s+"""
    + rf"""{RE_ADRESSE}"""
    + r""")"""
)
M_SYNDIC = re.compile(RE_SYNDIC, re.MULTILINE | re.IGNORECASE)

# date de l'arrêté
RE_DATE_DOC = (
    r"""(?:"""
    + r"""^Fait\s+à\s+\S+[,]?\s+le|"""  # Roquevaire (fin)
    + r"""^Fait à Aix-en-Provence, en l'Hôtel de Ville,\nle|"""  # Aix-en-Provence (fin)
    + r"""^Gardanne, le|"""  # Gardanne
    + r"""Arrêté\s+n°[\s\S]+?\s+du"""  # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + r""")"""
    + r"""\s+(?P<arr_date>"""
    + rf"""{RE_DATE}"""
    + r""")"""
)
M_DATE_DOC = re.compile(RE_DATE_DOC, re.MULTILINE | re.IGNORECASE)

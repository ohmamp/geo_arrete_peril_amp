"""Éléments dénotant la structure du texte.

"""

import re

from adresse import RE_ADRESSE, RE_COMMUNE
from domain_vocab import RE_NO
from str_date import RE_DATE
from typologie_securite import RE_CLASSE


# numéro de l'arrêté
RE_NUM_ARR = (
    r"(?:"
    + rf"Extrait\s+du\s+registre\s+des\s+arrêtés\s+{RE_NO}"
    + r"|Réf\s+:"
    + r"|^Nos\s+Réf\s+:"  # Gardanne
    + rf"|^A\.M\s+{RE_NO}"  # Martigues
    + rf"|^Décision\s+{RE_NO}"  # Marseille (1)
    + rf"|Arrêté\s+{RE_NO}"  # en-tête Peyrolles-en-Provence
    + rf"|ARRETE\s+{RE_NO}"
    # + rf"|^{RE_NO}"  # motif trop peu spécifique, capture par exemple un numéro de parcelle
    + r")"
    + r"\s*(?P<num_arr>[^,;\n(]+)"
)
P_NUM_ARR = re.compile(RE_NUM_ARR, re.MULTILINE | re.IGNORECASE)
# 2e motif pour reconnaître le numéro d'arrêté, très générique donc à n'utiliser qu'en 2e lame (ou dernier recours)
RE_NUM_ARR_FALLBACK = (
    r"(?:"
    + rf"^{RE_NO}"  # Gardanne?
    + r"|^ARR-[^-]{2,3}-"  # Gemenos ; la 2e partie du préfixe varie selon les références (au même acte!): JUR, SG, ST, DGS... donc le numéro est la partie stable qui vient après
    + r")"
    + r"\s*(?P<num_arr>[^,;\n(]+)"
)
P_NUM_ARR_FALLBACK = re.compile(RE_NUM_ARR_FALLBACK, re.MULTILINE | re.IGNORECASE)

# nom de l'arrêté
RE_NOM_ARR = r"Objet:\s+(?P<nom_arr>[^\n]+)"  # on laisse volontairement de côté la capture de "OBJET :\n\nARRÊTÉ DE PÉRIL\nORDINAIRE..." (Peyrolles) qu'il faudra traiter proprement par le layout 2 colonnes
P_NOM_ARR = re.compile(RE_NOM_ARR, re.MULTILINE | re.IGNORECASE)

# tous arrêtés
RE_VU = r"^\s*VU[^e]"
# RE_VU = r"^\s*(?P<vu>V[Uu][, ](.+))"
P_VU = re.compile(RE_VU, re.MULTILINE | re.IGNORECASE)  # re.VERBOSE ?

RE_CONSIDERANT = r"^\s*CONSID[EÉ]RANT"
# RE_CONSIDERANT = r"^\s*(?P<considerant>(Considérant|CONSIDERANT)[, ](.+))"
P_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE | re.IGNORECASE)

RE_ARRETE = r"^\s*(?P<par_arrete>ARR[ÊE]T(?:E|ONS)(?:\s*:)?)"
# RE_ARRETE = r"^\s*(ARR[ÊE]TE|ARR[ÊE]TONS)"
P_ARRETE = re.compile(RE_ARRETE, re.MULTILINE | re.IGNORECASE)

RE_ARTICLE = r"^\s*ARTICLE\s+\d+"
P_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE | re.IGNORECASE)

# éléments à extraire
# - commune
# capture: Peyrolles-en-Provence, Gignac-la-Nerthe, GEMENOS, Roquevaire, Gardanne
RE_MAIRE_COMM_DE = (
    r"Maire\s+" + r"(?:de\s+la\s+(?:Commune|Ville)\s+)?" + r"(?:de\s+|d['’]\s*)"
)
# "Nous[,.]": gestion d'erreur d'OCR ("." reconnu au lieu de ",")
RE_MAIRE_COMMUNE = (
    r"(?P<autorite>"
    + r"(?:"  # le maire de X
    + r"^Le\s+"
    + RE_MAIRE_COMM_DE
    + r")"
    + r"|(?:"  # Nous, (...,)? maire de X
    + r"Nous[,.]\s+(?P<autorite_nom>[^,]+,\s+)?"  # pas de "^" pour augmenter la robustesse (eg. séparateur "-" en fin de ligne précédente interprété comme un tiret de coupure de mot)
    + RE_MAIRE_COMM_DE
    + r")"
    + r")"  # fin named group "autorite"
    + rf"(?P<commune>{RE_COMMUNE})"
    + r"(?:[,])?"
)
P_MAIRE_COMMUNE = re.compile(RE_MAIRE_COMMUNE, re.MULTILINE | re.IGNORECASE)

# - adresse
# contexte droit (lookahead) possible pour une adresse de document
RE_ADR_RCONT = (
    r"(?:"
    + r"parcelle|section|référence|cadastr[ée]|situé"
    + r"|concernant|concerné"
    + r"|à\s+l[’']exception"
    + r"|à\s+leur\s+jonction"
    + r"|ainsi"
    + r"|appartenant"  # NEW 2023-03-11
    + r"|assorti"
    + r"|avec\s+risque"
    + r"|ce\s+diagnostic"
    + r"|ces\s+derniers"
    + r"|condamner"
    + r"|copropriété"
    + r"|de\s+mettre\s+fin"
    + r"|(?:doivent|doit)\s+prendre"
    + r"|(?:doivent|doit)\s+sous\s+un\s+délai"
    + r"|est\s+à\s+l['’]état|jusqu'à\s+nouvel"
    + r"|est\s+dans"
    + r"|(?:est|sont)\s+de\s+nouveau"
    + r"|(?:est|sont|reste|restent)\s+interdit"  # (?:e|s|es)?
    + r"|(?:(?:est|sont|ont\s+été|est\s+de|doit|doivent)$)"
    + r"|est\s+pris\s+en|pris\s+en\s+l"
    + r"|est\s+strictement\s+interdit"
    + r"|et(?:\s+à\s+en)?\s+interdire"
    + r"|et\s+au\s+cabinet"
    + r"|et\s+concerné"
    + r"|et\s+des\s+risques"
    + r"|et\s+installation"
    + r"|et\s+l['’]immeuble"  # 2023-03-11
    + r"|et\s+notamment"
    + r"|et\s+ordonne"
    + r"|(?:et\s+son\s+)?occupation"
    + r"|et\s+sur\s+l"
    + r"|étaiement"
    + r"|évacuation"
    + r"|faire\s+réaliser"
    + r"|fragilisé"  # 2023-03-11
    + r"|il\s+sera"
    + r"|jusqu['’]au"  # 2023-03-11
    + r"|lors\s+de"
    + r"|menace\s+de"
    + r"|mentionné"
    + r"|n['’](?:a|ont)\s+pas"
    + r"|ont\s+été\s+évacués"
    + r"|(?:peut|peuvent|doit|doivent|devra|devront|il\s+devra)\s+être"
    + r"|peuvent\s+exploiter"
    + r"|(?:pour$)"
    + r"|préconise"  # 2023-03-11
    + r"|présente"
    + r"|(?:pris$)"
    + r"|qui\s+se\s+retrouve"
    + r"|réalisé|effectué|établi"
    + r"|selon\s+les\s+hachures"
    + r"|signé"
    + r"|sont\s+accessibles"
    + r"|sur\s+une\s+largeur"
    + r"|sur\s+la\s+base"
    + r"|susceptible|permettant"
    + r"|suivant\s+annexe"
    # + r"|(?:[.]$)"  # RESUME HERE
    + r"|(?:^Nous,\s+Maire)|(?:^vu)|(?:^consid[ée]rant)|(?:^article)"
    + r")"
)
# adresse du bâtiment visé par l'arrêté
# TODO choisir la ou les bonnes adresses quand il y a risque de confusion
# (ex compliqué: "59, rue Peysonnel 13003 - PGI 18.06.20.pdf")
RE_ADR_DOC = (
    r"(?:"
    + r"situ[ée](?:\s+au)?"
    + r"|désordres\s+sur\s+le\s+bâtiment\s+sis"
    + r"|un\s+péril\s+grave\s+et\s+imminent\s+au"
    + r"|immeuble\s+(?:du|numéroté)"
    # + r"|sis[e]?(?:\s+à)?"
    + r"|(?:(?<!Risques, )sis[e]?(?:\s+à)?)"  # éviter un match sur l'adresse d'un service municipal
    + r"|(?:Objet\s*:"
    + rf"(?:\s+{RE_CLASSE}\s*[,:–-]?)?"
    + r")"  # fin "Objet:(classe)?"
    + rf"|(?:{RE_CLASSE}\s*[–-])"  # <classe> - <adresse>
    + r")\s+"  # fin alternatives contexte gauche
    + rf"(?P<adresse>{RE_ADRESSE})"  # TODO ajouter la reconnaissance explicite d'une 2e adresse optionnelle (ex: "... / ...")
    # contexte droit
    + r"(?:\s+"
    + r"(?:[,;:–-]\s+|[(])?"  # NEW 2023-03-11: ";"
    + rf"(?={RE_ADR_RCONT})"
    + r")?"
)
M_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)


# date de l'arrêté
RE_DATE_SIGNAT = (
    r"(?:"
    + r"^Fait\s+à\s+\S+[,]?\s+le"  # Roquevaire (fin)
    + r"|^Fait\s+à\s+Aix-en-Provence,\s+en\s+l['’]Hôtel\s+de\s+Ville,\nle"  # Aix-en-Provence (fin)
    + r"|^Gardanne,\s+le"  # Gardanne
    + r"|^Signé\s+le\s*:\s+"
    + rf"|^Arrêté\s+{RE_NO}[\s\S]+?\s+du"  # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + r")"
    + r"\s+(?P<arr_date>"
    + RE_DATE  # TODO str_date.RE_DATE_PREC ?
    + r")"
)
P_DATE_SIGNAT = re.compile(RE_DATE_SIGNAT, re.MULTILINE | re.IGNORECASE)

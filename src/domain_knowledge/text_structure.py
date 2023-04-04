"""Éléments dénotant la structure du texte.

"""

import re

from src.domain_knowledge.adresse import RE_ADRESSE
from src.domain_knowledge.arrete import RE_ARRETE
from src.domain_knowledge.typologie_securite import RE_CLASSE
from src.utils.text_utils import RE_NO


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
    + r"|depuis"
    + r"|(?:doit|doivent|devra|devront|il\s+devra|peut|peuvent)\s+(être|exploiter|prendre|(?:dans|sous)\s+un\s+délai)"
    + r"|(?:est|sont)\s+(?:à\s+l['’]état|de\s+nouveau|dans|à)"
    + r"|(?:est|sont)\s+(?:mis\s+en\s+demeure)"
    + r"|(?:est|sont|reste|restent)\s+((strictement\s+)?interdit|accessible|pris)"  # (?:e|s|es)?
    + r"|(?:(?:est|sont|ont\s+été|est\s+de|doit|doivent)$)"
    + r"|et(?:\s+à\s+en)?\s+interdire"
    + r"|et\s+au\s+cabinet"
    + r"|et\s+(?:concerné|donnant\s+sur)"
    + r"|et\s+de\s+l['’]appartement"  # la fin du motif évite de capturer "rue Roug*et de *Lisle"
    + r"|et\s+des\s+risques"
    + r"|et\s+installation"
    + r"|et\s+l['’]immeuble"  # 2023-03-11
    + rf"|et\s+l['’]{RE_ARRETE}"
    + r"|(?:et\s+(?:l['’]\s*|son\s+))?occupation"
    + r"|et\s+notamment"
    + r"|et\s+ordonne"
    + r"|et\s+repr[ée]sentant"
    + r"|et\s+sur\s+l"
    + r"|étaiement"
    + r"|évacuation"
    + r"|faire\s+réaliser"
    + r"|figurant"
    + r"|fragilisé"  # 2023-03-11
    + r"|il\s+sera"
    + r"|jusqu['’](?:au|à)"  # 2023-03-11
    + r"|le\s+rapport"
    + r"|leur\s+demandant"
    + r"|lors\s+de"
    + r"|menace\s+de"
    + r"|mentionné"
    + r"|mettant\s+fin"
    + r"|^Nomenclature\s+ACTES"
    + r"|n['’](?:a|ont)\s+pas"
    + rf"|{RE_NO}"  # WIP 2023-03-12
    + r"|ont\s+été\s+évacués"
    + r"|permettant"
    + r"|(?:pour$)"
    + r"|préconise"  # 2023-03-11
    + r"|présence\s+de"
    + r"|présente"
    + r"|pris\s+en\s+l"
    + r"|(?:pris$)"
    + r"|propri[ée]taire"
    + r"|qui\s+se\s+retrouve"
    + r"|réalisé|effectué|établi"
    + r"|représenté"
    + r"|selon\s+les\s+hachures"
    + r"|signé"
    + r"|sur\s+une\s+largeur"
    + r"|sur\s+la\s+(?:base|parcelle)"
    + r"|susceptible"
    + r"|suivant\s+annexe"
    # + r"|(?:[.]$)"  # RESUME HERE
    + r"|(?:^Nous,\s+)|(?:^le\s+maire)|(?:^vu)|(?:^consid[ée]rant)|(?:^article)"  # NEW 2023-03-29 "le maire"
    + r")"
)
# adresse du bâtiment visé par l'arrêté
# TODO choisir la ou les bonnes adresses quand il y a risque de confusion
# (ex compliqué: "59, rue Peysonnel 13003 - PGI 18.06.20.pdf")
RE_ADR_DOC = (
    # contexte gauche (pas de lookbehind car pas de longueur fixe et unique)
    r"(?:"
    + r"situ[ée](?:\s+(?:au|du))?"
    + r"|désordres\s+(?:importants\s+)?(?:sur|affectant)\s+(?:le\s+bâtiment|l['’]immeuble)\s+sis"
    + r"|un\s+péril\s+grave\s+et\s+imminent\s+(?:à|au)"
    + r"|immeuble\s+(?:du|numéroté)"
    # + r"|sis[e]?(?:\s+à)?"
    + r"|(?:(?<!Risques, )sis[e]?[,]?(?:\s+(?:[àa]|au|du))?)"  # éviter un match sur l'adresse d'un service municipal
    # Objet: <classe>? - <adresse> (ex: "Objet: Péril grave et imminent - 8 rue X")
    + r"|(?:Objet\s*:"
    + rf"(?:\s+{RE_CLASSE}(?:\s*[,:–-]|\s+au)?)?"
    + r")"  # fin "Objet:(classe)?"
    + rf"|(?:{RE_CLASSE}\s*[–-])"  # <classe> - <adresse>
    + r")\s+"  # fin alternatives contexte gauche
    # adresse du document
    + rf"(?P<adresse>{RE_ADRESSE})"  # TODO ajouter la reconnaissance explicite d'une 2e adresse optionnelle (ex: "... / ...")
    # contexte droit
    + r"(?P<rcont>\s*"  # WIP \s+  # WIP (?=
    + r"(?:[,;:–-]\s*|[(])?"  # NEW 2023-03-11: ";"  # WIP \s+
    + rf"(?:{RE_ADR_RCONT})"  # WIP (?=
    + r")?"
)
P_ADR_DOC = re.compile(RE_ADR_DOC, re.MULTILINE | re.IGNORECASE)

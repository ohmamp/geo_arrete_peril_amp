"""Repérage et extraction d'entités nommées propres aux arrêtés sur le logement.

Propriétaire, gérant, syndic ou administrateur.
"""

import re

from adresse import RE_ADRESSE


# formule courante dans ces arrêtés pour l'identification des propriétaires ou du syndic
RE_INFOS_JOUR = r"\s*,\s+selon\s+nos\s+informations\s+à\s+ce\s+jour\s*(?:[:,])"

# expression générique "sis <ADRESSE> | domicilié (au)? <ADRESSE>"
RE_SIS_DOMICILIE_ADR = (
    r"(?:"  # début global
    + r"(?:"
    + r"(?:sis(?:e|es)?)"
    + r"|(?:domicilié(?:e|s|es)?(?:\s+(?:au|à))?)"
    + r")(?:\s*,)?\s+"
    + rf"(?:{RE_ADRESSE})?"
    + r")"  # fin global
)

# propriétaire
# - mono propriété
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
    + r"(?P<proprio>[^,–]+)"  # identité du propriétaire
    + r"[,]?\s+(?:sis(?:e)?|domicilié(?:e)?)\s+"
    + r"(?P<prop_adr>"
    + r"[\s\S]*?"  # complément d'adresse non-capturé dans RE_ADRESSE (ex: "Les toits de la Pounche")
    + rf"{RE_ADRESSE}"  # adresse du propriétaire
    + r")"
    # + r"(?:\s+ou\s+à\s+ses\s+ayants\s+droit)"  # WIP: contexte obligatoire?
)
P_PROPRIO_MONO = re.compile(RE_PROPRIO_MONO, re.MULTILINE | re.IGNORECASE)

# FIXME multi-propriété
RE_PROPRIO = (
    r"(?:"  # global
    # contexte gauche
    + r"(?:"
    + r"(?:appartenant\s+à|appartient\s+à|propriété\s+de)"
    + r"\s+la"
    + r")"
    # propriétaire
    + r"(?P<proprio>"
    + r"(?:Société\s+Civile\s+Immobilière|SCI)\s+.+"
    # TODO propriétaires non SCI
    + r")"
    # contexte droit: adresse éventuelle
    + r"[,]?\s+(?:sis(?:e)?|domicili[ée](?:e)?)\s+"
    + r"(?P<prop_adr>"
    + rf"{RE_ADRESSE}"
    # TODO "dont le représentant est..."
    + r")"
    + r")"  # fin global
)
P_PROPRIO = re.compile(RE_PROPRIO, re.MULTILINE | re.IGNORECASE)


# syndic ou administrateur, en formes courtes et longues
RE_SYNDIC_ADMIN = (
    r"(?:"
    + r"(?:syndic(?:\s+(?:bénévole|judiciaire|provisoire))?(?:\s+de\s+copropriété)?)"
    + r"|(?:syndicat\s+des\s+copropriétaires)"
    + r"|(?:administrateur\s+(?:judiciaire|provisoire))"
    + r")"
)

# - syndic
# FIXME nettoyer le texte en amont: convertir les accents combinés (U+0300 \xcc\x80, U+0301 \xcc\x81...): e\xcc\x81 => é
# ====> https://docs.python.org/3/howto/unicode.html#comparing-strings
# RESUME HERE

# FIXME retrouver le syndic de "/home/mathieu/dev/agperils-amp/data/raw/arretes_peril_compil/évacuation au 08.11.2019.pdf"
# FIXME retrouver le syndic de "/home/mathieu/dev/agperils-amp/data/raw/arretes_peril_compil/modif 57 rue Louis Merlino 13014 le Super Belvédère.pdf"
# FIXME (syndic) "bénévole X"
# FIXME "pris en la personne ..."
# TODO syndic judiciaire?
# TODO M. ... en qualité de syndic?
# ex: "Considérant que le syndicat des copropriétaires de cet immeuble est pris en la personne du Cabinet xxxx syndic, domicilié 11, avenue du Dol - 13001 MARSEILLE,"
RE_SYNDIC = (
    r"(?:"
    + r"(?P<syndic_pre>"
    # contexte 1: syndic|administrateur (de cet immeuble) pris en la personne de|du <syndic>
    r"(?:"
    # + r"|syndic\s+:"
    + RE_SYNDIC_ADMIN
    + r"(?:"  # optionnel: immeuble
    + r"\s+de\s+(?:cet\s+|l['’]\s*)(?:immeuble|ensemble\s+immobilier)"
    # + rf"(?:\s+sis\s+{RE_ADRESSE})?"  # option dans l'option: adresse de l'immeuble
    + r")?"  # fin optionnel: immeuble
    + r"(?:\s+est|(?:\s*,))?"  # + r"(?:\s+est|,)?"  # FIXME confusions possibles ancien/nouveau syndic (ex: "1 cours Jean Ballard 13001.pdf")
    + r"\s+pris\s+en\s+la\s+personne\s+(?:de|du)"
    + r")"  # fin contexte 1
    # contexte 2: syndicat des copropriétaires représenté par <syndic>
    + r"|(?:syndicat\s+des\s+copropriétaires(?:\s*,)?\s+représenté\s+par"
    + r"(?:\s+"
    + r"(?:le\s+syndic(?:\s+(?:bénévole|judiciaire|provisoire))?)"
    + r"|(?:l['’]\s*administrateur\s+(?:judiciaire|provisoire))"
    + r")?"
    + r")"  # fin contexte 2
    + r")\s+"  # fin syndic_pre
    + r"(?P<syndic>"
    # - personnes physiques ; il faut notamment capturer explicitement les formes "M./Mr."
    # sinon le "." arrête la capture (et le syndic extrait est seulement "M" ou "Mr"...)
    + r"(?:(?:M\s*[.]|Mr(\s*[.])?|Mme|Monsieur|Madame)\s+[^,]+?)"
    # - liste explicite de syndics dont le nom inclut "syndic", pour éviter la capture à droite
    + r"|(?:(le\s+)?Cabinet\s+ACTIV[’']\s+SYNDIC)"
    + r"|(?:(le\s+)?Cabinet\s+LE\s+BON\s+SYNDIC)"
    # - "le cabinet | l'agence immobilière ..."
    + r"|(?:"
    + r"(?:(le\s+)?cabinet|(?:(l['’]\s*)?agence(?:immobili[èe]re)?))"
    + r"\s+[^,]+?"  # nom attrape-tout sauf virgules
    + r")"
    + r"|(?:[^,.]+?)"  # attrape tout, sauf les points (acceptés pour les personnes physiques et cabinets)  # [\s\S]+?
    + r")"  # fin alternative syndic
    + r"(?:"  # contexte droit: rien (,|.) ou adresse du syndic et éventuellement qualité
    + r"(?:\s*[.]\s+)"  # s'arrêter au point ".", sauf pour "M." (monsieur)
    + r"|(?:\s*,\s+(?!(?:sis|domicilié|syndic|administrateur)))"  # s'arrêter à la virgule "," sauf si... negative lookahead
    + r"|(?P<syndic_post>"
    + r"(?:\s*,)?\s+"  # adresse et/ou qualité du syndic, mais il faut au moins l'un des deux
    + r"(?:"
    + rf"(?:(?:{RE_SIS_DOMICILIE_ADR})(?:(?:\s*,)?\s+{RE_SYNDIC_ADMIN})?)"  # adresse + éventuellement qualité du syndic|admin
    + rf"|(?:(?:{RE_SYNDIC_ADMIN})(?:(?:\s*,)?\s+{RE_SIS_DOMICILIE_ADR})?)"  # qualité du syndic|admin + éventuellement adresse
    + r")"  # fin optionnel: adresse et/ou qualité du syndic
    + r")"  # fin syndic_post
    + r")"  # fin contexte droit
    + r")"  # fin global
)
P_SYNDIC = re.compile(RE_SYNDIC, re.MULTILINE | re.IGNORECASE)

# gestionnaire
RE_GEST = (
    r"(?:"
    # contexte gauche
    + r"(?:"
    + r"gestionnaire"
    + r"\s+de\s+(?:cet\s+|l['’]\s*)immeuble"
    + r"(?:"  # alternative: est | ( est|,) pris en la personne de|du
    + r"(?:\s+est\s+(?!pris\s+en\s+la\s+personne\s+))"
    + r"|(?:(?:\s+est|\s*,)?\s+pris\s+en\s+la\s+personne\s+(?:du|de)\s+)"
    + r")"  # fin alternative "est"
    + r")"
    # fin contexte gauche
    # identité du gestionnaire
    + r"(?P<gestio>[^,.]+?)"  # [\s\S]+?
    # contexte droit
    + r"(?:"
    + r"[,.]"
    # (contenant éventuellement son adresse)
    + r"|[,]?\s+(?:sis(?:e)?|domicilié(?:e)?)\s+"
    + rf"{RE_ADRESSE}"
    + r")"
    # fin contexte droit
    + r")"
)
P_GEST = re.compile(RE_GEST, re.MULTILINE | re.IGNORECASE)


# (hors périmètre)
RE_ABF = r"[Aa]rchitecte\s+des\s+[Bb][âa]timents\s+de\s+France"
M_ABF = re.compile(RE_ABF, re.MULTILINE | re.IGNORECASE)

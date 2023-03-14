"""Repérage et extraction de données propres aux arrêtés sur le logement.

Propriétaire, gestionnaire, syndic ou administrateur, adresse de l'immeuble concerné.
"""

import logging
import re

from src.domain_knowledge.adresse import RE_ADRESSE
from src.domain_knowledge.text_structure import M_ADR_DOC, RE_ADR_RCONT


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

# "en|ne" : gestion des typos
RE_PRIS_EN_LA_PERSONNE_DE = (
    r"(?:pris\s+(?:en|ne)\s+la\s+personne\s+(?:de\s+|du\s+|d['’]\s*)?)"
)

# - gestionnaire
RE_GEST = (
    r"(?:"
    # contexte gauche
    + r"(?:"
    # negative lookbehind, à réactiver si on décide de ne pas capturer "appartient en toute propriété au gestionnaire pris en la personne du Consulat Général..."
    # + r"(?!en\s+toute\s+propri[ée]t[ée]\s+au)"
    + r"gestionnaire"
    + r"(?:\s+de\s+(?:cet\s+|l['’]\s*)immeuble)?"
    # TODO ajouter "sis <adresse>"
    + r"(?:"
    # est (tout court)
    + rf"(?:\s+est\s+(?!{RE_PRIS_EN_LA_PERSONNE_DE}))"
    # (est|,)? pris en la personne de
    + rf"|(?:(?:\s+est|\s*,)?\s+{RE_PRIS_EN_LA_PERSONNE_DE})"
    + r")"  # fin alternative "est"
    + r")"
    # fin contexte gauche
    # identité du gestionnaire
    + r"(?P<gestio>"
    # (cabinet | groupe | agence) Xyz: nom attrape-tout sauf virgules ; autorise les points (ex: cabinet S.I.P.)
    + r"(?:"
    + r"(?:(?:le\s+)?cabinet|(?:le\s+)?groupe|(?:l['’]\s*)?agence(?:\s+immobili[èe]re)?)"
    + r"\s+[^,]+?"
    + r")"
    # attrape tout, sauf les points (acceptés pour les personnes physiques et cabinets)  # [\s\S]+?
    + r"|(?:[^,.]+?)"  # [\s\S]+?
    + r")"
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


def get_gest(page_txt: str) -> str:
    """Détecte si une page contient un nom de gestionnaire immobilier.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    syndic: str
        Nom de gestionnaire si détecté, None sinon.
    """
    match = P_GEST.search(page_txt)
    return match.group("gestio") if match is not None else None


# - propriétaire
#   - mono propriété
# TODO cas complexe: plusieurs mono- et copropriétés: "12a, boulevard Dugommier 13001.pdf"
# TODO "preneur du bail emphytéotique" => propriétaire? (mais il y a aussi un propriétaire !) ex: "2 chemin de la Mure.pdf"
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
    # optionnel: représentants (si société)
    + r"(?:"
    + r"[,]?\s+(?:représenté(?:e)?\s+par)\s+(?:[,–-]\s*)?"
    + r"[^,–]+"
    + r")?"
    + r"[,]?\s+(?:sis(?:e)?|domicili[ée](?:e)?)\s+(?:[,–-]\s*)?"
    + r"(?P<prop_adr>"
    + r"[\s\S]*?"  # complément d'adresse non-capturé dans RE_ADRESSE (ex: "Les toits de la Pounche")
    + rf"{RE_ADRESSE}"  # adresse du propriétaire
    + r")"
    # + r"(?:[,]?\s+ou\s+(?:à\s+)?(?:ses|leurs)\s+ayant[s]?(?:\s+|[-])droit[s]?)"  # WIP: contexte obligatoire?
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


def get_proprio(page_txt: str) -> bool:
    """Extrait le nom et l'adresse du propriétaire.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    syndic: str
        Nom et adresse du propriétaire si détecté, None sinon.
    """
    # on essaie d'abord de détecter un mono-propriétaire (WIP)
    if match := P_PROPRIO_MONO.search(page_txt):
        logging.warning(f"mono-propriétaire: {match}\n{match.group(0)}")
        return match.group("proprio")
    # puis sinon les multi-propriétaires (TODO proprement)
    elif match := P_PROPRIO.search(page_txt):
        logging.warning(f"mono- ou multi-propriétaire: {match}\n{match.group(0)}")
        return match.group("proprio")
    else:
        return None


# - syndic / administrateur
# FIXME retrouver le syndic de "évacuation au 08.11.2019.pdf"
# TODO M. ... en qualité de syndic?
#
#   - administrateur judiciaire|provisoire
RE_ADMIN = r"(?:administrateur\s+(?:judiciaire|provisoire))"
#   - syndic, en formes courtes et longues
RE_SYNDIC = (
    r"(?:syndic"
    + r"(?:\s+(?:bénévole|judiciaire|provisoire))?"
    + r"(?:\s+de\s+copropriété)?"
    + r")"
)
#   - syndic ou administrateur
# + rf"|{RE_SYNDICAT_COPRO}"
RE_SYNDIC_ADMIN = r"(?:" + RE_SYNDIC + rf"|{RE_ADMIN}" + r")"
#   - syndicat des copropriétaires
RE_SYNDICAT_COPRO = r"(?:syndicat\s+des\s+copropriétaires)"
#   - avec le contexte
RE_SYNDIC_LONG = (
    r"(?:"
    + r"(?P<syndic_pre>"
    # contexte 1: syndic|administrateur (de cet immeuble) pris en la personne de|du <syndic>
    r"(?:"
    # + r"|syndic\s+:"
    + RE_SYNDIC_ADMIN
    + r"(?:"  # optionnel: immeuble
    + r"\s+de\s+(?:cet\s+|l['’]\s*)(?:immeuble|ensemble\s+immobilier)"
    # + rf"(?:\s+sis\s+{RE_ADRESSE})?"  # option dans l'option: adresse de l'immeuble  # WIP 2023-03-11
    + r")?"  # fin optionnel: immeuble
    + r"(?:\s+est|(?:\s*,))?"  # + r"(?:\s+est|,)?"  # FIXME confusions possibles ancien/nouveau syndic (ex: "1 cours Jean Ballard 13001.pdf")
    + rf"\s+{RE_PRIS_EN_LA_PERSONNE_DE}"
    + r")"  # fin contexte 1
    # contexte 1b: syndicat des copropriétaires pris en la personne de|du
    + rf"|(?:{RE_SYNDICAT_COPRO}"
    + r"(?:"  # optionnel: immeuble
    + r"\s+de\s+(?:cet\s+|l['’]\s*)(?:immeuble|ensemble\s+immobilier)"
    # + rf"(?:\s+sis\s+{RE_ADRESSE})?"  # option dans l'option: adresse de l'immeuble  # WIP 2023-03-11
    + r")?"  # fin optionnel: immeuble
    + r"(?:\s+est|(?:\s*,))?"  # + r"(?:\s+est|,)?"  # FIXME confusions possibles ancien/nouveau syndic (ex: "1 cours Jean Ballard 13001.pdf")
    + rf"\s+{RE_PRIS_EN_LA_PERSONNE_DE}"
    + r")"  # fin contexte 1b
    # contexte 2: syndicat des copropriétaires représenté par <syndic>
    + rf"|(?:{RE_SYNDICAT_COPRO}"
    + r"(?:"  # optionnel: immeuble
    + r"\s+de\s+(?:cet\s+|l['’]\s*)(?:immeuble|ensemble\s+immobilier)"
    # + rf"(?:\s+sis\s+{RE_ADRESSE})?"  # option dans l'option: adresse de l'immeuble  # WIP 2023-03-11
    + r")?"  # fin optionnel: immeuble
    + r"(?:\s+est|(?:\s*,))?"
    + r"\s+représenté\s+par\s+"
    + r"(?:"  # optionnel:
    # le syndic | l'admin (pris en la personne de)?
    + rf"(?:(?:l['’]\s*{RE_ADMIN}|le\s+{RE_SYNDIC})\s+(?:{RE_PRIS_EN_LA_PERSONNE_DE})?)"
    # un syndic | un admin pris en la personne de
    + rf"|(?:un\s+(?:{RE_ADMIN}|{RE_SYNDIC})\s+{RE_PRIS_EN_LA_PERSONNE_DE})"  # WIP
    + r")?"  # fin optionnel
    + r")"  # fin contexte 2
    + r")"  # fin syndic_pre
    + r"(?P<syndic>"
    # - personnes physiques ; il faut notamment capturer explicitement les formes "M./Mr."
    # sinon le "." arrête la capture (et le syndic extrait est seulement "M" ou "Mr"...)
    + r"(?:(?:M\s*[.]|Mr(\s*[.])?|Mme|Monsieur|Madame)\s+[^,]+?)"
    # - liste explicite de syndics dont le nom inclut "syndic", pour éviter la capture à droite
    + r"|(?:(le\s+)?Cabinet\s+ACTIV[’']?\s+SYNDIC)"
    + r"|(?:(le\s+)?Cabinet\s+LE\s+BON\s+SYNDIC)"
    # - "le cabinet | l'agence immobilière ..."
    + r"|(?:"
    + r"(?:(?:le\s+)?cabinet|(?:le\s+)?groupe|(?:l['’]\s*)?agence(?:\s+immobili[èe]re)?)"
    + r"\s+[^,]+?"  # nom attrape-tout sauf virgules ; autorise les points (ex: cabinet S.I.P.)
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
    + rf"|(?:(?:(?<!un ){RE_SYNDIC_ADMIN})(?:(?:\s*,)?\s+{RE_SIS_DOMICILIE_ADR})?)"  # qualité du syndic|admin + éventuellement adresse
    # TODO? (?:en\s+qualité\s+(?:de\s+|d['’]\s*))? [syndic|administrateur...]
    + r")"  # fin optionnel: adresse et/ou qualité du syndic
    + r")"  # fin syndic_post
    + r")"  # fin contexte droit
    + r")"  # fin global
)
P_SYNDIC = re.compile(RE_SYNDIC_LONG, re.MULTILINE | re.IGNORECASE)


def get_syndic(page_txt: str) -> bool:
    """Détecte si une page contient un nom de syndic.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    syndic: str
        Nom de syndic si détecté, None sinon.
    """
    if m_synd := P_SYNDIC.search(page_txt):
        logging.warning(
            f"Syndic: {m_synd.group(0)}\n{m_synd.group('syndic_pre')} / {m_synd.group('syndic')} / {m_synd.group('syndic_post')}"
        )
        return m_synd.group("syndic")
    else:
        return None


# (hors périmètre)
RE_ABF = r"[Aa]rchitecte\s+des\s+[Bb][âa]timents\s+de\s+France"
M_ABF = re.compile(RE_ABF, re.MULTILINE | re.IGNORECASE)


# éléments spécifiques à certains types d'arrêtés
# - données
# nettoyage de l'adresse récupérée: on supprime le contexte droit
RE_ADR_CLEANUP = (
    # rf"""(?P<adresse>{RE_ADRESSE})"""
    r"(?:[(]"  # parenthèse ou
    + r"|(?:\s*[-–,])?\s*)"  # séparateur puis espace(s)
    + rf"{RE_ADR_RCONT}"
    + r"[\s\S]*"
)


# TODO plusieurs adresses, ex: "32, rue Félix Zoccola, 1-3-5, rue Edgar Quinet.pdf"
def get_adr_doc(page_txt: str) -> bool:
    """Extrait l'adresse visée par le document.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    adresse: str | None
        Adresse visée par le document si trouvée dans le texte, None sinon.
    """
    if m_adr := M_ADR_DOC.search(page_txt):
        adr = m_adr.group("adresse")
        # nettoyer la valeur récupérée
        # - couper sur certains contextes droits
        adr = re.sub(RE_ADR_CLEANUP, "", adr, flags=(re.MULTILINE | re.IGNORECASE))
        # - enlever l'éventuelle ponctuation finale
        if adr.endswith((".", ",")):
            adr = adr[:-1]
        # - remplacer les retours à la ligne par des espaces
        adr = adr.replace("\n", " ")  # 2023-03-04
        return adr
    else:
        return None


# M_ADR_CLEANUP = re.compile(RE_ADR_CLEANUP, re.MULTILINE | re.IGNORECASE)

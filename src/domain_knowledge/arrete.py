"""Structure d'un arrêté de collectivité territoriale.

"""

# TODO garder la date de signature ou d'affichage ? (ex: Peyrolles)

import re

from src.domain_knowledge.adresse import RE_COMMUNE
from src.utils.text_utils import RE_CARDINAUX, RE_NO, RE_ORDINAUX
from src.utils.str_date import RE_DATE


# "arrêté" et ses graphies
RE_ARRETE = r"Arr[êeé]t[ée](?:\s+municipal)?"

# - maire de la commune
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
# nettoyage
RE_MAIRE_COMMUNE_CLEANUP = (
    rf"""(?P<commune>{RE_COMMUNE})"""
    + r"""\s+"""
    + r"""(?:(CB|JFF) Accusé de réception)"""
)
M_MAIRE_COMMUNE_CLEANUP = re.compile(
    RE_MAIRE_COMMUNE_CLEANUP, re.MULTILINE | re.IGNORECASE
)

# - extraction de la commune prenant l'arrêté, à partir de la mention du maire
# il peut être nécessaire de nettoyer la zone extraite pour enlever le contexte droit (reconnaissance trop étendue)
def get_commune_maire(page_txt: str) -> bool:
    """Extrait le nom de la commune précédé de la mention du maire.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    nom_commune: str | None
        Nom de la commune si le texte contient une mention du maire, None sinon.
    """
    if match_mc := P_MAIRE_COMMUNE.search(page_txt):
        com_maire = match_mc.group("commune")
        # nettoyage de la valeur récupérée
        if m_com_cln := M_MAIRE_COMMUNE_CLEANUP.search(com_maire):
            com_maire = m_com_cln.group("maire_commune")
        return com_maire
    else:
        return None


# Vu, considérant, article
RE_VU = r"^\s*VU[^e]"
# RE_VU = r"^\s*(?P<vu>V[Uu][,\s](.+))"
P_VU = re.compile(RE_VU, re.MULTILINE | re.IGNORECASE)  # re.VERBOSE ?


def contains_vu(page_txt: str) -> bool:
    """Détecte si une page contient un VU.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient un VU
    """
    return P_VU.search(page_txt) is not None


RE_CONSIDERANT = r"^\s*CONSID[EÉ]RANT"
# RE_CONSIDERANT = r"^\s*(?P<considerant>(Considérant|CONSIDERANT)[,\s](.+))"
P_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE | re.IGNORECASE)


def contains_considerant(page_txt: str) -> bool:
    """Détecte si une page contient un CONSIDERANT.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient un CONSIDERANT
    """
    return P_CONSIDERANT.search(page_txt) is not None


#
RE_ARRETONS = rf"^\s*(?P<par_arrete>ARR[ÊE]T(?:E|ONS|É(?!\s+{RE_NO}))(?:\s*:)?)"  # Rognes: "ARRÊTÉ" dans cette position (?! conflit avec le repérage d'ARRÊTÉ?)
# RE_ARRETONS = r"^\s*(ARR[ÊE]TE|ARR[ÊE]TONS)"
P_ARRETONS = re.compile(RE_ARRETONS, re.MULTILINE | re.IGNORECASE)


def contains_arrete(page_txt: str) -> bool:
    """Détecte si une page contient ARRET(E|ONS).

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    has_stamp: bool
        True si le texte contient ARRET(E|ONS)
    """
    return P_ARRETONS.search(page_txt) is not None


# "Article 1(er)?", "Article 2" etc ; confusion possible OCR: "l" pour "1"
#
RE_ARTICLE = r"^\s*ARTICLE\s+(?:[1l]\s*(?:er)?|\d+" + rf"|{RE_ORDINAUX}|{RE_CARDINAUX})"
P_ARTICLE = re.compile(RE_ARTICLE, re.MULTILINE | re.IGNORECASE)


def contains_article(page_txt: str) -> bool:
    """Détecte si une page contient un Article.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient un Article
    """
    return P_ARTICLE.search(page_txt) is not None


# date de signature de l'arrêté
RE_DATE_SIGNAT = (
    r"(?:"
    + r"^Fait\s+à\s+\S+[,]?\s+le"  # Roquevaire (fin), Gémenos (fin ; à vérifier après OCR)
    # Aix-en-Provence (fin)
    + r"|^Fait\s+à\s+Aix-en-Provence,\s+en\s+l['’]Hôtel\s+de\s+Ville,\nle"
    # Gardanne
    + r"|^Gardanne,\s+le"
    # Marseille
    + r"|^Signé\s+le\s*:\s+"
    # Meyrargues
    + rf"|^ARRÊTÉ\s+DU\s+MAIRE\s+{RE_NO}[^\n]+\nen\s+date\s+du\s+"
    # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + rf"|^Arrêté\s+{RE_NO}[\s\S]+?\s+du"
    # Peyrolles-en-Provence (fin)
    + r"|^Peyrolles-en-Provence,\s+le"
    # + r"|^Affiché[e]\s+le\s+:"  # TODO garder la date de signature ou d'affichage?
    + r")"
    + r"\s+(?P<arr_date>"
    + RE_DATE  # TODO str_date.RE_DATE_PREC ?
    + r")"
)
P_DATE_SIGNAT = re.compile(RE_DATE_SIGNAT, re.MULTILINE | re.IGNORECASE)


def get_date(page_txt: str) -> bool:
    """Récupère la date de l'arrêté.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_date: str
        Date du document si trouvée, None sinon.
    """
    if m_date_d := P_DATE_SIGNAT.search(page_txt):
        return m_date_d.group("arr_date")
    else:
        return None


# numéro de l'arrêté
# TODO Peyrolles:  + r"|(?:A \d{4}-" + RE_MM + r"-\d{3})"
RE_NUM_ARR = (
    r"(?:"
    #
    + rf"Extrait\s+du\s+registre\s+des\s+arrêtés\s+{RE_NO}"
    # Gignac-la-Nerthe:
    + rf"|EXTRAIT\s+DU\s+REGISTRE\s+des\s+ARRETES\s+du\s+MAIRE\n{RE_NO}\s+"
    #
    + r"|Réf\s+:"
    # Gardanne:
    + r"|^Nos\s+Réf\s+:"
    # Martigues:
    + rf"|^A\.M\s+{RE_NO}"
    # Marseille (1)
    + rf"|^Décision\s+{RE_NO}"
    # Meyrargues
    + rf"|^ARRÊTÉ\s+DU\s+MAIRE\s+{RE_NO}"
    # en-tête Peyrolles-en-Provence
    + rf"|Arrêté\s+{RE_NO}"
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
)  # on laisse volontairement de côté la capture de "OBJET :\n\nARRÊTÉ DE PÉRIL\nORDINAIRE..." (Peyrolles) qu'il faudra traiter proprement par le layout 2 colonnes
P_NUM_ARR_FALLBACK = re.compile(RE_NUM_ARR_FALLBACK, re.MULTILINE | re.IGNORECASE)


def get_num(page_txt: str) -> bool:
    """Récupère le numéro de l'arrêté.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_num: str
        Numéro de l'arrêté si trouvé, None sinon.
    """
    if m_num := P_NUM_ARR.search(page_txt):
        return m_num.group("num_arr")
    elif m_num_fb := P_NUM_ARR_FALLBACK.search(page_txt):
        return m_num_fb.group("num_arr")
    else:
        return None


# nom de l'arrêté
RE_NOM_ARR = r"Objet:\s+(?P<nom_arr>[^\n]+)"
P_NOM_ARR = re.compile(RE_NOM_ARR, re.MULTILINE | re.IGNORECASE)


def get_nom(page_txt: str) -> bool:
    """Récupère le nom de l'arrêté.
    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    doc_nom: str
        Nom de l'arrêté si trouvé, None sinon.
    """
    # TODO nettoyer à gauche ("Dossier suivi par") et à droite: "\nNous,"
    if m_nom := P_NOM_ARR.search(page_txt):
        return m_nom.group("nom_arr")
    else:
        return None

"""Structure d'un arrêté de collectivité territoriale.

"""

# TODO garder la date de signature ou d'affichage ? (ex: Peyrolles)

import re

from src.domain_knowledge.codes_geo import RE_COMMUNES_AMP_ALLFORMS
from src.domain_knowledge.adresse import RE_COMMUNE
from src.utils.text_utils import RE_CARDINAUX, RE_NO, RE_ORDINAUX
from src.utils.str_date import RE_DATE, RE_MM


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
    # sans mention de la commune: "Le Maire,"  # Aubagne
    + r"(?:^Le\s+Maire\s*(?=,\s*$))"
    # avec mention de la commune
    + r"|(?:"
    + r"(?:"  # alternatives
    # le maire de X
    + rf"(?:^Le\s+{RE_MAIRE_COMM_DE})"
    # Nous, (...,)? maire de X
    + r"|(?:"
    + r"Nous[,.]\s+(?P<autorite_nom>[^,]+,\s+)?"  # pas de "^" pour augmenter la robustesse (eg. séparateur "-" en fin de ligne précédente interprété comme un tiret de coupure de mot)
    + RE_MAIRE_COMM_DE
    + r")"
    + r")"  # fin alternatives
    + rf"(?P<commune>{RE_COMMUNE})"  # nom commune
    + r")"  # fin avec mention de la commune
    + r")"  # fin named group "autorite"
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


# normalement "Arrête" ou "Arrêtons"
# cas particulier: Rognes: "ARRÊTÉ" dans cette position (negative lookahead pour éviter les conflits avec le repérage d'ARRÊTÉ <num_arr>)
RE_ARRETONS = (
    r"^\s*(?P<par_arrete>ARR[ÊÈE]{1,2}T(?:E|ONS|É"  # {1,2}: robustesse OCR
    + r"(?!"  # negative lookahead pour la seule alternative "arrêté":
    + r"(?:S)"  # pas "arrêtés" (ex: "arrêtés municipaux susvisés")
    + rf"|(?:\s+(?:{RE_NO}|\d|de|d['’]))"  #  pas "n°", ni chiffre, ni "de", ni "d'"
    + r")"
    + r")(?:\s*:)?)"
)
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
# "Atlicle": robustesse OCR...
RE_ARTICLE = (
    r"^\s*(?:ARTICLE|Atlicle|Aïticle)(?:[-]|\s+)"  # Atlicle, Aïtlicle, "-": robustesse OCR
    + r"(?:[1lI]\s*(?:er)?|\d+"  # 1, 1er et variantes robustes aux erreurs d'OCR
    + rf"|{RE_ORDINAUX}|{RE_CARDINAUX})"
)
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
    # "^Fait à <ville>, le"
    # Aix-en-Provence, Aubagne, Gémenos, La Ciotat, Roquevaire, Gémenos (fin)
    + r"^Fait\s+à\s+"
    + rf"(?P<arr_ville_signat>{RE_COMMUNES_AMP_ALLFORMS}|[^\s,]+)"  # fallback: [^\s,]+ ou RE_COMMUNES ?
    + r"(?:(?:\s*,)?\s+en\s+l['’]H[ôo]tel\s+de\s+Ville)?"
    + r"(?:\s*,)?\s+le"
    # "^<ville>, le"
    # Gardanne, Peyrolles-en-Provence
    + r"|^(?:Gardanne|Peyrolles-en-Provence),\s+le"
    # Marseille
    + r"|^Sign[ée]\s+le\s*:\s+"
    # Meyrargues
    + rf"|^ARR[ÊE]T[ÉE]\s+DU\s+MAIRE\s+{RE_NO}[^\n]+\nen\s+date\s+du\s+"
    # Peyrolles-en-Provence (en-tête), Martigues (fin)
    + rf"|^Arr[êe]t[ée]\s+{RE_NO}[\s\S]+?\s+du"
    # + r"|^Affiché[e]\s+le\s+:"  # TODO garder la date de signature ou d'affichage?
    + r")"
    + r"\s+(?P<arr_date>"
    + RE_DATE  # TODO str_date.RE_DATE_PREC ?
    + r")"
)
P_DATE_SIGNAT = re.compile(RE_DATE_SIGNAT, re.MULTILINE | re.IGNORECASE)


def get_date(page_txt: str) -> bool:
    """Récupère la date de l'arrêté.

    Actuellement, correspond à la date de signature, en fin d'arrêté.

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
    + rf"Extrait\s+du\s+registre\s+des\s+arrêtés\s+{RE_NO}\s*"
    # Gignac-la-Nerthe:
    + rf"|EXTRAIT\s+DU\s+REGISTRE\s+des\s+ARRETES\s+du\s+MAIRE\n{RE_NO}\s*"
    # La Ciotat
    + r"|^Réf\s*:\s*"
    # Gardanne:
    + r"|^Nos\s+Réf\s+:\s*"
    # Istres
    + rf"|^{RE_NO}(?=[^\n]+\s+Mati[èe]re\s+de\s+l['’]acte)\s*"  # N° ...\n\nMatière de l'acte 6.4 (positive lookahead)
    # Martigues:
    + rf"|^A\.M\s+{RE_NO}\s*"
    # Marseille (1)
    + rf"|^Décision\s+{RE_NO}\s*"
    # Meyrargues ;
    # (+ Septèmes, quand le layout sera bien lu)
    + rf"|^ARRÊTÉ\s+DU\s+MAIRE\s+{RE_NO}\s*"
    # en-tête Peyrolles-en-Provence
    + rf"|Arrêté\s+{RE_NO}\s*"
    + rf"|ARRETE\s+{RE_NO}\s*"
    # abrégé Peyrolles, ex: A 2020-02-117
    + r"|(?:A\s(?=\d{4}-"
    + RE_MM
    + r"-\d{3})\s*)"  # fin abrégé
    # Pennes-Mirabeau: pur lookahead (fonctionne car on ne prend que la 1re occurrence dans get_num_arr)
    + r"|(?=(?:AG\d{2}|URB\d{3})X\d{2}(?:\d{2})?\s*$)"
    # + rf"|^{RE_NO}"  # motif trop peu spécifique, capture par exemple un numéro de parcelle
    + r")"
    + r"(?P<num_arr>"
    # Pennes Mirabeau: URBdddXdd ou URBddXdddd
    + r"(?:(?:AG\d{2}|URB\d{3})X\d{2}(?:\d{2})?\s*$)"
    # expression générique
    + r"|(?:[^,;\n(]+)"
    + r")"
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
RE_NOM_ARR = r"Objet\s*:\s+(?P<nom_arr>[^\n]+(?:\n[^\n]+)*)"
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

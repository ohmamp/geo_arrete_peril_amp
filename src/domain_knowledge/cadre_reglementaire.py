"""Références au cadre réglementaire.
"""

import re

# arrêtés spécifiques:
# - entités du contexte réglementaire
# CGCT
RE_CGCT = r"""Code\s+Général\s+des\s+Collectivités\s+Territoriales"""
P_CGCT = re.compile(RE_CGCT, re.MULTILINE | re.IGNORECASE)
#
RE_CGCT_ART = r"""articles(?:\s)L[.\s]*2131-1,(?:\s)L[.\s]*2212-4(?:\s)et(?:\s)L[.\s]*2215-1"""  # TODO généraliser
# TODO L.2212-2 et L.2213-24 ?
P_CGCT_ART = re.compile(RE_CGCT_ART, re.MULTILINE | re.IGNORECASE)
# CCH
RE_CCH = r"""Code\s+de\s+la\s+Construction\s+et\s+de\s+l’Habitation"""
P_CCH = re.compile(RE_CCH, re.MULTILINE | re.IGNORECASE)
# L111-6-1: <https://www.legifrance.gouv.fr/codes/id/LEGIARTI000028808282/2014-03-27> (en vigueur jusque 2021-07-01)
RE_CCH_L111 = r"""L[.\s]*111(?:-[\d]){0,2}"""
P_CCH_L111 = re.compile(RE_CCH_L111, re.MULTILINE | re.IGNORECASE)
# L511-1 à L511-22 du CCH
RE_CCH_L511 = r"""L[.\s]*511-1(?:\s)(?:(?:à(?:\s)?L[.\s]*511-[\d]{1,2})|(?:et\s+suivants))"""  # TODO trop général ?
P_CCH_L511 = re.compile(RE_CCH_L511, re.MULTILINE | re.IGNORECASE)
# 521-1, 521-2, 521-3-[1-4], 521-4
# 521-3: relogement
# 521-4: sanctions
RE_CCH_L521 = (
    r"""L[.\s]*521-1(?:\s)à(?:\s)?L[.\s]*521-[\d](?:-[\d])?"""  # TODO affiner ?
)
P_CCH_L521 = re.compile(RE_CCH_L521, re.MULTILINE | re.IGNORECASE)
RE_CCH_L541 = r"""L[.\s]*541-2"""
P_CCH_L541 = re.compile(RE_CCH_L541, re.MULTILINE | re.IGNORECASE)
# R511-1 à R511-13 du CCH
RE_CCH_R511 = (
    r"""R[.\s]*511-1(?:\s)à(?:\s)?R[.\s]*511-[\d]{1,2}"""  # TODO trop général ?
)
P_CCH_R511 = re.compile(RE_CCH_R511, re.MULTILINE | re.IGNORECASE)
# CC
RE_CC = r"""Code\s+Civil"""
P_CC = re.compile(RE_CC, re.MULTILINE | re.IGNORECASE)
#
RE_CC_ART = r"""articles(?:\s)2384-1,(?:\s)2384-3"""  # TODO généraliser
P_CC_ART = re.compile(RE_CC_ART, re.MULTILINE | re.IGNORECASE)


# association entre un motif compilé et un type d'empan
REG_TYP = [
    (P_CGCT, "cgct"),
    (P_CGCT_ART, "cgct_art"),
    (P_CCH, "cch"),
    (P_CCH_L111, "cch_l111"),
    (P_CCH_L511, "cch_l511"),
    (P_CCH_L521, "cch_l521"),
    (P_CCH_L541, "cch_l541"),
    (P_CCH_R511, "cch_r511"),
    (P_CC, "cc"),
    (P_CC_ART, "cc_art"),
]


def parse_refs_reglement(txt_body: str, span_beg: int, span_end: int) -> list:
    """Repère dans un texte des références au cadre réglementaire.

    Parameters
    ----------
    txt_body: string
        Corps de texte à analyser
    main_beg: int
        Début de l'empan à analyser.
    main_end: int
        Fin de l'empan à analyser.

    Returns
    -------
    content: list
        Liste d'empans de références
    """
    content = []
    for p_reg, typ_reg in REG_TYP:
        if matches := p_reg.finditer(txt_body, span_beg, span_end):
            for match in matches:
                content.append(
                    {
                        "span_beg": match.start(),
                        "span_end": match.end(),
                        "span_txt": match.group(0),
                        "span_typ": typ_reg,
                    }
                )
    return content


def contains_cgct(page_txt: str) -> bool:
    """Détecte si une page contient une référence au Code Général des Collectivités Territoriales.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence au Code Général des Collectivités Territoriales.
    """
    return P_CGCT.search(page_txt) is not None


def contains_cgct_art(page_txt: str) -> bool:
    """Détecte si une page contient une référence à des articles du Code Général des Collectivités Territoriales.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à des articles du Code Général des Collectivités Territoriales.
    """
    return P_CGCT_ART.search(page_txt) is not None


def contains_cch(page_txt: str) -> bool:
    """Détecte si une page contient une référence au Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence au Code de la Construction et de l'Habitation.
    """
    return P_CCH.search(page_txt) is not None


def contains_cch_L111(page_txt: str) -> bool:
    """Détecte si une page contient une référence à l'article L111 du Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à l'article L111 du Code de la Construction et de l'Habitation.
    """
    return P_CCH_L111.search(page_txt) is not None


def contains_cch_L511(page_txt: str) -> bool:
    """Détecte si une page contient une référence à l'article L511 du Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à l'article L511 du Code de la Construction et de l'Habitation.
    """
    return P_CCH_L511.search(page_txt) is not None


def contains_cch_L521(page_txt: str) -> bool:
    """Détecte si une page contient une référence à l'article L521 du Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à l'article L521 du Code de la Construction et de l'Habitation.
    """
    return P_CCH_L521.search(page_txt) is not None


def contains_cch_L541(page_txt: str) -> bool:
    """Détecte si une page contient une référence à l'article L541 du Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à l'article L541 du Code de la Construction et de l'Habitation.
    """
    return P_CCH_L541.search(page_txt) is not None


def contains_cch_R511(page_txt: str) -> bool:
    """Détecte si une page contient une référence à l'article R511 du Code de la Construction et de l'Habitation.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à l'article R511 du Code de la Construction et de l'Habitation.
    """
    return P_CCH_R511.search(page_txt) is not None


def contains_cc(page_txt: str) -> bool:
    """Détecte si une page contient une référence au Code Civil.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence au Code Civil.
    """
    return P_CC.search(page_txt) is not None


def contains_cc_art(page_txt: str) -> bool:
    """Détecte si une page contient une référence à des articles du Code Civil.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document
    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence à des articles du Code Civil.
    """
    return P_CC_ART.search(page_txt) is not None

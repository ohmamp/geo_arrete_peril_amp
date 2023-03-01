"""Extrait la structure des documents.

Découpe chaque arrêté en zones:
* préambule (?),
* VUs,
* CONSIDERANTs,
* ARTICLES,
* postambule (?)
"""

# TODO repérer les rapports d'expertise (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 3 à 10)
# TODO repérer les citations des textes réglementaires en annexe (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 11 à 15)
# TODO mieux traiter les pages d'AR @ctes (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 16)

import argparse
from datetime import datetime
import logging
from pathlib import Path
import re
from typing import NamedTuple

import pandas as pd

from actes import P_STAMP, P_ACCUSE
from cadastre import M_PARCELLE
from cadre_reglementaire import (
    P_CGCT,
    P_CGCT_ART,
    P_CCH,
    P_CCH_L111,
    P_CCH_L511,
    P_CCH_L521,
    P_CCH_L541,
    P_CCH_R511,
    P_CC,
    P_CC_ART,
)

from typologie_securite import (
    #   * classification + procédure d'urgence
    M_CLASS_PS_PO,
    M_CLASS_PS_PO_MOD,
    M_CLASS_MS,
    M_CLASS_MS_MOD,
    M_CLASS_PGI,
    M_CLASS_PGI_MOD,
    M_CLASS_MSU,
    M_CLASS_MSU_MOD,
    M_CLASS_ML,
    M_CLASS_ML_PA,
    M_CLASS_DE,
    M_CLASS_ABRO_DE,
    M_CLASS_INS,
    M_CLASS_INT,
    M_CLASS_ABRO_INT,
    #   * interdiction d'habiter
    M_INTERDICT_HABIT,
    #   * démolition et déconstruction
    M_DEMOL_DECONST,
    #   * équipements communs
    M_EQUIPEMENTS_COMMUNS,
)

from filter_docs import DTYPE_META_NTXT_FILT, DTYPE_NTXT_PAGES_FILT
from text_structure import (
    # tous arrêtés
    P_ARR_NUM,  # numéro/identifiant de l'arrêté
    P_ARR_NUM_FALLBACK,  # motif plus générique pour num arrêté (repli)
    P_ARR_OBJET,  # nom/objet de l'arrêté
    P_VU,
    P_CONSIDERANT,
    P_ARRETE,
    P_ARTICLE,
    # spécifiques arrêtés
    # - données
    RE_COMMUNE,
    P_MAIRE_COMMUNE,
    M_ADR_DOC,
    RE_ADRESSE,  # pour le nettoyage de l'adresse récupérée
    M_PROPRI,  # fallback propriétaire (WIP)
    P_PROPRIO_MONO,  # mono-propriétaire (WIP)
    M_SYNDIC,
    P_GESTIO,
    P_DATE_SIGNAT,
)


# dtypes des champs extraits
DTYPE_PARSE = {
    # @ctes
    "has_stamp": "boolean",
    "is_accusedereception_page": "boolean",
    # tous arrêtés
    "commune_maire": "string",
    "has_vu": "boolean",
    "has_considerant": "boolean",
    "has_arrete": "boolean",
    "has_article": "boolean",
    # arrêtés spécifiques
    # - réglementaires
    "has_cgct": "boolean",
    "has_cgct_art": "boolean",
    "has_cch": "boolean",
    "has_cch_L111": "boolean",
    "has_cch_L511": "boolean",
    "has_cch_L521": "boolean",
    "has_cch_L541": "boolean",
    "has_cch_R511": "boolean",
    "has_cc": "boolean",
    "has_cc_art": "boolean",
    # - données
    #   * parcelle
    "parcelle": "string",
    #   * adresse
    "adresse": "string",
    #   * notifiés
    "proprietaire": "string",
    "syndic": "string",
    "gestio": "string",
    #   * arrêté
    "date": "string",
    "arr_num": "string",
    "arr_nom": "string",
    # type d'arrêté
    "arr_classification": "string",
    "arr_proc_urgence": "string",
    "arr_demolition": "string",
    "arr_interdiction": "string",
    "arr_equipcomm": "string",
}

# dtype du fichier de sortie
DTYPE_META_NTXT_PROC = (
    DTYPE_META_NTXT_FILT | {"pagenum": DTYPE_NTXT_PAGES_FILT["pagenum"]} | DTYPE_PARSE
)


# marqueurs de télétransmission à @ctes
# TODO test: "2 rue Gasquet Trets 01.02.21.txt": les 3 pages
def is_stamped_page(page_txt: str) -> bool:
    """Détecte si une page contient un tampon (encadré) de transmission @actes.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    has_stamp: bool
        True si le texte contient un tampon de transmission
    """
    return P_STAMP.search(page_txt) is not None


# TODO test: 12 rue Parmentier Gardanne - MS.txt : dernière page (4)
def is_accusedereception_page(page_txt: str) -> bool:
    """Détecte si une page contient un tampon (encadré) de transmission @actes.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    has_stamp: bool
        True si le texte contient un tampon de transmission
    """
    return P_ACCUSE.search(page_txt) is not None


# structure des arrêtés

# - extraction de la commune prenant l'arrêté, à partir de la mention du maire

# il peut être nécessaire de nettoyer la zone extraite pour enlever le contexte droit (reconnaissance trop étendue)
RE_MAIRE_COMMUNE_CLEANUP = (
    rf"""(?P<commune>{RE_COMMUNE})"""
    + r"""\s+"""
    + r"""(?:(CB|JFF) Accusé de réception)"""
)
M_MAIRE_COMMUNE_CLEANUP = re.compile(
    RE_MAIRE_COMMUNE_CLEANUP, re.MULTILINE | re.IGNORECASE
)


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
    return P_ARRETE.search(page_txt) is not None


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


# éléments spécifiques à certains types d'arrêtés
# - réglementaires
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


# - données
def get_parcelle(page_txt: str) -> bool:
    """Récupère la ou les références de parcelles cadastrales.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    id_parcelles: str
        Référence d'une ou plusieurs parcelles cadastrales si détectées dans le texte,
        None sinon.
    """
    m_parc = M_PARCELLE.search(page_txt)
    return m_parc.group("cadastre_id") if m_parc is not None else None


# nettoyage de l'adresse récupérée: on supprime le contexte droit
RE_ADR_CLEANUP = (
    # rf"""(?P<adresse>{RE_ADRESSE})"""
    r"""(?:\s*[-–,])?\s+"""
    + r"""(?:"""
    + r"""parcelle|section|référence|(?:cadastr[ée])"""
    + r"""|copropriété"""
    + r"""|susceptible|concernant"""
    + r"""|(?:est\s+à\s+l['’]état)|(?:jusqu'à\s+nouvel\s+ordre)"""
    + r"""|(?:est\s+strictement\s+interdit)|(?:et\s+[àà]\s+en\s+interdire)"""
    + r"""|ainsi|situé"""  # Marseille
    + r"""|(?:pour$)"""
    + r"""|(?:^Nous,\s+Maire)|(?:^vu)|(?:^consid[ée]rant)|(?:^article)"""
    + r""")"""
    + r"""[\s\S]*"""
)
# M_ADR_CLEANUP = re.compile(RE_ADR_CLEANUP, re.MULTILINE | re.IGNORECASE)


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
        # nettoyage de la valeur récupérée
        adr = re.sub(RE_ADR_CLEANUP, "", adr, flags=(re.MULTILINE | re.IGNORECASE))
        return adr
    else:
        return None


def get_proprietaire(page_txt: str) -> bool:
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
        return match.group("propri")
    # puis sinon les multi-propriétaires (TODO proprement)
    elif match := M_PROPRI.search(page_txt):
        return match.group("propri")
    else:
        return None


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
    m_synd = M_SYNDIC.search(page_txt)
    return m_synd.group("syndic") if m_synd is not None else None


def get_gestio(page_txt: str) -> str:
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
    match = P_GESTIO.search(page_txt)
    return match.group("gestio") if match is not None else None


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
    if m_num := P_ARR_NUM.search(page_txt):
        return m_num.group("arr_num")
    elif m_num_fb := P_ARR_NUM_FALLBACK.search(page_txt):
        return m_num_fb.group("arr_num")
    else:
        return None


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
    if m_nom := P_ARR_OBJET.search(page_txt):
        return m_nom.group("arr_nom")
    else:
        return None


def get_classification(page_txt: str) -> bool:
    """Récupère la classification de l'arrêté.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_class: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    if (
        M_CLASS_PS_PO_MOD.search(page_txt)
        or M_CLASS_MS_MOD.search(page_txt)
        or M_CLASS_PGI_MOD.search(page_txt)
        or M_CLASS_MSU_MOD.search(page_txt)
        or M_CLASS_ML_PA.search(page_txt)
    ):
        return "Arrêté de mise en sécurité modificatif"
    elif (
        M_CLASS_PS_PO.search(page_txt)
        or M_CLASS_MS.search(page_txt)
        or M_CLASS_PGI.search(page_txt)
        or M_CLASS_MSU.search(page_txt)
        or M_CLASS_DE.search(page_txt)
        or M_CLASS_INS.search(page_txt)
        or M_CLASS_INT.search(page_txt)
    ):
        return "Arrêté de mise en sécurité"
    elif (
        M_CLASS_ML.search(page_txt)
        or M_CLASS_ABRO_DE.search(page_txt)
        or M_CLASS_ABRO_INT.search(page_txt)
    ):
        return "Arrêté de mainlevée"
    else:
        return None


def get_urgence(page_txt: str) -> bool:
    """Récupère le caractère d'urgence de l'arrêté.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_class: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    if (
        M_CLASS_PS_PO.search(page_txt)
        or M_CLASS_PS_PO_MOD.search(page_txt)
        or M_CLASS_MS.search(page_txt)
        or M_CLASS_MS_MOD.search(page_txt)
    ):
        return "non"
    elif (
        M_CLASS_PGI.search(page_txt)
        or M_CLASS_PGI_MOD.search(page_txt)
        or M_CLASS_MSU.search(page_txt)
        or M_CLASS_MSU_MOD.search(page_txt)
    ):
        return "oui"
    elif (
        M_CLASS_ML_PA.search(page_txt)
        or M_CLASS_DE.search(page_txt)
        or M_CLASS_ABRO_DE.search(page_txt)
        or M_CLASS_INS.search(page_txt)
        or M_CLASS_INT.search(page_txt)
    ):
        # FIXME ajouter la prise en compte des articles cités pour déterminer l'urgence
        return "oui ou non"
    elif M_CLASS_ML.search(page_txt) or M_CLASS_ABRO_INT.search(page_txt):
        return "/"
    else:
        return None


def get_interdiction_habiter(page_txt: str) -> bool:
    """Détermine si l'arrêté porte interdiction d'habiter et d'occuper.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_equip_comm: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif M_INTERDICT_HABIT.search(page_txt):
        return "oui"
    else:
        return "non"


def get_demol_deconst(page_txt: str) -> bool:
    """Détermine si l'arrêté porte une démolition ou déconstruction.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_demol_deconst: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif M_DEMOL_DECONST.search(page_txt):
        return "oui"
    else:
        return "non"


def get_equipements_communs(page_txt: str) -> bool:
    """Détermine si l'arrêté porte sur la sécurité des équipements communs.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    doc_equip_comm: str
        Classification de l'arrêté si trouvé, None sinon.
    """
    if page_txt is None:
        return None
    elif M_EQUIPEMENTS_COMMUNS.search(page_txt):
        return "oui"
    else:
        return "non"


def spot_text_structure(
    df_row: NamedTuple,
) -> pd.DataFrame:
    """Détecte la présence d'éléments de structure dans une page d'arrêté.

    Détecte la présence de tampons, pages d'accusé de réception,
    VU, CONSIDERANT, ARTICLE.

    Parameters
    ----------
    df_row: NamedTuple
        Page de document

    Returns
    -------
    rec_struct: dict
        Dictionnaire de valeurs booléennes ou nulles, selon que les éléments de structure ont été détectés.
        Les clés et les types de valeurs sont spécifiés dans `DTYPE_PARSE`.
        Si df_row ne contient pas de texte, toutes les valeurs de sortie sont None.
    """
    if pd.notna(df_row.pagetxt) and (
        not df_row.exclude
    ):  # WIP " and (not df_row.exclude)"
        rec_struct = {
            # @ctes
            "has_stamp": is_stamped_page(df_row.pagetxt),
            "is_accusedereception_page": is_accusedereception_page(df_row.pagetxt),
            # tous arrêtés
            "commune_maire": get_commune_maire(df_row.pagetxt),
            "has_vu": contains_vu(df_row.pagetxt),
            "has_considerant": contains_considerant(df_row.pagetxt),
            "has_arrete": contains_arrete(df_row.pagetxt),
            "has_article": contains_article(df_row.pagetxt),
            # arrêtés spécifiques
            # - réglementaires
            "has_cgct": contains_cgct(df_row.pagetxt),
            "has_cgct_art": contains_cgct_art(df_row.pagetxt),
            "has_cch": contains_cch(df_row.pagetxt),
            "has_cch_L111": contains_cch_L111(df_row.pagetxt),
            "has_cch_L511": contains_cch_L511(df_row.pagetxt),
            "has_cch_L521": contains_cch_L521(df_row.pagetxt),
            "has_cch_L541": contains_cch_L541(df_row.pagetxt),
            "has_cch_R511": contains_cch_R511(df_row.pagetxt),
            "has_cc": contains_cc(df_row.pagetxt),
            "has_cc_art": contains_cc_art(df_row.pagetxt),
            # - données
            "adresse": get_adr_doc(df_row.pagetxt),
            "parcelle": get_parcelle(df_row.pagetxt),
            "proprietaire": get_proprietaire(df_row.pagetxt),  # WIP
            "syndic": get_syndic(df_row.pagetxt),
            "gestio": get_gestio(df_row.pagetxt),
            "date": get_date(df_row.pagetxt),
            #   * arrêté
            "arr_num": get_num(df_row.pagetxt),
            "arr_nom": get_nom(df_row.pagetxt),
            "arr_classification": get_classification(df_row.pagetxt),
            "arr_proc_urgence": get_urgence(df_row.pagetxt),
            "arr_demolition": get_demol_deconst(df_row.pagetxt),
            "arr_interdiction": get_interdiction_habiter(df_row.pagetxt),
            "arr_equipcomm": get_equipements_communs(df_row.pagetxt),
        }
    else:
        # tous les champs sont vides ("None")
        rec_struct = {x: None for x in DTYPE_PARSE}
    return rec_struct


def process_files(
    df_meta: pd.DataFrame,
    df_txts: pd.DataFrame,
) -> pd.DataFrame:
    """Traiter un ensemble d'arrêtés: repérer des éléments de structure des textes.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de métadonnées des fichiers à traiter.
    df_txts: pd.DataFrame
        Liste de pages de documents à traiter.

    Returns
    -------
    df_proc: pd.DataFrame
        Liste de métadonnées des pages traitées, avec indications des éléments de
        structure détectés.
    """
    indics_struct = []
    for df_row in df_txts.itertuples():
        # pour chaque page de document, repérer des indications de structure
        rec_struct = spot_text_structure(df_row)
        indics_struct.append(
            {
                "filename": df_row.filename,
                "fullpath": df_row.fullpath,
                "pagenum": df_row.pagenum,
            }
            | rec_struct  # python >= 3.9 (dict union)
        )
    df_indics = pd.DataFrame.from_records(indics_struct)
    df_proc = pd.merge(df_meta, df_indics, on=["filename", "fullpath"])
    df_proc = df_proc.astype(dtype=DTYPE_META_NTXT_PROC)
    return df_proc


# liste de documents pour lesquels certains champs sont nécessairement vides, car la donnée est absente du document
# TODO transformer en script
# - parcelle
PARCELLE_ABS = [
    "2 rue Lisse Bellegarde - IO 06.03.20.PDF",  # Aix-en-Provence
    "MS 673 av Jean Monnet à Vitrolles.pdf",  # Vitrolles
]

if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/parse_native_pages_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file_meta",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées des fichiers PDF",
    )
    parser.add_argument(
        "in_file_pages",
        help="Chemin vers le fichier CSV en entrée contenant les pages de texte",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées des fichiers PDF enrichies, par page",
    )
    group = parser.add_mutually_exclusive_group()
    # par défaut, le fichier out_file ne doit pas exister, sinon deux options mutuellement exclusives:
    # "redo" (écrase le fichier existant) et "append" (étend le fichier existant)
    group.add_argument(
        "--redo",
        action="store_true",
        help="Ré-exécuter le traitement d'un lot, et écraser le fichier de sortie",
    )
    group.add_argument(
        "--append",
        action="store_true",
        help="Ajoute les pages annotées au fichier out_file s'il existe",
    )
    args = parser.parse_args()

    # entrée: CSV de métadonnées
    in_file_meta = Path(args.in_file_meta).resolve()
    if not in_file_meta.is_file():
        raise ValueError(f"Le fichier en entrée {in_file_meta} n'existe pas.")

    # entrée: CSV de pages de texte
    in_file_pages = Path(args.in_file_pages).resolve()
    if not in_file_pages.is_file():
        raise ValueError(f"Le fichier en entrée {in_file_pages} n'existe pas.")

    # sortie: CSV de pages de texte annotées
    # on crée le dossier parent (récursivement) si besoin
    out_file = Path(args.out_file).resolve()
    if out_file.is_file():
        if not args.redo and not args.append:
            # erreur si le fichier CSV existe déjà mais ni redo, ni append
            raise ValueError(
                f"Le fichier de sortie {out_file} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
            )
    else:
        # si out_file n'existe pas, créer son dossier parent si besoin
        out_dir = out_file.parent
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(exist_ok=True)

    # ouvrir le fichier de métadonnées en entrée
    logging.info(f"Ouverture du fichier CSV de métadonnées {in_file_meta}")
    df_meta = pd.read_csv(in_file_meta, dtype=DTYPE_META_NTXT_FILT)
    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV de pages de texte {in_file_pages}")
    df_txts = pd.read_csv(in_file_pages, dtype=DTYPE_NTXT_PAGES_FILT)
    # traiter les documents (découpés en pages de texte)
    df_tmod = process_files(df_meta, df_txts)

    # optionnel: afficher des statistiques
    if True:  # TODO ajouter une option si utilité confirmée
        new_cols = [
            # @ctes
            "has_stamp",
            "is_accusedereception_page",
            # structure générique des arrêtés
            "commune_maire",
            # "has_vu",
            # "has_considerant",
            # "has_arrete",
            # "has_article",
            # données à extraire
            "parcelle",
            # "adresse",
            # "syndic",
        ]
        print(
            df_tmod.query("pagenum == 1")
            .dropna(axis=0, how="all", subset=["has_stamp"])[new_cols]
            .groupby("commune_maire")
            .value_counts(dropna=False)
        )
        # TODO écrire des "expectations": cohérence entre colonnes sur le même document,
        # AR sur la dernière page (sans doute faux dans certains cas, eg. annexes ou rapport d'expertise)
        # page has_article=TRUE >= page has_vu, has_considerant
        # pour tout document ayant au moins une page où has_article=TRUE, alors il existe une page has_vu=TRUE
        # (et il existe une page où has_considerant=TRUE ?)

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT_PROC)
        df_proc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_tmod
    df_proc.to_csv(out_file, index=False)

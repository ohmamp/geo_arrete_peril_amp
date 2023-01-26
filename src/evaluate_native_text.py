"""Extrait la structure des documents.

Découpe chaque arrêté en zones:
* préambule (?),
* VUs,
* CONSIDERANTs,
* ARTICLES,
* postambule (?)
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from text_structure import (
    # @ctes
    M_STAMP,
    M_ACCUSE,
    # tous arrêtés
    M_VU,
    M_CONSIDERANT,
    M_ARRETE,
    M_ARTICLE,
    # spécifiques arrêtés
    # - règlementaires
    M_CGCT,
    M_CGCT_ART,
    M_CCH,
    M_CCH_L511,
    M_CCH_L521,
    M_CCH_L541,
    M_CCH_R511,
    M_CC,
    M_CC_ART,
    # - données
    M_PARCELLE,
    M_SYNDIC,
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
    return M_STAMP.search(page_txt) is not None


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
    return M_ACCUSE.search(page_txt) is not None


# structure des arrêtés
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
    return M_VU.search(page_txt) is not None


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
    return M_CONSIDERANT.search(page_txt) is not None


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
    return M_ARRETE.search(page_txt) is not None


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
    return M_ARTICLE.search(page_txt) is not None


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
    return M_CGCT.search(page_txt) is not None


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
    return M_CGCT_ART.search(page_txt) is not None


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
    return M_CCH.search(page_txt) is not None


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
    return M_CCH_L511.search(page_txt) is not None


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
    return M_CCH_L521.search(page_txt) is not None


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
    return M_CCH_L541.search(page_txt) is not None


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
    return M_CCH_R511.search(page_txt) is not None


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
    return M_CC.search(page_txt) is not None


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
    return M_CC_ART.search(page_txt) is not None


# - données
def contains_parcelle(page_txt: str) -> bool:
    """Détecte si une page contient une référence de parcelle cadastrale.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    has_stamp: bool
        True si le texte contient une référence de parcelle cadastrale.
    """
    return M_PARCELLE.search(page_txt) is not None


def contains_syndic(page_txt: str) -> bool:
    """Détecte si une page contient un nom de syndic.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    has_stamp: bool
        True si le texte contient un nom de syndic.
    """
    return M_SYNDIC.search(page_txt) is not None


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
    """
    if pd.notna(df_row.pagetxt):
        rec_struct = {
            # @ctes
            "has_stamp": is_stamped_page(df_row.pagetxt),
            "is_accusedereception_page": is_accusedereception_page(df_row.pagetxt),
            # tous arrêtés
            "has_vu": contains_vu(df_row.pagetxt),
            "has_considerant": contains_considerant(df_row.pagetxt),
            "has_arrete": contains_arrete(df_row.pagetxt),
            "has_article": contains_article(df_row.pagetxt),
            # arrêtés spécifiques
            # - réglementaires
            "has_cgct": contains_cgct(df_row.pagetxt),
            "has_cgct_art": contains_cgct_art(df_row.pagetxt),
            "has_cch": contains_cch(df_row.pagetxt),
            "has_cch_L511": contains_cch_L511(df_row.pagetxt),
            "has_cch_L521": contains_cch_L521(df_row.pagetxt),
            "has_cch_L541": contains_cch_L541(df_row.pagetxt),
            "has_cch_R511": contains_cch_R511(df_row.pagetxt),
            "has_cc": contains_cc(df_row.pagetxt),
            "has_cc_art": contains_cc_art(df_row.pagetxt),
            # - données
            "has_parcelle": contains_parcelle(df_row.pagetxt),
            "has_syndic": contains_syndic(df_row.pagetxt),
        }
    else:
        rec_struct = {
            # @ctes
            "has_stamp": None,
            "is_accusedereception_page": None,
            # tous arrêtés
            "has_vu": None,
            "has_considerant": None,
            "has_arrete": None,
            "has_article": None,
            # arrêtés spécifiques
            # - réglementaires
            "has_cgct": None,
            "has_cgct_art": None,
            "has_cch": None,
            "has_cch_L511": None,
            "has_cch_L521": None,
            "has_cch_L541": None,
            "has_cch_R511": None,
            "has_cc": None,
            "has_cc_art": None,
            # - données
            "has_parcelle": None,
            "has_syndic": None,
        }
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
    return df_proc


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/parse_text_structure_{datetime.now().isoformat()}.log",
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
    df_meta = pd.read_csv(in_file_meta)
    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV de pages de texte {in_file_pages}")
    df_txts = pd.read_csv(in_file_pages, dtype={"pagetxt": "string"})
    # traiter les documents (découpés en pages de texte)
    df_tmod = process_files(df_meta, df_txts)

    # optionnel: afficher des statistiques
    if True:  # TODO ajouter une option si utilité confirmée
        new_cols = [
            "has_stamp",
            "is_accusedereception_page",
            "has_vu",
            "has_considerant",
            "has_article",
        ]
        print(df_tmod[new_cols].value_counts())
        # TODO écrire des expectations: cohérence entre colonnes sur le même document,
        # AR sur la dernière page (sans doute faux dans certains cas, eg. annexes ou rapport d'expertise)
        # page has_article=TRUE >= page has_vu, has_considerant
        # pour tout document ayant au moins une page où has_article=TRUE, alors il existe une page has_vu=TRUE
        # (et il existe une page où has_considerant=TRUE ?)

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file)
        df_proc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_tmod
    df_proc.to_csv(out_file, index=False)

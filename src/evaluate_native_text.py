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
import re
from typing import NamedTuple

import pandas as pd

from text_structure import M_STAMP, M_ACCUSE, M_VU, M_CONSIDERANT


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
            "has_stamp": is_stamped_page(df_row.pagetxt),
            "is_accusedereception_page": is_accusedereception_page(df_row.pagetxt),
            "has_vu": contains_vu(df_row.pagetxt),
            "has_considerant": contains_considerant(df_row.pagetxt),
        }
    else:
        rec_struct = {
            "has_stamp": None,
            "is_accusedereception_page": None,
            "has_vu": None,
            "has_considerant": None,
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
            {"filename": df_row.filename, "fullpath": df_row.fullpath}
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
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file)
        df_proc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_tmod
    df_proc.to_csv(out_file, index=False)

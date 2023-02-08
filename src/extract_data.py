"""Extraire les données des documents.

Les données sont extraites des empans de texte repérés au préalable,
et normalisées.
Lorsque plusieurs empans de texte sont susceptibles de renseigner sur
la même donnée, les différentes valeurs extraites sont accumulées pour
certains champs (ex: propriétaires) ou comparées et sélectionnées pour
d'autres champs (ex: commune).
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
import re

import pandas as pd

from aggregate_pages import DTYPE_META_NTXT_DOC


DTYPE_DATA = {
    "idu": "string",  # identifiant unique
    # arrêté
    "arr_date": "string",
    "arr_num": "string",
    "arr_nom": "string",
    "arr_classification": "string",
    "arr_proc_urgence": "string",
    "arr_demolition": "string",
    "arr_interdiction": "string",
    "arr_equipcomm": "string",
    "arr_nom_pdf": "string",  # = filename
    "arr_url": "string",  # TODO URL serveur
    # adresse
    "adr_ad_brute": "string",  # adresse brute
    "adr_adresse": "string",  # adresse normalisée
    "adr_num": "string",  # numéro de la voie
    "adr_ind": "string",  # indice de répétition
    "adr_voie": "string",  # nom de la voie
    "adr_compl": "string",  # complément d'adresse
    "adr_cpostal": "string",  # code postal
    "adr_ville": "string",  # ville
    "adr_codeinsee": "string",  # code insee (5 chars)
    # parcelle
    "par_ref_cad": "string",  # référence cadastrale
    # notifié
    "not_nom_propri": "string",  # nom des propriétaries
    "not_ide_syndic": "string",  # identification du syndic
    "not_nom_syndic": "string",  # nom du syndic
    "not_ide_gestio": "string",  # identification du gestionnaire
}


def normalize_string(raw_str: str) -> str:
    """Normaliser une chaîne de caractères.

    Remplacer les séquences d'espaces par une unique espace.

    Parameters
    ----------
    raw_str: str
        Chaîne de caractères à normaliser

    Returns
    -------
    nor_str: str
        Chaîne de caractères normalisée
    """
    nor_str = re.sub(r"\s+", " ", raw_str, flags=re.MULTILINE)
    return nor_str


def create_docs_dataframe(
    df_agg: pd.DataFrame,
) -> pd.DataFrame:
    """Extraire les informations des documents dans un DataFrame.

    Normaliser et extraire les données de chaque document en une entrée par document.

    Parameters
    ----------
    df_pages: pd.DataFrame
        Métadonnées et données extraites des pages.

    Returns
    -------
    df_docs: pd.DataFrame
        Tableau contenant les données normalisées extraites des documents.
    """
    doc_rows = []
    for i, df_row in enumerate(df_agg.itertuples()):
        doc_data = {
            "idu": f"id_{i:04}",  # FIXME identifiant unique
            # arrêté
            "arr_date": (
                normalize_string(getattr(df_row, "arr_date"))
                if pd.notna(getattr(df_row, "arr_date"))
                else None
            ),
            "arr_num": (
                normalize_string(getattr(df_row, "arr_num"))
                if pd.notna(getattr(df_row, "arr_num"))
                else None
            ),
            "arr_nom": (
                normalize_string(getattr(df_row, "arr_nom"))
                if pd.notna(getattr(df_row, "arr_nom"))
                else None
            ),
            "arr_classification": (
                normalize_string(getattr(df_row, "arr_classification"))
                if pd.notna(getattr(df_row, "arr_classification"))
                else None
            ),
            "arr_proc_urgence": (
                normalize_string(getattr(df_row, "arr_proc_urgence"))
                if pd.notna(getattr(df_row, "arr_proc_urgence"))
                else None
            ),
            "arr_demolition": "TODO_demol",  # RESUME HERE
            "arr_interdiction": "TODO_inter",  # RESUME HERE
            "arr_equipcomm": "TODO_equip",  # RESUME HERE
            # (métadonnées du doc)
            "arr_nom_pdf": getattr(df_row, "filename"),
            "arr_url": getattr(df_row, "fullpath"),  # TODO URL localhost?
            # adresse
            "adr_ad_brute": (
                normalize_string(getattr(df_row, "adresse_brute"))
                if pd.notna(getattr(df_row, "adresse_brute"))
                else None
            ),  # adresse brute
            "adr_adresse": "TODO_adresse",  # adresse normalisée
            "adr_num": "TODO_adr_num",  # numéro de la voie
            "adr_ind": "TODO_adr_ind",  # indice de répétition
            "adr_voie": "TODO_adr_voie",  # nom de la voie
            "adr_compl": "TODO_adr_compl",  # complément d'adresse
            "adr_cpostal": "TODO_adr_cpostal",  # code postal
            "adr_ville": (
                normalize_string(getattr(df_row, "commune_maire"))
                if pd.notna(getattr(df_row, "commune_maire"))
                else None
            ),  # ville
            "adr_codeinsee": "TODO_adr_codeinsee",  # code insee (5 chars)
            # parcelle
            "par_ref_cad": (
                normalize_string(getattr(df_row, "parcelle"))
                if pd.notna(getattr(df_row, "parcelle"))
                else None
            ),  # référence cadastrale
            # notifié
            "not_nom_propri": "TODO_proprietaire",  # nom des propriétaries
            "not_ide_syndic": (
                normalize_string(getattr(df_row, "syndic"))
                if pd.notna(getattr(df_row, "syndic"))
                else None
            ),  # identification du syndic
            "not_nom_syndic": "TODO_syndic",  # nom du syndic
            "not_ide_gestio": "TODO_gestio",  # identification du gestionnaire
        }
        doc_rows.append(doc_data)
    df_docs = pd.DataFrame.from_records(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_DATA)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/extract_data_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées et données extraites des documents",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées et données normalisées extraites des documents",
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

    # entrée: CSV de pages de texte
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de documents
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

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_meta = pd.read_csv(in_file, dtype=DTYPE_META_NTXT_DOC)
    # traiter les documents (découpés en pages de texte)
    df_txts = create_docs_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file, dtype=DTYPE_DATA)
        df_txts = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

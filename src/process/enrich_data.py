"""Enrichit les données avec des données supplémentaires.

Ajoute le code INSEE de la commune.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd

from src.process.extract_data import DTYPE_DATA
from src.domain_knowledge.cadastre import generate_refcadastrale_norm
from src.domain_knowledge.code_insee import get_codeinsee


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
        # ajoute le code INSEE, à partir de la commune et du code postal
        df_row_enr = df_row._replace(
            adr_codeinsee=get_codeinsee(df_row.adr_ville, df_row.adr_cpostal)
        )
        # remplace la référence cadastrale par sa version normalisée
        df_row_enr = df_row._replace(
            par_ref_cad=generate_refcadastrale_norm(
                df_row.adr_codeinsee,
                df_row.par_ref_cad,
                df_row.arr_pdf,
                df_row.adr_cpostal,
            )
        )
        doc_rows.append(df_row_enr)
    df_docs = pd.DataFrame(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_DATA)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/enrich_data_{datetime.now().isoformat()}.log",
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
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées et données enrichies extraites des documents",
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
    df_meta = pd.read_csv(in_file, dtype=DTYPE_DATA)
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

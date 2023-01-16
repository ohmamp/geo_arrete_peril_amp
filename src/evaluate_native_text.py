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


def parse_text_structure(
    df_row: NamedTuple,
    latest_anno: NamedTuple | None,
    redo: bool = False,
) -> pd.DataFrame:
    """Analyse la structure d'une page d'arrêté.

    Découpe chaque arrêté en zones:
    * préambule (?),
    * VUs,
    * CONSIDERANTs,
    * ARTICLES,
    * postambule (?)

    Parameters
    ----------
    df_row: NamedTuple
        Page de document
    last_anno: NamedTuple | None
        Dernière annotation de structure de la page précédente, ou None si c'est la première page du document.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.

    Returns
    -------
    df_amod: pd.DataFrame
        Liste d'annotations en entrée, augmentée des nouvelles annotations de structure.
    """


def process_files(
    df_txts: pd.DataFrame,
    df_anno: pd.DataFrame,
    redo: bool = False,
) -> pd.DataFrame:
    """Traiter un ensemble d'arrêtés: extraire la structure des textes.

    Parameters
    ----------
    df_txts: pd.DataFrame
        Liste de documents à traiter, découpés en pages.
    df_anno: pd.DataFrame
        Liste d'annotations existantes, dont les empans "nettoyés"
        sur les documents d'intérêt.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.

    Returns
    -------
    df_amod: pd.DataFrame
        Liste d'annotations en entrée, augmentée des nouvelles annotations de structure.
    """
    annos_new = []
    for df_row in df_txts.itertuples():
        # pour chaque page de document, en extraire la structure ;
        # si ce n'est pas la première page du document, alors la dernière zone
        # de la page précédente peut se poursuivre sur la page courante
        # TODO confirmer si ce contexte est suffisant
        annos_struct = parse_text_structure(
            df_row,
            latest_anno=annos_new[-1] if df_row.page_num > 1 else None,
            redo=redo,
        )
        # stocker les nouvelles annotations de structure
        annos_new.extend(annos_struct)
    df_annos_new = pd.DataFrame.from_records(annos_new)
    df_amod = df_anno.concat(df_annos_new)
    return df_amod


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
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les pages de texte",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les pages de texte annotées",
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

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_txts = pd.read_csv(in_file)
    # traiter les documents (découpés en pages de texte)
    df_tmod = process_files(
        df_txts,
        redo=args.redo,
    )
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file)
        df_proc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_tmod
    df_proc.to_csv(out_file, index=False)

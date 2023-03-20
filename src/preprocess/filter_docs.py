"""Filtrer les fichiers PDF hors du champ de la base de données.

Annexes des arrêtés: plan de périmètre de sécurité, rapports d'expertise etc.

TODO filtrer automatiquement à partir du texte
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd

# TODO détection automatique à partir du texte
from src.preprocess.data_sources import EXCLUDE_FILES
from src.preprocess.separate_pages import DTYPE_META_NTXT_PDFTYPE, DTYPE_NTXT_PAGES

DTYPE_META_NTXT_FILT = DTYPE_META_NTXT_PDFTYPE | {"exclude": "boolean"}

DTYPE_NTXT_PAGES_FILT = DTYPE_NTXT_PAGES | {"exclude": "boolean"}

SET_EXCLUDE = set(EXCLUDE_FILES)


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
    df_mmod: pd.DataFrame
        Liste de métadonnées des fichiers, filtrés.
    df_tmod: pd.DataFrame
        Liste de métadonnées des pages traitées, avec indications des éléments de
        structure détectés.
    """
    df_mmod = df_meta.assign(exclude=(lambda x: x.pdf.isin(SET_EXCLUDE)))
    df_mmod = df_mmod.astype(dtype=DTYPE_META_NTXT_FILT)

    df_tmod = df_txts.assign(exclude=(lambda x: x.pdf.isin(SET_EXCLUDE)))
    df_tmod = df_tmod.astype(dtype=DTYPE_NTXT_PAGES_FILT)

    return df_mmod, df_tmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/filter_docs_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    # mêmes entrées et sorties que parse_native_pages
    parser.add_argument(
        "in_file_meta",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées des fichiers PDF",
    )
    parser.add_argument(
        "in_file_pages",
        help="Chemin vers le fichier CSV en entrée contenant les pages de texte",
    )
    parser.add_argument(
        "out_file_meta",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées des fichiers PDF filtrés (enrichies, par page)",
    )
    parser.add_argument(
        "out_file_pages",
        help="Chemin vers le fichier CSV en sortie contenant les pages de texte des fichiers PDF filtrés",
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

    # sortie: CSV de métadonnées
    # on crée le dossier parent (récursivement) si besoin
    out_file_meta = Path(args.out_file_meta).resolve()
    if out_file_meta.is_file():
        if not args.redo and not args.append:
            # erreur si le fichier CSV existe déjà mais ni redo, ni append
            raise ValueError(
                f"Le fichier de sortie {out_file_meta} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
            )
    else:
        # si out_file_meta n'existe pas, créer son dossier parent si besoin
        out_dir = out_file_meta.parent
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(exist_ok=True)

    # sortie: CSV de pages de texte annotées
    # on crée le dossier parent (récursivement) si besoin
    out_file_pages = Path(args.out_file_pages).resolve()
    if out_file_pages.is_file():
        if not args.redo and not args.append:
            # erreur si le fichier CSV existe déjà mais ni redo, ni append
            raise ValueError(
                f"Le fichier de sortie {out_file_pages} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
            )
    else:
        # si out_file_pages n'existe pas, créer son dossier parent si besoin
        out_dir = out_file_pages.parent
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(exist_ok=True)

    # ouvrir le fichier de métadonnées en entrée
    logging.info(f"Ouverture du fichier CSV de métadonnées {in_file_meta}")
    df_meta = pd.read_csv(in_file_meta, dtype=DTYPE_META_NTXT_PDFTYPE)
    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV de pages de texte {in_file_pages}")
    df_txts = pd.read_csv(in_file_pages, dtype=DTYPE_NTXT_PAGES)
    # traiter les documents (découpés en pages de texte)
    df_mmod, df_tmod = process_files(df_meta, df_txts)

    # optionnel: afficher des statistiques
    # TODO nombre de fichiers ignorés

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file_meta.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file_meta, dtype=DTYPE_META_NTXT_FILT)
        df_mproc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_mproc = df_mmod
    df_mproc.to_csv(out_file_meta, index=False)

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file_pages.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file_pages, dtype=DTYPE_NTXT_PAGES_FILT)
        df_tproc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_tproc = df_tmod
    df_tproc.to_csv(out_file_pages, index=False)

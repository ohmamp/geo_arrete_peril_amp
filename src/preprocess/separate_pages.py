"""Chaque ligne correspond à une page d'un document.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd

from src.preprocess.determine_pdf_type import DTYPE_META_NTXT_PDFTYPE
from src.utils.txt_format import load_pages_text

# champs des documents copiés pour les pages: métadonnées du fichier PDF et du TXT
# nom du fichier, chemin PDF original, chemin TXT, nombre de pages
COLS_DOC = ["pdf", "fullpath", "fullpath_txt", "nb_pages"]

# format des données de sortie
DTYPE_NTXT_PAGES = {x: DTYPE_META_NTXT_PDFTYPE[x] for x in COLS_DOC} | {
    "pagenum": "Int64",  # Int16?
    "pagetxt": "string",
}


def create_pages_dataframe(
    df_meta: pd.DataFrame,
) -> pd.DataFrame:
    """Charger le texte des documents dans un DataFrame.

    Une entrée par page de document.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des documents.

    Returns
    -------
    df_txts: pd.DataFrame
        Tableau contenant le texte des documents, séparé par page.
    """
    page_txts = []
    for df_row in df_meta.itertuples():
        if pd.isna(df_row.fullpath_txt):
            # créer une entrée vide par page du PDF
            pages = [
                {
                    # métadonnées de la page
                    "pagenum": i,
                    # texte de la page
                    "pagetxt": None,
                }
                for i in range(1, df_row.nb_pages + 1)
            ]
        else:
            # créer une entrée par page de texte
            doc_txt = load_pages_text(df_row.fullpath_txt)
            # vérifier que le fichier TXT contient autant de pages que le PDF
            try:
                assert len(doc_txt) == df_row.nb_pages
            except AssertionError:
                print(repr(df_row))
                print(
                    f"{len(doc_txt)} pages de texte != {df_row.nb_pages} pages dans le fichier PDF"
                )
                raise
            # pour chaque page, charger le texte
            pages = [
                {
                    # métadonnées de la page
                    "pagenum": i,
                    # texte de la page
                    "pagetxt": page_txt,
                }
                for i, page_txt in enumerate(doc_txt, start=1)
            ]
        # dupliquer les métadonnées du fichier PDF et du TXT, dans chaque entrée de page
        doc_rows = [
            {x: getattr(df_row, x) for x in COLS_DOC}
            | page  # python >= 3.9 (dict union)
            for page in pages
        ]
        # vérifier que le nombre de pages de texte extrait est inférieur ou égal au nombre de pages du PDF
        # (certaines pages peuvent être blanches, ne contenir que des images ou photos...)
        # TODO vérifier redondance avec l'assertion ci-dessus?
        assert len(doc_rows) <= df_row.nb_pages
        page_txts.extend(doc_rows)
    df_txts = pd.DataFrame.from_records(page_txts)
    df_txts = df_txts.astype(dtype=DTYPE_NTXT_PAGES)
    return df_txts


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/separate_pages_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées des fichiers PDF et le chemin vers les TXT",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les pages de texte",
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
        out_dir.mkdir(parents=True, exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_meta = pd.read_csv(in_file, dtype=DTYPE_META_NTXT_PDFTYPE)
    # traiter les documents (découpés en pages de texte)
    df_txts = create_pages_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file, dtype=DTYPE_NTXT_PAGES)
        df_proc = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

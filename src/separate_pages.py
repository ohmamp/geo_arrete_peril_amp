"""Charge le texte des documents dans un DataFrame.

Chaque ligne correspond à une page d'un document.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import List

import pandas as pd


def load_pages_text(fp_txt: Path, page_break: str = "\f") -> List[str]:
    """Charge le texte d'un document, découpé en pages.

    Parameters
    ----------
    fp_txt: Path
        Chemin du fichier contenant le texte d'un document.
    page_break: string, defaults to "\f"
        Séparateur de pages. Les fichiers PDF texte produits par l'export
        direct depuis les logiciels de traitement de texte contiennent
        déjà un "form feed" ("\f"), comme les fichiers "sidecar" produits
        par ocrmypdf (pour les fichiers PDF image).

    Returns
    -------
    doc_txt: List[str]
        Texte du document, par page.
    """
    with open(fp_txt) as f_txt:
        doc_txt = f_txt.read().split(page_break)
    # chaque page se termine par un séparateur de page, y compris la dernière ;
    # split() a pour effet de créer une fausse dernière page vide
    # on vérifie que cette fausse page vide existe et on la retire
    assert doc_txt[-1] == ""
    doc_txt.pop()
    #
    return doc_txt


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
                print(len(doc_txt))
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
            {
                # métadonnées du fichier PDF et du TXT
                "filename": df_row.filename,  # nom du fichier
                "fullpath": df_row.fullpath,  # chemin PDF original
                "fullpath_txt": df_row.fullpath_txt,  # chemin TXT
                "nb_pages": df_row.nb_pages,  # nombre de pages
            }
            | page  # python >= 3.9 (dict union)
            for page in pages
        ]
        # vérifier que le nombre de pages de texte extrait est inférieur ou égal au nombre de pages du PDF
        # (certaines pages peuvent être blanches, ne contenir que des images ou photos...)
        # TODO vérifier redondance avec l'assertion ci-dessus?
        assert len(doc_rows) <= df_row.nb_pages
        page_txts.extend(doc_rows)
    df_txts = pd.DataFrame.from_records(page_txts)
    return df_txts


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
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
        out_dir.mkdir(exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_meta = pd.read_csv(in_file, dtype={"fullpath_txt": "string"})
    # traiter les documents (découpés en pages de texte)
    df_txts = create_pages_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file)
        df_txts = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

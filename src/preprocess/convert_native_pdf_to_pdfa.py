"""Convertir les fichiers PDF natifs (texte natif) en PDF/A.

Utilise ocrmypdf sans appeler le moteur d'OCR.
"""

# 2023-03-19: 2029 fichiers pdf convertis en 1h01

import argparse
from datetime import datetime
import logging
from pathlib import Path

#
import pandas as pd

# schéma des données en entrée: sortie de extract_native_text
from src.preprocess.determine_pdf_type import DTYPE_META_NTXT_PDFTYPE
from src.preprocess.convert_to_pdfa import convert_pdf_to_pdfa


# schéma des données en sortie
DTYPE_META_NTXT_PDFA = DTYPE_META_NTXT_PDFTYPE | {
    "fullpath_pdfa": "string",  # chemin vers le fichier PDF/A produit
}


# TODO redo='all'|'ocr'|'none' ? 'ocr' pour ré-extraire le texte quand le fichier source est mal océrisé par la source, ex: 99_AI-013-211300264-20220223-22_100-AI-1-1_1.pdf
def process_files(
    df_meta: pd.DataFrame,
    out_pdf_dir: Path,
    redo: bool = False,
    verbose: int = 0,
) -> pd.DataFrame:
    """Convertir les fichiers PDF natifs en PDF/A.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de fichiers PDF à traiter, avec leurs métadonnées.
    out_pdf_dir: Path
        Dossier de sortie pour les PDF/A.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées des fichiers d'entrée et chemins vers les fichiers PDF/A.
    """
    fullpath_pdfa = []
    for df_row in df_meta.itertuples():
        # fichier d'origine
        fp_pdf_in = Path(df_row.fullpath)
        # fichiers à produire
        fp_pdf_out = out_pdf_dir / fp_pdf_in.name

        # si le fichier à produire existe déjà
        if fp_pdf_out.is_file():
            if redo:
                # ré-exécution explicitement demandée: émettre une info et traiter le fichier
                # TODO comparer les versions d'ocrmypdf/tesseract/pikepdf dans les métadonnées du PDF de sortie et les versions actuelles des dépendances,
                # et si pertinent émettre un message proposant de ré-analyser le PDF ?
                logging.info(
                    f"Re-traitement de {fp_pdf_in}, le fichier de sortie {fp_pdf_out} existant sera écrasé."
                )
            else:
                # pas de ré-exécution demandée: émettre un warning et passer au fichier suivant
                logging.info(
                    f"{fp_pdf_in} est ignoré car le fichier {fp_pdf_out} existe déjà."
                )
                fullpath_pdfa.append(fp_pdf_out)
                continue

        if df_row.processed_as == "text" and not df_row.exclude:
            # convertir le PDF natif ("texte") en PDF/A-2b
            logging.info(f"Conversion en PDF/A d'un PDF texte: {fp_pdf_in}")
            convert_pdf_to_pdfa(fp_pdf_in, fp_pdf_out, verbose=verbose)
            # TODO stocker la valeur de retour d'ocrmypdf dans une nouvelle colonne "retcode_pdfa" ?
            # stocker le chemin vers le fichier PDF/A produit
            fullpath_pdfa.append(fp_pdf_out)
        else:
            # ignorer le PDF non-natif ("image") ;
            # le fichier PDF/A sera produit lors de l'OCRisation
            fullpath_pdfa.append(None)

    # remplir le fichier CSV de sortie
    df_mmod = df_meta.assign(
        fullpath_pdfa=fullpath_pdfa,
    )
    # forcer les types des nouvelles colonnes
    df_mmod = df_mmod.astype(dtype=DTYPE_META_NTXT_PDFA)
    return df_mmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/convert_native_pdf_to_pdfa_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées enrichies et le chemin vers le texte extrait pour les PDF natifs",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées enrichies et les chemins vers le PDF et le texte, pour les PDF natifs",
    )
    parser.add_argument(
        "out_dir",
        help="Chemin vers le dossier de sortie contenant les PDF-A",
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
        help="Ajoute les métadonnées au fichier out_file s'il existe",
    )
    parser.add_argument(
        # <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>
        "--verbose",
        action="store",
        default=0,
        help="Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2)",
    )
    args = parser.parse_args()

    # entrée: CSV de métadonnées enrichi
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de métadonnées enrichi + infos fichiers produits
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

    # sortie: dossier pour PDF-A
    out_dir = Path(args.out_dir).resolve()
    out_pdf_dir = out_dir / "pdf"
    # on le crée si besoin
    out_pdf_dir.mkdir(parents=True, exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_metas = pd.read_csv(in_file, dtype=DTYPE_META_NTXT_PDFTYPE)
    # traiter les fichiers
    df_mmod = process_files(df_metas, out_pdf_dir, redo=args.redo, verbose=args.verbose)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT_PDFA)
        df_proc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_mmod
    df_proc.to_csv(out_file, index=False)

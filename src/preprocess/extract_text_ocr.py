"""Extraire le texte des fichiers PDF fournis en entrée.

Le texte des PDF natifs ("PDF texte") est extrait avec pdftotext.
Le texte des PDF non-natifs ("PDF image") est extrait avec ocrmypdf,
qui ajoute au fichier PDF une couche avec le texte extrait par OCR.

Tous les fichiers PDF sont convertis en PDF/A.
"""

# TODO détecter les première et dernière page: de "nous" + vu, considérant etc jusqu'à la signature
# pour exclure les annexes (rappel des articles du code de la construction, rapport de BE), page de garde etc.
# => ajouter un mode "early_stopping", optionnel, à l'extraction de texte
# TODO tester si (1) la sortie de pdftotext et (2) le sidecar (sur des PDF différents) sont globalement formés de façon similaire
# pour valider qu'on peut appliquer les mêmes regex/patterns d'extraction, ou s'il faut prévoir des variantes
# TODO si redo='ocr', ré-OCRisation des documents (mal) OCRisés (avec un warning.info)
# TODO tester l'appel direct à ocrmypdf par API python
# TODO tester "--clean" sur plusieurs PDF (aucun gain sur le pdf de test)
# TODO ajuster le logging
# TODO logger la sortie de ocrmypdf pour les messages sur les métadonnées
# (ex: "Some input metadata could not be copied because it is not permitted in PDF/A. You may wish to examine the output PDF's XMP metadata.")
# ou l'extraction (ex: "9 [tesseract] lots of diacritics - possibly poor OCR")
# TODO examiner si tous les cas de pages "sautées" sont légitimes: grep -Ri "OCR skipped on page" ../data/interim/txt/*

# alternatives testées sur les PDF image OCRisés:
# * pdftotext (xpdf/poppler) mélange le texte (comparé au fichier "sidecar" de ocrmypdf)
# * pdf2txt (pdfminer) mélange le texte (idem)
# * pdfplumber introduit des espaces et lignes superflus

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import NamedTuple

# bibliothèques tierces
import pandas as pd

# imports locaux
from src.preprocess.extract_native_text_pdftotext import extract_native_text_pdftotext
from src.preprocess.extract_text_ocr_ocrmypdf import extract_text_from_pdf_image

# schéma des données en entrée
from src.preprocess.process_metadata import DTYPE_META_PROC

# schéma des données en sortie
DTYPE_META_NTXT_OCR = DTYPE_META_PROC | {
    "processed_as": "string",
    "fullpath_pdfa": "string",
    "fullpath_txt": "string",
}


# TODO type hint pour la valeur de retour: str, Literal ou LiteralString? dépend de la version de python
def preprocess_pdf_file(
    df_row: NamedTuple,
    fp_pdf_in: Path,
    fp_pdf_out: Path,
    fp_txt_out: Path,
    redo: bool = False,
    verbose: int = 0,
) -> str:
    """Deviner le type de PDF (image ou texte) et extraire le texte.

    Si pdftotext renvoie du texte, le fichier est considéré PDF texte,
    sinon il est considéré PDF image et OCRisé avec ocrmypdf.
    Dans les deux cas, ocrmypdf est appelé pour créer un PDF/A.

    La version actuelle est: ocrmypdf 14.0.3 / Tesseract OCR-PDF 5.2.0
    (+ pikepdf 5.6.1).

    Parameters
    ----------
    df_row: NamedTuple
        Métadonnées et informations sur le fichier PDF à traiter.
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.
    fp_pdf_out: Path
        Chemin du fichier PDF converti en PDF/A (avec OCR le cas échéant).
    fp_txt_out: Path
        Chemin du fichier txt contenant le texte extrait.
    redo: boolean, defaults to False
        Si True, le traitement est ré-appliqué même si les fichiers de sortie existent.
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    pdf_type: str
        Type de fichier PDF qui a été supposé pour extraire le texte: "text" ou "image"
    """
    logging.info(f"Ouverture du fichier {fp_pdf_in}")
    # définir les pages à traiter
    page_beg = 1
    # exclure la dernière page si c'est un accusé de réception de transmission à @ctes
    page_end = (
        df_row.nb_pages - 1
        if (pd.notna(df_row.guess_dernpage) and df_row.guess_dernpage)
        else df_row.nb_pages
    )

    # on utilise les heuristiques sur les métadonnées, calculées dans "convert_native_pdf_to_pdfa"
    # auparavant, pour déterminer les PDFs (image) à OCRiser
    if df_row.processed_as == "image":
        if pd.notna(df_row.guess_dernpage) and df_row.guess_dernpage:
            # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
            # sauf pour la dernière page (accusé de réception de transmission à @ctes)
            logging.info(f"PDF image: {fp_pdf_in}")
            extract_text_from_pdf_image(
                fp_pdf_in,
                fp_txt_out,
                fp_pdf_out,
                page_beg=1,
                page_end=page_end,
                verbose=verbose,
            )
            # RESUME HERE !
    elif pd.notna(df_row.guess_badocr) and df_row.guess_badocr:
        # le PDF contient une couche d'OCR produite par un logiciel moins performant: refaire l'OCR
        #
        # PDF image
        pdf_type = "image"
        # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
        logging.info(f"PDF image: {fp_pdf_in}")
        # même extraction que pour les PDF image standard mais en indiquant explicitement à ocrmypdf qu'il doit
        # refaire l'OCR même s'il détecte des couches OCR existantes: "--redo-ocr"
        # (si cela ne fonctionne pas, modifier le code pour utiliser "--force-ocr" qui forcera la rasterization
        # des pages puis leur appliquera l'OCR)
        extract_text_from_pdf_image(
            fp_pdf_in,
            fp_txt_out,
            fp_pdf_out,
            page_beg=page_beg,
            page_end=page_end,
            redo_ocr=True,
            verbose=verbose,
        )
    else:
        # PDF image
        pdf_type = "image"
        # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
        logging.info(f"PDF image: {fp_pdf_in}")
        page_beg = 1
        page_end = df_row.nb_pages
        # FIXME force ocr pour les PDF avec une mauvaise OCR, eg. "Image Capture Plus"
        extract_text_from_pdf_image(
            fp_pdf_in,
            fp_txt_out,
            fp_pdf_out,
            page_beg=page_beg,
            page_end=page_end,
            verbose=verbose,
        )
    return pdf_type


# TODO redo='all'|'ocr'|'none' ? 'ocr' pour ré-extraire le texte quand le fichier source est mal océrisé par la source, ex: 99_AI-013-211300264-20220223-22_100-AI-1-1_1.pdf
def process_files(
    df_meta: pd.DataFrame,
    out_pdf_dir: Path,
    out_txt_dir: Path,
    redo: bool = False,
    verbose: int = 0,
) -> pd.DataFrame:
    """Traiter un ensemble de fichiers PDF: convertir les PDF en PDF/A et extraire le texte.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de fichiers PDF à traiter, avec leurs métadonnées.
    out_pdf_dir: Path
        Dossier de sortie pour les PDF/A.
    out_txt_dir: Path
        Dossier de sortie pour les fichiers texte.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées des fichiers d'entrée et chemins vers les fichiers PDF/A et TXT.
    """
    processed_as = []
    fullpath_pdfa = []
    fullpath_txt = []
    for df_row in df_meta.itertuples():
        # fichier d'origine
        fp_pdf_in = Path(df_row.fullpath)
        # fichiers à produire
        fp_pdf_out = out_pdf_dir / fp_pdf_in.name
        fp_txt = out_txt_dir / (fp_pdf_in.stem + ".txt")
        # si les fichiers à produire existent déjà
        if fp_pdf_out.is_file() and fp_txt.is_file():
            if redo:
                # ré-exécution explicitement demandée: émettre une info et traiter le fichier
                # TODO comparer les versions d'ocrmypdf/tesseract/pikepdf dans les métadonnées du PDF de sortie et les versions actuelles des dépendances,
                # et si pertinent émettre un message proposant de ré-analyser le PDF ?
                logging.info(
                    f"Re-traitement de {fp_pdf_in}, les fichiers de sortie {fp_pdf_out} et {fp_txt} existants seront écrasés."
                )
            else:
                # pas de ré-exécution demandée: émettre un warning et passer au fichier suivant
                logging.info(
                    f"{fp_pdf_in} est ignoré car les fichiers {fp_pdf_out} et {fp_txt} existent déjà."
                )
                processed_as.append(
                    "?"
                )  # TODO déterminer "pdf_type" à partir des champs existants
                fullpath_pdfa.append(fp_pdf_out)
                fullpath_txt.append(fp_txt)
                continue
        # traiter le fichier: extraire le texte par OCR si nécessaire, corriger et convertir le PDF d'origine en PDF/A-2b
        pdf_type = preprocess_pdf_file(
            df_row, fp_pdf_in, fp_pdf_out, fp_txt, redo=redo, verbose=verbose
        )
        # stocker les chemins vers les fichiers PDF/A et TXT produits
        processed_as.append(pdf_type)
        fullpath_pdfa.append(fp_pdf_out)
        fullpath_txt.append(fp_txt)
    df_mmod = df_meta.assign(
        processed_as=processed_as,
        fullpath_pdfa=fullpath_pdfa,
        fullpath_txt=fullpath_txt,
    )
    # forcer les types des nouvelles colonnes
    df_mmod = df_mmod.astype(dtype=DTYPE_META_NTXT_OCR)
    return df_mmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/extract_text_ocr_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées enrichies",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées enrichies et les chemins vers le PDF et le texte",
    )
    parser.add_argument(
        "out_dir",
        help="Chemin vers le dossier de sortie contenant les PDF-A et le texte extrait",
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
        out_dir.mkdir(exist_ok=True)

    # sortie: dossiers pour PDF-A et TXT
    out_dir = Path(args.out_dir).resolve()
    out_pdf_dir = out_dir / "pdf"
    out_txt_dir = out_dir / "txt"
    # on les crée si besoin
    out_pdf_dir.mkdir(exist_ok=True)
    out_txt_dir.mkdir(exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_metas = pd.read_csv(
        in_file, dtype=DTYPE_META_PROC
    )  # FIXME DTYPE_META_NTXT si après extract_native_text
    # traiter les fichiers
    df_mmod = process_files(
        df_metas, out_pdf_dir, out_txt_dir, redo=args.redo, verbose=args.verbose
    )
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT_OCR)
        df_proc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_mmod
    df_proc.to_csv(out_file, index=False)

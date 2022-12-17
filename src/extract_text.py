"""Extraire le texte des fichiers PDF fournis en entrée.

Le texte des PDF natifs ("PDF texte") est extrait avec pdftotext.
Le texte des PDF non-natifs ("PDF image") est extrait avec ocrmypdf,
qui ajoute au fichier PDF une couche avec le texte extrait par OCR.

Tous les fichiers PDF sont convertis en PDF/A.
"""

# TODO détecter les première et dernière page: de "nous" + vu, considérant etc jusqu'à la signature
# pour exclure les annexes (rappel des articles du code de la construction, rapport de BE), page de garde etc.
# TODO tester si (1) la sortie de pdftotext et (2) le sidecar (sur des PDF différents) sont globalement formés de façon similaire
# pour valider qu'on peut appliquer les mêmes regex/patterns d'extraction, ou s'il faut prévoir des variantes
# TODO si redo='ocr', ré-OCRisation des documents (mal) OCRisés (avec un warning.info)
# TODO tester l'appel direct à ocrmypdf par API python
# TODO tester "--clean" sur plusieurs PDF (aucun gain sur le pdf de test)
# TODO ajuster le logging
# TODO logger la sortie de ocrmypdf pour les messages sur les métadonnées
# (ex: "Some input metadata could not be copied because it is not permitted in PDF/A. You may wish to examine the output PDF's XMP metadata.")
# ou l'extraction (ex: "9 [tesseract] lots of diacritics - possibly poor OCR")

# alternatives testées sur les PDF image OCRisés:
# * pdftotext (xpdf/poppler) mélange le texte (comparé au fichier "sidecar" de ocrmypdf)
# * pdf2txt (pdfminer) mélange le texte (idem)
# * pdfplumber introduit des espaces et lignes superflus

import argparse
from datetime import datetime, timedelta
from importlib.metadata import version  # pour récupérer la version de pdftotext
import logging
from pathlib import Path
import subprocess
from subprocess import PIPE, STDOUT
from typing import Dict, List, NamedTuple, Tuple

import pandas as pd
from ocrmypdf.exceptions import ExitCode
import pdftotext

# version des bibliothèques d'extraction de contenu des PDF texte et image
PDFTOTEXT_VERSION = version("pdftotext")
OCRMYPDF_VERSION = (
    subprocess.run(["ocrmypdf", "--version"], capture_output=True)
    .stdout.decode()
    .strip()
)


# TODO récupérer les métadonnées du PDF perdues par ocrmypdf <https://github.com/ocrmypdf/OCRmyPDF/issues/327>
def convert_pdf_to_pdfa(fp_pdf_in: Path, fp_pdf_out: Path, verbose: int = 0) -> int:
    """Convertir un PDF en PDF/A.

    Utilise ocrmypdf sans appliquer d'OCR.

    Parameters
    ----------
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    returncode: int
        0 si un fichier PDF/A a été produit, 1 sinon.
    """
    try:
        compl_proc = subprocess.run(
            [
                "ocrmypdf",
                "-l",
                "fra",
                "--skip-text",
                fp_pdf_in,
                fp_pdf_out,
                "--verbose",
                str(verbose),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        logging.info(compl_proc.stdout)
        logging.info(compl_proc.stderr)
    if compl_proc.returncode == ExitCode.pdfa_conversion_failed:
        # <https://ocrmypdf.readthedocs.io/en/latest/advanced.html#return-code-policy>
        logging.warning(
            f"Un PDF a été généré mais la conversion en PDF/A a échoué: {fp_pdf_out}"
        )
        # cela arrive quand les métadonnées du PDF contiennent des caractères que ghostscript considère incorrects
        # "DEBUG ocrmypdf.subprocess.gs - GPL Ghostscript 9.54.0: Text string detected in DOCINFO cannot be represented in XMP for PDF/A1, discarding DOCINFO"
        # ex: les métadonnées PDF contiennent "Microsoft® Word 2010"
        # <https://stackoverflow.com/questions/57167784/ghostscript-wont-generate-pdf-a-with-utf16be-text-string-detected-in-docinfo>
    return compl_proc.returncode


def extract_text_from_pdf_image(
    fp_pdf_in: Path,
    fp_txt_out: Path,
    fp_pdf_out: Path,
    page_beg: int,
    page_end: int,
    verbose: int = 0,
) -> int:
    """Extraire le texte d'un PDF image et convertir le fichier en PDF/A.

    Utilise ocrmypdf.
    On utilise "-l fra" pour améliorer la reconnaissance de: "à", "è",
    "ê", apostrophe, "l'", "œ", "ô" etc.

    Parameters
    ----------
    fp_pdf_in: Path
        Fichier PDF image à traiter.
    fp_txt_out: Path
        Fichier TXT produit, contenant le texte extrait par OCR.
    fp_pdf_out: Path
        Fichier PDF/A produit, incluant le texte océrisé.
    page_beg: int
        Numéro de la première page à traiter, la première page d'un PDF est supposée numérotée 1.
    page_end: int
        Numéro de la dernière page à traiter (cette page étant incluse).
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    returncode: int
        0 si deux fichiers PDF/A et TXT ont été produits, 1 sinon.
    """
    # appeler ocrmypdf pour produire 2 fichiers: PDF/A-2b (inc. OCR) + sidecar (txt)
    try:
        compl_proc = subprocess.run(
            [
                "ocrmypdf",
                # langue française
                "-l",
                "fra",
                # sélection de pages
                "--page",
                f"{page_beg}-{page_end}",
                "--sidecar",
                fp_txt_out,
                fp_pdf_in,
                fp_pdf_out,
                "--verbose",
                str(verbose),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        logging.info(compl_proc.stdout)
        logging.info(compl_proc.stderr)
    if compl_proc.returncode == ExitCode.pdfa_conversion_failed:
        # <https://ocrmypdf.readthedocs.io/en/latest/advanced.html#return-code-policy>
        logging.warning(
            f"Un PDF a été généré mais la conversion en PDF/A a échoué: {fp_pdf_out}"
        )
        # cela arrive quand les métadonnées du PDF contiennent des caractères que ghostscript considère incorrects
        # "DEBUG ocrmypdf.subprocess.gs - GPL Ghostscript 9.54.0: Text string detected in DOCINFO cannot be represented in XMP for PDF/A1, discarding DOCINFO"
        # ex: les métadonnées PDF contiennent "Microsoft® Word 2010"
        # <https://stackoverflow.com/questions/57167784/ghostscript-wont-generate-pdf-a-with-utf16be-text-string-detected-in-docinfo>
    return compl_proc.returncode


def extract_text_from_pdf_text(
    fp_pdf_in: Path, fp_txt_out: Path, page_beg: int, page_end: int, page_break=""
) -> int:
    """Extrait le texte d'un PDF texte.

    Utilise pdftotext. Si le texte extrait par pdftotext n'est pas vide,
    alors le fichier est considéré comme PDF texte et un fichier TXT est
    produit, sinon aucun fichier TXT n'est produit (et un code d'erreur
    est renvoyé).

    Parameters
    ----------
    fp_pdf_in: Path
        Fichier PDF d'entrée.
    fp_txt_out: Path
        Fichier TXT produit par extraction directe du texte.
    page_beg: int
        Numéro de la première page à traiter, la première page d'un PDF est supposée numérotée 1.
    page_end: int, defaults to None
        Numéro de la dernière page à traiter (cette page étant incluse).
    page_break: string, defaults to ""
        Texte ajouté entre chaque paire de pages. Il devrait être inutile
        d'en ajouter un car les fichiers PDF texte produits par l'export
        direct depuis les logiciels de traitement de texte contiennent
        déjà un "form feed" ("\f"), comme les fichiers "sidecar" produits
        par ocrmypdf (pour les fichiers PDF image).

    Returns
    -------
    returncode: int
        0 si un fichier TXT a été produit, 1 sinon.
    """
    # TODO vérifier que le texte contient bien "\f" en début ou fin de page
    with open(fp_pdf_in, "rb") as f:
        pdf = pdftotext.PDF(f)
    # les numéros de page commencent à 1, mais pdftotext crée une liste de pages
    # qui commence à l'index 0
    page_beg = page_beg - 1
    # le numéro de la dernière page ne doit pas être décalé car la borne sup d'un slice est exclue
    # pdftotext.PDF permet de getitem, mais pas de récupérer un slice... il faut créer un range et itérer manuellement
    txt = page_break.join(pdf[i] for i in range(page_beg, page_end)).strip()
    if txt:
        # stocker le texte dans un fichier .txt
        with open(fp_txt_out, "w") as f_txt:
            f_txt.write(txt)
        return 0
    else:
        # code d'erreur
        return 1


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

    La version actuelle est: ocrmypdf 14.0.1 / Tesseract OCR-PDF 5.2.0
    (+ pikepdf 5.6.0).

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
    # on utilise les heuristiques sur les métadonnées pour prédire si c'est un PDF texte ou image, et orienter le traitement
    if df_row.guess_pdftext:
        # forte présomption que c'est un PDF texte, d'après les métadonnées
        pdf_type = "text"
        # on veut extraire le texte de toutes les pages
        page_beg = 1
        page_end = df_row.nb_pages
        # extraire le texte
        retcode = extract_text_from_pdf_text(
            fp_pdf_in, fp_txt_out, page_beg=page_beg, page_end=page_end
        )
        # convertir le PDF (texte) en PDF/A-2b (parallélisme des traitements)
        logging.info(f"PDF texte: {fp_pdf_in}")
        convert_pdf_to_pdfa(fp_pdf_in, fp_pdf_out, verbose=verbose)
    elif df_row.guess_dernpage:
        # (pour les PDF du stock) la dernière page est un accusé de réception de transmission à @ctes,
        # donc les métadonnées ont été écrasées et:
        # 1. il faut exclure la dernière page (accusé de réception de la transmission) puis
        # 2. si pdftotext parvient à extraire du texte, alors c'est un PDF texte, sinon c'est un PDF image
        page_beg = 1
        page_end = df_row.nb_pages - 1
        retcode = extract_text_from_pdf_text(
            fp_pdf_in, fp_txt_out, page_beg=page_beg, page_end=page_end
        )
        if retcode == 0:
            pdf_type = "text"
            # convertir le PDF (texte) en PDF/A-2b (parallélisme des traitements)
            logging.info(f"PDF texte: {fp_pdf_in}")
            convert_pdf_to_pdfa(fp_pdf_in, fp_pdf_out, verbose=verbose)
        else:
            pdf_type = "image"
            # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
            # sauf pour la dernière page !
            logging.info(f"PDF image: {fp_pdf_in}")
            extract_text_from_pdf_image(
                fp_pdf_in,
                fp_txt_out,
                fp_pdf_out,
                page_beg=1,
                page_end=page_end,
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
    out_dir_pdf: Path,
    out_dir_txt: Path,
    redo: bool = False,
    verbose: int = 0,
) -> pd.DataFrame:
    """Traiter un ensemble de fichiers PDF: convertir les PDF en PDF/A et extraire le texte.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de fichiers PDF à traiter, avec leurs métadonnées.
    out_dir_pdf: Path
        Dossier de sortie pour les PDF/A.
    out_dir_txt: Path
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
    return df_mmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/extract_text_{datetime.now().isoformat()}.log",
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
    df_metas = pd.read_csv(in_file)
    # traiter les fichiers
    df_mmod = process_files(
        df_metas, out_pdf_dir, out_txt_dir, redo=args.redo, verbose=args.verbose
    )
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file)
        df_proc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_mmod
    df_proc.to_csv(out_file, index=False)

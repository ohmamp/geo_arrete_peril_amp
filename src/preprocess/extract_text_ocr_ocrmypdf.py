"""Utilise ocrmypdf.
"""

import logging
from pathlib import Path
import subprocess

#
from ocrmypdf.exceptions import ExitCode


# version des bibliothèques d'extraction de contenu des PDF image
OCRMYPDF_VERSION = (
    subprocess.run(["ocrmypdf", "--version"], capture_output=True)
    .stdout.decode()
    .strip()
)


def extract_text_from_pdf_image(
    fp_pdf_in: Path,
    fp_txt_out: Path,
    fp_pdf_out: Path,
    page_beg: int,
    page_end: int,
    redo_ocr: bool = False,
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
    redo_ocr: boolean, defaults to False
        Si True, refait l'OCR même si une couche d'OCR est détectée sur certaines pages.
    verbose: int, defaults to 0
        Niveau de verbosité d'ocrmypdf (-1, 0, 1, 2):
        <https://ocrmypdf.readthedocs.io/en/latest/api.html#ocrmypdf.Verbosity>

    Returns
    -------
    returncode: int
        0 si deux fichiers PDF/A et TXT ont été produits, une autre valeur sinon
        <https://ocrmypdf.readthedocs.io/en/latest/advanced.html#return-code-policy> .
    """
    # appeler ocrmypdf pour produire 2 fichiers: PDF/A-2b (inc. OCR) + sidecar (txt)
    cmd = (
        ["ocrmypdf"]
        + [
            # langue française
            "-l",
            "fra",
            # sélection de pages
            "--page",
            f"{page_beg}-{page_end}",
            # TXT en sortie
            "--sidecar",
            fp_txt_out,
            # verbosité
            "--verbose",
            str(verbose),
        ]
        + (["--redo-ocr"] if redo_ocr else [])
        + [
            # PDF en entrée
            fp_pdf_in,
            # PDF/A en sortie
            fp_pdf_out,
        ]
    )
    try:
        compl_proc = subprocess.run(
            cmd,
            capture_output=True,
            check=False,
            text=True,
        )
    finally:
        logging.info(compl_proc.stdout)
        logging.info(compl_proc.stderr)
    if compl_proc.returncode == ExitCode.pdfa_conversion_failed:
        # <https://ocrmypdf.readthedocs.io/en/latest/advanced.html#return-code-policy>
        # <https://ocrmypdf.readthedocs.io/en/v14.0.4/apiref.html#ocrmypdf.exceptions.ExitCode>
        logging.warning(
            f"Un PDF a été généré mais la conversion en PDF/A a échoué: {fp_pdf_out}"
        )
        # cela arrive quand les métadonnées du PDF contiennent des caractères que ghostscript considère incorrects
        # "DEBUG ocrmypdf.subprocess.gs - GPL Ghostscript 9.54.0: Text string detected in DOCINFO cannot be represented in XMP for PDF/A1, discarding DOCINFO"
        # ex: les métadonnées PDF contiennent "Microsoft® Word 2010"
        # <https://stackoverflow.com/questions/57167784/ghostscript-wont-generate-pdf-a-with-utf16be-text-string-detected-in-docinfo>
    return compl_proc.returncode

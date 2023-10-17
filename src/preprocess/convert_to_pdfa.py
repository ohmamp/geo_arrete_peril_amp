"""
# Convertir un fichier PDF en PDF/A (archivable).

Utilise ocrmypdf.

NB: Certaines métadonnées du PDF sont perdues
<https://github.com/ocrmypdf/OCRmyPDF/issues/327> .
"""

# TODO récupérer les métadonnées du PDF perdues par ocrmypdf


import logging
from pathlib import Path
import subprocess

#
from ocrmypdf.exceptions import ExitCode


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

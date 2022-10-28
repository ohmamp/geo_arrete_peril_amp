"""Prétraiter les fichiers PDF fournis en entrée, pour en extraire le texte.

Le texte est extrait avec pdftotexte pour les fichiers PDF texte, et ocrmypdf
pour les fichiers PDF image.
"""

# TODO tester l'appel direct à ocrmypdf par API python
# TODO tester "--clean" sur plusieurs PDF (aucun gain sur le pdf de test)
# TODO ajuster le logging, remplacer des warning() par info()

# alternatives testées sur les PDF image OCRisés:
# * pdftotext (xpdf/poppler) mélange le texte (comparé au fichier "sidecar" de ocrmypdf)
# * pdf2txt (pdfminer) mélange le texte (idem)
# * pdfplumber introduit des espaces et lignes superflus

from importlib.metadata import version  # pour récupérer la version de pdftotext
import logging
from pathlib import Path
import subprocess

import pandas as pd
from poppler import load_from_file
import pdftotext

PDFTOTEXT_VERSION = version("pdftotext")
OCRMYPDF_VERSION = (
    subprocess.run(["ocrmypdf", "--version"], capture_output=True)
    .stdout.decode()
    .strip()
)


def convert_pdf_to_pdfa(fp_pdf_in: Path, fp_pdf_out: Path) -> int:
    """Convertir un PDF en PDF/A.

    Utilise ocrmypdf sans appliquer d'OCR.

    Returns
    -------
    returncode: int
        0 si un fichier PDF/A a été produit, 1 sinon.
    """
    compl_proc = subprocess.run(
        ["ocrmypdf", "-l", "fra", "--skip-text", fp_pdf_in, fp_pdf_out], check=True
    )
    return compl_proc.returncode


def extract_text_from_pdf_image(
    fp_pdf_in: Path, fp_txt_out: Path, fp_pdf_out: Path
) -> int:
    """Extraire le texte d'un PDF image et convertir le fichier en PDF/A.

    Utilise ocrmypdf.

    Parameters
    ----------
    fp_pdf_in: Path
        Fichier PDF image à traiter.
    fp_txt_out: Path
        Fichier TXT produit, contenant le texte extrait par OCR.
    fp_pdf_out: Path
        Fichier PDF/A produit, incluant le texte océrisé.

    Returns
    -------
    returncode: int
        0 si deux fichiers PDF/A et TXT ont été produits, 1 sinon.
    """
    # appeler ocrmypdf pour produire 2 fichiers: PDF/A-2b (inc. OCR) + sidecar (txt)
    compl_proc = subprocess.run(
        ["ocrmypdf", "-l", "fra", "--sidecar", fp_txt_out, fp_pdf_in, fp_pdf_out],
        check=True,
    )
    return compl_proc.returncode


def extract_text_from_pdf_text(fp_pdf_in: Path, fp_txt_out: Path, page_break="") -> int:
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
    txt = page_break.join(pdf).strip()
    if txt:
        # stocker le texte dans un fichier .txt
        with open(fp_txt_out, "w") as f_txt:
            f_txt.write(txt)
        return 0
    else:
        # code d'erreur
        return 1


# TODO renommer: ingest_pdf_file() ? ou définir ingest_* au niveau d'un dossier incluant le fichier liste ?
# TODO redo-ocr quand le fichier source est mal océrisé par la source, ex: 99_AI-013-211300264-20220223-22_100-AI-1-1_1.pdf
# TODO utiliser les propriétés du PDF pour détecter les vrais PDF texte
def guess_pdf_type_and_extract_text(
    fp_pdf_in: Path,
    fp_pdf_out: Path,
    fp_txt_out: Path,
    exist_ok: bool = True,
    overwrite: bool = False,
) -> str:
    """Deviner le type de PDF (image ou texte) et extraire le texte.

    Si pdftotext renvoie du texte, le fichier est considéré PDF texte,
    sinon il est considéré PDF image et OCRisé avec ocrmypdf.
    Dans les deux cas, ocrmypdf est appelé pour créer un PDF/A.

    La version actuelle est: ocrmypdf 14.0.1 / Tesseract OCR-PDF 5.2.0
    (+ pikepdf 5.6.0).
    On utilise "-l fra" pour améliorer la reconnaissance de: "à", "è",
    "ê", apostrophe, "l'", "œ", "ô".

    Parameters
    ----------
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.
    fp_pdf_out: Path
        Chemin du fichier PDF converti en PDF/A (avec OCR le cas échéant).
    fp_txt_out: Path
        Chemin du fichier txt contenant le texte extrait.
    exist_ok: bool, defaults to True
        Si True, ignore les fichiers en entrée pour lesquels les fichiers de
        sortie fp_pdf_out et fp_pdf_out existent déjà.
    overwrite: bool, defaults to False
        Si True, retraite le fichier d'entrée et écrase les fichiers de sortie s'ils existent.

    Returns
    -------
    text_extractor: str
        Extracteur utilisé pour le texte: "ocrmypdf" ou "pdftotext {version}"
    """
    if fp_pdf_out.is_file() and fp_txt_out.is_file():
        if not exist_ok:
            # émettre une erreur et sortir de la fonction
            logging.error(
                f"Les fichiers {fp_pdf_out} et {fp_txt_out} existent déjà mais `exist_ok=False`."
            )
        elif not overwrite:
            # émettre un warning et sortir de la fonction
            # TODO comparer les versions d'ocrmypdf/tesseract/pikepdf dans les métadonnées du PDF de sortie et les versions actuelles des dépendanecs, et si pertinent émettre un message proposant de ré-analyser le PDF ?
            logging.warning(
                f"Pas de traitement pour {fp_pdf_in} car les fichiers de sortie {fp_pdf_out} et {fp_txt_out} existent déjà et `overwrite=False`."
            )
            return
    # 1. ouvrir le fichier PDF avec pdftotext
    retcode = extract_text_from_pdf_text(fp_pdf_in, fp_txt_out)
    if retcode == 0:
        # 2. si du texte a pu être extrait directement, alors c'est un PDF texte
        logging.warning(f"PDF texte: {fp_pdf_in}")
        # convertir le PDF (texte) en PDF/A-2b (parallélisme des traitements)
        convert_pdf_to_pdfa(fp_pdf_in, fp_pdf_out)
        return f"pdftotext {PDFTOTEXT_VERSION}"
    else:
        # sinon c'est un PDF image
        # ex: RAW_PDF_DIR / "99_AR-013-211300025-20220128-A_2022_136-AR-1-1_1.pdf"
        logging.warning(f"PDF image: {fp_pdf_in}")
        # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
        extract_text_from_pdf_image(fp_pdf_in, fp_txt_out, fp_pdf_out)
        return f"ocrmypdf {OCRMYPDF_VERSION}"


def get_pdf_info(fp_pdf_in: Path) -> dict:
    """Renvoie les infos du PDF.

    Les infos sont fournies par poppler, elles incluent "Creator" et "Producer".

    Parameters
    ----------
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.

    Returns
    -------
    infos: dict
        Dictionnaire contenant les infos du PDF.
    """
    doc = load_from_file(fp_pdf_in)  # poppler
    # métadonnées: https://cbrunet.net/python-poppler/usage.html#document-properties ;
    # infos() ne les renvoie pas toutes, et nous fixons ici l'ordre des champs
    infos = {
        "filename": fp_pdf_raw.name,  # nom du fichier
        "nb_pages": doc.pages,  # nombre de pages
        "producer": doc.producer,
        "creator": doc.creator,
        "creation_date": doc.creation_date,
        "modification_date": doc.modification_date,
    }
    return infos


if __name__ == "__main__":
    # TODO argparse
    # dossier contenant des PDF texte et image
    RAW_DATA_DIR = Path("../data/raw/")
    in_dir = "2022-03"
    if in_dir == "2022-03":
        RAW_PDF_DIR = RAW_DATA_DIR / "2022-03-08_export-actes/Export_@ctes_arretes_pdf"
    elif in_dir == "2022-04":
        RAW_PDF_DIR = (
            RAW_DATA_DIR
            / "2022-04-13_export-actes/extraction_actes_010122_130422_pdf/extraction_actes_pdf"
        )
    else:
        # attention, dossier très volumineux
        RAW_PDF_DIR = RAW_DATA_DIR / "Arretes_2018_2021" / "12_ArretesPDF_VdM"
    # TODO --resume: passer les fichiers déjà traités, ajouter les nouveaux fichiers aux CSV meta_raw et meta_interim
    # TODO --redo: forcer la réextraction du texte => overwrite
    redo = True
    # RESUME HERE
    # TODO détecter les conflits de noms entre fichiers dans les sous-dossiers de raw/ avant traitement et tri vers interim/
    # dossier contenant les PDF image OCRisés
    INT_DATA_DIR = Path("../data/interim")
    INT_PDF_DIR = INT_DATA_DIR / "pdf"
    INT_TXT_DIR = INT_DATA_DIR / "txt"
    #
    INT_PDF_DIR.mkdir(exist_ok=True)
    INT_TXT_DIR.mkdir(exist_ok=True)
    # fichier CSV contenant les métadonnées des documents d'origine
    RAW_METAS_CSV = INT_DATA_DIR / "doc_metas_raw.csv"
    # fichier CSV contenant les métadonnées des documents transformés
    INT_METAS_CSV = INT_DATA_DIR / "doc_metas_interim.csv"
    # end TODO argparse

    raw_doc_metas = []
    int_doc_metas = []
    for fp_pdf_raw in sorted(RAW_PDF_DIR.glob("*.[Pp][Dd][Ff]")):
        # métadonnées des fichiers PDF d'origine
        raw_doc_meta = get_pdf_info(fp_pdf_raw)
        raw_doc_metas.append(raw_doc_meta)
        # fichiers produits
        fp_pdf_mod = INT_PDF_DIR / fp_pdf_raw.name
        fp_txt = INT_TXT_DIR / (fp_pdf_raw.stem + ".txt")
        # TODO déterminer si un document est PDF texte ou PDF image à partir des champs "Creator" et/ou "Producer" extraits par poppler,
        # plutôt que si pdftotext parvient à extraire du texte ?
        # Impact: ré-OCRisation des documents (mal) OCRisés, si on force (avec un warning)
        # extraire le texte si nécessaire, corriger et convertir le PDF d'origine en PDF/A-2b
        text_extractor = guess_pdf_type_and_extract_text(
            fp_pdf_raw, fp_pdf_mod, fp_txt, exist_ok=True, overwrite=redo
        )
        # métadonnées des fichiers PDF produits
        int_doc_meta = get_pdf_info(fp_pdf_mod)
        int_doc_meta["text_extractor"] = text_extractor
        int_doc_metas.append(int_doc_meta)
    # sauvegarder dans un fichier CSV les métadonnées des fichiers PDF en entrée: nom du fichier, nombre de pages, créateur, producteur
    df_raw_metas = pd.DataFrame(raw_doc_metas)
    df_raw_metas.to_csv(RAW_METAS_CSV, index=False)
    # sauvegarder dans un fichier CSV les métadonnées des fichiers PDF produits
    df_int_metas = pd.DataFrame(int_doc_metas)
    df_int_metas.to_csv(INT_METAS_CSV, index=False)
    # TODO tester si (1) la sortie de pdftotext et (2) le sidecar (sur des PDF différents) sont globalement formés de façon similaire
    # pour valider qu'on peut appliquer les mêmes regex/patterns d'extraction, ou s'il faut prévoir des variantes
    # TODO stocker les métadonnées d'extraction (au moins colonnes, éventuellement table dédiée) incluant
    # notamment ocrmypdf ou pdftotext (et les params?)

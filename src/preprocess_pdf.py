"""Prétraiter les fichiers PDF fournis en entrée, pour en extraire le texte.

Le texte est extrait avec pdftotexte pour les fichiers PDF texte, et ocrmypdf
pour les fichiers PDF image.
"""

# TODO tester l'appel direct à ocrmypdf par API python
# TODO tester "--clean" sur plusieurs PDF (aucun gain sur le pdf de test)
# TODO ajuster le logging, remplacer des warning() par info()
# TODO logger la sortie de ocrmypdf pour les messages sur les métadonnées
# (ex: "Some input metadata could not be copied because it is not permitted in PDF/A. You may wish to examine the output PDF's XMP metadata.")
# ou l'extraction (ex: "9 [tesseract] lots of diacritics - possibly poor OCR")

# alternatives testées sur les PDF image OCRisés:
# * pdftotext (xpdf/poppler) mélange le texte (comparé au fichier "sidecar" de ocrmypdf)
# * pdf2txt (pdfminer) mélange le texte (idem)
# * pdfplumber introduit des espaces et lignes superflus

import argparse
from importlib.metadata import version  # pour récupérer la version de pdftotext
import logging
from multiprocessing.sharedctypes import Value
from pathlib import Path
import subprocess
from typing import Dict, List, Tuple

import pandas as pd
from poppler import load_from_file
import pdftotext

# version des bibliothèques d'extraction de contenu des PDF texte et image
PDFTOTEXT_VERSION = version("pdftotext")
OCRMYPDF_VERSION = (
    subprocess.run(["ocrmypdf", "--version"], capture_output=True)
    .stdout.decode()
    .strip()
)

# chemins par défaut, arborescence cookiecutter
RAW_DATA_DIR = Path("../data/raw/")  # ici: entrée
INT_DATA_DIR = Path("../data/interim")  # ici: sortie

# lots connus: dossiers contenant des PDF texte et image
RAW_BATCHES = {
    "2022-03": RAW_DATA_DIR / "2022-03-08_export-actes/Export_@ctes_arretes_pdf",
    "2022-04": (
        RAW_DATA_DIR
        / "2022-04-13_export-actes/extraction_actes_010122_130422_pdf/extraction_actes_pdf"
    ),
    # attention, dossier très volumineux
    "2018-2021-VdM": RAW_DATA_DIR / "Arretes_2018_2021" / "12_ArretesPDF_VdM",
}


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
        "filename": fp_pdf_in.name,  # nom du fichier
        "nb_pages": doc.pages,  # nombre de pages
        "producer": doc.producer,
        "creator": doc.creator,
        "creation_date": doc.creation_date,
        "modification_date": doc.modification_date,
    }
    return infos


def preprocess_pdf_file(
    fp_pdf_in: Path,
    fp_pdf_out: Path,
    fp_txt_out: Path,
) -> Tuple[Dict, Dict]:
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

    Returns
    -------
    doc_meta_in: dict
        Métadonnées du fichier PDF d'entrée
    doc_meta_out: dict
        Métadonnées des fichiers PDF et TXT de sortie
    """
    # 1. lire les métadonnées du PDF en entrée
    doc_meta_in = get_pdf_info(fp_pdf_in)
    # 2. ouvrir le fichier PDF avec pdftotext
    retcode = extract_text_from_pdf_text(fp_pdf_in, fp_txt_out)
    # 3. si du texte a pu être extrait directement, alors c'est un PDF texte,
    # sinon c'est un PDF image
    # TODO utiliser les propriétés du PDF pour détecter les vrais PDF texte
    pdf_type = "pdf_txt" if retcode == 0 else "pdf_img"
    if pdf_type == "pdf_txt":
        # convertir le PDF (texte) en PDF/A-2b (parallélisme des traitements)
        logging.warning(f"PDF texte: {fp_pdf_in}")
        convert_pdf_to_pdfa(fp_pdf_in, fp_pdf_out)
        # mémoriser la bibliothèque utilisée et sa version
        text_extractor = f"pdftotext {PDFTOTEXT_VERSION}"
    else:
        # extraire le texte par OCR et convertir le PDF (image) en PDF/A-2b
        logging.warning(f"PDF image: {fp_pdf_in}")
        extract_text_from_pdf_image(fp_pdf_in, fp_txt_out, fp_pdf_out)
        # mémoriser la bibliothèque utilisée et sa version
        text_extractor = f"ocrmypdf {OCRMYPDF_VERSION}"
    # 6.
    doc_meta_out = get_pdf_info(fp_pdf_out)
    doc_meta_out["text_extractor"] = text_extractor
    return doc_meta_in, doc_meta_out


# TODO redo='all'|'ocr'|'none' ? 'ocr' pour ré-extraire le texte quand le fichier source est mal océrisé par la source, ex: 99_AI-013-211300264-20220223-22_100-AI-1-1_1.pdf
# TODO traiter également le fichier liste CSV s'il existe?
def ingest_folder(
    in_dir: Path, out_dir_pdf: Path, out_dir_txt: Path, redo: bool = False
) -> Tuple[List[Dict[str, str | int]], List[Dict[str, str | int]]]:
    """Ingérer un dossier: convertir les PDF en PDF/A et extraire le texte.

    Parameters
    ----------
    in_dir: Path
        Dossier à traiter, contenant des PDF
    out_dir_pdf: Path
        Dossier de sortie pour les PDF/A.
    out_dir_txt: Path
        Dossier de sortie pour les fichiers texte.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.

    Returns
    -------
    metas_raw: List[Dict[str, str | int]]
        Métadonnées des fichiers d'entrée.
    metas_int: List[Dict[str, str | int]]
        Métadonnées des fichiers produits: PDF et TXT.
    """
    # lister les PDFs dans le dossier à traiter
    pdfs_in = sorted(in_dir.glob("*.[Pp][Dd][Ff]"))
    #
    metas_raw = []
    metas_int = []
    for fp_pdf_in in pdfs_in:
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
        # TODO déterminer si un document est PDF texte ou PDF image à partir des champs "Creator" et/ou "Producer" extraits par poppler,
        # plutôt que si pdftotext parvient à extraire du texte ? alors si redo='ocr', ré-OCRisation des documents (mal) OCRisés (avec un warning.info)
        #
        # extraire le texte si nécessaire, corriger et convertir le PDF d'origine en PDF/A-2b
        doc_meta_in, doc_meta_out = preprocess_pdf_file(fp_pdf_in, fp_pdf_out, fp_txt)
        # métadonnées des fichiers PDF en entrée et sortie
        metas_raw.append(doc_meta_in)
        metas_int.append(doc_meta_out)
    return metas_raw, metas_int


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_dir", help="Nom du lot dans data/raw, ou chemin vers le dossier"
    )
    parser.add_argument(
        "--out_dir",
        default=str(INT_DATA_DIR),
        help="Chemin vers le dossier de sortie contenant les PDF-A et le texte extrait",
    )
    parser.add_argument(
        "--redo", action="store_true", help="Ré-exécuter le traitement d'un lot"
    )
    args = parser.parse_args()

    # entrée: lot connu ou chemin vers un dossier
    if args.in_dir in RAW_BATCHES:
        # nom de lot connu
        in_dir = RAW_BATCHES[args.in_dir]
        if not in_dir.is_dir():
            raise ValueError(f"Le lot {args.in_dir} n'est pas à l'emplacement {in_dir}")
    else:
        # chemin vers un dossier (nouveau lot?)
        in_dir = Path(args.in_dir).resolve()
        if not in_dir.is_dir():
            raise ValueError(f"Le dossier {in_dir} n'existe pas")

    # sortie: dossiers pour PDF-A et TXT
    out_dir = Path(args.out_dir).resolve()
    out_pdf_dir = out_dir / "pdf"
    out_txt_dir = out_dir / "txt"
    # on les crée si besoin
    out_pdf_dir.mkdir(exist_ok=True)
    out_txt_dir.mkdir(exist_ok=True)
    # fichier CSV contenant les métadonnées des documents d'origine
    CSV_METAS_RAW = out_dir / "metas_raw.csv"
    # fichier CSV contenant les métadonnées des documents transformés
    CSV_METAS_INT = out_dir / "metas_interim.csv"

    # TODO détecter les conflits de noms entre fichiers dans les sous-dossiers de raw/ avant traitement et tri vers interim/
    #
    # traiter le dossier, contenant les PDF image OCRisés
    metas_raw, metas_int = ingest_folder(
        in_dir, out_pdf_dir, out_txt_dir, redo=args.redo
    )

    # sauvegarder dans un fichier CSV les métadonnées des fichiers PDF en entrée: nom du fichier, nombre de pages, créateur, producteur
    df_metas_raw_new = pd.DataFrame(metas_raw)
    if CSV_METAS_RAW.is_file():
        # charger le fichier existant et concaténer les anciennes et nouvelles entrées
        df_metas_raw_old = pd.read_csv(CSV_METAS_RAW)
        df_metas_raw = pd.concat([df_metas_raw_old, df_metas_raw_new])
    else:
        df_metas_raw = df_metas_raw_new
    df_metas_raw.to_csv(CSV_METAS_RAW, index=False)

    # sauvegarder dans un fichier CSV les métadonnées des fichiers PDF produits, ainsi que les métadonnées d'extraction,
    # incluant notamment la version d'ocrmypdf ou pdftotext
    # TODO stocker aussi les paramètres d'appel de ces libs?
    df_metas_int_new = pd.DataFrame(metas_int)
    if CSV_METAS_INT.is_file():
        # charger le fichier existant et concaténer les anciennes et nouvelles entrées
        df_metas_int_old = pd.read_csv(CSV_METAS_INT)
        df_metas_int = pd.concat([df_metas_int_old, df_metas_int_new])
    else:
        df_metas_int = df_metas_int_new
    df_metas_int.to_csv(CSV_METAS_INT, index=False)

    # TODO tester si (1) la sortie de pdftotext et (2) le sidecar (sur des PDF différents) sont globalement formés de façon similaire
    # pour valider qu'on peut appliquer les mêmes regex/patterns d'extraction, ou s'il faut prévoir des variantes

"""Extrait le texte natif des fichiers PDF avec pdftotext

<https://github.com/jalan/pdftotext>

Dépendances Windows (<https://github.com/jalan/pdftotext#os-dependencies>):
* Microsoft Visual C++ Build Tools: <https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/>
* poppler ( `conda install -c conda-forge poppler` )
"""

from importlib.metadata import version  # pour récupérer la version de pdftotext
from pathlib import Path
import unicodedata

import pdftotext

# version des bibliothèques d'extraction de contenu des PDF texte et image
PDFTOTEXT_VERSION = version("pdftotext")


def extract_native_text_pdftotext(
    fp_pdf_in: Path, fp_txt_out: Path, page_beg: int, page_end: int
) -> int:
    """Extrait le texte natif d'un PDF avec pdftotext.

    Si le texte extrait par pdftotext n'est pas vide alors un fichier TXT est produit,
    sinon aucun fichier TXT n'est produit et un code d'erreur est renvoyé.

    Les pages sont séparées par un "form feed" ("\x0c", "\f" en python).

    Le texte est normalisé en forme NFC (NEW 2023-03-10, NFC plutôt que NFKC car ce dernier transforme "º" en "o").

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

    Returns
    -------
    returncode: int
        0 si un fichier TXT a été produit, 1 sinon.
    """
    # les numéros de page commencent à 1, mais pdftotext crée une liste de pages
    # qui commence à l'index 0
    page_beg_ix = page_beg - 1
    # le numéro de la dernière page ne doit pas être décalé car la borne sup d'un slice est exclue
    # page_end_ix = page_end

    with open(fp_pdf_in, "rb") as f:
        pdf = pdftotext.PDF(f)

    # pdftotext.PDF a getitem(), mais ne permet pas de récupérer un slice
    # donc il faut créer un range et itérer manuellement
    doc_txt = [pdf[i] for i in range(page_beg_ix, page_end)]
    # chaque page produite par pdftotext se termine par "\f",
    # il faut enlever le dernier "\f" pour avoir la même
    # structure qu'en sortie d'ocrmypdf
    assert doc_txt[-1][-1] == "\f"
    doc_txt[-1] = doc_txt[-1][:-1]
    # concaténer le texte des pages
    txt = "".join(doc_txt)  # .strip() ?

    # normaliser le texte extrait en forme NFC
    norm_txt = unicodedata.normalize("NFC", txt)
    #
    if norm_txt:
        # stocker le texte dans un fichier .txt
        with open(fp_txt_out, "w") as f_txt:
            f_txt.write(norm_txt)
        # code ok
        return 0
    else:
        # code d'erreur
        return 1

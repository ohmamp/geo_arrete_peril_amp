"""
# Extrait le texte natif des fichiers PDF avec pdfminer.six

Nécessite d'installer pdfminer.six.

Non utilisé pour le moment, faute d'avoir identifié les bonnes valeurs des paramètres
utilisés pour l'analyse du layout, mais pourrait être utile pour ré-analyser les
arrêtés de certaines communes avec une mise en page compliquée.
"""

from pathlib import Path
import unicodedata


from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams


# <https://pdfminersix.readthedocs.io/en/latest/reference/composable.html?highlight=laparams#laparams>
LAPARAMS = LAParams(char_margin=10.0, word_margin=4.0, boxes_flow=None)
# - "char_margin=10.0" (def: 2.0) permet de garder en une seule ligne,
# donc un seul bloc, les mots très espacés comme dans certains arrêtés de
# la ville de Marseille: "Article 1      Pour des raisons..."
# char_margin=4.0 semble suffire pour "1 bis, rue d'Isoard 13001.pdf" ;
# char_margin=10.0 pour "10 bd de Letz 13015.pdf" (mais à analyser plutôt comme un tableau?)
# TODO tester d'autres valeurs de char_margin, contrôler qu'on ne perd pas
# ailleurs ce qu'on gagne sur quelques arrêtés
#
# - "word_margin=4.0" (def: 0.1) permet de garder un seul mot malgré de petites
# variations d'écartement entre caractères
# word_margin=4.0 pour "10 bd de Letz 13015.pdf"
#
# - "boxes_flow=None" désactive la détection automatique avancée du layout
# Sinon, le texte extrait des arrêtés de la ville de Marseille contient
# la suite d'intitulés "Article 1", "Article 2" (etc) d'une page, car ils
# sont en colonne à gauche, puis le texte des articles 1, 2 (etc).
# TODO tester d'autres valeurs de boxes_flow ? [-1.0 ; 1.0], def: 0.5
#
# TODO si on veut récupérer le texte des tampons d'actes sur les arrêtés où
# ceux-ci sont ajoutés dans un encart en surcouche, il faut a priori utiliser
# "all_texts=True" (à tester)


def extract_native_text_pdfminer(
    fp_pdf_in: Path, fp_txt_out: Path, page_beg: int, page_end: int
) -> int:
    """Extrait le texte natif d'un PDF avec pdfminer.six.

    Si le texte extrait par pdfminer.six n'est pas vide alors un fichier TXT est produit,
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
    # pages à extraire
    # les numéros de page commencent à 1, mais pdftotext crée une liste de pages
    # qui commence à l'index 0
    page_beg_ix = page_beg - 1
    # le numéro de la dernière page ne doit pas être décalé car la borne sup d'un slice est exclue
    # page_end_ix = page_end
    page_numbers = list(range(page_beg_ix, page_end))

    # TODO vérifier que le texte contient bien "\f" en fin de page
    txt = extract_text(fp_pdf_in, page_numbers=page_numbers, laparams=LAPARAMS)
    # codec="utf-8" ? "latin-1"?
    # with open(fp_pdf_in, "rb") as f, open(fp_txt_out, "w") as f_txt:
    #     extract_text_to_fp(f, f_txt, page_numbers=page_numbers, output_type="text")

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

"""Charger les fichiers de texte extraits des PDF, natifs ou non.

"""

from pathlib import Path
from typing import List


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

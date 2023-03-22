"""Analyse un arrêté et en extrait les données.

"""

import logging
from pathlib import Path

from src.domain_knowledge.actes import P_ACCUSE
from src.process.parse_doc import parse_arrete_pages
from src.utils.txt_format import load_pages_text


def parse_arrete(fp_pdf_in: Path, fp_txt_in: Path) -> list:
    """Analyse un arrêté et extrait les données qu'il contient.

    L'arrêté est découpé en paragraphes puis les données sont
    extraites.

    Parameters
    ----------
    fp_pdf_in: Path
        Fichier PDF source (temporairement?)
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    doc_data: dict
        Données extraites du document.
    """
    pages = load_pages_text(fp_txt_in)
    if not any(pages):
        logging.warning(f"{fp_txt_in}: aucune page de texte")
        return {}

    # filtrer les pages qui sont à sortir du traitement:
    # - la ou les éventuelles pages d'accusé de réception d'actes
    pages_ar = [i for i, x in enumerate(pages, start=1) if P_ACCUSE.match(x)]
    if pages_ar:
        logging.warning(
            f"{fp_txt_in}: {len(pages_ar)} page(s) d'accusé de réception actes: {pages_ar} (sur {len(pages)})"
        )
    # - la ou les éventuelles pages d'annexes ? (TODO)
    skip_pages = pages_ar
    # remplacer les pages filtrées par une chaîne vide
    filt_pages = [
        (x if i not in skip_pages else "") for i, x in enumerate(pages, start=1)
    ]

    # analyser la structure des pages
    fn_pdf = fp_pdf_in.name  # FIXME temporaire?
    doc_content = parse_arrete_pages(fn_pdf, filt_pages)

    # extraire les données
    doc_data = {}

    # - au préalable, rassembler toutes les données en ajoutant le numéro de page (FIXME)
    pages_body = [pg_cont["body"] for pg_cont in doc_content]
    # pages_cont = [pg_cont["content"] for pg_cont in doc_content]  # future
    pages_cont = []
    for pg_num, pg_cont in enumerate(doc_content, start=1):
        # pg_template = page_cont["template"]
        pg_txt_body = pg_cont["body"]
        # pg_content = page_cont["content"]  # future
        # FIXME ajouter "page_num" en amont, dans parse_arrete_pages()
        pages_cont.extend([({"page_num": pg_num} | x) for x in pg_cont["content"]])

    # extraire les champs un par un:
    # - commune via les mentions de l'autorité prenant l'arrêté
    adr_commune_maire = [x for x in pages_cont if x["span_typ"] == "adr_ville"]
    print(adr_commune_maire)
    # RESUME HERE
    return doc_data

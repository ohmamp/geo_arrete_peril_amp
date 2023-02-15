"""Analyse le document dans son ensemble.

Extrait des empans de texte correspondant aux en-têtes, pieds-de-page,
autorité, vus, correspondants, articles, signature...
"""

from pathlib import Path
import re

import pandas as pd  # tableau récapitulatif des extractions

from doc_template import P_HEADER, P_FOOTER
from text_structure import (
    RE_MAIRE_COMMUNE,
    M_MAIRE_COMMUNE,
    RE_VU,
    M_VU,
    RE_CONSIDERANT,
    M_CONSIDERANT,
)

# type de données des colonnes du fichier CSV résultat
DTYPE_PARSES = {
    # doc
    "filename": "string",
    # page
    "page_num": "int64",
    # pour chaque empan repéré: position et texte
    "span_beg": "int64",
    "span_end": "int64",
    "span_txt": "string",
    "span_typ": "string",  # header, footer, ...  # TODO ensemble fermé?
}


# Marseille: PDF texte, dans lesquels les articles du code de la construction et de l'habitation sont ajoutés en annexe
# *sous forme d'images*


def parse_page(txt: str) -> dict:
    """Analyse une page.

    Repère l'en-tête et le pied-de-page.

    Parameters
    ----------
    txt: str
        Texte d'origine de la page.

    Returns
    -------
    content: dict
        Contenu structuré de la page.
    """
    content = []

    # en-tête
    # TODO expectation: n=0..2 par page
    if m_headers := P_HEADER.finditer(txt):
        for match in m_headers:
            content.append(
                {
                    "span_beg": match.span()[0],
                    "span_end": match.span()[1],
                    "span_txt": match.group(0),
                    "span_typ": "header",
                }
            )

    # pied-de-page
    # TODO expectation: n=0..2 par page
    if m_footers := P_FOOTER.finditer(txt):
        for match in m_footers:
            content.append(
                {
                    "span_beg": match.span()[0],
                    "span_end": match.span()[1],
                    "span_txt": match.group(0),
                    "span_typ": "footer",
                }
            )

    # corps du texte
    body_beg = max(
        list(x["span_end"] for x in content if x["span_typ"] == "header"), default=0
    )
    body_end = min(
        list(x["span_beg"] for x in content if x["span_typ"] == "footer"),
        default=len(txt),
    )
    # si l'en-tête et le pied de page ne devaient pas nécessairement aller jusqu'aux limites, on aurait:
    # clean_txt = txt[:header_beg] + txt[header_end:footer_beg] + txt[footer_end:]
    content.append(
        {
            "span_beg": body_beg,
            "span_end": body_end,
            "span_txt": txt[body_beg:body_end],
            "span_typ": "body",
        }
    )
    return content


def parse_arrete(fp_txt_in: Path) -> list:
    """Analyse un arrêté pour le découper en zones.

    Parameters
    ----------
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    doc_content: List[dict]
        Contenu du document, par page découpée en zones de texte.
    """
    print(fp_txt_in.name)  # DEBUG
    # ouvrir le fichier
    with open(fp_txt_in) as f:
        txt = f.read()
    doc_content = []  # valeur de retour
    # métadonnées du document
    mdata_doc = {
        "filename": fp_txt_in.name,
    }
    # traiter les pages
    pages = txt.split("\f")
    for i, page in enumerate(pages, start=1):
        mdata_page = mdata_doc | {"page_num": i}
        page_content = mdata_page | {"content": parse_page(page)}
        doc_content.append(page_content)
    return doc_content
    # WIP
    m_preambule = P_PREAMBULE.search(txt)
    if m_preambule is not None:
        print(fp_txt_in.name, "\tPREAMBULE ", m_preambule)
    else:
        for line in txt.split("\n"):
            m_autorite = M_MAIRE_COMMUNE.match(line)
            if m_autorite is not None:
                print(fp_txt_in.name, "\tAUTORITE  ", m_autorite)
                break
        else:
            raise ValueError(f"{fp_txt_in.name}")
    # end WIP
    # chercher le point de référence "ARRETE|ARRÊTE|ARRÊTONS"
    m_arrete = P_ARRETE.search(txt)
    if m_arrete is not None:
        content["arrete"] = m_arrete.groups()
    else:
        print(repr(txt))
        raise ValueError(f"{fp_txt_in.name}:\t !?")
    # avant ARRETE, on trouve l'en-tête, l'objet, l'autorité, les "vu" et les "considérant"
    # entete
    # objet
    # autorite
    m_autorite = M_MAIRE_COMMUNE.search(txt)
    if m_autorite is not None:
        content["autorite"] = m_autorite.group(0)
    # vus
    m_vu = P_VU.findall(txt)
    content["vu"] = m_vu
    # considerants
    m_considerant = P_CONSIDERANT.findall(txt)
    content["considerant"] = m_considerant
    if not m_considerant:
        if fp_txt_in.name not in (
            "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).txt",  # mainlevée => optionnel ?
            "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.txt",  # mainlevée => optionnel ?
        ):
            raise ValueError(fp_txt_in.name)
    # articles
    # pieddepage
    return content


if __name__ == "__main__":
    # TODO argparse
    INT_TXT_DIR = Path("../data/interim/txt")
    CSV_PARSES = Path("../data/interim") / "parses.csv"
    # stocker les champs extraits dans un tableau
    parses = []
    for fp_txt in sorted(INT_TXT_DIR.glob("*.txt")):
        content = parse_arrete(fp_txt)
        parses.extend(content)
    df_parses = pd.DataFrame(parses)
    # on force les types de colonnes (impossible dans le constructeur...)
    df_parses = df_parses.astype(DTYPE_PARSES)
    # TODO tests: dropna() puis:
    # assert header_beg == 0
    # alt: assert txt[:header_beg] == ""
    # assert footer_end == len(txt)
    # alt: assert txt[footer_end:] == ""
    df_parses.to_csv(CSV_PARSES, index=False)

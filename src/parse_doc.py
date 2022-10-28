"""Analyse le document dans son ensemble.

Découpe l'arrêté en zones.
"""

from pathlib import Path
import re

import pandas as pd  # tableau récapitulatif des extractions

# type de données des colonnes du fichier CSV résultat
DTYPE_PARSES = {
    # doc
    "filename": "string",
    "page_num": "int64",
    # en-tête
    # les index de string sont des entiers, peuvent être manquants
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/integer_na.html
    "header_beg": "Int64",
    "header_end": "Int64",
    "txt_header": "string",
    # pied-de-page
    "footer_beg": "Int64",
    "footer_end": "Int64",
    "txt_footer": "string",
    # corps
    "txt_body": "string",
}

# en-tête et pied-de-page

# Aix-en-Provence
# TODO en-tête p. 2 et suivantes: numéro de page (en haut à droite)
RE_FOOTER_AIX = r"""
Hotel[ ]de[ ]Ville[ ]13616[ ]AIX-EN-PROVENCE[ ]CEDEX[ ]1[ ]-[ ]France[ ]-
[ ]Tél[.][ ][+][ ]33[(]0[)]4[.]42[.]91[.]90[.]00[ ]-
[ ]Télécopie[ ][+][ ]33[(]0[)]4[.]42[.]91[.]94[.]92[ ]-
[ ]www[.]mairie[-]aixenprovence[.]fr
[.]
"""

# Allauch
# TODO en-tête p. 2..
# pied-de-page p. 1
RE_FOOTER_ALLAUCH = r"""
Hôtel[ ]de[ ]Ville[ ][+][ ]Place[ ]Pierre[ ]Bellot[ ]e[ ]BP[ ]27[ ][+][ ]13718[ ]Allauch[ ]cedex[ ]e
[ ]Tél[.][ ]04[ ]91[ ]10[ ]48[ ]00[ ][+]
[ ]Fax[ ]04[ ]91[ ]10[ ]48[ ]23
\nWeb[ ][:][ ]http[:]//www[.]allauch[.]com[ ][+]
[ ]Courriel[ ][:][ ]info@allauch[.]com
"""
# TODO pied-de-page p. 2..
# TODO

RE_FOOTER_AUBAGNE = r"""
Hôtel[ ]de[ ]Ville[ ]BP[ ]41465[ ]13785[ ]Aubagne[ ]Cedex
[ ]T[ ]?04[ ]?42[ ]?18[ ]?19[ ]?19
[ ]F[ ]?04[ ]?42[ ]?18[ ]?18[ ]?18
[ ]www[.]aubagne[.]fr
"""

RE_FOOTER_AURIOL = r"""
(Certifié[ ]exécutoire[,][ ]compte[ ]tenu[ ]de[ ]la[ ]transmission[ ]en[ ]Préfecture[ ]et[ ]de[ ]la[ ]publication[ ]le[ ][:][ ]\d{2}/\d{2}/\d{4}[ ])?
Page[ ]\d{1,2}[ ]sur[ ]\d{1,2}
"""

# Châteauneuf-les-Martigues: en-tête sur p. 1, puis rien
# FIXME modifier si on refait l'OCR
RE_HEADER_CHATEAUNEUF_LES_MARTIGUES = r"""
Gommune[ ]de[ ]Châteauneuf-les-Martigues[ ]-[ ]Arrondissement[ ]d'lstres[ ]-[ ]Bouches[ ]du[ ]Rhône
"""

RE_HEADER_GARDANNE = r"""
Arrêté[ ]n°\d{4}-\d{2}-ARR-SIHI[ ]Page[ ]\d{1,2}/\d{1,2}
"""
# Gardanne: pas de footer

# TODO RE_FOOTER_ISTRES

RE_FOOTER_MARSEILLE = r"""
Ville[ ]de[ ]Marseille[,][ ]2[ ]quai[ ]du[ ]Port[ ][–][ ]13233[ ]MARSEILLE[ ]CEDEX[ ]20
"""
# Marseille: PDF texte, dans lesquels les articles du code de la construction et de l'habitation sont ajoutés en annexe
# *sous forme d'images*

RE_HEADER = (
    r"(?P<header>"
    + r"|".join(
        r"(" + x + r")"
        for x in [
            RE_HEADER_CHATEAUNEUF_LES_MARTIGUES,
            RE_HEADER_GARDANNE,
        ]
    )
    + r")"
)
P_HEADER = re.compile(RE_HEADER, flags=re.MULTILINE | re.VERBOSE)

RE_FOOTER = (
    r"(?P<footer>"
    + r"|".join(
        r"(" + x + r")"
        for x in [
            RE_FOOTER_AIX,
            RE_FOOTER_ALLAUCH,
            RE_FOOTER_AUBAGNE,
            RE_FOOTER_AURIOL,
            RE_FOOTER_MARSEILLE,
        ]
    )
    + r"[^\f]*"
    + r")"
)
P_FOOTER = re.compile(RE_FOOTER, flags=re.MULTILINE | re.VERBOSE)

RE_AUTORITE = (
    r"\s*(?P<autorite>"
    + r"("
    + r"("
    + r"|".join(
        [
            r"(NOUS,[ ]MAIRE D')",  # AIX-EN-PROVENCE
            r"(Nous,[ ]Maire[ ]de[ ])",  # Marseille
            r"(NOUS,[ ](?P<autorite_nom>.*),[ ]Maire[ ]de[ ]la[ ]commune[ ]d')",  # Allauch
            r"(Le[ ]Maire[ ]de[ ]la[ ]Commune[ ]d['’])",  # ISTRES, Auriol, Aubagne (certains)
            r"(Le[ ]Maire[ ]de[ ]la[ ]Ville[ ]de[ ])",  # Châteauneuf-les-Martigues
            r"(Le[ ]Maire[ ]de[ ])",  # Gardanne
        ]
    )
    + r")"
    + r"(?P<commune>.+)"
    + r")"
    # + r"|(Le Maire)"  # fallback, utile pour certains arrêtés d'Aubagne
    + r")"
)
P_AUTORITE = re.compile(RE_AUTORITE, re.MULTILINE | re.VERBOSE)

RE_VU = r"^\s*(?P<vu>V[Uu][, ](.+))"
P_VU = re.compile(RE_VU, flags=re.MULTILINE | re.VERBOSE)

RE_CONSIDERANT = r"^\s*(?P<considerant>(Considérant|CONSIDERANT)[, ](.+))"
P_CONSIDERANT = re.compile(RE_CONSIDERANT, flags=re.MULTILINE | re.VERBOSE)

RE_ARRETE = r"^\s*(ARR[ÊE]TE|ARR[ÊE]TONS)"
P_ARRETE = re.compile(RE_ARRETE, flags=re.MULTILINE | re.VERBOSE)

RE_PREAMBULE = r"""
{re_autorite}\n
(^\s*$)*
""".format(
    re_autorite=RE_AUTORITE
)
P_PREAMBULE = re.compile(RE_PREAMBULE, flags=re.MULTILINE | re.VERBOSE)


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
    content = {}

    # en-tête
    m_header = P_HEADER.search(txt)
    if m_header:
        header_beg, header_end = m_header.span()
        txt_header = m_header.group(0)
    else:
        header_beg, header_end = (None, None)
        txt_header = None
    content["header_beg"] = header_beg
    content["header_end"] = header_end
    content["txt_header"] = txt_header

    # pied-de-page
    m_footer = P_FOOTER.search(txt)
    if m_footer:
        footer_beg, footer_end = m_footer.span()
        txt_footer = m_footer.group(0)
    else:
        footer_beg, footer_end = (None, None)
        txt_footer = None
    content["footer_beg"] = footer_beg
    content["footer_end"] = footer_end
    content["txt_footer"] = txt_footer

    # corps du texte
    # si l'en-tête et le pied de page ne devaient pas nécessairement aller jusqu'aux limites, on aurait:
    # clean_txt = txt[:header_beg] + txt[header_end:footer_beg] + txt[footer_end:]
    content["txt_body"] = txt[header_end:footer_beg]

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
        page_content = mdata_page | parse_page(page)
        doc_content.append(page_content)
    return doc_content
    # WIP
    m_preambule = P_PREAMBULE.search(txt)
    if m_preambule is not None:
        print(fp_txt_in.name, "\tPREAMBULE ", m_preambule)
    else:
        for line in txt.split("\n"):
            m_autorite = P_AUTORITE.match(line)
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
    m_autorite = P_AUTORITE.search(txt)
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

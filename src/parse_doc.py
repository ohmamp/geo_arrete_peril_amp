"""Analyse le document dans son ensemble.

Extrait des empans de texte correspondant aux en-têtes, pieds-de-page,
autorité, vus, correspondants, articles, signature...
"""

from pathlib import Path
import re
from typing import Optional

import pandas as pd  # tableau récapitulatif des extractions

from actes import P_STAMP  # tampon
from cadre_reglementaire import parse_refs_reglement
from doc_template import P_HEADER, P_FOOTER  # en-tête et pied-de-page
from separate_pages import load_pages_text
from text_structure import (
    P_ARR_NUM,
    P_ARR_OBJET,
    P_MAIRE_COMMUNE,
    P_VU,
    P_VU_PAR,
    P_CONSIDERANT,
    P_CONSID_PAR,
    P_ARRETE,
    P_ARTICLE,
    P_ARTICLE_PAR,
    P_DATE_SIGNAT,
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


def parse_page_template(txt: str) -> tuple[list, str]:
    """Analyse une page pour repérer le template.

    Repère les en-têtes, pieds-de-page, tampons, et renvoie
    les empans correspondants, ainsi que le texte débarrassé
    de ces éléments de template.

    Parameters
    ----------
    txt: str
        Texte d'origine de la page.

    Returns
    -------
    content: list
        Liste d'empans repérés sur la page.
    txt_body: string
        Corps de texte, défini comme le texte en entrée
        dans lequel les empans d'en-têtes, pieds-de-page et tampons
        de `content` ont été effacés (remplacés par des espaces de
        même longueur).
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

    # tampon de transmission à actes
    if m_stamps := P_STAMP.finditer(txt):
        for match in m_stamps:
            m_beg, m_end = match.span()
            content.append(
                {
                    "span_beg": m_beg,
                    "span_end": m_end,
                    "span_txt": match.group(0),
                    "span_typ": "stamp",
                }
            )

    # corps du texte
    # défini comme le texte d'origine, dans lequel on a effacé les empans repérés
    # (en-têtes, pieds-de-page, tampons) ;
    # remplacer les empans par des espaces permet de conserver les indices d'origine
    # et éviter les décalages
    spans = list((x["span_beg"], x["span_end"]) for x in content)
    txt_body = txt[:]
    for sp_beg, sp_end in spans:
        txt_body = txt_body[:sp_beg] + " " * (sp_end - sp_beg) + txt_body[sp_end:]

    return content, txt_body


# motif pour capturer tout le texte sauf les espaces initiaux et finaux
RE_STRIP = r"""(?:\s*)(?P<outstrip>\S[\s\S]*?)(?:\s*)"""
P_STRIP = re.compile(RE_STRIP, re.IGNORECASE | re.MULTILINE)


def parse_doc_preamble(txt_body: str, pream_beg: int, pream_end: int) -> list[dict]:
    """Analyse le préambule d'un document, sur la 1re page, avant le 1er "Vu".

    Parameters
    ----------
    txt_body: string
        Corps de texte de la page à analyser
    pream_beg: int
        Début de l'empan à analyser.
    pream_end: int
        Fin de l'empan à analyser, correspondant au début du 1er "Vu".

    Returns
    -------
    content: list
        Liste d'empans de contenu
    """
    content = []
    # a. ce préambule se termine par l'intitulé de l'autorité prenant l'arrêté (obligatoire)
    if match := P_MAIRE_COMMUNE.search(txt_body, pream_beg, pream_end):
        # toute la zone reconnue
        span_beg, span_end = match.span()
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
                "span_txt": match.group(0),
                "span_typ": "par_autorite",
            }
        )
        autorite_beg = (
            span_beg  # la zone restant à traiter est avant cette zone d'autorité
        )
        # vérifier que la zone de l'autorité est bien en fin de préambule
        try:
            assert txt_body[span_end:pream_end].strip() == ""
        except AssertionError:
            print(txt_body[span_end:pream_end].strip())
            raise
        # stocker la donnée de la commune
        content.append(
            {
                "span_beg": match.start("commune"),
                "span_end": match.end("commune"),
                "span_txt": match.group("commune"),
                "span_typ": "adr_ville",  # TODO utiliser un autre nom pour éviter le conflit?
            }
        )
    else:
        # pas d'autorité détectée: anormal
        autorite_beg = pream_end
        raise ValueError(f"Pas d'autorité détectée !?\n{txt_body}")

    # b. ce préambule peut contenir le numéro de l'arrêté (si présent, absent dans certaines communes)
    if match := P_ARR_NUM.search(txt_body, pream_beg, autorite_beg):
        # marquer toute la zone reconnue (contexte + numéro de l'arrêté)
        span_beg, span_end = match.span()
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
                "span_txt": match.group(0),
                "span_typ": "par_arr_num",  # paragraphe contenant le numéro de l'arrêté
            }
        )
        # stocker le numéro de l'arrêté
        content.append(
            {
                "span_beg": match.start("arr_num"),
                "span_end": match.end("arr_num"),
                "span_txt": match.group("arr_num"),
                "span_typ": "arr_num",
            }
        )
        arr_num_end = span_end
    else:
        # pas de numéro d'arrêté (ex: Aubagne)
        arr_num_end = 0

    # c. entre les deux doit se trouver le titre ou objet de l'arrêté (obligatoire)
    if match := P_ARR_OBJET.search(txt_body, arr_num_end, autorite_beg):
        # stocker la zone reconnue
        content.append(
            {
                "span_beg": match.start(),
                "span_end": match.end(),
                "span_txt": match.group(0),
                "span_typ": "par_arr_nom",
            }
        )
        # stocker la donnée
        content.append(
            {
                "span_beg": match.start("arr_nom"),
                "span_end": match.end("arr_nom"),
                "span_txt": match.group("arr_nom"),
                "span_typ": "arr_nom",
            }
        )
    else:
        # hypothèse: sans marquage explicite comme "Objet:", le titre est tout le texte restant
        # dans cette zone (entre le numéro et l'autorité)
        if match := P_STRIP.fullmatch(txt_body, arr_num_end, autorite_beg):
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start(),
                    "span_end": match.end(),
                    "span_txt": match.group(0),
                    "span_typ": "par_arr_nom",
                }
            )
            # stocker la donnée
            content.append(
                {
                    "span_beg": match.start("outstrip"),
                    "span_end": match.end("outstrip"),
                    "span_txt": match.group("outstrip"),
                    "span_typ": "arr_nom",
                }
            )
        else:
            raise ValueError(
                f"Pas de texte trouvé pour le nom!?\n{txt_body[arr_num_end:autorite_beg]}"
            )

    print(content)  # WIP
    # TODO remplacer les zones reconnues par des espaces, et afficher le texte non-capturé?
    return content


def parse_doc_postamble(txt_body: str, pream_beg: int, pream_end: int) -> list[dict]:
    """Analyse le postambule d'un document, sur la dernière page (hors annexes).

    Le postambule correspond à la zone de signature: date, lieu éventuel et signataire.

    Parameters
    ----------
    txt_body: string
        Corps de texte de la page à analyser
    pream_beg: int
        Début de l'empan à analyser.
    pream_end: int
        Fin de l'empan à analyser, correspondant au début du 1er "Vu".

    Returns
    -------
    content: list
        Liste d'empans de contenu
    """
    content = []
    # a. extraire la date de signature
    if m_signature := P_DATE_SIGNAT.search(txt_body, pream_beg, pream_end):
        # stocker la zone reconnue
        content.append(
            {
                "span_beg": m_signature.start(),
                "span_end": m_signature.end(),
                "span_txt": m_signature.group(0),
                "span_typ": "par_sign_date",
            }
        )
        # stocker la donnée
        content.append(
            {
                "span_beg": m_signature.start("arr_date"),
                "span_end": m_signature.end("arr_date"),
                "span_txt": m_signature.group("arr_date"),
                "span_typ": "arr_date",
            }
        )
    # TODO b. extraire l'identité et la qualité du signataire? (eg. délégation de signature)
    #
    return content


def parse_page_content(
    txt_body: str, main_beg: int, main_end: int, latest_span: Optional[dict]
) -> list:
    """Analyse une page pour repérer les zones de contenus.

    Parameters
    ----------
    txt_body: string
        Corps de texte de la page à analyser
    main_beg: int
        Début de l'empan à analyser.
    main_end: int
        Fin de l'empan à analyser.
    latest_span: dict, optional
        Dernier empan de contenu repéré sur la page précédente.
        Vaut `None` pour la première page.

    Returns
    -------
    content: list
        Liste d'empans de contenu
    """
    content = []

    # repérer les débuts de paragraphes: "Vu", "Considérant", "Arrête", "Article"
    par_begs = (
        [(m.start(), "par_vu") for m in P_VU.finditer(txt_body, main_beg, main_end)]
        + [
            (m.start(), "par_considerant")
            for m in P_CONSIDERANT.finditer(txt_body, main_beg, main_end)
        ]
        + [
            (m.start(), "par_arrete")
            for m in P_ARRETE.finditer(txt_body, main_beg, main_end)
        ]
        + [
            (m.start(), "par_article")
            for m in P_ARTICLE.finditer(txt_body, main_beg, main_end)
        ]
    )
    # s'il y a du texte avant le 1er début de paragraphe, c'est la continuation du
    # dernier paragraphe de la page précédente ;
    # le mettre dans un empan de type span_typ + "_suite"
    if par_begs:
        nxt_beg, nxt_typ = par_begs[0]
    else:
        # aucun début de paragraphe détecté sur la page ; cela peut arriver lorsqu'un empan
        # court sur plusieurs pages, eg. un "Considérant" très long incluant la liste des
        # copropriétaires
        nxt_beg = main_end  # analyser jusqu'en bas de la page
        nxt_typ = None  # pas de prochain empan connu sur cette page
        # RESUME HERE vérifier qu'il y a bien un latest_span (et d'un type possible pour une continuation)
    if match := P_STRIP.fullmatch(txt_body, main_beg, nxt_beg):
        lst_typ = latest_span["span_typ"]
        # un empan peut courir sur plus d'une page complète (ex: "Considérant" très long, incluant la liste des copropriétaires)
        cur_typ = lst_typ if lst_typ.endswith("_suite") else lst_typ + "_suite"
        # stocker la zone reconnue
        content.append(
            {
                "span_beg": match.start(),
                "span_end": match.end(),
                "span_txt": match.group(0),
                "span_typ": cur_typ,
            }
        )
        if nxt_typ is not None:
            # vérifier que la transition autorisée est correcte
            # TODO déplacer cette vérification en amont ou en aval?
            assert (cur_typ, nxt_typ) in (
                ("par_vu_suite", "par_vu"),
                ("par_vu_suite", "par_considerant"),
                ("par_considerant_suite", "par_considerant"),
                ("par_considerant_suite", "par_arrete"),
                # ("par_arrete_suite", "par_article"),  # "Arrête" ne peut pas être coupé par un saut de page car il est toujours sur une seule ligne
                ("par_article_suite", "par_article"),
            )
    # créer un empan par paragraphe
    for (cur_beg, cur_typ), (nxt_beg, nxt_typ) in zip(par_begs[:-1], par_begs[1:]):
        # extraire le texte hors espaces de début et fin
        if match := P_STRIP.fullmatch(txt_body, cur_beg, nxt_beg):
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start(),
                    "span_end": match.end(),
                    "span_txt": match.group(0),
                    "span_typ": cur_typ,
                }
            )
        # vérifier que la transition autorisée est correcte
        # TODO déplacer cette vérification en amont ou en aval?
        assert (cur_typ, nxt_typ) in (
            ("par_vu", "par_vu"),
            ("par_vu", "par_considerant"),
            ("par_considerant", "par_considerant"),
            ("par_considerant", "par_arrete"),
            ("par_arrete", "par_article"),
            ("par_article", "par_article"),
        )
    # repérer, dans chaque paragraphe, les références au cadre réglementaire
    # TODO seulement pour les "vu"? ou utile pour les autres?
    # TODO certaines références peuvent-elles être coupées par des sauts de page ? => concaténer latest_span["span_txt"] et content[0]["span_txt"] ?
    content_reg = []
    for par in content:
        par_reg = parse_refs_reglement(txt_body, par["span_beg"], par["span_end"])
        content_reg.extend(par_reg)
    content.extend(content_reg)

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
    doc_content = []  # valeur de retour
    # métadonnées du document
    mdata_doc = {
        "filename": fp_txt_in.name,
    }
    print(fp_txt_in.name)  # DEBUG
    # traiter les pages
    pages = load_pages_text(fp_txt_in)
    latest_span = None  # init
    for i, page in enumerate(pages, start=1):
        mdata_page = mdata_doc | {"page_num": i}
        pg_template, pg_txt_body = parse_page_template(page)
        pg_content = []

        # préambule du document: seulement en page 1
        if i == 1:
            # 1re page: il faut d'abord analyser le préambule du document (avant le 1er "Vu")
            # contient la commune, l'autorité prenant l'arrêté, parfois le numéro de l'arrêté
            if fst_vu := P_VU.search(pg_txt_body):
                pream_beg = 0
                pream_end = fst_vu.start()
                pream_content = parse_doc_preamble(pg_txt_body, pream_beg, pream_end)
                pg_content.extend(pream_content)
            else:
                raise ValueError(f"Pas de 'Vu' en page 1\n{mdata_page}\n{pg_txt_body}")
            main_beg = pream_end
        else:
            # p. 2 et suivantes: la zone à analyser commence en haut de la page (les éléments de
            # template ayant été effacés au préalable)
            main_beg = 0

        # postambule du document: en dernière page (hors annexes)
        # (NB: peut être la page 1 ou 2, pour les arrêtés les plus courts)
        # le corps du document s'arrête à la signature ou la date de prise de l'arrêté
        # FIXME attraper le 1er qui apparaît: date de signature ou signataire
        if m_date_sign := P_DATE_SIGNAT.search(pg_txt_body, main_beg):
            # si la page contient la signature de fin de l'acte, l'analyse du contenu
            # principal s'arrêter à la signature
            main_end = m_date_sign.start()
        else:
            main_end = len(pg_txt_body)

        # appliquer sur la zone principale ainsi définie une fonction d'analyse générique
        # du contenu (pour toutes les pages)
        pg_content = parse_page_content(pg_txt_body, main_beg, main_end, latest_span)
        # récupérer le dernier paragraphe de la page, car il peut être continué
        # en début de page suivante
        latest_span = [x for x in pg_content if x["span_typ"].startswith("par_")][-1]
        # accumulation au niveau du document
        page_content = mdata_page | {
            "template": pg_template,  # empans de template
            "body": pg_txt_body,  # texte (sans le texte du template)
            "content": pg_content,  # empans de contenu (paragraphes et données)
        }
        doc_content.append(page_content)
        # TODO arrêter le traitement à la fin du postambule et tronquer le texte / le PDF si possible? (utile pour l'OCR)

    # vérifier certaines hypothèses sur la composition du document
    par_typs = [x["span_typ"] for x in doc_content if x["span_typ"].startswith("par_")]
    # "considérant" obligatoire sauf pour certains arrêtés?
    if "par_considerant" not in par_typs:
        if fp_txt_in.name not in (
            "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).txt",  # mainlevée => optionnel ?
            "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.txt",  # mainlevée => optionnel ?
        ):
            raise ValueError(fp_txt_in.name)
    # TODO autres vérifications: "Vu" obligatoire, exactement 1 "Arrête" etc.

    return doc_content


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

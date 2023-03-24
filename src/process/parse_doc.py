"""Analyse le document dans son ensemble.

Extrait des empans de texte correspondant aux en-têtes, pieds-de-page,
autorité, vus, correspondants, articles, signature...
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

import pandas as pd  # tableau récapitulatif des extractions

from src.domain_knowledge.actes import P_STAMP, P_ACCUSE  # tampon
from src.domain_knowledge.arrete import (
    P_ARRETONS,
    P_ARTICLE,
    P_CONSIDERANT,
    P_DATE_SIGNAT,
    P_MAIRE_COMMUNE,
    P_NOM_ARR,
    P_NUM_ARR,
    P_NUM_ARR_FALLBACK,
    P_VU,
)
from src.domain_knowledge.cadastre import get_parcelle
from src.domain_knowledge.cadre_reglementaire import (
    contains_cc,
    contains_cc_art,
    contains_cch,
    contains_cch_L111,
    contains_cch_L511,
    contains_cch_L521,
    contains_cch_L541,
    contains_cch_R511,
    contains_cgct,
    contains_cgct_art,
    parse_refs_reglement,
)
from src.domain_knowledge.doc_template import (
    P_HEADER,
    P_FOOTER,
    P_BORDEREAU,
)  # en-têtes, pieds-de-page, pages spéciales
from src.domain_knowledge.logement import get_adr_doc, get_gest, get_proprio, get_syndic
from src.domain_knowledge.typologie_securite import (
    get_classe,
    get_demo,
    get_equ_com,
    get_int_hab,
    get_urgence,
)

from src.preprocess.data_sources import EXCLUDE_FIXME_FILES, EXCLUDE_FILES
from src.preprocess.separate_pages import load_pages_text
from src.preprocess.filter_docs import DTYPE_META_NTXT_FILT, DTYPE_NTXT_PAGES_FILT
from src.quality.validate_parses import examine_doc_content  # WIP
from src.utils.text_utils import P_STRIP, P_LINE


# dtypes des champs extraits
DTYPE_PARSE = {
    # @ctes
    "has_stamp": "boolean",
    "is_accusedereception_page": "boolean",
    # tous arrêtés
    "commune_maire": "string",
    "has_vu": "boolean",
    "has_considerant": "boolean",
    "has_arrete": "boolean",
    "has_article": "boolean",
    # arrêtés spécifiques
    # - réglementaires
    "has_cgct": "boolean",
    "has_cgct_art": "boolean",
    "has_cch": "boolean",
    "has_cch_L111": "boolean",
    "has_cch_L511": "boolean",
    "has_cch_L521": "boolean",
    "has_cch_L541": "boolean",
    "has_cch_R511": "boolean",
    "has_cc": "boolean",
    "has_cc_art": "boolean",
    # - données
    #   * parcelle
    "parcelle": "string",
    #   * adresse
    "adresse": "string",
    #   * notifiés
    "proprio": "string",
    "syndic": "string",
    "gest": "string",
    #   * arrêté
    "date": "string",
    "num_arr": "string",
    "nom_arr": "string",
    # type d'arrêté
    "classe": "string",
    "urgence": "string",
    "demo": "string",
    "int_hab": "string",
    "equ_com": "string",
}

# dtype du fichier de sortie
DTYPE_META_NTXT_PROC = (
    DTYPE_META_NTXT_FILT | {"pagenum": DTYPE_NTXT_PAGES_FILT["pagenum"]} | DTYPE_PARSE
)


# (spécifique)
# type de données des colonnes du fichier CSV résultat
DTYPE_SPANS = {
    # doc
    "pdf": "string",
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
    print(f"<<<<< template:headers={content}")
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


def parse_doc_preamble(
    fn_pdf: str, txt_body: str, pream_beg: int, pream_end: int
) -> list[dict]:
    """Analyse le préambule d'un document, sur la 1re page, avant le 1er "Vu".

    Parameters
    ----------
    fn_pdf: string
        Nom du fichier PDF
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
    rem_txt = ""  # s'il reste du texte après l'autorité (WIP)

    # créer une copie du texte du préambule, de même longueur que le texte complet pour que les empans soient bien positionnés
    # le texte sera effacé au fur et à mesure qu'il sera "consommé"
    txt_copy = txt_body[:]
    txt_copy = (
        " " * (pream_beg - 0)
        + txt_copy[pream_beg:pream_end]
        + " " * (len(txt_copy) - pream_end)
    )
    assert len(txt_copy) == len(txt_body)

    # a. ce préambule contient (vers la fin) l'intitulé de l'autorité prenant l'arrêté
    # TODO est-ce obligatoire? exceptions: La Ciotat
    if matches := list(P_MAIRE_COMMUNE.finditer(txt_copy, pream_beg, pream_end)):
        # on garde la première occurrence, normalement la seule
        match = matches[0]
        # * toute la zone reconnue
        span_beg, span_end = match.span()
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
                "span_txt": match.group(0),
                "span_typ": "par_autorite",
            }
        )
        # * stocker la donnée de la commune
        content.append(
            {
                "span_beg": match.start("commune"),
                "span_end": match.end("commune"),
                "span_txt": match.group("commune"),
                "span_typ": "adr_ville",  # TODO utiliser un autre nom pour éviter le conflit?
            }
        )
        # * effacer l'empan reconnu
        txt_copy = (
            txt_copy[:span_beg] + " " * (span_end - span_beg) + txt_copy[span_end:]
        )

        # la ou les éventuelles autres occurrences sont des doublons
        if len(matches) > 1:
            logging.warning(
                f"{fn_pdf}: > 1 mention d'autorité trouvée dans le préambule: {matches}"
            )
            for match_dup in matches[1:]:
                # toute la zone reconnue
                span_dup_beg, span_dup_end = match_dup.span()
                content.append(
                    {
                        "span_beg": span_dup_beg,
                        "span_end": span_dup_end,
                        "span_txt": match_dup.group(0),
                        "span_typ": "par_autorite_dup",
                    }
                )
                # stocker la donnée de la commune
                content.append(
                    {
                        "span_beg": match_dup.start("commune"),
                        "span_end": match_dup.end("commune"),
                        "span_txt": match_dup.group("commune"),
                        "span_typ": "adr_ville_dup",  # TODO utiliser un autre nom pour éviter le conflit?
                    }
                )
                # effacer l'empan reconnu
                txt_copy = (
                    txt_copy[:span_dup_beg]
                    + " " * (span_dup_end - span_dup_beg)
                    + txt_copy[span_dup_end:]
                )

        # vérifier que la zone de l'autorité est bien en fin de préambule
        try:
            rem_txt = txt_copy[span_end:pream_end].strip()
            assert rem_txt == ""
        except AssertionError:
            logging.warning(
                f"{fn_pdf}: Texte après l'autorité, en fin de préambule: {rem_txt}"
            )
            if len(rem_txt) < 2:
                # s'il ne reste qu'un caractère, c'est probablement une typo => avertir et effacer
                logging.warning(
                    f"{fn_pdf}: Ignorer le fragment de texte en fin de préambule, probablement une typo: {rem_txt}"
                )
                txt_copy = (
                    txt_copy[:span_end]
                    + " " * (pream_end - span_end)
                    + txt_copy[pream_end:]
                )
    else:
        # pas d'autorité détectée: anormal
        logging.warning(f"{fn_pdf}: pas d'autorité détectée dans le préambule")

    # b. ce préambule peut contenir le numéro de l'arrêté (si présent, absent dans certaines communes)
    # NB: ce numéro d'arrêté peut se trouver avant ou après l'autorité (ex: Gardanne)
    match = P_NUM_ARR.search(txt_copy, pream_beg, pream_end)
    if match is None:
        # si la capture précise échoue, utiliser une capture plus permissive (mais risque d'attrape-tout)
        match = P_NUM_ARR_FALLBACK.search(txt_copy, pream_beg, pream_end)

    if match is not None:
        # marquer toute la zone reconnue (contexte + numéro de l'arrêté)
        span_beg, span_end = match.span()
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
                "span_txt": match.group(0),
                "span_typ": "par_num_arr",  # paragraphe contenant le numéro de l'arrêté
            }
        )
        # stocker le numéro de l'arrêté
        content.append(
            {
                "span_beg": match.start("num_arr"),
                "span_end": match.end("num_arr"),
                "span_txt": match.group("num_arr"),
                "span_typ": "num_arr",
            }
        )
        # effacer le texte reconnu
        txt_copy = (
            txt_copy[:span_beg] + " " * (span_end - span_beg) + txt_copy[span_end:]
        )
        # print(f"num arr: {content[-1]['span_txt']}")  # DEBUG
    else:
        # pas de numéro d'arrêté (ex: Aubagne)
        logging.warning(
            f"{fn_pdf}: Pas de numéro d'arrêté trouvé: "
            + '"'
            + txt_copy[pream_beg:pream_end].replace("\n", " ").strip()
            + '"'
        )
        pass

    # c. entre les deux doit se trouver le titre ou objet de l'arrêté (obligatoire)
    if match := P_NOM_ARR.search(txt_copy, pream_beg, pream_end):
        span_beg, span_end = match.span()
        # stocker la zone reconnue
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
                "span_txt": match.group(0),
                "span_typ": "par_nom_arr",
            }
        )
        # stocker la donnée
        content.append(
            {
                "span_beg": match.start("nom_arr"),
                "span_end": match.end("nom_arr"),
                "span_txt": match.group("nom_arr"),
                "span_typ": "nom_arr",
            }
        )
        # effacer l'empan reconnu
        txt_copy = (
            txt_copy[:span_beg] + " " * (span_end - span_beg) + txt_copy[span_end:]
        )
    else:
        # hypothèse: sans marquage explicite comme "Objet:", le titre est tout le texte restant
        # dans cette zone (entre le numéro et l'autorité)
        if (not P_LINE.fullmatch(txt_copy, pream_beg, pream_end)) and (
            match := P_STRIP.fullmatch(txt_copy, pream_beg, pream_end)
        ):
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start(),
                    "span_end": match.end(),
                    "span_txt": match.group("outstrip"),
                    "span_typ": "par_nom_arr",
                }
            )
            # stocker la donnée
            content.append(
                {
                    "span_beg": match.start("outstrip"),
                    "span_end": match.end("outstrip"),
                    "span_txt": match.group("outstrip"),
                    "span_typ": "nom_arr",
                }
            )
        else:
            logging.warning(
                f"{fn_pdf}: Pas de texte restant pour le nom de l'arrêté: "
                + '"'
                + txt_copy[pream_beg:pream_end].replace("\n", " ").strip()
                + '"'
            )

        # WIP
        if rem_txt and content[-1]["span_typ"] == "nom_arr":
            arr_nom = content[-1]["span_txt"].replace("\n", " ")
            logging.warning(f"{fn_pdf}: texte restant et nom: {arr_nom}")
        # end WIP

    # print(content)  # WIP
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
    txt_body: str,
    main_beg: int,
    main_end: int,
    cur_state: str,
    latest_span: Optional[dict],
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
    cur_state: str
        État actuel: "avant_articles", "avant_signature", "apres_signature"
    latest_span: dict, optional
        Dernier empan de contenu repéré sur la page précédente.
        Vaut `None` pour la première page.

    Returns
    -------
    content: list
        Liste d'empans de contenu
    """
    print(
        f"parse_page_content: {(main_beg, main_end, cur_state, latest_span)}"
    )  # DEBUG
    if cur_state not in ("avant_articles", "avant_signature"):
        raise ValueError(
            f"État inattendu {cur_state}\n{main_beg}:{main_end}\n{txt_body[main_beg:main_end]}"
        )

    if txt_body[main_beg:main_end].strip() == "":
        # la zone de texte à analyser est vide
        return []

    content = []

    # repérer les débuts de paragraphes: "Vu", "Considérant", "Arrête", "Article"
    if cur_state == "avant_articles":
        # "Vu" et "Considérant"
        par_begs = sorted(
            [(m.start(), "par_vu") for m in P_VU.finditer(txt_body, main_beg, main_end)]
            + [
                (m.start(), "par_considerant")
                for m in P_CONSIDERANT.finditer(txt_body, main_beg, main_end)
            ]
        )

        # éventuellement, "Arrêtons|Arrête|Arrêté" entre les "Vu" "Considérant" d'une part,
        # les "Article" d'autre part
        # si la page en cours contient le dernier "Vu" ou "Considérant" du document, ou
        # la fin de ce dernier "Vu" ou "Considérant", "Arrêtons" doit être là
        if par_begs:
            # il y a au moins un "Vu" ou "Considérant" sur la page:
            # le dernier de la page est-il aussi le dernier du document?
            searchzone_beg = par_begs[-1][0]
        else:
            # le dernier "Vu" ou "Considérant" peut avoir commencé sur la page précédente,
            # auquel cas on cherche "Arrêtons|Arrête|Arrêté" sur toute la zone en cours
            # d'analyse
            searchzone_beg = main_beg
        print(f"Cherche ARRETE dans:\n{txt_body[searchzone_beg:main_end]}")
        if m_arretons := P_ARRETONS.search(txt_body, searchzone_beg, main_end):
            par_begs.append((m_arretons.start(), "par_arrete"))

    elif cur_state == "avant_signature":
        par_begs = [
            (m.start(), "par_article")
            for m in P_ARTICLE.finditer(txt_body, main_beg, main_end)
        ]
    else:
        raise ValueError(f"cur_state: {cur_state}?")

    # 1. traiter le texte avant le 1er début de paragraphe
    if not par_begs:
        # aucun début de paragraphe détecté sur la page ; cela peut arriver lorsqu'un empan
        # court sur plusieurs pages, eg. un "Considérant" très long incluant la liste des
        # copropriétaires
        #
        # ce n'est possible que s'il y a bien un latest_span, et d'un type admettant une continuation
        if (latest_span is None) or (
            latest_span["span_typ"]
            not in (
                "par_vu",
                "par_considerant",
                "par_article",
                # une continuation peut être elle-même continuée
                "par_vu_suite",
                "par_considerant_suite",
                "par_article_suite",
            )
        ):
            raise ValueError(
                f"Aucun paragraphe continuable sur cette page sans nouveau paragraphe?\ncur_state={cur_state}, latest_span={latest_span}, (main_beg, main_end)=({main_beg}, {main_end})\n{txt_body[main_beg:main_end]}"
            )
        # analyser jusqu'en bas de la page, sans visibilité sur le type du prochain empan (absent de la page)
        nxt_beg = main_end
        nxt_typ = None
    else:
        # s'il y a du texte avant le 1er début de paragraphe, c'est la continuation du
        # dernier paragraphe de la page précédente ;
        # le mettre dans un empan de type span_typ + "_suite"
        nxt_beg, nxt_typ = par_begs[0]

    # récupérer ce texte et le mettre dans un empan spécial _suite
    if (not P_LINE.fullmatch(txt_body, main_beg, nxt_beg)) and (
        match := P_STRIP.fullmatch(txt_body, main_beg, nxt_beg)
    ):
        txt_dang = match.group("outstrip")
        if txt_dang:
            # print(f"txt_dang: {txt_dang}")  # DEBUG
            try:
                lst_typ = latest_span["span_typ"]
            except TypeError:
                print(
                    f"cur_state={cur_state}\npar_begs={par_begs}\n(main_beg, nxt_beg)=({main_beg}, {nxt_beg})\n{txt_body[main_beg:nxt_beg]}"
                )
                raise
            # un empan peut courir sur plus d'une page complète (ex: "Considérant" très long, incluant la liste des copropriétaires)
            cur_typ = lst_typ if lst_typ.endswith("_suite") else lst_typ + "_suite"
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start("outstrip"),
                    "span_end": match.end("outstrip"),
                    "span_txt": match.group("outstrip"),
                    "span_typ": cur_typ,
                }
            )
            if nxt_typ is not None:
                # vérifier que la transition autorisée est correcte
                # TODO déplacer cette vérification en amont ou en aval?
                try:
                    assert (cur_typ, nxt_typ) in (
                        # les "Vu" sont généralement avant les "Considérant" mais certains arrêtés mêlent les deux types de paragraphes
                        ("par_vu_suite", "par_vu"),
                        ("par_vu_suite", "par_considerant"),
                        ("par_vu_suite", "par_arrete"),  # NEW 2023-03-23
                        ("par_considerant_suite", "par_vu"),  # NEW 2023-03-23
                        ("par_considerant_suite", "par_considerant"),
                        ("par_considerant_suite", "par_arrete"),
                        # ("par_arrete_suite", "par_article"),  # "Arrête" ne peut pas être coupé par un saut de page car il est toujours sur une seule ligne
                        # les articles forment un bloc homogène, sans retour vers des "Vu" ou "Considérant" (s'il y en a, ce sont des citations de passage dans un article...)
                        ("par_article_suite", "par_article"),
                    )
                except AssertionError:
                    print(
                        f"Transition inattendue: ({cur_typ}, {nxt_typ})\n{latest_span}\n{txt_body}"
                    )
                    raise

    # 2. pour chaque début de paragraphe, créer un empan allant jusqu'au prochain début
    for (cur_beg, cur_typ), (nxt_beg, nxt_typ) in zip(par_begs[:-1], par_begs[1:]):
        # extraire le texte hors espaces de début et fin
        if (not P_LINE.fullmatch(txt_body, cur_beg, nxt_beg)) and (
            match := P_STRIP.fullmatch(txt_body, cur_beg, nxt_beg)
        ):
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start(),
                    "span_end": match.end(),
                    "span_txt": match.group("outstrip"),
                    "span_typ": cur_typ,
                }
            )
        # vérifier que la transition autorisée est correcte
        # TODO déplacer cette vérification en amont ou en aval?
        try:
            assert (cur_typ, nxt_typ) in (
                ("par_vu", "par_vu"),
                ("par_vu", "par_considerant"),
                (
                    "par_vu",
                    "par_arrete",
                ),  # transition rare mais qui arrive (ex: abrogation d'arrêté dont la raison est donnée dans un autre arrêté...)
                ("par_considerant", "par_considerant"),
                ("par_considerant", "par_arrete"),
                ("par_arrete", "par_article"),
                ("par_article", "par_article"),
            )
        except AssertionError:
            print(f"Transition imprévue: ({cur_typ, nxt_typ})\n{content}")
            raise

    # 3. pour le dernier début de paragraphe, créer un empan allant jusqu'à la fin du texte
    if par_begs:
        cur_beg, cur_typ = par_begs[-1]
        nxt_beg = main_end
        nxt_typ = None
        # extraire le texte hors espaces de début et fin
        if (not P_LINE.fullmatch(txt_body, cur_beg, nxt_beg)) and (
            match := P_STRIP.fullmatch(txt_body, cur_beg, nxt_beg)
        ):
            # stocker la zone reconnue
            content.append(
                {
                    "span_beg": match.start(),
                    "span_end": match.end(),
                    "span_txt": match.group("outstrip"),
                    "span_typ": cur_typ,
                }
            )
        # on ne peut pas vérifier si la transition autorisée est correcte puisque
        # le prochain empan n'est pas connu (page suivante) ; cette vérification
        # sera faite de toute façon lors du traitement du haut de la prochaine page

    # repérer, dans chaque paragraphe, les références au cadre réglementaire
    # TODO seulement pour les "vu"? ou utile pour les autres?
    # TODO certaines références peuvent-elles être coupées par des sauts de page ? => concaténer latest_span["span_txt"] et content[0]["span_txt"] ?
    content_reg = []
    for par in content:
        par_reg = parse_refs_reglement(txt_body, par["span_beg"], par["span_end"])
        content_reg.extend(par_reg)
    content.extend(content_reg)

    return content


# FIXME enlever les EXCLUDE_FILES en amont (idéalement: les détecter et filtrer automatiquement, juste avant)
EXCLUDE_SET = set(EXCLUDE_FIXME_FILES)


def parse_arrete_pages(fn_pdf: str, pages: list[str]) -> list:
    """Analyse les pages de texte d'un arrêté.

    Parameters
    ----------
    fn_pdf: str
        Nom du fichier PDF.
    pages: list[str]
        Liste de pages de texte à analyser.

    Returns
    -------
    doc_content: list[dict]
        Contenu du document, par page découpée en zones de texte.
    """
    doc_content = []  # valeur de retour

    # FIXME on ne traite pas une poignée de documents qui posent différents problèmes
    if fn_pdf in EXCLUDE_SET:
        return doc_content
    # end FIXME

    # métadonnées du document
    mdata_doc = {
        "pdf": fn_pdf,
    }
    # print(fn_pdf)  # DEBUG
    # traiter les pages
    # TODO états alternatifs? ["preambule", "vu", "considerant", "arrete", "article", "postambule" ou "signature", "apres_signature" ou "annexes"] ?
    cur_state = "avant_vucons"  # init ; "avant_vucons" < "avant_articles" < "avant_signature"  # TODO ajouter "avant_considerant" ?
    latest_span = None  # init
    for i, page in enumerate(pages, start=1):
        # métadonnées de la page
        mdata_page = mdata_doc | {"page_num": i}

        if pd.isna(page):
            # * la page n'a pas de texte
            page_content = mdata_page | {
                "template": None,  # empans de template
                "body": None,  # texte (sans le texte du template)
                "content": None,  # empans de contenu (paragraphes et données): vide
            }
            doc_content.append(page_content)
            continue

        # repérer et effacer les éléments de template, pour ne garder que le contenu de chaque page
        pg_template, pg_txt_body = parse_page_template(page)
        pg_content = []  # initialisation de la liste des éléments de contenu

        # détecter et traiter spécifiquement les pages vides, de bordereau ou d'annexes
        if pg_txt_body.strip() == "":
            # * la page est vide de texte (hors template), donc aucun empan de contenu ne pourra être reconnu
            page_content = mdata_page | {
                "template": pg_template,  # empans de template
                "body": pg_txt_body,  # texte (sans le texte du template)
                "content": pg_content,  # empans de contenu (paragraphes et données): vide
            }
            doc_content.append(page_content)
            continue
        elif P_BORDEREAU.search(pg_txt_body):
            # * page de bordereau de formalités (Aix-en-Provence)
            # TODO extraire le contenu (date de l'acte, numéro, titre) pour vérifier la correction des données extraites ailleurs?
            page_content = mdata_page | {
                "template": pg_template,  # empans de template
                "body": pg_txt_body,  # texte (sans le texte du template)
                "content": pg_content,  # empans de contenu (paragraphes et données): vide
            }
            doc_content.append(page_content)
            continue

        # TODO pages d'annexe

        # TODO si la signature est déjà passée, on peut considérer que le document est terminé et stopper tout le traitement? => ajouter un état cur_state == "apres_signature" ?
        # NB: certains fichiers PDF contiennent un arrêté modificatif puis l'arrêté d'origine (ex: "modif 39 rue Tapis Vert 13001.pdf"), on ignore le 2e ?

        # la page n'est pas vide de texte
        main_end = len(pg_txt_body)
        # 1. préambule du document: avant le 1er "Vu", contient la commune, l'autorité prenant l'arrêté, parfois le numéro de l'arrêté
        if cur_state == "avant_vucons":
            fst_vucons = []
            if fst_vu := P_VU.search(pg_txt_body):
                fst_vucons.append(fst_vu)
            if fst_cons := P_CONSIDERANT.search(pg_txt_body):
                fst_vucons.append(fst_cons)
            if fst_vucons:
                fst_vu_or_cons = sorted(fst_vucons, key=lambda x: x.start())[0]
                pream_beg = 0
                pream_end = fst_vu_or_cons.start()
                pream_content = parse_doc_preamble(
                    fn_pdf, pg_txt_body, pream_beg, pream_end
                )
                pg_content.extend(pream_content)
                if pream_content:
                    latest_span = None  # le dernier empan de la page précédente n'est plus disponible
                cur_state = "avant_articles"
            else:
                # la 1re page ne contient ni "vu" ni "considérant", ce doit être une page de courrier
                # ex: "21, rue Martinot Aubagne.pdf"
                logging.warning(
                    f"{fn_pdf}: page {i}: ni 'vu' ni 'considérant' donc page ignorée"
                )
                continue
            main_beg = pream_end
        else:
            # p. 2 et suivantes: la zone à analyser commence en haut de la page (les éléments de
            # template ayant été effacés au préalable)
            main_beg = 0
        # TODO si tout le texte a déjà été reconnu, ajouter le contenu de la page au doc et passer à la page suivante

        # 2. les "vu" et "considérant"
        if cur_state == "avant_articles":
            vucons_beg = main_beg
            # la page contient-elle un "Article" ? (le 1er)
            if m_article := P_ARTICLE.search(pg_txt_body, main_beg):
                # si oui, les "Vu" et "Considérant" de cette page, puis "Arrête",
                # sont à chercher avant le 1er "Article"
                print(f"m_article={m_article}")  # DEBUG
                vucons_end = m_article.start()
            else:
                # si non, les "Vu" et "Considérant" sont sur toute la page
                vucons_end = main_end
            # repérer les "Vu" et "Considérant", et "Arrête" si présent
            print(f"avant parse_page_content/Vucons: pg_content={pg_content}")  # DEBUG
            vucons_content = parse_page_content(
                pg_txt_body, vucons_beg, vucons_end, cur_state, latest_span
            )  # FIXME spécialiser la fonction pour restreindre aux "Vu" et "Considérant" et/ou passer cur_state? ; NB: ces deux types de paragraphes admettent des continuations
            pg_content.extend(vucons_content)
            print(f"après parse_page_content/Vucons: pg_content={pg_content}")  # DEBUG
            if vucons_content:
                latest_span = (
                    None  # le dernier empan de la page précédente n'est plus disponible
                )

            # si "Arrête" était bien sur la page, il faut ajouter l'empan reconnu, déplacer le curseur et changer d'état
            if pg_content:
                spans_arrete = [x for x in pg_content if x["span_typ"] == "par_arrete"]
                if spans_arrete:
                    assert len(spans_arrete) == 1
                    span_arrete = spans_arrete[0]
                    #
                    main_beg = span_arrete["span_end"]
                    latest_span = None  # le dernier empan de la page précédente n'est plus disponible
                    cur_state = "avant_signature"
        # TODO si tout le texte a déjà été reconnu, ajouter le contenu de la page au doc et passer à la page suivante

        # 3. les "article" et le postambule
        if cur_state == "avant_signature":
            # le corps du document s'arrête à la signature ou la date de prise de l'arrêté
            # FIXME attraper le 1er qui apparaît: date de signature ou signataire
            artic_beg = main_beg
            if m_date_sign := P_DATE_SIGNAT.search(pg_txt_body, main_beg):
                # si la page contient la signature de fin de l'acte, l'analyse du contenu
                # principal s'arrêter à la signature
                artic_end = m_date_sign.start()
            else:
                artic_end = main_end

            # repérer les articles
            print(
                f"avant parse_page_content/Articles: pg_content={pg_content}"
            )  # DEBUG
            try:
                artic_content = parse_page_content(
                    pg_txt_body, artic_beg, artic_end, cur_state, latest_span
                )  # FIXME spécialiser la fonction pour restreindre aux "Vu" et "Considérant" et/ou passer cur_state? ; NB: ces deux types de paragraphes admettent des continuations
            except TypeError:
                print(f"Fichier fautif: {fn_pdf}, p. {i}")
                raise
            pg_content.extend(artic_content)
            if artic_content:
                latest_span = (
                    None  # le dernier empan de la page précédente n'est plus disponible
                )

            if m_date_sign:
                # analyser le postambule et changer l'état
                posta_beg = m_date_sign.start()
                posta_end = main_end
                posta_content = parse_doc_postamble(pg_txt_body, posta_beg, posta_end)
                pg_content.extend(posta_content)
                if posta_content:
                    latest_span = None  # le dernier empan de la page précédente n'est plus disponible
                cur_state = "apres_signature"
        # TODO si tout le texte a déjà été reconnu, ajouter le contenu de la page au doc et passer à la page suivante

        if cur_state == "apres_signature":
            pass  # FIXME faire quelque chose? vérifier s'il reste du texte?

        # récupérer le dernier paragraphe de la page, car il peut être continué
        # en début de page suivante
        if pg_content:
            try:
                latest_span = [
                    x for x in pg_content if x["span_typ"].startswith("par_")
                ][-1]
            except IndexError:
                print(
                    f"{fn_pdf} / p.{i} : pas de paragraphe sur l'empan {main_beg}:{main_end}\ncontenu:{pg_content}\ntexte:\n{pg_txt_body}"
                )
                raise
        # accumulation au niveau du document
        page_content = mdata_page | {
            "template": pg_template,  # empans de template
            "body": pg_txt_body,  # texte (sans le texte du template)
            "content": pg_content,  # empans de contenu (paragraphes et données)
        }
        doc_content.append(page_content)
        if False:  # DEBUG
            print("<<<<<<<<<<<<<<<<")
            print(pg_content)  # DEBUG
            print("----------------")
            print(pg_txt_body)  # DEBUG
            print("~~~~~~~~~~~~~~~~")
            print(pg_txt_body[main_beg:main_end])  # DEBUG
            print("================")
        # TODO arrêter le traitement à la fin du postambule et tronquer le texte / le PDF si possible? (utile pour l'OCR)

    # vérifier que le résultat est bien formé
    examine_doc_content(fn_pdf, doc_content)
    #
    return doc_content


def unique_txt(spans: list[dict], span_typ: str) -> str:
    """Cherche l'unique empan d'un type donné et renvoie son texte.

    Si plusieurs empans de la liste en entrée sont du type recherché,
    une exception est levée.
    Si aucun empan de la liste n'est du type recherché, renvoie None.

    Parameters
    ----------
    spans: list(dict)
        Liste d'empans extraits
    span_typ: str
        Type d'empan recherché

    Returns
    -------
    span_txt: str
        Texte de l'unique empan du type recherché.
    """
    if not spans:
        return None
    cands = [x for x in spans if x["span_typ"] == span_typ]
    if not cands:
        return None
    elif len(cands) > 1:
        raise ValueError(f"Plusieurs empans de type {span_typ}: {cands}")
    else:
        return cands[0]["span_txt"]


def has_one(spans: list[dict], span_typ: str) -> str:
    """Détecte si la liste contient au moins un empan d'un type donné.

    Si la liste est vide, renvoie None.

    Parameters
    ----------
    spans: list(dict)
        Liste d'empans extraits
    span_typ: str
        Type d'empan recherché

    Returns
    -------
    has_span: boolean
        True si au moins un empan de la liste est du type recherché.
    """
    if not spans:
        return None
    return any(x for x in spans if x["span_typ"] == span_typ)


def process_files(
    df_meta: pd.DataFrame,
    df_txts: pd.DataFrame,
) -> pd.DataFrame:
    """Traiter un ensemble d'arrêtés: repérer des éléments de structure des textes.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de métadonnées des fichiers à traiter.
    df_txts: pd.DataFrame
        Liste de pages de documents à traiter.

    Returns
    -------
    df_proc: pd.DataFrame
        Liste de métadonnées des pages traitées, avec indications des éléments de
        structure détectés.
    """
    indics_struct = []
    for _, df_doc_pages in df_txts.groupby("fullpath"):  # RESUME HERE ~exclude
        # méta à passer en fin
        df_doc_meta = df_doc_pages[["pdf", "fullpath", "pagenum"]]
        #
        fn_pdf = df_doc_pages["pdf"].iat[0]
        pages = df_doc_pages["pagetxt"].values
        exclude = df_doc_pages["exclude"].values
        # actes
        try:
            has_stamp_pages = [
                (P_STAMP.search(x) is not None) if pd.notna(x) else None for x in pages
            ]
        except TypeError:
            print(repr(pages))
            raise
        # repérer les pages d'accusé de réception d'actes, elles seront marquées et non passées au parser
        # TODO vérifier si la page d'AR actes apparaît seulement en dernière page, sinon on peut couper le doc et passer moins de pages au parser
        # TODO timer et réécrire les deux instructions en pandas[pyarrow] pour améliorer la vitesse?
        is_ar_pages = [
            (P_ACCUSE.match(x) is not None) if pd.notna(x) else None for x in pages
        ]
        # filtrer les pages
        filt_pages = []
        for x, excl, is_ar in zip(pages, exclude, is_ar_pages):
            if excl:  # flag d'exclusion de la page
                filt_p = None
            elif is_ar:  # page d'accusé de réception de télétransmission actes
                filt_p = ""
            else:
                filt_p = x
            filt_pages.append(filt_p)
        # analyser les pages
        doc_content = parse_arrete_pages(fn_pdf, filt_pages)
        # filtrer les empans de données, et laisser de côté les empans de structure
        for page_cont, has_st, is_ar, page_meta in zip(
            doc_content, has_stamp_pages, is_ar_pages, df_doc_meta.itertuples()
        ):
            pg_content = page_cont["content"]
            pg_txt_body = page_cont["body"]
            rec_struct = {
                # @ctes
                "has_stamp": has_st,
                "is_accusedereception_page": is_ar,
                # tous arrêtés
                "commune_maire": unique_txt(pg_content, "adr_ville"),
                "has_vu": has_one(pg_content, "par_vu"),
                "has_considerant": has_one(pg_content, "par_considerant"),
                "has_arrete": has_one(pg_content, "par_arrete"),
                "has_article": has_one(pg_content, "par_article"),
                # arrêtés spécifiques
                # - réglementaires
                "has_cgct": contains_cgct(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cgct_art": contains_cgct_art(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch": contains_cch(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch_L111": contains_cch_L111(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch_L511": contains_cch_L511(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch_L521": contains_cch_L521(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch_L541": contains_cch_L541(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cch_R511": contains_cch_R511(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cc": contains_cc(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                "has_cc_art": contains_cc_art(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO
                # - données
                "adresse": get_adr_doc(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO urgent
                "parcelle": get_parcelle(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO urgent
                "proprio": get_proprio(pg_txt_body)
                if pg_txt_body is not None
                else None,  # WIP
                "syndic": get_syndic(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO urgent-
                "gest": get_gest(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO urgent-
                "date": unique_txt(pg_content, "arr_date"),
                #   * arrêté
                "num_arr": unique_txt(pg_content, "num_arr"),
                "nom_arr": unique_txt(pg_content, "nom_arr"),
                "classe": get_classe(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO improve
                "urgence": get_urgence(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO improve
                "demo": get_demo(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO improve
                "int_hab": get_int_hab(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO improve
                "equ_com": get_equ_com(pg_txt_body)
                if pg_txt_body is not None
                else None,  # TODO improve
            }
            indics_struct.append(
                {
                    "pdf": page_meta.pdf,
                    "fullpath": page_meta.fullpath,
                    "pagenum": page_meta.pagenum,
                }
                | rec_struct  # python >= 3.9 (dict union)
            )
    df_indics = pd.DataFrame.from_records(indics_struct)
    df_proc = pd.merge(df_meta, df_indics, on=["pdf", "fullpath"])
    df_proc = df_proc.astype(dtype=DTYPE_META_NTXT_PROC)
    return df_proc


# FIXME refactor dans process_files et __main__


if False:
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
        df_parses = df_parses.astype(DTYPE_SPANS)
        # TODO tests: dropna() puis:
        # assert header_beg == 0
        # alt: assert txt[:header_beg] == ""
        # assert footer_end == len(txt)
        # alt: assert txt[footer_end:] == ""
        df_parses.to_csv(CSV_PARSES, index=False)


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/parse_doc_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    # mêmes entrées et sorties que parse_native_pages
    parser.add_argument(
        "in_file_meta",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées des fichiers PDF",
    )
    parser.add_argument(
        "in_file_pages",
        help="Chemin vers le fichier CSV en entrée contenant les pages de texte",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées des fichiers PDF enrichies, par page",
    )
    group = parser.add_mutually_exclusive_group()
    # par défaut, le fichier out_file ne doit pas exister, sinon deux options mutuellement exclusives:
    # "redo" (écrase le fichier existant) et "append" (étend le fichier existant)
    group.add_argument(
        "--redo",
        action="store_true",
        help="Ré-exécuter le traitement d'un lot, et écraser le fichier de sortie",
    )
    group.add_argument(
        "--append",
        action="store_true",
        help="Ajoute les pages annotées au fichier out_file s'il existe",
    )
    args = parser.parse_args()

    # entrée: CSV de métadonnées
    in_file_meta = Path(args.in_file_meta).resolve()
    if not in_file_meta.is_file():
        raise ValueError(f"Le fichier en entrée {in_file_meta} n'existe pas.")

    # entrée: CSV de pages de texte
    in_file_pages = Path(args.in_file_pages).resolve()
    if not in_file_pages.is_file():
        raise ValueError(f"Le fichier en entrée {in_file_pages} n'existe pas.")

    # sortie: CSV de pages de texte annotées
    # on crée le dossier parent (récursivement) si besoin
    out_file = Path(args.out_file).resolve()
    if out_file.is_file():
        if not args.redo and not args.append:
            # erreur si le fichier CSV existe déjà mais ni redo, ni append
            raise ValueError(
                f"Le fichier de sortie {out_file} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
            )
    else:
        # si out_file n'existe pas, créer son dossier parent si besoin
        out_dir = out_file.parent
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(exist_ok=True)

    # ouvrir le fichier de métadonnées en entrée
    logging.info(f"Ouverture du fichier CSV de métadonnées {in_file_meta}")
    df_meta = pd.read_csv(in_file_meta, dtype=DTYPE_META_NTXT_FILT)
    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV de pages de texte {in_file_pages}")
    df_txts = pd.read_csv(in_file_pages, dtype=DTYPE_NTXT_PAGES_FILT)
    # traiter les documents (découpés en pages de texte)
    df_tmod = process_files(df_meta, df_txts)

    # optionnel: afficher des statistiques
    if True:  # TODO ajouter une option si utilité confirmée
        new_cols = [
            # @ctes
            "has_stamp",
            "is_accusedereception_page",
            # structure générique des arrêtés
            "commune_maire",
            # "has_vu",
            # "has_considerant",
            # "has_arrete",
            # "has_article",
            # données à extraire
            "parcelle",
            # "adresse",
            # "syndic",
        ]
        print(
            df_tmod.query("pagenum == 1")
            .dropna(axis=0, how="all", subset=["has_stamp"])[new_cols]
            .groupby("commune_maire")
            .value_counts(dropna=False)
        )
        # TODO écrire des "expectations": cohérence entre colonnes sur le même document,
        # AR sur la dernière page (sans doute faux dans certains cas, eg. annexes ou rapport d'expertise)
        # page has_article=TRUE >= page has_vu, has_considerant
        # pour tout document ayant au moins une page où has_article=TRUE, alors il existe une page has_vu=TRUE
        # (et il existe une page où has_considerant=TRUE ?)

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_tmod_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT_PROC)
        df_proc = pd.concat([df_tmod_old, df_tmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_tmod
    df_proc.to_csv(out_file, index=False)

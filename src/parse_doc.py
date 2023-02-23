"""Analyse le document dans son ensemble.

Extrait des empans de texte correspondant aux en-têtes, pieds-de-page,
autorité, vus, correspondants, articles, signature...
"""

from pathlib import Path
import re
from typing import Optional

import pandas as pd  # tableau récapitulatif des extractions

from actes import P_STAMP, P_ACCUSE  # tampon
from cadre_reglementaire import parse_refs_reglement
from doc_template import (
    P_HEADER,
    P_FOOTER,
    P_BORDEREAU,
)  # en-têtes, pieds-de-page, pages spéciales
from separate_pages import load_pages_text
from text_structure import (
    P_ARR_NUM,
    P_ARR_NUM_FALLBACK,
    P_ARR_OBJET,
    P_MAIRE_COMMUNE,
    P_VU,
    P_CONSIDERANT,
    P_ARRETE,
    P_ARTICLE,
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
RE_STRIP = (
    r"(?:\s*)"  # espaces initiaux
    + r"(?P<outstrip>\S[\s\S]*?)"  # texte à capturer
    + r"(?:\s*)"  # espaces finaux
)
P_STRIP = re.compile(RE_STRIP, re.IGNORECASE | re.MULTILINE)
# motif pour capturer les lignes (pour ne pas les confondre avec du vrai texte, en garde-fou avant STRIP)
RE_LINE = (
    r"(?:\s*)"  # espaces initiaux
    + r"(?:_{3,})"  # capturer les traits/lignes "_______"
    + r"(?:\s*)"  # espaces finaux
)
P_LINE = re.compile(RE_LINE, re.IGNORECASE | re.MULTILINE)


def parse_doc_preamble(
    filename: str, txt_body: str, pream_beg: int, pream_end: int
) -> list[dict]:
    """Analyse le préambule d'un document, sur la 1re page, avant le 1er "Vu".

    Parameters
    ----------
    filename: string
        Nom du fichier texte
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

    # a. ce préambule contient (vers la fin) l'intitulé de l'autorité prenant l'arrêté (obligatoire)
    if match := P_MAIRE_COMMUNE.search(txt_copy, pream_beg, pream_end):
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
        # stocker la donnée de la commune
        content.append(
            {
                "span_beg": match.start("commune"),
                "span_end": match.end("commune"),
                "span_txt": match.group("commune"),
                "span_typ": "adr_ville",  # TODO utiliser un autre nom pour éviter le conflit?
            }
        )
        # effacer l'empan reconnu
        txt_copy = (
            txt_copy[:span_beg] + " " * (span_end - span_beg) + txt_copy[span_end:]
        )
        # vérifier que la zone de l'autorité est bien en fin de préambule
        try:
            rem_txt = txt_copy[span_end:pream_end].strip()
            assert rem_txt == ""
        except AssertionError:
            # FIXME log warning
            print(
                f"W: {filename}\tTexte après l'autorité, en fin de préambule: {rem_txt}"
            )
            if len(rem_txt) < 2:
                # s'il ne reste qu'un caractère, c'est probablement une typo => avertir et effacer
                # FIXME warning
                print(
                    f"W: {filename}\tIgnorer le fragment de texte en fin de préambule, probablement une typo: {rem_txt}"
                )
                txt_copy = (
                    txt_copy[:span_end]
                    + " " * (pream_end - span_end)
                    + txt_copy[pream_end:]
                )
    else:
        # pas d'autorité détectée: anormal
        raise ValueError(f"Pas d'autorité détectée !?\n{txt_copy}")

    # b. ce préambule peut contenir le numéro de l'arrêté (si présent, absent dans certaines communes)
    # NB: ce numéro d'arrêté peut se trouver avant ou après l'autorité (ex: Gardanne)
    match = P_ARR_NUM.search(txt_copy, pream_beg, pream_end)
    if match is None:
        # si la capture précise échoue, utiliser une capture plus permissive (mais risque d'attrape-tout)
        match = P_ARR_NUM_FALLBACK.search(txt_copy, pream_beg, pream_end)

    if match is not None:
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
        # effacer le texte reconnu
        txt_copy = (
            txt_copy[:span_beg] + " " * (span_end - span_beg) + txt_copy[span_end:]
        )
        # print(f"num arr: {content[-1]['span_txt']}")  # DEBUG
    else:
        # pas de numéro d'arrêté (ex: Aubagne)
        # FIXME log warning
        print(f"{filename}: Pas de numéro d'arrêté\n{txt_copy[pream_beg:pream_end]}")
        pass

    # c. entre les deux doit se trouver le titre ou objet de l'arrêté (obligatoire)
    if match := P_ARR_OBJET.search(txt_copy, pream_beg, pream_end):
        span_beg, span_end = match.span()
        # stocker la zone reconnue
        content.append(
            {
                "span_beg": span_beg,
                "span_end": span_end,
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
                f"Pas de texte trouvé pour le nom!?\n{txt_copy[pream_beg:pream_end]}"
            )
        # WIP
        if rem_txt and content[-1]["span_typ"] == "arr_nom":
            arr_nom = content[-1]["span_txt"].replace("\n", " ")
            print(f"W: {filename} - nom: {arr_nom}")
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
        État actuel: "avant_arrete", "avant_signature", "apres_signature"
    latest_span: dict, optional
        Dernier empan de contenu repéré sur la page précédente.
        Vaut `None` pour la première page.

    Returns
    -------
    content: list
        Liste d'empans de contenu
    """
    if cur_state not in ("avant_arrete", "avant_signature"):
        raise ValueError(
            f"État inattendu {cur_state}\n{main_beg}:{main_end}\n{txt_body[main_beg:main_end]}"
        )

    if txt_body[main_beg:main_end].strip() == "":
        # la zone de texte à analyser est vide
        return []

    content = []

    # repérer les débuts de paragraphes: "Vu", "Considérant", "Arrête", "Article"
    if cur_state == "avant_arrete":
        par_begs = [
            (m.start(), "par_vu") for m in P_VU.finditer(txt_body, main_beg, main_end)
        ] + [
            (m.start(), "par_considerant")
            for m in P_CONSIDERANT.finditer(txt_body, main_beg, main_end)
        ]
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
                # une continuation peut être continuée
                "par_vu_suite",
                "par_considerant_suite",
                "par_article_suite",
            )
        ):
            raise ValueError(
                f"Aucun paragraphe continuable sur cette page sans nouveau paragraphe?\n{cur_state} {main_beg}:{main_end}\n{txt_body[main_beg:main_end]}"
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
                print(f"{par_begs}")
                print(f"{main_beg} {nxt_beg} {txt_body[main_beg:nxt_beg]}")
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
                        ("par_vu_suite", "par_vu"),
                        ("par_vu_suite", "par_considerant"),
                        ("par_considerant_suite", "par_considerant"),
                        ("par_considerant_suite", "par_arrete"),
                        # ("par_arrete_suite", "par_article"),  # "Arrête" ne peut pas être coupé par un saut de page car il est toujours sur une seule ligne
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


def examine_doc_content(filename: str, doc_content: list[dict]):
    """Vérifie des hypothèses de bonne formation sur le contenu extrait du document.

    Parameters
    ----------
    doc_content: list[dict]
        Empans de contenu extraits du document
    """
    # paragraphes
    par_typs = [
        x["span_typ"]
        for pg_content in doc_content
        for x in pg_content["content"]
        if x["span_typ"].startswith("par_")
    ]
    # "considérant" obligatoire sauf pour certains arrêtés?
    # TODO déterminer si les assertions ne s'appliquent qu'à certaines classes d'arrêtés
    if par_typs:
        # chaque arrêté contient au moins un "vu"
        if "par_vu" not in par_typs:
            raise ValueError(f"{filename}: pas de vu")
        # chaque arrêté contient au moins un "considérant"
        # * sauf dans les mainlevées et abrogations où dans la pratique ce n'est pas le cas
        if "par_considerant" not in par_typs:
            if filename not in (
                "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).txt",  # mainlevée => optionnel ?
                "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.txt",  # mainlevée => optionnel ?
                "abrogation interdiction d'occuper 35, bld Barbieri.txt",  # abrogation => optionnel ?
                "abrogation 232 et 236 rue Roger Salengro 13003.txt",  # abrogation => optionnel ?
                "abrogation 79, rue de Rome.txt",  # abrogation => optionnel ?
                "abrogation 19 24 rue Moustier 13001.txt",  # abrogation => optionnel ?
                "102, rue d'Aubagne abrogation.txt",  # abrogation => optionnel ?
                "9, rue Brutus ABROGATION.txt",  # abrogation
                "ABROGATION 73, rue d'Aubagne.txt",  # abrogation
                "abrogation 24, rue des Phocéens 13002.txt",  # abrogation
                "abrogation.txt",  # abrogation
                "abrogation 19, rue d'Italie 13006.txt",  # abrogation
                "ABROGATION 54, bld Dahdah.txt",  # abrogation
                "abrogation 3, rue Loubon 13003.txt",  # abrogation
                "abrogation 35, rue de Lodi.txt",  # abrogation
                "abrogation 4 - 6 rue Saint Georges.txt",  # abrogation
                "abrogation 23, bld Salvator.txt",  # abrogation
                "abrogation 25, rue Nau.txt",  # abrogation
                "abrogation 51 rue Pierre Albrand.txt",  # abrogation
                "abrogation 80 a, rue Longue des Capucins.txt",  # abrogation
                "abrogation 36, cours Franklin Roosevelt.txt",  # abrogation
                "abrogation 356, bld National.txt",  # abrogation
                "abrogation 57, bld Dahdah.txt",  # abrogation
                "abrogation 86, rue Longue des Capucins.txt",  # abrogation
                "abrogation 26, bld Battala.txt",  # abrogation
                "abrogation 24, rue Montgrand.txt",  # abrogation
                "mainlevée 102 bld Plombières 13014.txt",  # mainlevée (Marseille)
                "mainlevée 29 bld Michel 13016.txt",  # mainlevée (Marseille)
                "mainlevée 7 rue de la Tour Peyrolles.txt",  # mainlevée (Peyrolles)
                "mainlevée de péril ordinaire 8 rue Longue Roquevaire.txt",  # mainlevée (Roquevaire)
                "mainlevée 82L chemin des Lavandières Roquevaire.txt",  # mainlevée (Roquevaire)
                "8, rue Maréchal Foch Roquevaire.txt",  # PGI ! (Roquevaire)
                "grave 31 rue du Calvaire Roquevaire.txt",  # PGI ! (Roquevaire)
                "PGI rue docteur Paul Gariel -15122020.txt",  # PGI ! (Roquevaire)
                "modif Maréchal Foch.txt",  # modif PGI ! (Roquevaire)
            ):
                raise ValueError(f"{filename}: pas de considérant")
        # chaque arrêté contient exactement 1 "Arrête"
        try:
            assert len([x for x in par_typs if x == "par_arrete"]) == 1
        except AssertionError:
            if filename not in (
                "16, rue de la République Gemenos.txt",  # OCR p.1 seulement => à ré-océriser
                "mainlevée 6, rue des Jaynes Gemenos.txt",  # OCR p.1 seulement => à ré-océriser
            ):
                raise ValueError(f"{filename}: pas de vu")
        # l'ordre relatif (vu < considérant < arrête < article) est vérifié au niveau des transitions admissibles


def parse_arrete_pages(filename: str, pages: list[str]) -> list:
    """Analyse les pages de texte d'un arrêté.

    Parameters
    ----------
    filename: str
        Nom du fichier texte source.
    pages: list[str]
        Liste de pages de texte à analyser.

    Returns
    -------
    doc_content: list[dict]
        Contenu du document, par page découpée en zones de texte.
    """
    doc_content = []  # valeur de retour
    # métadonnées du document
    mdata_doc = {
        "filename": filename,
    }
    # print(filename)  # DEBUG
    # traiter les pages
    # TODO états alternatifs? ["preambule", "vu", "considerant", "arrete", "article", "postambule" ou "signature", "apres_signature" ou "annexes"] ?
    cur_state = "avant_vu"  # init ; "avant_vu" < "avant_arrete" < "avant_signature"  # TODO ajouter "avant_considerant" ?
    latest_span = None  # init
    for i, page in enumerate(pages, start=1):
        # métadonnées de la page
        mdata_page = mdata_doc | {"page_num": i}

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
        if cur_state == "avant_vu":
            if fst_vu := P_VU.search(pg_txt_body):
                pream_beg = 0
                pream_end = fst_vu.start()
                pream_content = parse_doc_preamble(
                    filename, pg_txt_body, pream_beg, pream_end
                )
                pg_content.extend(pream_content)
                if pream_content:
                    latest_span = None  # le dernier empan de la page précédente n'est plus disponible
                cur_state = "avant_arrete"
            else:
                # le 1er "vu" est toujours (implicitement) en p. 1
                # TODO à vérifier
                raise ValueError(f"Pas de 'Vu' en page 1\n{mdata_page}\n{pg_txt_body}")
            main_beg = pream_end
        else:
            # p. 2 et suivantes: la zone à analyser commence en haut de la page (les éléments de
            # template ayant été effacés au préalable)
            main_beg = 0
        # TODO si tout le texte a déjà été reconnu, ajouter le contenu de la page au doc et passer à la page suivante

        # 2. les "vu" et "considérant"
        if cur_state == "avant_arrete":
            vucons_beg = main_beg
            # la page contient-elle un "Arrête" ?
            m_arrete = P_ARRETE.search(pg_txt_body, main_beg)
            if m_arrete:
                # si oui, les "Vu" et "Considérant" de cette page sont à chercher avant "Arrête"
                vucons_end = m_arrete.start()
            else:
                # si non, les "Vu" et "Considérant" sont sur toute la page
                vucons_end = main_end
            # repérer les "Vu" et "Considérant"
            vucons_content = parse_page_content(
                pg_txt_body, vucons_beg, vucons_end, cur_state, latest_span
            )  # FIXME spécialiser la fonction pour restreindre aux "Vu" et "Considérant" et/ou passer cur_state? ; NB: ces deux types de paragraphes admettent des continuations
            pg_content.extend(vucons_content)
            if vucons_content:
                latest_span = (
                    None  # le dernier empan de la page précédente n'est plus disponible
                )

            # si "Arrête" était bien sur la page, il faut ajouter l'empan reconnu, déplacer le curseur et changer d'état
            if m_arrete:
                arrete_beg, arrete_end = m_arrete.span("par_arrete")
                pg_content.append(
                    {
                        "span_beg": arrete_beg,
                        "span_end": arrete_end,
                        "span_txt": m_arrete.group("par_arrete"),
                        "span_typ": "par_arrete",
                    }
                )
                main_beg = arrete_end
                latest_span = (
                    None  # le dernier empan de la page précédente n'est plus disponible
                )
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
            try:
                artic_content = parse_page_content(
                    pg_txt_body, artic_beg, artic_end, cur_state, latest_span
                )  # FIXME spécialiser la fonction pour restreindre aux "Vu" et "Considérant" et/ou passer cur_state? ; NB: ces deux types de paragraphes admettent des continuations
            except TypeError:
                print(f"Fichier fautif: {filename}, p. {i}")
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
                    f"{filename} / p.{i} : pas de paragraphe sur l'empan {main_beg}:{main_end}\ncontenu:{pg_content}\ntexte:\n{pg_txt_body}"
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
    examine_doc_content(filename, doc_content)
    #
    return doc_content


def parse_arrete(fp_txt_in: Path) -> list:
    """Analyse un arrêté pour le découper en zones.

    Parameters
    ----------
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    doc_content: list[dict]
        Contenu du document, par page découpée en zones de texte.
    """
    pages = load_pages_text(fp_txt_in)
    # exclure la dernière page si c'est une page d'accusé de réception d'actes
    lst_page = pages[-1]
    if m_accuse := P_ACCUSE.match(lst_page):
        pages = pages[:-1]
    doc_content = parse_arrete_pages(fp_txt_in.name, pages)
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

""""""

# TODO remplacer les listes de documents à exclure, dressées manuellement, par une procédure de détection automatique

import argparse
from collections import OrderedDict
from datetime import datetime, date
import itertools
import logging
from pathlib import Path
import shutil
from typing import Dict, List
from src.utils.text_utils import create_file_name_url


import pandas as pd
import numpy as np

from src.domain_knowledge.actes import P_ACCUSE
from src.domain_knowledge.adresse import (
    create_adresse_normalisee,
    normalize_adresse,
)
from src.domain_knowledge.agences_immo import (
    P_CABINET,
    P_NOMS_CABINETS,
    normalize_nom_cabinet,
)
from src.domain_knowledge.cadastre import generate_refcadastrale_norm, get_parcelles
from src.domain_knowledge.codes_geo import (
    get_codeinsee,
    get_codepostal,
    normalize_ville,
)
from src.domain_knowledge.logement import (
    P_MONSIEUR_MADAME,
    get_adr_doc,
    get_gest,
    get_proprio,
    get_syndic,
)
from src.domain_knowledge.typologie_securite import (
    get_classe,
    get_demo,
    get_equ_com,
    get_int_hab,
    get_urgence,
)
from src.preprocess.data_sources import (
    EXCLUDE_FILES,
    EXCLUDE_FIXME_FILES,
    EXCLUDE_HORS_AMP,
)
from src.preprocess.extract_text_ocr import DTYPE_META_NTXT_OCR
from src.process.export_data import (
    DTYPE_ADRESSE,
    DTYPE_ARRETE,
    DTYPE_NOTIFIE,
    DTYPE_PARCELLE,
)
from src.process.extract_data import determine_commune, detect_digital_signature
from src.process.parse_doc import parse_arrete_pages
from src.quality.validate_parses import generate_html_report
from src.utils.str_date import process_date_brute
from src.utils.text_utils import normalize_string, remove_accents
from src.utils.txt_format import load_pages_text


# TODO déplacer dans un fichier dotenv ?
# URL stable pour les PDF: "yyyy" sera remplacé par l'année de l'arrêté, "pdf" par le nom du fichier
FS_URL = "https://sig.ampmetropole.fr/geodata/geo_arretes_peril/pdf_analyses/{commune}/{yyyy}/{pdf}"
# URLs partielles pour les PDF qui n'ont pu être analysés complètement, à compléter manuellement après
# déplacement du fichier
# TODO forcer la cohérence entre le bout d'URL "pdf_a_reclasser" et les chemins de dossiers dans "process.sh"
FS_URL_NO_YEAR = "https://sig.ampmetropole.fr/geodata/geo_arretes_peril/pdf_analyses/pdf_a_reclasser/{commune}/{pdf}"
# URL de dernier recours, à mettre à jour manuellement
# TODO forcer la cohérence entre le bout d'URL "pdf_a_reclasser" et les chemins de dossiers dans "process.sh"
FS_URL_FALLBACK = "https://sig.ampmetropole.fr/geodata/geo_arretes_peril/pdf_analyses/pdf_a_reclasser/{pdf}"
# 13055 with date
FS_URL_13055 = "https://sig.ampmetropole.fr/geodata/geo_arretes_peril/pdf_analyses/pdf_a_reclasser/13055/{yyyy}/{pdf}"


# 4 fichiers CSV seront générés
OUT_BASENAMES = {
    x: f"paquet_{x}.csv" for x in ["arrete", "adresse", "parcelle", "notifie"]
}


def enrich_adresse(fn_pdf: str, adresse: dict, commune_maire: str) -> Dict:
    """Consolide et enrichit une adresse, avec ville et codes (INSEE et code postal).

    Harmonise et complète les informations extraites de l'adresse visée à partir
    des informations extraites du template ou de l'autorité prenant l'arrêté.
    Ajoute une adresse normalisée.

    Parameters
    ----------
    fn_pdf: str
        Nom du fichier PDF (pour debug).
    adresse: dict
        Adresse visée par le document.
    commune_maire: str
        Ville extraite du template ou de l'autorité prenant l'arrêté.

    Returns
    -------
    adresse_enr: dict
        Adresse enrichie et augmentée.
    """
    adresse_enr = adresse.copy()
    # - déterminer la commune de l'adresse visée par l'arrêté en reconciliant la commune mentionnée
    # dans cette adresse avec celle extraite des mentions de l'autorité ou du template
    adresse_enr["ville"] = determine_commune(adresse_enr["ville"], commune_maire)
    if not adresse_enr["ville"]:
        logging.warning(
            f"{fn_pdf}: impossible de déterminer la commune: {adresse_enr['ville'], commune_maire}"
        )
    # - déterminer le code INSEE de la commune
    # FIXME communes hors Métropole: le filtrage sera-t-il fait en amont, lors de l'extraction depuis actes? sinon AssertionError ici
    try:
        codeinsee = get_codeinsee(adresse_enr["ville"], adresse_enr["cpostal"])
    except AssertionError:
        print(
            f"{fn_pdf}: get_codeinsee(): adr_ville={adresse_enr['ville']}, adr_cpostal={adresse_enr['cpostal']}"
        )
        print(f"{adresse}")
        raise
    else:
        if not codeinsee:
            logging.warning(
                f"{fn_pdf}: impossible de déterminer le code INSEE: {adresse_enr['ville'], adresse_enr['cpostal']}"
            )
    # - si l'adresse ne contenait pas de code postal, essayer de déterminer le code postal
    # à partir du code INSEE de la commune (ne fonctionne pas pour Aix-en-Provence)
    if not adresse_enr["cpostal"]:
        adresse_enr["cpostal"] = get_codepostal(adresse_enr["ville"], codeinsee)
        if not adresse_enr["cpostal"]:
            logging.warning(
                f"{fn_pdf}: Pas de code postal: adr_brute={adresse_enr['ad_brute']}, commune={adresse_enr['ville']}, code_insee={codeinsee}, get_codepostal={adresse_enr['cpostal']}"
            )
    # - créer une adresse normalisée ; la cohérence des champs est vérifiée
    adresse_enr = normalize_adresse(adresse_enr)
    if adresse_enr["ad_brute"]:
        adresse_enr["adresse"] = create_adresse_normalisee(
            adresse_enr["num"],
            adresse_enr["ind"],
            adresse_enr["voie"],
            adresse_enr["compl"],
            adresse_enr["cpostal"],
            adresse_enr["ville"],
        )
    else:
        adresse_enr["adresse"] = None
    # - positionner finalement le code INSEE
    adresse_enr["codeinsee"] = codeinsee

    return adresse_enr


def extract_adresses_commune(
    fn_pdf: str, pg_txt_body: str, commune_maire: str
) -> List[Dict]:
    """Extraire les adresses visées par l'arrêté, et la commune.

    Parameters
    ----------
    fn_pdf: string
        Nom du fichier PDF de l'arrêté (pour les messages de logs: warnings et erreurs)
    pg_txt_body: string
        Corps de texte de la page
    commune_maire: string
        Mention de la commune extraite de l'autorité prenant l'arrêté,
        ou des

    Returns
    -------
    adresses: list(dict)
        Adresses visées par l'arrêté
    """
    try:
        adresses_visees = get_adr_doc(pg_txt_body)
    except AssertionError:
        logging.error(f"{fn_pdf}: problème d'extraction d'adresse")
        raise
    # if fn_pdf == "périmètre de sécurité 82 Hoche 105 Kleber 13003.pdf":
    #     print(f"{commune_maire}, {adresses_visees}")
    #     # raise ValueError("don't stop me now (too soon)")

    if not adresses_visees:
        adr = {
            # adresse brute
            "ad_brute": None,
            # champs
            "num": None,
            "ind": None,
            "voie": None,
            "compl": None,
            "cpostal": None,
            "ville": None,
            # adresse propre
            "adresse": None,
        }
        adr_enr = enrich_adresse(fn_pdf, adr, commune_maire)
        return [adr_enr]

    # renommer les champs
    # TODO le faire dans get_adr_doc et adapter le code dans les autres modules
    adresses_visees = [
        {
            "ad_brute": x["adresse_brute"],
            "adresses": [
                {k.replace("adr_", ""): v for k, v in y.items()} for y in x["adresses"]
            ],
        }
        for x in adresses_visees
    ]

    # prendre la 1re zone d'adresses reconnue dans le texte (heuristique)
    # TODO en repérer d'autres? incertain
    adr0 = adresses_visees[0]
    adresse_brute = adr0["ad_brute"]
    # TODO améliorer les résultats par une collecte plus exhaustive (qui nécessiterait le dédoublonnage) ou une meilleure heuristique ?
    # extraire la ou les adresses de cette zone
    # (on supprime au passage les préfixes "adr_" des noms des champs, archaïsme à corriger plus tard éventuellement)
    adresses = [({"ad_brute": adresse_brute} | x) for x in adr0["adresses"]]
    if not adresses:
        logging.error(
            f"{fn_pdf}: aucune adresse extraite de la zone d'adresse(s): {adresse_brute}"
        )

    if len(adresses_visees) > 1:
        # si la 1re adresse n'a pas de code postal, tenter de récupérer le code postal des adresses suivantes
        # on construit 2 mappings:
        # - (num, voie) => cp
        numvoie2cp = dict()
        # - voie => cp  # fallback, quand la mention d'adresse extraite ne contient pas de numéro (mais une mention ultérieure, oui)
        voie2cp = dict()
        # on itère sur l'ensemble des adresses extraites du document pour créer une table d'association vers les codes postaux
        for x in adresses_visees:
            for y in x["adresses"]:
                if y["cpostal"]:
                    norm_voie = normalize_string(
                        remove_accents(y["voie"]),
                        num=True,
                        apos=True,
                        hyph=True,
                        spaces=True,
                    ).lower()
                    # (numéro, voie) -> cp
                    numvoie2cp[(y["num"], norm_voie)] = y["cpostal"]
                    # fallback: voie -> cp
                    voie2cp[norm_voie] = y["cpostal"]  # WIP 2023-05-09
        # print(numvoie2cp)

        for sel_adr in adresses:
            # pour chaque adresse considérée comme étant visée par l'arrêté
            if sel_adr["voie"] and not sel_adr["cpostal"]:
                # si on a une voie mais pas de code postal, on essaie de renseigner
                # le code postal par propagation à partir des autres adresses
                norm_voie = normalize_string(
                    remove_accents(sel_adr["voie"]),
                    num=True,
                    apos=True,
                    hyph=True,
                    spaces=True,
                ).lower()
                if sel_adr["num"]:
                    # si on a un numéro de voie (c'est l'idéal, car le code postal est normalement unique)
                    sel_short = (sel_adr["num"], norm_voie)
                    # print(f">>>>>> sel_short: {sel_short}")
                    sel_adr["cpostal"] = numvoie2cp.get(sel_short, None)
                else:
                    # sans numéro de voie, on recourt au tableau associatif sans numéro
                    sel_adr["cpostal"] = voie2cp.get(norm_voie, None)  # WIP 2023-05-09

    # if fn_pdf == "90 cours Sextius - ML.pdf":
    #     print(f"{adresses_visees}\n{numvoie2cp}\n{adresses}")
    #     raise ValueError("don't stop me now")
    #     pass

    # si besoin d'une alternative: déterminer commune, code INSEE et code postal pour les adresses[0] et propager les valeurs aux autres adresses
    adresses_enr = [enrich_adresse(fn_pdf, x, commune_maire) for x in adresses]
    return adresses_enr


def parse_arrete(fp_pdf_in: Path, fp_txt_in: Path) -> dict:
    """Analyse un arrêté et extrait les données qu'il contient.

    L'arrêté est découpé en paragraphes puis les données sont
    extraites.

    Parameters
    ----------
    fp_pdf_in : Path
        Fichier PDF source (temporairement?)
    fp_txt_in : Path
        Fichier texte à analyser.

    Returns
    -------
    doc_data : dict
        Données extraites du document.
    """
    fn_pdf = fp_pdf_in.name
    fn_pdf_out = create_file_name_url(fn_pdf)

    pages = load_pages_text(fp_txt_in)
    if not any(pages):
        logging.warning(f"{fp_txt_in}: aucune page de texte")
        arr_url = FS_URL_FALLBACK.format(pdf=fn_pdf_out)
        logging.warning(f"URL temporaire (sans code commune ni année): {arr_url}")
        return {
            "adresses": [],
            "arretes": [
                {
                    "pdf": fn_pdf,
                    "url": arr_url,
                }
            ],
            "notifies": [],
            "parcelles": [],
        }

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
    doc_content = parse_arrete_pages(fn_pdf, filt_pages)

    # extraire les données
    adresses = []
    arretes = {}  # un seul
    notifies = {
        "proprios": OrderedDict(),  # propriétaires
        "syndics": OrderedDict(),  # syndic (normalement unique)
        "gests": OrderedDict(),  # gestionnaire (normalement unique)
    }
    parcelles = OrderedDict()  # références de parcelles cadastrales

    # - au préalable, rassembler toutes les données en ajoutant le numéro de page (FIXME)
    pages_body = [pg_cont["body"] for pg_cont in doc_content]
    # pages_cont = [pg_cont["content"] for pg_cont in doc_content]  # future
    pages_cont = []
    for pg_num, pg_cont in enumerate(doc_content, start=1):
        # pg_template = page_cont["template"]
        # pg_content = page_cont["content"]  # future
        # FIXME ajouter "page_num" en amont, dans parse_arrete_pages()
        pages_cont.extend([({"page_num": pg_num} | x) for x in pg_cont["content"]])

    # extraire les champs un par un:
    # - arrêté
    arr_dates = [
        process_date_brute(x["span_txt"])
        for x in pages_cont
        if x["span_typ"] == "arr_date"
    ]

    if not arr_dates:
        arr_date = detect_digital_signature(fp_pdf_in)
        if arr_date:
            arr_dates = [arr_date]
        else:
            logging.warning(f"{fn_pdf}: pas de date d'arrêté trouvée")

    if arr_dates:
        arretes["date"] = normalize_string(
            arr_dates[0], num=True, apos=True, hyph=True, spaces=True
        )
    arr_nums = [x["span_txt"] for x in pages_cont if x["span_typ"] == "num_arr"]
    if arr_nums:
        arretes["num_arr"] = normalize_string(
            arr_nums[0], num=True, apos=True, hyph=True, spaces=True
        )
    arr_noms = [x["span_txt"] for x in pages_cont if x["span_typ"] == "nom_arr"]
    if arr_noms:
        arretes["nom_arr"] = normalize_string(
            arr_noms[0], num=True, apos=True, hyph=True, spaces=True
        )

    # - commune extraite des mentions de l'autorité prenant l'arrêté, ou du template du document
    adrs_commune_maire = [x for x in pages_cont if x["span_typ"] == "adr_ville"]
    # - prendre arbitrairement la 1re mention et la nettoyer a minima
    # TODO regarder les erreurs et vérifier si un autre choix donnerait de meilleurs résultats
    # TODO tester: si > 1, tester de matcher avec la liste des communes de la métropole
    # (et éventuellement calculer la distance de Levenshtein pour vérifier s'il est vraisemblable
    # que ce soient des variantes de graphie ou erreurs)
    if not adrs_commune_maire:
        adr_commune_maire = None
    else:
        adr_commune_maire = normalize_string(
            adrs_commune_maire[0]["span_txt"],
            num=True,
            apos=True,
            hyph=True,
            spaces=True,
        )
        # remplacer par la forme canonique (communes AMP)
        adr_commune_maire = normalize_ville(adr_commune_maire)
    logging.warning(f"adrs_commune_maire: {adrs_commune_maire}")  # DEBUG
    logging.warning(f"adr_commune_maire: {adr_commune_maire}")  # DEBUG
    #
    # parcelles
    codeinsee = None  # valeur par défaut
    cpostal = None  # valeur par défaut
    for pg_txt_body in pages_body:
        if pg_txt_body:
            # extraire les informations sur l'arrêté
            if "classe" not in arretes and (classe := get_classe(pg_txt_body)):
                arretes["classe"] = classe
            if "urgence" not in arretes and (urgence := get_urgence(pg_txt_body)):
                arretes["urgence"] = urgence
            if "demo" not in arretes and (demo := get_demo(pg_txt_body)):
                arretes["demo"] = demo
            if "int_hab" not in arretes and (int_hab := get_int_hab(pg_txt_body)):
                arretes["int_hab"] = int_hab
            if "equ_com" not in arretes and (equ_com := get_equ_com(pg_txt_body)):
                arretes["equ_com"] = equ_com
            if "pdf" not in arretes:
                arretes["pdf"] = fn_pdf

            # extraire la ou les adresse(s) visée(s) par l'arrêté détectées sur cette page
            if not adresses:
                # pour le moment, on se contente de la première page contenant au moins une zone d'adresse,
                # et sur cette page, de la première zone d'adresse trouvée ;
                # une zone peut contenir une ou plusieurs adresses obtenues par "dépliage" (ex: 12 - 14 rue X)
                # TODO examiner les erreurs et déterminer si une autre stratégie donnerait de meilleurs résultats
                # si une adresse a déjà été ajoutée mais qu'elle n'a été remplie que grâce à commune_maire
                pg_adresses = extract_adresses_commune(
                    fn_pdf, pg_txt_body, adr_commune_maire
                )
                if pg_adresses:
                    adresses.extend(pg_adresses)
                    # WIP on prend le code INSEE et code postal de la 1re adresse
                    # print(adrs_doc)
                    cpostal = adresses[0]["cpostal"]
                    codeinsee = adresses[0]["codeinsee"]
                    if ("codeinsee" not in arretes) and codeinsee:
                        arretes["codeinsee"] = codeinsee
            elif len(adresses) == 1 and not adresses[0]["ad_brute"]:
                # si une adresse a déjà été ajoutée mais qu'elle n'a été remplie que grâce à commune_maire
                # (donc ne contient qu'une commune), on en cherche une plus précise sur la page suivante,
                # à tout hasard
                pg_adresses = extract_adresses_commune(
                    fn_pdf, pg_txt_body, adr_commune_maire
                )
                if pg_adresses and pg_adresses[0]["ad_brute"]:
                    # on a bien extrait au moins une adresse du texte, on remplace l'adresse contenant
                    # seulement une commune
                    adresses = pg_adresses
                    # WIP on prend le code INSEE et code postal de la 1re adresse
                    # print(adrs_doc)
                    cpostal = adresses[0]["cpostal"]
                    codeinsee = adresses[0]["codeinsee"]
                    if codeinsee:
                        # on remplace le code commune INSEE pour tout le document
                        arretes["codeinsee"] = codeinsee

            # extraire les notifiés
            if proprios := get_proprio(pg_txt_body):
                norm_proprios = normalize_string(
                    proprios, num=True, apos=True, hyph=True, spaces=True
                )
                notifies["proprios"][
                    norm_proprios
                ] = proprios  # WIP: proprios = [] + extend()
            if syndics := get_syndic(pg_txt_body):
                norm_syndics = normalize_string(
                    syndics, num=True, apos=True, hyph=True, spaces=True
                )
                notifies["syndics"][
                    norm_syndics
                ] = syndics  # WIP: syndics = [] + extend ?

            if gests := get_gest(pg_txt_body):
                norm_gests = normalize_string(
                    gests, num=True, apos=True, hyph=True, spaces=True
                )
                notifies["gests"][norm_gests] = gests  # WIP: gests = [] + extend ?

            # extraire la ou les parcelles visées par l'arrêté
            if pg_parcelles_str_list := get_parcelles(pg_txt_body):
                # TODO supprimer les références partielles (ex: Marseille mais sans code quartier) si la référence complète est aussi présente dans le doc
                refcads_norm = [
                    generate_refcadastrale_norm(
                        codeinsee, pg_parcelles_str, fn_pdf, cpostal
                    )
                    for pg_parcelles_str in pg_parcelles_str_list
                ]
                parcelles = parcelles | OrderedDict(
                    zip(refcads_norm, pg_parcelles_str_list)
                )  # WIP get_parcelles:list()
    if False:
        # WIP hypothèses sur les notifiés
        try:
            assert len(notifies["proprios"]) <= 1
            assert len(notifies["syndics"]) <= 1
            assert len(notifies["gests"]) <= 1
        except AssertionError:
            print(f"{notifies}")
            raise
    # déplacer le PDF et déterminer l'URL
    if "codeinsee" in arretes:
        if "date" in arretes:
            # ré-extraire l'année de la date formatée
            # TODO stocker l'année dans un champ dédié, au moment de l'extraction et normalisation
            # de la date, et le récupérer ici?
            # code correct:
            # arr_year = datetime.strptime(arretes["date"], "%d/%m/%Y").date().year
            # mais ne fonctionne pas sur des dates mal reconnues (OCR) ex: "00/02/2022"
            # alors qu'on peut extraire l'année
            arr_year = arretes["date"].rsplit("/", 1)[1]
            arr_comm = arretes["codeinsee"]

            if arretes["codeinsee"] != "13055":
                arretes["url"] = FS_URL.format(
                    commune=arretes["codeinsee"], yyyy=arr_year, pdf=fn_pdf_out
                )
            else:
                # cas particulier de marseille 13055 => besoin de reclasser manuellement même si on a l'année
                arretes["url"] = FS_URL_13055.format(yyyy=arr_year, pdf=fn_pdf_out)
                logging.warning(f"URL temporaraire (13055): {arretes['url']}")
        else:
            arretes["url"] = FS_URL_NO_YEAR.format(
                commune=arretes["codeinsee"], pdf=fn_pdf_out
            )
            logging.warning(f"URL temporaire (sans année): {arretes['url']}")
    else:
        # ("codeinsee" not in arretes)
        # dans le pire cas: (arretes == {})
        arretes = {"pdf": fn_pdf, "url": FS_URL_FALLBACK.format(pdf=fn_pdf_out)}
        logging.warning(
            f"URL temporaire (sans code commune ni année): {arretes['url']}"
        )

    # notifies
    # formes brutes puis normalisées
    # * propriétaires
    id_proprio = list(notifies["proprios"])[0] if notifies["proprios"] else None
    proprio = id_proprio  # TODO appliquer une normalisation?
    # * syndic
    id_syndic = list(notifies["syndics"])[0] if notifies["syndics"] else None
    if (
        id_syndic is not None
        and (P_NOMS_CABINETS.search(id_syndic) is None)
        and (P_CABINET.search(id_syndic) is None)
        and (P_MONSIEUR_MADAME.search(id_syndic) is not None)
    ):
        # si le champ "id_syndic" ne contient pas de mention de cabinet ou d'agence,
        # et contient une référence à une personne physique,
        # alors la valeur normalisée est "syndic bénévole"
        # TODO si on observe trop de faux positifs, mettre en place une condition
        # plus restrictive sur la chaîne "bénévole"
        syndic = "Syndic bénévole"
    else:
        # sinon, valeur normalisée (fallback: id_syndic)
        syndic = normalize_nom_cabinet(id_syndic)
    # * gestionnaire
    id_gest = list(notifies["gests"])[0] if notifies["gests"] else None
    # valeur normalisée (fallback: id_syndic)
    gest = normalize_nom_cabinet(id_gest)
    #

    code_insee = arretes["codeinsee"] if "codeinsee" in arretes else None
    doc_data = {
        "adresses": (
            adresses
            if adresses
            else [
                {
                    "ad_brute": None,
                    "num": None,
                    "ind": None,
                    "voie": None,
                    "compl": None,
                    "cpostal": None,
                    "ville": None,
                    "adresse": None,
                    "codeinsee": code_insee,
                }
            ]
        ),
        "arretes": [arretes],  # a priori un seul par fichier
        "notifies": [
            {
                "id_proprio": id_proprio,
                "proprio": proprio,  # forme normalisée
                "id_syndic": id_syndic,
                "syndic": syndic,  # forme normalisée
                "id_gest": id_gest,
                "gest": gest,  # forme normalisée
                "codeinsee": codeinsee,
            }
        ],  # a priori un seul par fichier (pour le moment)
        "parcelles": (
            [{"ref_cad": x, "codeinsee": codeinsee} for x in parcelles]
            if parcelles
            else [{"ref_cad": None, "codeinsee": code_insee}]
        ),
    }
    return doc_data


def process_files(
    df_in: pd.DataFrame,
    out_dir: Path,
    date_exec: date,
) -> Dict[str, Path]:
    """Analyse le texte des fichiers PDF extrait dans des fichiers TXT.

    Parameters
    ----------
    df_in: pd.DataFrame
        Fichier meta_$RUN_otxt.csv contenant les métadonnées enrichies et
        les fichiers PDF et TXT (natif ou OCR) à traiter.
    out_dir : Path
        Dossier de sortie
    date_exec : date
        Date d'exécution du script, utilisée pour (a) le nom des copies de fichiers CSV
        incluant la date de traitement, (b) l'identifiant unique des arrêtés dans les 4
        tables, (c) le champ 'datemaj' initialement rempli avec la date d'exécution.

    Returns
    -------
    out_files : Dict[str, Path]
        Fichiers CSV produits, contenant les données extraites.
        Dictionnaire indexé par les clés {"adresse", "arrete", "notifie", "parcelle"}.
    """
    # - les fichiers CSV datés sont stockés dans un sous-dossier "csv_historique"
    out_dir_csv = out_dir / "csv_historique"
    logging.info(
        f"Sous-dossier de sortie: {out_dir_csv} {'existe déjà' if out_dir_csv.is_dir() else 'va être créé'}."
    )
    out_dir_csv.mkdir(parents=True, exist_ok=True)
    # - les fichiers PDF à reclasser sont stockés dans un sous-dossier (temporaire) "pdf_a_reclasser"
    out_dir_pdf_areclass = out_dir / "pdf_analyses/pdf_a_reclasser"
    logging.info(
        f"Sous-dossier de sortie: {out_dir_pdf_areclass} {'existe déjà' if out_dir_pdf_areclass.is_dir() else 'va être créé'}."
    )
    out_dir_pdf_areclass.mkdir(parents=True, exist_ok=True)
    # - les fichiers TXT extraits nativement ou par OCR dans un sous-dossier "txt"
    out_dir_txt = out_dir / "txt"
    logging.info(
        f"Sous-dossier de sortie: {out_dir_txt} {'existe déjà' if out_dir_txt.is_dir() else 'va être créé'}."
    )
    out_dir_txt.mkdir(parents=True, exist_ok=True)

    # 0. charger la liste des PDF déjà traités, définis comme les PDF déjà
    # présents dans un des fichiers "paquet_arrete_*.csv"
    fps_paquet_arrete = sorted(
        out_dir_csv.glob(
            f"paquet_arrete_[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_[0-9][0-9].csv"
        )
    )
    pdfs_old = []
    for fp_paquet_arrete in fps_paquet_arrete:
        df_arr_old = pd.read_csv(fp_paquet_arrete, dtype=DTYPE_ARRETE, sep=";")
        pdfs_old.extend(df_arr_old["pdf"])
    pdfs_old = set(pdfs_old)

    # 1. déterminer le nom des fichiers de sortie
    # les noms des fichiers de sortie incluent:
    # - la date de traitement (ex: "2023-05-30")
    date_proc_dash = date_exec.strftime("%Y-%m-%d")
    # - le numéro d'exécution ce jour (ex: "02"), calculé en recensant les
    # éventuels fichiers existants
    out_prevruns = sorted(
        itertools.chain.from_iterable(
            out_dir_csv.glob(f"paquet_{x}_{date_proc_dash}_[0-9][0-9].csv")
            for x in OUT_BASENAMES
        )
    )
    #    - numéro d'exécution du script ce jour
    i_run = 0  # init
    for fp_prevrun in out_prevruns:
        # le numéro se trouve à la fin du stem, après le dernier séparateur "_"
        fp_out_idx = int(fp_prevrun.stem.split("_")[-1])
        i_run = max(i_run, fp_out_idx)
    i_run += 1  # on prend le numéro d'exécution suivant
    # résultat: fichiers générés par cette exécution
    out_files = {
        x: out_dir_csv / f"paquet_{x}_{date_proc_dash}_{i_run:>02}.csv"
        for x in OUT_BASENAMES
    }

    # 2. déterminer le premier identifiant unique (idu) des prochaines entrées:
    # il suit le dernier idu généré par les exécutions précédentes le même jour
    i_idu = 0  # init
    for fp_prevrun in out_prevruns:
        # ouvrir le fichier, lire les idus, prendre le dernier, extraire l'index
        s_idus = pd.read_csv(
            fp_prevrun, usecols=["idu"], dtype={"idu": "string"}, sep=";"
        )["idu"]
        max_idx = s_idus.str.rsplit("-", n=1, expand=True)[1].astype("int32").max()
        i_idu = max(i_idu, max_idx)
    i_idu += 1  # on prend le numéro d'arrêté suivant

    # 3. filtrer les arrêtés
    # - filtrer les documents hors périmètre thématique ou géographique ?
    # TODO vérifier si ok sans liste d'exclusion ici ; sinon corriger avant déploiement?
    # df_in["pdf"].str.split("-", 1)[0] not in set(EXCLUDE_FILES + EXCLUDE_FIXME_FILES)  # + EXCLUDE_HORS_AMP)
    #
    # - filtrer les fichiers déjà traités: ne garder que les PDF qui ne
    # sont pas déjà présents dans un "paquet_arrete_*.csv"
    pdfs_in_old = set(df_in["pdf"].tolist()).intersection(pdfs_old)

    # vérifier que le fichier PDF existe bien dans les dossiers destination,
    # pdf_a_reclasser ou un dossier de commune,
    # sinon il faut le traiter comme s'il était complètement nouveau
    already_proc = []
    # sous-dossiers par code commune (INSEE), sur 5 chiffres
    out_dir_analyses = out_dir / "pdf_analyses"
    out_dir_pdf_communes = [
        d for d in out_dir_analyses.glob("[0-9][0-9][0-9][0-9][0-9]") if d.is_dir()
    ]

    for fn in pdfs_in_old:
        fn_url = create_file_name_url(fn)
        areclass = sorted(out_dir_pdf_areclass.rglob(fn_url))
        bienclas = []
        for directory in out_dir_pdf_communes:
            bienclas += sorted(directory.rglob(fn_url))

        if areclass or bienclas:
            logging.warning(
                f"Fichier à ignorer car déjà traité: {areclass[0] if areclass else bienclas[0]}"
            )
            print(
                f"\n/!\\ Fichier à ignorer car déjà traité: {areclass[0] if areclass else bienclas[0]}"
            )
            already_proc.append(fn)
    already_proc = set(already_proc)
    #
    s_dups = df_in["pdf"].isin(already_proc)
    if any(s_dups):
        logging.info(
            f"{s_dups.sum()} fichiers seront déplacés dans 'doublons/'"
            + " et ne seront pas retraités, car ils sont déjà présents"
            + " dans un fichier 'paquet_arrete_*.csv' de 'csv_historique/'"
            + " et dans un dossier de commune"
            + " ou 'pdf_a_reclasser' ."
        )
        # déplacer les fichiers déjà traités dans doublons/
        # (plus prudent que de les supprimer d'emblée)
        out_dups = out_dir_analyses / "doublons"
        out_dups.mkdir(exist_ok=True)
        #
        df_dups = df_in[s_dups]
        for df_row in df_dups.itertuples():
            fp = Path(df_row.fullpath)
            fp_dst = out_dups / fp.name
            shutil.move(fp, fp_dst)
            # si le move a réussi, on peut supprimer le fichier dans le dossier d'entrée
            if fp_dst.is_file():
                fp_orig = Path(df_row.origpath)
                fp_orig.unlink()

    #
    df_in = df_in[~s_dups]
    # si après filtrage, df_in est vide, aucun fichier CSV ne sera produit
    # et on peut sortir immédiatement
    if df_in.empty:
        return {}

    # 4 tables de sortie
    rows_adresse = []
    rows_arrete = []
    rows_notifie = []
    rows_parcelle = []

    # date de traitement, en 2 formats
    date_proc = date_exec.strftime("%Y%m%d")  # pour "idu" (id uniques des arrêtés)
    datemaj = date_exec.strftime("%d/%m/%Y")  # pour "datemaj" des 4 tables

    # identifiant des entrées dans les fichiers de sortie: <type arrêté>-<date du traitement>-<index>
    # itérer sur les fichiers PDF et TXT
    for i, df_row in enumerate(df_in.itertuples(), start=i_idu):
        # fichier PDF
        fp_pdf = Path(df_row.fullpath)
        if not fp_pdf.is_file():
            raise ValueError(f"{fp_pdf}: fichier PDF introuvable ({fp_txt})")
        # fichier TXT (OCR sinon natif)
        fp_txt = Path(df_row.fullpath_txt)
        if not fp_txt.is_file():
            raise ValueError(f"{fp_pdf}: fichier TXT introuvable ({fp_txt})")

        # type d'arrêté ; à date, seulement des arrêtés de péril "AP" ;
        # à l'avenir, pourrait être prédit à partir du texte, avec un classifieur
        type_arr = "AP"
        # identifiant unique du document dans les tables de sortie (paquet_*.csv):
        # TODO détecter le ou les éventuels fichiers déjà produits ce jour, écarter les doublons (blake2b?)
        # et initialiser le compteur à la prochaine valeur
        # format: {type d'arrêté}-{date}-{id relatif, sur 4 chiffres}
        idu = f"{type_arr}-{date_proc}-{i:04}"
        # analyser le texte
        doc_data = parse_arrete(fp_pdf, fp_txt)

        # ajouter des entrées dans les 4 tables
        rows_adresse.extend(
            ({"idu": idu} | x | {"datemaj": datemaj}) for x in doc_data["adresses"]
        )
        rows_arrete.extend(
            ({"idu": idu} | x | {"datemaj": datemaj}) for x in doc_data["arretes"]
        )
        rows_notifie.extend(
            ({"idu": idu} | x | {"datemaj": datemaj}) for x in doc_data["notifies"]
        )
        rows_parcelle.extend(
            ({"idu": idu} | x | {"datemaj": datemaj}) for x in doc_data["parcelles"]
        )

    # créer les 4 DataFrames et les exporter en CSV
    for key, rows, dtype in [
        ("adresse", rows_adresse, DTYPE_ADRESSE),
        ("arrete", rows_arrete, DTYPE_ARRETE),
        ("notifie", rows_notifie, DTYPE_NOTIFIE),
        ("parcelle", rows_parcelle, DTYPE_PARCELLE),
    ]:
        out_file = out_files[key]
        df = pd.DataFrame.from_records(rows)

        for dtype_key, _ in dtype.items():
            if dtype_key not in df.columns:
                df[dtype_key] = np.nan

        df = df.astype(dtype=dtype)
        df.to_csv(out_file, index=False, sep=";")

    # déplacer les fichiers PDF traités ;
    # le code est redondant avec celui utilisé pour remplir le champ d'URL
    # mais on fait les déplacements de fichiers après l'écriture du dataframe
    # pour éviter de déplacer le fichier si les CSV ne sont finalement pas
    # produits (eg. à cause d'un échec sur un autre document)
    df_arr = pd.read_csv(out_files["arrete"], dtype=DTYPE_ARRETE, sep=";")
    for df_row in df_arr.itertuples():
        # nom du PDF (incluant hash)
        fn = df_row.pdf
        # déterminer le dossier destination
        if pd.notna(df_row.codeinsee):
            commune = df_row.codeinsee
            if pd.notna(df_row.date):
                # code correct
                # year = str(datetime.strptime(df_row.date, "%d/%m/%Y").date().year)
                # mais ne fonctionne pas sur des dates mal reconnues (OCR) ex: "00/02/2022"
                # alors qu'on peut extraire l'année
                year = df_row.date.rsplit("/", 1)[1]

                if commune != "13055":
                    dest_dir = out_dir / "pdf_analyses" / commune / year
                else:
                    # cas particulier de marseille 13055 => besoin de reclasser manuellement même si on a l'année
                    dest_dir = out_dir / "pdf_analyses/pdf_a_reclasser/13055" / year
            else:
                dest_dir = out_dir / "pdf_analyses/pdf_a_reclasser" / commune
        else:
            dest_dir = out_dir / "pdf_analyses/pdf_a_reclasser"
        # créer le dossier destination si besoin
        dest_dir.mkdir(parents=True, exist_ok=True)
        # retrouver l'entrée correspondance dans df_in, pour avoir le
        # chemin complet de sa copie (à déplacer) et du fichier original
        # (à supprimer)
        # .head(1) car normalement il y a *exactement une* entrée correspondante
        # et .itertuples() pour avoir facilement un namedtuple
        for df_row_in in df_in.loc[df_in["pdf"] == fn].head(1).itertuples():
            # chemin du fichier traité (copié depuis dir_in vers le dossier de travail)
            fp = Path(df_row_in.fullpath)
            # chemin du fichier d'origine (pour suppression après move)
            fp_orig = Path(df_row_in.origpath)
            # chemin destination du fichier traité
            print(fp.name)
            fp_dst = dest_dir / create_file_name_url(fp.name)
            print(fp_dst)
            print()

            shutil.move(fp, fp_dst)
            # si le move a réussi, on peut supprimer le fichier dans le dossier d'entrée
            if fp_dst.is_file():
                fp_orig.unlink()
            # chemin du fichier TXT (OCR sinon natif)
            fp_txt = Path(df_row_in.fullpath_txt)
            shutil.copy2(fp_txt, out_dir_txt / fp_txt.name)

    # faire une copie des 4 fichiers générés avec les noms de base (écraser chaque fichier
    # pré-existant ayant le nom de base)
    for fp_out in out_files.values():
        # retirer la date et le numéro d'exécution pour retrouver le nom de base
        fp_copy = (
            out_dir / fp_out.with_stem(f"{fp_out.stem.rsplit('_', maxsplit=2)[0]}").name
        )
        shutil.copy2(fp_out, fp_copy)

    return out_files


if __name__ == "__main__":
    # date et heure d'exécution
    dtim_exec = datetime.now()
    # date seulement (suffit pour les noms de fichiers CSV et les valeurs des colonnes
    # 'idu' et 'datemaj')
    date_exec = dtim_exec.date()

    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    if not dir_log.is_dir():
        dir_log.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=f"{dir_log}/parse_doc_direct_{dtim_exec.isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "meta_run_otxt",
        help="Fichier 'meta_$RUN_otxt.csv' contenant le lot de fichiers à traiter (métadonnées enrichies et chemins vers les fichiers PDF et TXT, natif ou OCR)",
    )
    parser.add_argument(
        "out_dir",
        help="Dossier de sortie pour les fichiers produits."
        + " Les 4 fichiers CSV (paquet_*.csv) sont rangés à la racine,"
        + " leur copie datée est conservée dans le dossier csv_historique/ ."
        + " Les fichiers PDF traités sont rangés dans des dossiers par code commune puis année (ex: 13201/2023/),"
        + " et en l'absence de code commune ou d'année dans le dossier temporaire pdf_a_reclasser/ .)",
    )
    args = parser.parse_args()

    # entrée: fichiers PDF et TXT
    meta_run_otxt = Path(args.meta_run_otxt).resolve()
    if not meta_run_otxt.is_file():
        raise ValueError(f"Impossible de trouver le fichier {meta_run_otxt}")
    df_in = pd.read_csv(meta_run_otxt, dtype=DTYPE_META_NTXT_OCR)

    # sortie: fichiers CSV générés
    # créer le dossier destination, récursivement, si besoin
    out_dir = Path(args.out_dir).resolve()
    logging.info(
        f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'va être créé'}."
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    #
    out_files = process_files(
        df_in,
        out_dir,
        date_exec=date_exec,
    )

    # update arrete pdf column with create_name to match the url
    df_arrete = pd.read_csv(out_files["arrete"], dtype=DTYPE_ARRETE, sep=";")
    df_arrete["pdf"] = df_arrete["pdf"].apply(lambda x: create_file_name_url(x))
    df_arrete.to_csv(out_files["arrete"], index=False, sep=";")
    df_arrete.to_csv(out_dir / "paquet_arrete.csv", index=False, sep=";")

    # générer le rapport d'erreurs
    run = out_files["adresse"].stem.split("_", 2)[2]
    dfs = {
        x: pd.read_csv(out_files[x], dtype=x_dtype, sep=";")
        for (x, x_dtype) in (
            ("adresse", DTYPE_ADRESSE),
            ("arrete", DTYPE_ARRETE),
            ("notifie", DTYPE_NOTIFIE),
            ("parcelle", DTYPE_PARCELLE),
        )
    }
    html_report = generate_html_report(
        run,
        dfs["adresse"],
        dfs["arrete"],
        dfs["notifie"],
        dfs["parcelle"],
    )
    out_dir_rapport = out_dir / "rapport_erreurs"
    logging.info(
        f"Sous-dossier de sortie: {out_dir_rapport} {'existe déjà' if out_dir_rapport.is_dir() else 'va être créé'}."
    )
    out_dir_rapport.mkdir(parents=True, exist_ok=True)
    fp_rapport = out_dir_rapport / f"rapport_{run}.html"
    with open(fp_rapport, mode="w") as f_rapport:
        f_rapport.write(html_report)

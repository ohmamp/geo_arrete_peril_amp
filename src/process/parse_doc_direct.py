"""Analyse un arrêté et en extrait les données.

"""

# TODO remplacer les listes de documents à exclure, dressées manuellement, par une procédure de détection automatique

import argparse
from collections import OrderedDict
from datetime import datetime, date
import itertools
import logging
from pathlib import Path
import shutil
from typing import Dict, List

import pandas as pd

from src.domain_knowledge.actes import P_ACCUSE
from src.domain_knowledge.adresse import (
    create_adresse_normalisee,
    normalize_adresse,
)
from src.domain_knowledge.cadastre import generate_refcadastrale_norm, get_parcelles
from src.domain_knowledge.codes_geo import (
    get_codeinsee,
    get_codepostal,
    normalize_ville,
)
from src.domain_knowledge.logement import get_adr_doc, get_gest, get_proprio, get_syndic
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
from src.process.export_data import (
    DTYPE_ADRESSE,
    DTYPE_ARRETE,
    DTYPE_NOTIFIE,
    DTYPE_PARCELLE,
)
from src.process.extract_data import determine_commune
from src.process.parse_doc import parse_arrete_pages
from src.utils.file_utils import get_file_digest
from src.utils.str_date import process_date_brute
from src.utils.text_utils import normalize_string, remove_accents
from src.utils.txt_format import load_pages_text


# URL stable pour les PDF: "yyyy" sera remplacé par l'année de l'arrêté, "pdf" par le nom du fichier
FS_URL = "https://sig.ampmetropole.fr/geodata/geo_arretes/peril/{yyyy}/{pdf}"


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
    fp_pdf_in: Path
        Fichier PDF source (temporairement?)
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    doc_data: dict
        Données extraites du document.
    """
    fn_pdf = fp_pdf_in.name

    pages = load_pages_text(fp_txt_in)
    if not any(pages):
        logging.warning(f"{fp_txt_in}: aucune page de texte")
        return {
            "adresses": [],
            "arretes": [
                {
                    "pdf": fn_pdf,
                    "url": fp_pdf_in,  # FS_URL.format(yyyy="unk", fn_pdf)  # TODO arretes["date"].dt.year ?
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
            if "url" not in arretes:
                arretes[
                    "url"
                ] = fp_pdf_in  # FS_URL.format(yyyy="unk", fn_pdf)  # TODO arretes["date"].dt.year ?

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

    # si parse_content() a renvoyé [], arretes vaut toujours {} mais on veut pdf et url
    # TODO corriger, c'est moche (et un peu fragile)
    if not arretes:
        arretes = {
            "pdf": fn_pdf,
            "url": fp_pdf_in,  # FS_URL.format(yyyy="unk", fn_pdf)  # TODO arretes["date"].dt.year ?
        }

    doc_data = {
        "adresses": adresses,
        "arretes": [arretes],  # a priori un seul par fichier
        "notifies": [
            {
                "id_proprio": list(notifies["proprios"])[0]
                if notifies["proprios"]
                else None,
                "proprio": "TODO_proprio",
                "id_syndic": list(notifies["syndics"])[0]
                if notifies["syndics"]
                else None,
                "syndic": "TODO_syndic",
                "id_gest": list(notifies["gests"])[0] if notifies["gests"] else None,
                "gest": "TODO_gest",
                "codeinsee": codeinsee,
            }
        ],  # a priori un seul par fichier (pour le moment)
        "parcelles": [{"ref_cad": x, "codeinsee": codeinsee} for x in parcelles],
    }
    return doc_data


def process_files(
    in_dir_pdf: Path,
    in_dir_ntxt: Path,
    in_dir_otxt: Path,
    out_files: Dict[str, Path],
    date_exec: date,
):
    """Analyse le texte des fichiers PDF extrait dans des fichiers TXT.

    Parameters
    ----------
    in_dir_pdf : Path
        Dossier contenant les fichiers PDF
    in_dir_ntxt : Path
        Dossier contenant les fichiers TXT natif
    in_dir_otxt : Path
        Dossier contenant les fichiers TXT extrait par OCR
    out_files : Dict[str, Path]
        Fichiers CSV destination, contenant les données extraites.
        Dictionnaire indexé par les clés {"adresse", "arrete", "notifie", "parcelle"}.
    date_exec : date
        Date d'exécution du script, utilisée pour (a) le nom des copies de fichiers CSV
        incluant la date de traitement, (b) l'identifiant unique des arrêtés dans les 4
        tables, (c) le champ 'datemaj' initialement rempli avec la date d'exécution.
    """
    # date de traitement, en 2 formats
    date_proc = date_exec.strftime("%Y%m%d")  # format identifiants uniques des arrêtés
    datemaj = date_exec.strftime("%d/%m/%Y")  # format colonne "datemaj" des tables

    # filtrage en deux temps, car glob() est case-sensitive (sur linux en tout cas)
    # et l'extension de certains fichiers est ".PDF" plutôt que ".pdf"
    fps_pdf = sorted(
        x
        for x in in_dir_pdf.glob("*")
        if (
            (x.suffix.lower() == ".pdf")
            and (
                x.name
                not in set(EXCLUDE_FILES + EXCLUDE_FIXME_FILES)  # + EXCLUDE_HORS_AMP)
            )
        )
    )

    # 4 tables de sortie
    rows_adresse = []
    rows_arrete = []
    rows_notifie = []
    rows_parcelle = []
    # hash utilisé dans le preprocessing
    # TODO en faire un paramètre?
    digest = "blake2b"
    # identifiant des entrées dans les fichiers de sortie: <type arrêté>-<date du traitement>-<index>
    type_arr = "AP"  # arrêtés de péril
    idx_beg = 1
    # itérer sur les fichiers PDF et TXT
    for i, fp_pdf in enumerate(fps_pdf, start=idx_beg):
        # hash du fichier PDF en entrée (utile pour éviter les conflits de fichiers ayant le même nom ;
        # pourra être utilisé aussi pour détecter certains doublons)
        # TODO utiliser le hash pour détecter les doublons: fichier existant avec le même hash en préfixe
        fp_digest = get_file_digest(fp_pdf, digest=digest)  # hash du fichier
        # identifiant unique du document dans les tables de sortie (paquet_*.csv):
        # TODO détecter le ou les éventuels fichiers déjà produits ce jour, initialiser
        # le compteur à la prochaine valeur mais en écartant les doublons (blake2b?)
        # format: {type d'arrêté}-{date}-{id relatif, sur 4 chiffres}
        idu = f"{type_arr}-{date_proc}-{i:04}"
        # fichier txt
        fp_otxt = in_dir_otxt / f"{fp_digest}-{fp_pdf.stem}.txt"  # ocr
        fp_ntxt = in_dir_ntxt / f"{fp_digest}-{fp_pdf.stem}.txt"  # natif
        if fp_otxt.is_file():
            # texte ocr
            fp_txt = fp_otxt
        elif fp_ntxt.is_file():
            # sinon texte natif
            fp_txt = fp_ntxt
        else:
            # sinon anomalie
            fp_txt = None
            raise ValueError(f"{fp_pdf}: aucun fichier txt trouvé ({fp_otxt, fp_ntxt})")
        # print(f"---------\n{fp_pdf}")  # DEBUG
        doc_data = parse_arrete(fp_pdf, fp_txt)

        # ajout des entrées dans les 4 tables
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
    # créer les 4 DataFrames
    for key, rows, dtype in [
        ("adresse", rows_adresse, DTYPE_ADRESSE),
        ("arrete", rows_arrete, DTYPE_ARRETE),
        ("notifie", rows_notifie, DTYPE_NOTIFIE),
        ("parcelle", rows_parcelle, DTYPE_PARCELLE),
    ]:
        out_file = out_files[key]
        df = pd.DataFrame.from_records(rows).astype(dtype=dtype)
        df.to_csv(out_file, index=False)
        # TODO copier le fichier CSV en ajoutant au nom de fichier la date de traitement


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
        "in_dir_pdf",
        help="Chemin vers le dossier contenant les fichiers PDF",
    )
    parser.add_argument(
        "in_dir_ntxt",
        help="Chemin vers le dossier contenant les fichiers TXT de texte natif",
    )
    parser.add_argument(
        "in_dir_otxt",
        help="Chemin vers le dossier contenant les fichiers TXT de texte extrait par OCR",
    )
    parser.add_argument(
        "out_dir",
        help="Chemin vers le dossier pour les 4 fichiers CSV en sortie contenant les données extraites des documents",
    )
    args = parser.parse_args()

    # entrée: fichiers PDF et TXT
    in_dir_pdf = Path(args.in_dir_pdf).resolve()
    if not in_dir_pdf.is_dir():
        raise ValueError(f"Impossible de trouver le dossier {in_dir_pdf}")
    in_dir_ntxt = Path(args.in_dir_ntxt).resolve()
    if not in_dir_ntxt.is_dir():
        raise ValueError(f"Impossible de trouver le dossier {in_dir_ntxt}")
    in_dir_otxt = Path(args.in_dir_otxt).resolve()
    if not in_dir_otxt.is_dir():
        raise ValueError(f"Impossible de trouver le dossier {in_dir_otxt}")

    # sortie: fichiers CSV générés
    # créer le dossier destination, récursivement, si besoin
    out_dir = Path(args.out_dir).resolve()
    logging.info(
        f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'va être créé'}."
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # 4 fichiers CSV seront générés
    out_basenames = {
        x: out_dir / f"paquet_{x}.csv"
        for x in ["arrete", "adresse", "parcelle", "notifie"]
    }
    # les fichiers avec les noms de base seront des copies des fichiers générés par la
    # dernière exécution, incluant:
    # - la date de traitement (ex: "2023-05-30")
    date_proc = date_exec.strftime("%Y-%m-%d")
    # et le numéro d'exécution de ce jour (ex: "02"), calculé en recensant les éventuels
    # fichiers existants
    idx_exec = 0  # init 0
    out_prevruns = itertools.chain.from_iterable(
        out_dir.glob(f"{fp_out.stem}_{date_proc}_[0-9][0-9]{fp_out.suffix}")
        for fp_out in out_basenames.values()
    )
    for fp_prevrun in out_prevruns:
        # le numéro se trouve à la fin du stem, après le dernier séparateur "_"
        fp_out_idx = int(fp_prevrun.stem.split("_")[-1])
        idx_exec = max(idx_exec, fp_out_idx)
    idx_exec += 1  # on prend le numéro d'exécution suivant
    # les noms des fichiers générés par cette exécution
    out_files = {
        x: fp_out.with_stem(f"{fp_out.stem}_{date_proc}_{idx_exec:>02}")
        for x, fp_out in out_basenames.items()
    }
    process_files(in_dir_pdf, in_dir_ntxt, in_dir_otxt, out_files, date_exec=date_exec)
    # faire une copie des 4 fichiers générés avec les noms de base (écraser chaque fichier
    # pré-existant ayant le nom de base)
    for fp_out in out_files.values():
        # retirer la date et le numéro d'exécution pour retrouver le nom de base
        fp_copy = fp_out.with_stem(f"{fp_out.stem.rsplit('_', maxsplit=2)[0]}")
        shutil.copy2(fp_out, fp_copy)

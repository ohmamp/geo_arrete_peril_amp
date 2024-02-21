"""Chaque ligne correspond à un document.
Les éventuelles incohérences entre valeurs extraites pour différentes pages
d'un même document sont signalées.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict
import time  # WIP

import pandas as pd

from parse_native_pages import (
    DTYPE_META_NTXT_FILT,
    DTYPE_META_NTXT_PROC,
)


# colonnes de données produites, avec leur dtype
# "boolean" est le dtype "nullable" <https://pandas.pydata.org/docs/user_guide/boolean.html>
DTYPE_PARSE_AGG = {
    # @ctes
    "actes_pages_tampon": "object",  # List[int]
    "actes_pages_ar": "object",  # List[int]
    # tous arrêtés
    "commune_maire": "string",
    "pages_vu": "object",  # List[int]
    "pages_considerant": "object",  # List[int]
    "pages_arrete": "object",  # List[int]
    "pages_article": "object",  # List[int]
    "pages_cgct": "object",  # List[int]
    "pages_cgct_art": "object",  # List[int]
    "pages_cch": "object",  # List[int]
    "pages_cch_L111": "object",  # List[int]
    "pages_cch_L511": "object",  # List[int]
    "pages_cch_L521": "object",  # List[int]
    "pages_cch_L541": "object",  # List[int]
    "pages_cch_R511": "object",  # List[int]
    "pages_cc": "object",  # List[int]
    "pages_cc_art": "object",  # List[int]
    # - arrêté
    "arr_date": "string",
    "num_arr": "string",
    "nom_arr": "string",
    "classe": "string",
    "urgence": "string",
    "demo": "string",
    "int_hab": "string",
    "equ_com": "string",
    # - adresse
    "adresse_brute": "string",
    "adr_num": "string",  # numéro de la voie
    "adr_ind": "string",  # indice de répétition
    "adr_voie": "string",  # nom de la voie
    "adr_compl": "string",  # complément d'adresse
    "adr_cpostal": "string",  # code postal
    "adr_ville": "string",  # ville
    # - parcelle
    "parcelle": "string",
    # - notifiés
    "proprio": "string",
    "syndic": "string",
    "gest": "string",
}


DTYPE_META_NTXT_DOC = DTYPE_META_NTXT_FILT | DTYPE_PARSE_AGG


def pagenums(df_grp: pd.DataFrame, col_on: str):
    """Renvoie la liste des numéros de pages où une colonne est vraie"""
    return df_grp[df_grp[col_on]]["pagenum"].to_list()


def first(df_grp: pd.DataFrame, col_on: str):
    """Renvoie la première valeur non-vide de la colonne"""
    s_ok = df_grp[col_on].dropna()
    if s_ok.empty:
        return None
    else:
        return s_ok.to_list()[0]


def aggregate_pages(df_grp: pd.DataFrame, include_actes_page_ar: bool = False) -> Dict:
    """Fusionne les champs extraits des différentes pages d'un document.

    Parameters
    ----------
    df_grp: pd.core.groupby.DataFrame
        Pages d'un document
    include_actes_page_ar: boolean, defaults to False
        Inclut la page d'accusé de réception d'@ctes.

    Returns
    -------
    rec_struct: dict
        Dictionnaire de valeurs de différents types ou nulles, selon que les éléments ont été détectés.
    """
    # conserver uniquement les pages avec du texte ;
    # actuellement: "has_stamp is None" implique que la page ne contient pas de texte
    # FIXME gérer les pages sans texte en amont?
    grp = df_grp.dropna(subset=["has_stamp"])
    # si demandé, exclure l'éventuelle page d'accusé de réception d'actes
    if not include_actes_page_ar:
        grp = grp.query("not is_accusedereception_page")

    # si le groupe est vide, renvoyer une ligne (pour le document) vide ;
    # utile lorsque le document ne contient pas de texte, notamment les PDF non-natifs non-océrisés (ou pas encore)
    if grp.empty:
        rec_struct = {x: None for x in DTYPE_PARSE_AGG}
        return rec_struct

    # t0 = time.time()
    if False:
        grp[grp.has_stamp]["pagenum"].to_list()
        t0b = time.time()
        grp[grp["has_stamp"]]["pagenum"].to_list()
        t0c = time.time()
        grp.query("has_stamp")["pagenum"].to_list()
        t0d = time.time()
        print(f"{t0b - t0:.3f}\t{t0c - t0b:.3f}\t{t0d - t0c:.3f}")
    # agréger les numéros de pages ou les valeurs extraites
    rec_actes = {
        # - métadonnées
        #   * @ctes
        # table: contrôle ; expectation: liste de valeurs continue (ex: 1,2,3) ou vide (all NaN)
        # grp.query("has_stamp")["pagenum"].to_list(),
        "actes_pages_tampon": pagenums(grp, "has_stamp"),
        # table: contrôle ; expectation: liste vide (all NaN) ou valeur unique
        # grp.query("is_accusedereception_page")["pagenum"].to_list()
        "actes_pages_ar": pagenums(grp, "is_accusedereception_page"),
    }
    # t1 = time.time()
    rec_commu = {
        # - tous arrêtés
        #   * champ "commune"
        # TODO table: ? ; TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "commune_maire": first(grp, "commune_maire"),
    }
    # t2 = time.time()
    rec_pars = {
        #   * champs structure de l'arrêté
        "pages_vu": pagenums(
            grp, "has_vu"
        ),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_considerant": pagenums(
            grp, "has_considerant"
        ),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_arrete": pagenums(
            grp, "has_arrete"
        ),  # table: contrôle ; expectation: valeur unique ou vide/NaN
        "pages_article": pagenums(
            grp, "has_article"
        ),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
    }
    # t3 = time.time()
    rec_regl = {
        # arrêtés spécifiques
        # - réglementaires
        "pages_cgct": pagenums(
            grp, "has_cgct"
        ),  # TODO retraiter pour classer les arrêtés?  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_cgct_art": pagenums(
            grp, "has_cgct_art"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch": pagenums(
            grp, "has_cch"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L111": pagenums(
            grp, "has_cch_L111"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L511": pagenums(
            grp, "has_cch_L511"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L521": pagenums(
            grp, "has_cch_L521"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L541": pagenums(
            grp, "has_cch_L541"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_R511": pagenums(
            grp, "has_cch_R511"
        ),  # TODO retraiter pour classer les arrêtés?
        "pages_cc": pagenums(grp, "has_cc"),  # TODO retraiter pour classer les arrêtés?
        "pages_cc_art": pagenums(
            grp, "has_cc_art"
        ),  # TODO retraiter pour classer les arrêtés?
    }
    # t4 = time.time()
    rec_adre = {
        # - données
        "adresse_brute": first(
            grp, "adresse"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "adr_num": first(grp, "adr_num"),
        "adr_ind": first(grp, "adr_ind"),
        "adr_voie": first(grp, "adr_voie"),
        "adr_compl": first(grp, "adr_compl"),
        "adr_cpostal": first(grp, "adr_cpostal"),
        "adr_ville": first(grp, "adr_ville"),
    }
    # t5 = time.time()
    rec_parce = {
        "parcelle": first(
            grp, "parcelle"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    # t6 = time.time()
    rec_proprio = {
        "proprio": first(
            grp, "proprio"
        ),  # TODO expectation: 1-n (TODO normalisation: casse, accents etc?) ; vide pour abrogation?
    }
    rec_syndi = {
        "syndic": first(
            grp, "syndic"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_gest = {
        "gest": first(
            grp, "gest"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    # t7 = time.time()
    rec_date = {
        "arr_date": first(
            grp, "date"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    # t8 = time.time()
    rec_num = {
        "num_arr": first(
            grp, "num_arr"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    # t9 = time.time()
    if False:
        print(
            f"actes: {t1 - t0:.3f}\tcommune: {t2 - t1:.3f}\tvu_etc: {t3 - t2:.3f}"
            + f"\tregl: {t4 - t3:.3f}\tadr: {t5 - t4:.3f}\tparcelle: {t6 - t5:.3f}"
            + f"\tsyndic: {t7 - t6:.3f}\tdate: {t8 - t7:.3f}\tnum: {t9 - t8:.3f}"
        )
    rec_nom = {
        "nom_arr": first(
            grp, "nom_arr"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_classi = {
        "classe": first(
            grp, "classe"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "urgence": first(
            grp, "urgence"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "demo": first(
            grp, "demo"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "int_hab": first(
            grp, "int_hab"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "equ_com": first(
            grp, "equ_com"
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_struct = (
        rec_actes
        | rec_commu
        | rec_pars
        | rec_regl
        | rec_adre
        | rec_parce
        | rec_proprio
        | rec_syndi
        | rec_gest
        | rec_date
        | rec_num
        | rec_nom
        | rec_classi
    )
    return rec_struct


def create_docs_dataframe(
    df_pages: pd.DataFrame,
) -> pd.DataFrame:
    """Rassembler les informations des documents dans un DataFrame.

    Fusionner les entrées de chaque page en une entrée par document.

    Parameters
    ----------
    df_pages: pd.DataFrame
        Métadonnées et données extraites des pages.

    Returns
    -------
    df_docs: pd.DataFrame
        Tableau contenant les métadonnées et données extraites des documents.
    """
    doc_rows = []
    for _, df_grp in df_pages.groupby("fullpath_txt"):
        # reporter les métadonnées du fichier PDF et du TXT, dans chaque entrée de document
        meta_doc = {
            x: df_grp[x].to_list()[0] for x in DTYPE_META_NTXT_FILT
        }  # FIXME prendre les métadonnées du document dans le CSV 1 ligne par doc?
        # retraiter spécifiquement le champ "exclude": si toutes les pages sont "exclude", alors le fichier aussi, sinon non
        meta_doc["exclude"] = df_grp["exclude"].all()
        # rassembler les données des pages ;
        # exclure l'éventuelle page d'accusé de réception d'actes
        data_doc = aggregate_pages(df_grp, include_actes_page_ar=False)
        doc_rows.append(meta_doc | data_doc)  # python >= 3.9 (dict union)
    df_docs = pd.DataFrame.from_records(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_META_NTXT_DOC)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/aggregate_pages_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées et données extraites des pages de documents",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées et donnés extraites des documents",
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

    # entrée: CSV de pages de texte
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de documents
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
        out_dir.mkdir(parents=True, exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_meta = pd.read_csv(in_file, dtype=DTYPE_META_NTXT_PROC)
    # traiter les documents (découpés en pages de texte)
    df_txts = create_docs_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT_DOC)
        df_txts = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

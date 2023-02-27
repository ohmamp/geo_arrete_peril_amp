"""Agrège les pages, et leurs données extraites, en documents.

Chaque ligne correspond à un document.
Les éventuelles incohérences entre valeurs extraites pour différentes pages
d'un même document sont signalées.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict

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
    # "arrete_date": "object",  # List[string]
    # "arrete_num": "object",  # List[string]
    # "arrete_nom": "object",  # List[string]
    "arr_classification": "string",
    "arr_proc_urgence": "string",
    "arr_demolition": "string",
    "arr_interdiction": "string",
    "arr_equipcomm": "string",
    # - adresse
    "adresse_brute": "string",
    # - parcelle
    "parcelle": "string",
    # - notifiés
    # "proprietaire": "string",
    "syndic": "string",
    "arr_date": "string",
    "arr_num": "string",
}


DTYPE_META_NTXT_DOC = DTYPE_META_NTXT_FILT | DTYPE_PARSE_AGG


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
        grp = df_grp.query("not is_accusedereception_page")

    # si le groupe est vide, renvoyer une ligne (pour le document) vide ;
    # utile lorsque le document ne contient pas de texte, notamment les PDF non-natifs non-océrisés (ou pas encore)
    if grp.empty:
        rec_struct = {x: None for x in DTYPE_PARSE_AGG}
        return rec_struct

    # agréger les numéros de pages ou les valeurs extraites
    rec_actes = {
        # - métadonnées
        #   * @ctes
        "actes_pages_tampon": grp.query("has_stamp")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: liste de valeurs continue (ex: 1,2,3) ou vide (all NaN)
        "actes_pages_ar": grp.query("is_accusedereception_page")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: liste vide (all NaN) ou valeur unique
    }
    rec_commu = {
        # - tous arrêtés
        #   * champ "commune"
        "commune_maire": (
            grp.dropna(subset=["commune_maire"])["commune_maire"].to_list()[0]
            if not grp.dropna(subset=["commune_maire"]).empty
            else None
        ),  # TODO table: ? ; TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_pars = {
        #   * champs structure de l'arrêté
        "pages_vu": grp.query("has_vu")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_considerant": grp.query("has_considerant")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_arrete": grp.query("has_arrete")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: valeur unique ou vide/NaN
        "pages_article": grp.query("has_article")[
            "pagenum"
        ].to_list(),  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
    }
    rec_regl = {
        # arrêtés spécifiques
        # - réglementaires
        "pages_cgct": grp.query("has_cgct")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_cgct_art": grp.query("has_cgct_art")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch": grp.query("has_cch")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L111": grp.query("has_cch_L111")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L511": grp.query("has_cch_L511")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L521": grp.query("has_cch_L521")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L541": grp.query("has_cch_L541")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cch_R511": grp.query("has_cch_R511")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cc": grp.query("has_cc")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
        "pages_cc_art": grp.query("has_cc_art")[
            "pagenum"
        ].to_list(),  # TODO retraiter pour classer les arrêtés?
    }
    rec_adre = {
        # - données
        "adresse_brute": (
            grp.dropna(subset=["adresse"])["adresse"].to_list()[0]
            if not grp.dropna(subset=["adresse"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_parce = {
        "parcelle": (
            grp.dropna(subset=["parcelle"])["parcelle"].to_list()[0]
            if not grp.dropna(subset=["parcelle"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_syndi = {
        "syndic": (
            grp.dropna(subset=["syndic"])["syndic"].to_list()[0]
            if not grp.dropna(subset=["syndic"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_date = {
        "arr_date": (
            grp.dropna(subset=["date"])["date"].to_list()[0]
            if not grp.dropna(subset=["date"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_num = {
        "arr_num": (
            grp.dropna(subset=["arr_num"])["arr_num"].to_list()[0]
            if not grp.dropna(subset=["arr_num"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_nom = {
        "arr_nom": (
            grp.dropna(subset=["arr_nom"])["arr_nom"].to_list()[0]
            if not grp.dropna(subset=["arr_nom"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_classi = {
        "arr_classification": (
            grp.dropna(subset=["arr_classification"])[
                "arr_classification"
            ].to_list()[0]
            if not grp.dropna(subset=["arr_classification"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "arr_proc_urgence": (
            grp.dropna(subset=["arr_proc_urgence"])["arr_proc_urgence"].to_list()[0]
            if not grp.dropna(subset=["arr_proc_urgence"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "arr_demolition": (
            grp.dropna(subset=["arr_demolition"])["arr_demolition"].to_list()[0]
            if not grp.dropna(subset=["arr_demolition"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "arr_interdiction": (
            grp.dropna(subset=["arr_interdiction"])["arr_interdiction"].to_list()[0]
            if not grp.dropna(subset=["arr_interdiction"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "arr_equipcomm": (
            grp.dropna(subset=["arr_equipcomm"])["arr_equipcomm"].to_list()[0]
            if not grp.dropna(subset=["arr_equipcomm"]).empty
            else None
        ),  # TODO expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
    rec_struct = (
        rec_actes
        | rec_commu
        | rec_pars
        | rec_regl
        | rec_adre
        | rec_parce
        | rec_syndi
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
    dir_log = Path(__file__).resolve().parents[1] / "logs"
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
        out_dir.mkdir(exist_ok=True)

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

"""Agrège les pages, et leurs données extraites, en documents.

Chaque ligne correspond à un document.
Les éventuelles incohérences entre valeurs extraites pour différentes pages
d'un même document sont signalées.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, NamedTuple

import pandas as pd

# métadonnées à reporter telles quelles
META_COLS = [
    "filename",
    "fullpath",
    "filesize",
    "nb_pages",
    "creatortool",
    "producer",
    "createdate",
    "modifydate",
    "col_res",
    "guess_tampon",
    "guess_dernpage",
    "guess_pdftext",
    "guess_badocr",
    "retcode_txt",
    "fullpath_txt",
]

PAGES_DATA_COLS = [
    # @ctes
    "has_stamp",
    "is_accusedereception_page",
    # tous arrêtés
    "commune_maire",
    "has_vu",
    "has_considerant",
    "has_arrete",
    "has_article",
    # spécifiques arrêtés
    # - règlementation
    "has_cgct",
    "has_cgct_art",
    "has_cch",
    "has_cch_L111",
    "has_cch_L511",
    "has_cch_L521",
    "has_cch_L541",
    "has_cch_R511",
    "has_cc",
    "has_cc_art",
    # - données
    "parcelle",
    "adresse",
    "syndic",
]

DATA_COLS = [
    # @ctes
    "actes_pages_tampon",
    "actes_pages_ar",
    # tous arrêtés
    "commune_maire",
    "pages_vu",
    "pages_considerant",
    "pages_arrete",
    "pages_article",
    "pages_cgct",
    "pages_cgct_art",
    "pages_cch",
    "pages_cch_L111",
    "pages_cch_L511",
    "pages_cch_L521",
    "pages_cch_L541",
    "pages_cch_R511",
    "pages_cc",
    "pages_cc_art",
    "parcelle",
    "adresse",
    "syndic",
]


def aggregate_pages(df_grp: pd.core.groupby.DataFrameGroupBy) -> Dict:
    """Fusionne les champs extraits des différentes pages d'un document.

    Parameters
    ----------
    df_grp: pd..core.groupby.DataFrameGroupBy
        Groupe de pages d'un même document

    Returns
    -------
    rec_struct: dict
        Dictionnaire de valeurs de différents types ou nulles, selon que les éléments ont été détectés.
    """
    print(df_grp)  # DEBUG
    print(df_grp["has_stamp"])  # DEBUG
    print(df_grp[df_grp["has_stamp"].dropna()])  # DEBUG
    print(repr(df_grp[df_grp["has_stamp"].dropna()]["pagenum"]))  # DEBUG
    raise ValueError("what?")  # RESUME HERE
    rec_struct = {
        # - métadonnées
        #   * @ctes
        "actes_pages_tampon": df_grp[df_grp["has_stamp"]][
            "pagenum"
        ],  # table: contrôle ; expectation: liste de valeurs continue (ex: 1,2,3) ou vide (all NaN)
        "actes_pages_ar": df_grp[df_grp["is_accusedereception_page"]][
            "pagenum"
        ],  # table: contrôle ; expectation: liste vide (all NaN) ou valeur unique
        # - tous arrêtés
        #   * champ "commune"
        "commune_maire": df_grp[df_grp["commune_maire"]]
        .unique()
        .first(),  # table: ? ; expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        #   * champs structure de l'arrêté
        "pages_vu": df_grp[df_grp["has_vu"]][
            "pagenum"
        ],  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_considerant": df_grp[df_grp["has_considerant"]][
            "pagenum"
        ],  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_arrete": df_grp[df_grp["has_arrete"]][
            "pagenum"
        ],  # table: contrôle ; expectation: valeur unique ou vide/NaN
        "pages_article": df_grp[df_grp["has_article"]][
            "pagenum"
        ],  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        # arrêtés spécifiques
        # - réglementaires
        "pages_cgct": df_grp[df_grp["has_cgct"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?  # table: contrôle ; expectation: liste de valeurs continue ou vide (all NaN)
        "pages_cgct_art": df_grp[df_grp["has_cgct_art"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch": df_grp[df_grp["has_cch"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L111": df_grp[df_grp["has_cch_L111"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L511": df_grp[df_grp["has_cch_L511"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L521": df_grp[df_grp["has_cch_L521"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch_L541": df_grp[df_grp["has_cch_L541"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cch_R511": df_grp[df_grp["has_cch_R511"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cc": df_grp[df_grp["has_cc"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        "pages_cc_art": df_grp[df_grp["has_cc_art"]][
            "pagenum"
        ],  # TODO retraiter pour classer les arrêtés?
        # - données
        "parcelle": df_grp[df_grp["parcelle"]]
        .unique()
        .first(),  # table: ? ; expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "adresse": df_grp[df_grp["adresse"]]
        .unique()
        .first(),  # table: ? ; expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
        "syndic": df_grp[df_grp["syndic"]]
        .unique()
        .first(),  # table: ? ; expectation: valeur unique (modulo normalisation: casse, accents etc?) ou vide/NaN
    }
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
        meta_doc = {x: df_grp[x] for x in META_COLS}
        # rassembler les données des pages
        data_doc = aggregate_pages(df_grp)
        doc_rows.append(meta_doc | data_doc)  # python >= 3.9 (dict union)
    df_docs = pd.DataFrame.from_records(doc_rows)
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
    df_meta = pd.read_csv(in_file, dtype={"fullpath_txt": "string"})
    # traiter les documents (découpés en pages de texte)
    df_txts = create_docs_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file)
        df_txts = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

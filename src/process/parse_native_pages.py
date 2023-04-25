"""Extrait la structure des documents.

Découpe chaque arrêté en zones:
* préambule (?),
* VUs,
* CONSIDERANTs,
* ARTICLES,
* postambule (?)
"""

# FIXME comment gérer les administrateurs provisoires? syndic ou gestionnaire? ("Considérant que l’Administrateur provisoire de cet immeuble est pris en la personne du SCP...")

# TODO repérer les rapports d'expertise (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 3 à 10)
# TODO repérer les citations des textes réglementaires en annexe (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 11 à 15)
# TODO mieux traiter les pages d'AR @ctes (ex: "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf" p. 16)

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from src.domain_knowledge.actes import is_accusedereception_page, is_stamped_page
from src.domain_knowledge.arrete import (
    contains_arrete,
    contains_article,
    contains_considerant,
    contains_vu,
    get_commune_maire,
    get_date,
    get_nom,
    get_num,
)
from src.domain_knowledge.cadastre import get_parcelle  # , P_CAD_AUTRES_NG
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
)
from src.domain_knowledge.logement import get_adr_doc, get_gest, get_proprio, get_syndic
from src.domain_knowledge.typologie_securite import (
    get_classe,
    get_demo,
    get_equ_com,
    get_int_hab,
    get_urgence,
)

# type des colonnes des fichiers CSV en entrée
from src.preprocess.filter_docs import DTYPE_META_NTXT_FILT, DTYPE_NTXT_PAGES_FILT


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
    "adr_num": "string",  # numéro de la voie
    "adr_ind": "string",  # indice de répétition
    "adr_voie": "string",  # nom de la voie
    "adr_compl": "string",  # complément d'adresse
    "adr_cpostal": "string",  # code postal
    "adr_ville": "string",  # ville
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


def spot_text_structure(
    df_row: NamedTuple,
) -> pd.DataFrame:
    """Détecte la présence d'éléments de structure dans une page d'arrêté.

    Détecte la présence de tampons, pages d'accusé de réception,
    VU, CONSIDERANT, ARTICLE.

    Parameters
    ----------
    df_row: NamedTuple
        Page de document

    Returns
    -------
    rec_struct: dict
        Dictionnaire de valeurs booléennes ou nulles, selon que les éléments de structure ont été détectés.
        Les clés et les types de valeurs sont spécifiés dans `DTYPE_PARSE`.
        Si df_row ne contient pas de texte, toutes les valeurs de sortie sont None.
    """
    if pd.notna(df_row.pagetxt) and (
        not df_row.exclude
    ):  # WIP " and (not df_row.exclude)"
        logging.warning(f"{df_row.pdf} / {df_row.pagenum}")  # WIP
        # adresse(s) visée(s) par l'arrêté
        if pg_adrs_doc := get_adr_doc(df_row.pagetxt):
            # on sélectionne arbitrairement la 1re zone d'adresse(s) (FIXME?)
            pg_adr_doc = pg_adrs_doc[0]["adresse_brute"]
            # temporairement: on prend la 1re adresse précise extraite de cette zone
            adr_fields = pg_adrs_doc[0]["adresses"][0]
            # end WIP
        else:
            pg_adr_doc = None
            adr_fields = {
                "adr_num": None,  # numéro de la voie
                "adr_ind": None,  # indice de répétition
                "adr_voie": None,  # nom de la voie
                "adr_compl": None,  # complément d'adresse
                "adr_cpostal": None,  # code postal
                "adr_ville": None,  # ville
            }

        rec_struct = {
            # @ctes
            "has_stamp": is_stamped_page(df_row.pagetxt),
            "is_accusedereception_page": is_accusedereception_page(df_row.pagetxt),
            # tous arrêtés
            "commune_maire": get_commune_maire(df_row.pagetxt),
            "has_vu": contains_vu(df_row.pagetxt),
            "has_considerant": contains_considerant(df_row.pagetxt),
            "has_arrete": contains_arrete(df_row.pagetxt),
            "has_article": contains_article(df_row.pagetxt),
            # arrêtés spécifiques
            # - réglementaires
            "has_cgct": contains_cgct(df_row.pagetxt),
            "has_cgct_art": contains_cgct_art(df_row.pagetxt),
            "has_cch": contains_cch(df_row.pagetxt),
            "has_cch_L111": contains_cch_L111(df_row.pagetxt),
            "has_cch_L511": contains_cch_L511(df_row.pagetxt),
            "has_cch_L521": contains_cch_L521(df_row.pagetxt),
            "has_cch_L541": contains_cch_L541(df_row.pagetxt),
            "has_cch_R511": contains_cch_R511(df_row.pagetxt),
            "has_cc": contains_cc(df_row.pagetxt),
            "has_cc_art": contains_cc_art(df_row.pagetxt),
            # - données
            "adresse": pg_adr_doc,
            # refactor 2023-03-31: remonter l'extraction de l'adresse précise
            "adr_num": adr_fields["adr_num"],  # numéro de la voie
            "adr_ind": adr_fields["adr_ind"],  # indice de répétition
            "adr_voie": adr_fields["adr_voie"],  # nom de la voie
            "adr_compl": adr_fields["adr_compl"],  # complément d'adresse
            "adr_cpostal": adr_fields["adr_cpostal"],  # code postal
            "adr_ville": adr_fields["adr_ville"],  # ville
            # end refactor 2023-03-31
            "parcelle": get_parcelle(df_row.pagetxt),
            "proprio": get_proprio(df_row.pagetxt),  # WIP
            "syndic": get_syndic(df_row.pagetxt),
            "gest": get_gest(df_row.pagetxt),
            "date": get_date(df_row.pagetxt),
            #   * arrêté
            "num_arr": get_num(df_row.pagetxt),
            "nom_arr": get_nom(df_row.pagetxt),
            "classe": get_classe(df_row.pagetxt),
            "urgence": get_urgence(df_row.pagetxt),
            "demo": get_demo(df_row.pagetxt),
            "int_hab": get_int_hab(df_row.pagetxt),
            "equ_com": get_equ_com(df_row.pagetxt),
        }
    else:
        # tous les champs sont vides ("None")
        rec_struct = {x: None for x in DTYPE_PARSE}
    return rec_struct


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
    for df_row in df_txts.itertuples():
        # pour chaque page de document, repérer des indications de structure
        rec_struct = spot_text_structure(df_row)
        indics_struct.append(
            {
                "pdf": df_row.pdf,
                "fullpath": df_row.fullpath,
                "pagenum": df_row.pagenum,
            }
            | rec_struct  # python >= 3.9 (dict union)
        )
    df_indics = pd.DataFrame.from_records(indics_struct)
    df_proc = pd.merge(df_meta, df_indics, on=["pdf", "fullpath"])
    df_proc = df_proc.astype(dtype=DTYPE_META_NTXT_PROC)
    return df_proc


# liste de documents pour lesquels certains champs sont nécessairement vides, car la donnée est absente du document
# TODO transformer en script
# - parcelle
PARCELLE_ABS = [
    "2 rue Lisse Bellegarde - IO 06.03.20.PDF",  # Aix-en-Provence
    "MS 673 av Jean Monnet à Vitrolles.pdf",  # Vitrolles
]

if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    if not dir_log.is_dir():
        dir_log.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=f"{dir_log}/parse_native_pages_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
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
        out_dir.mkdir(parents=True, exist_ok=True)

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

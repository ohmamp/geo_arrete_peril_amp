"""Extraire les données des documents.

Les données sont extraites des empans de texte repérés au préalable,
et normalisées.
Lorsque plusieurs empans de texte sont susceptibles de renseigner sur
la même donnée, les différentes valeurs extraites sont accumulées pour
certains champs (ex: propriétaires) ou comparées et sélectionnées pour
d'autres champs (ex: commune).
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd

from src.process.aggregate_pages import DTYPE_META_NTXT_DOC
from src.domain_knowledge.adresse import (
    create_adresse_normalisee,
    process_adresse_brute,
)
from src.domain_knowledge.codes_geo import P_COMMUNES_AMP_ALLFORMS
from src.utils.str_date import process_date_brute
from src.utils.text_utils import normalize_string


DTYPE_DATA = {
    "idu": "string",  # identifiant unique
    # arrêté
    "arr_date": "string",
    "arr_num_arr": "string",
    "arr_nom_arr": "string",
    "arr_classe": "string",
    "arr_urgence": "string",
    "arr_demo": "string",
    "arr_int_hab": "string",
    "arr_equ_com": "string",
    "arr_pdf": "string",  # = filename
    "arr_url": "string",  # TODO URL serveur
    # adresse
    "adr_ad_brute": "string",  # adresse brute
    "adr_num": "string",  # numéro de la voie
    "adr_ind": "string",  # indice de répétition
    "adr_voie": "string",  # nom de la voie
    "adr_compl": "string",  # complément d'adresse
    "adr_cpostal": "string",  # code postal
    "adr_ville": "string",  # ville
    "adr_adresse": "string",  # adresse normalisée
    "adr_codeinsee": "string",  # code insee (5 chars)
    # parcelle
    "par_ref_cad": "string",  # référence cadastrale
    # notifié
    "not_id_proprio": "string",  # identification du propriétaire
    "not_proprio": "string",  # nom des propriétaries
    "not_id_syndic": "string",  # identification du syndic
    "not_syndic": "string",  # nom du syndic
    "not_id_gest": "string",  # identification du gestionnaire
    "not_gest": "string",  # nom du gestionnaire
}


# TODO déplacer dans arrete ? ou ailleurs ?
def determine_commune(adr_commune_brute: str, adr_commune_maire: str) -> str:
    """Déterminer la commune de l'adresse visée par l'arrêté.

    Réconcilie la commune éventuellement contenue dans l'adresse du ou des bâtiments visés
    avec le nom de commune extrait du document (template, autorité ou lieu de signature).

    Parameters
    ----------
    adr_commune_brute: str
        Commune extraite de l'adresse du bâtiment visé par l'arrêté.
    adr_commune_maire: str
        Commune extraite de l'autorité prenant l'arrêté, ou du template du document.

    Returns
    -------
    adr_commune: str
        Commune de l'adresse visée.
    """
    # TODO normaliser vers la graphie de la table des codes INSEE? Quid des arrondissements de Marseille?
    # TODO comparer les graphies?
    if (adr_commune_brute is None) and (adr_commune_maire is None):
        # pas de commune
        adr_commune = None
    elif (adr_commune_maire is None) or (
        not P_COMMUNES_AMP_ALLFORMS.match(adr_commune_maire)
    ):
        adr_commune = adr_commune_brute  # TODO normaliser?
    elif (adr_commune_brute is None) or (
        not P_COMMUNES_AMP_ALLFORMS.match(adr_commune_brute)
    ):
        adr_commune = adr_commune_maire
    else:
        # was: adr_commune = adr_commune_maire
        adr_commune = adr_commune_brute  # .title() si on veut minimiser les différences avec adr_commune_maire pour comparer
    return adr_commune


def create_docs_dataframe(
    df_agg: pd.DataFrame,
) -> pd.DataFrame:
    """Extraire les informations des documents dans un DataFrame.

    Normaliser et extraire les données de chaque document en une entrée par document.

    Parameters
    ----------
    df_pages: pd.DataFrame
        Métadonnées et données extraites des pages.

    Returns
    -------
    df_docs: pd.DataFrame
        Tableau contenant les données normalisées extraites des documents.
    """
    doc_rows = []
    # filtrer les documents à exclure complètement: documents hors périmètre strict du jeu de données cible
    df_filt = df_agg[~df_agg["exclude"]]
    # itérer sur tous les documents non-exclus
    for i, df_row in enumerate(df_filt.itertuples()):
        doc_idu = {
            "idu": f"id_{i:04}",  # FIXME identifiant unique
        }
        doc_arr = {
            # arrêté
            "arr_date": (
                process_date_brute(getattr(df_row, "arr_date"))
                if pd.notna(getattr(df_row, "arr_date"))
                else None
            ),
            "arr_num_arr": (
                normalize_string(getattr(df_row, "num_arr"))
                if pd.notna(getattr(df_row, "num_arr"))
                else None
            ),
            "arr_nom_arr": (
                normalize_string(getattr(df_row, "nom_arr"))
                if pd.notna(getattr(df_row, "nom_arr"))
                else None
            ),
            "arr_classe": (
                normalize_string(getattr(df_row, "classe"))
                if pd.notna(getattr(df_row, "classe"))
                else None
            ),
            "arr_urgence": (
                normalize_string(getattr(df_row, "urgence"))
                if pd.notna(getattr(df_row, "urgence"))
                else None
            ),
            "arr_demo": (
                normalize_string(getattr(df_row, "demo"))
                if pd.notna(getattr(df_row, "demo"))
                else None
            ),  # TODO affiner
            "arr_int_hab": (
                normalize_string(getattr(df_row, "int_hab"))
                if pd.notna(getattr(df_row, "int_hab"))
                else None
            ),  # TODO affiner
            "arr_equ_com": (
                normalize_string(getattr(df_row, "equ_com"))
                if pd.notna(getattr(df_row, "equ_com"))
                else None
            ),  # TODO affiner
            # (métadonnées du doc)
            "arr_pdf": getattr(df_row, "pdf"),
            "arr_url": getattr(
                df_row, "fullpath"
            ),  # l'URL sera réécrite avec une URL locale (réseau) ou publique, au moment de l'export
        }
        # adresse
        # - nettoyer a minima de l'adresse brute
        adr_ad_brute = (
            normalize_string(getattr(df_row, "adresse_brute"))
            if pd.notna(getattr(df_row, "adresse_brute"))
            else None
        )
        # - extraire les éléments d'adresse en traitant l'adresse brute
        adr_fields = process_adresse_brute(adr_ad_brute)
        # WIP 2023-03-05 temporairement, prendre la 1re adresse ; il faudra toutes les écrire
        adr_fields = adr_fields[0]
        # end WIP
        # - nettoyer a minima la commune extraite des en-tête ou pied-de-page ou de la mention du maire signataire
        adr_commune_maire = (
            normalize_string(getattr(df_row, "commune_maire"))
            if pd.notna(getattr(df_row, "commune_maire"))
            else None
        )
        # - déterminer la commune de l'adresse visée par l'arrêté en reconciliant la commune de l'adresse et
        # celle de l'autorité
        adr_commune = determine_commune(adr_fields["adr_commune"], adr_commune_maire)
        if not adr_commune:
            logging.warning(f"Pas de commune pour {doc_arr['arr_pdf']}")
        # mettre à jour adr_fields["adr_commune"] pour garantir la cohérence
        adr_fields["adr_commune"] = adr_commune

        # - créer une adresse normalisée ; la cohérence des champs est vérifiée
        adr_adresse = create_adresse_normalisee(adr_fields)
        # - rassembler les champs
        doc_adr = {
            # adresse
            "adr_ad_brute": adr_ad_brute,  # adresse brute
            "adr_num": adr_fields["adr_num"],  # numéro de la voie
            "adr_ind": adr_fields["adr_ind"],  # indice de répétition
            "adr_voie": adr_fields["adr_voie"],  # nom de la voie
            "adr_compl": adr_fields["adr_compl"],  # complément d'adresse
            "adr_cpostal": adr_fields["adr_cpostal"],  # code postal
            "adr_ville": adr_fields["adr_commune"],  # ville
            "adr_adresse": adr_adresse,  # adresse normalisée
            "adr_codeinsee": None,  # code insee (5 chars)  # complété en aval par "enrichi"
        }
        # parcelle cadastrale
        ref_cad = (
            normalize_string(getattr(df_row, "parcelle"))
            if pd.notna(getattr(df_row, "parcelle"))
            else None
        )
        doc_par = {
            "par_ref_cad": ref_cad,  # référence cadastrale
        }
        # notifiés
        doc_not = {
            "not_id_proprio": (
                normalize_string(getattr(df_row, "proprio"))
                if pd.notna(getattr(df_row, "proprio"))
                else None
            ),  # identification des propriétaires
            "not_proprio": "TODO_proprio",  # TODO liste des noms des propriétaires
            "not_id_syndic": (
                normalize_string(getattr(df_row, "syndic"))
                if pd.notna(getattr(df_row, "syndic"))
                else None
            ),  # identification du syndic
            "not_syndic": "TODO_syndic",  # nom du syndic
            "not_id_gest": (
                normalize_string(getattr(df_row, "gest"))
                if pd.notna(getattr(df_row, "gest"))
                else None
            ),  # identification du gestionnaire
            "not_gest": "TODO_gest",  # nom du gestionnaire
        }
        doc_data = doc_idu | doc_arr | doc_adr | doc_par | doc_not
        doc_rows.append(doc_data)
    df_docs = pd.DataFrame.from_records(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_DATA)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/extract_data_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées et données extraites des documents",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées et données normalisées extraites des documents",
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
    df_meta = pd.read_csv(in_file, dtype=DTYPE_META_NTXT_DOC)
    # traiter les documents (découpés en pages de texte)
    df_txts = create_docs_dataframe(df_meta)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_txts_old = pd.read_csv(out_file, dtype=DTYPE_DATA)
        df_txts = pd.concat([df_txts_old, df_txts])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_txts
    df_proc.to_csv(out_file, index=False)

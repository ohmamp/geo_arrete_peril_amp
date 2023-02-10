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
import re
from typing import Dict

import pandas as pd

from adresse import M_ADRESSE
from aggregate_pages import DTYPE_META_NTXT_DOC
from str_date import RE_MOIS


DTYPE_DATA = {
    "idu": "string",  # identifiant unique
    # arrêté
    "arr_date": "string",
    "arr_num": "string",
    "arr_nom": "string",
    "arr_classification": "string",
    "arr_proc_urgence": "string",
    "arr_demolition": "string",
    "arr_interdiction": "string",
    "arr_equipcomm": "string",
    "arr_nom_pdf": "string",  # = filename
    "arr_url": "string",  # TODO URL serveur
    # adresse
    "adr_ad_brute": "string",  # adresse brute
    "adr_adresse": "string",  # adresse normalisée
    "adr_num": "string",  # numéro de la voie
    "adr_ind": "string",  # indice de répétition
    "adr_voie": "string",  # nom de la voie
    "adr_compl": "string",  # complément d'adresse
    "adr_cpostal": "string",  # code postal
    "adr_ville": "string",  # ville
    "adr_codeinsee": "string",  # code insee (5 chars)
    # parcelle
    "par_ref_cad": "string",  # référence cadastrale
    # notifié
    "not_nom_propri": "string",  # nom des propriétaries
    "not_ide_syndic": "string",  # identification du syndic
    "not_nom_syndic": "string",  # nom du syndic
    "not_ide_gestio": "string",  # identification du gestionnaire
}


def normalize_string(raw_str: str) -> str:
    """Normaliser une chaîne de caractères.

    Remplacer les séquences d'espaces par une unique espace.

    Parameters
    ----------
    raw_str: str
        Chaîne de caractères à normaliser

    Returns
    -------
    nor_str: str
        Chaîne de caractères normalisée
    """
    nor_str = re.sub(r"\s+", " ", raw_str, flags=re.MULTILINE).strip()
    return nor_str


def create_adresse_normalisee(adr_fields: Dict, adr_commune_maire: str) -> str:
    """Créer une adresse normalisée.

    L'adresse normalisée rassemble les champs extraits de l'adresse brute, et
    la commune extraite par ailleurs, qui doivent être cohérents.

    Parameters
    ----------
    adr_fields: dict
        Champs de l'adresse, extraits de l'adresse brute
    adr_commune_maire: str
        Commune de l'arrêté

    Returns
    -------
    adr_norm: str
        Adresse normalisée
    """
    adr_commune_brute = adr_fields["adr_commune"]
    # TODO retenir la graphie standard, prise par exemple dans la table des codes INSEE ?
    # croisement entre la commune qui prend l'arrêté et l'éventuelle commune extraite de l'adresse brute
    if (adr_commune_brute is None) and (adr_commune_maire is None):
        # pas de commune  # TODO émettre un warning?
        commune = None
    elif adr_commune_brute is None:
        commune = adr_commune_maire  # TODO normaliser?
    elif adr_commune_maire is None:
        commune = adr_commune_brute  # TODO normaliser?
    elif (adr_commune_brute is not None) and (adr_commune_maire is not None):
        # deux mentions potentiellement différentes de la commune ; normalement de simples variantes de graphie
        # pour le moment on retient la commune qui prend l'arrêté (commune_maire)
        # TODO comparer les graphies, définir et retenir une forme canonique
        commune = adr_commune_maire  # TODO normaliser?

    adr_norm_parts = [
        adr_fields["adr_num"],
        adr_fields["adr_ind"],
        adr_fields["adr_voie"],
        adr_fields["adr_compl"],
        adr_fields["adr_cpostal"],
        commune,
    ]
    adr_norm = " ".join(
        x for x in adr_norm_parts if x is not None
    )  # TODO normaliser la graphie?
    adr_norm = normalize_string(adr_norm)
    return adr_norm


def process_adresse_brute(adr_ad_brute: str) -> Dict:
    """Extraire les différents champs d'une adresse brute.

    Parameters
    ----------
    adr_ad_brute: str
        Adresse brute

    Returns
    -------
    adr_fields: dict
        Champs d'adresse
    """
    if (adr_ad_brute is not None) and (m_adresse := M_ADRESSE.search(adr_ad_brute)):
        m_dict = m_adresse.groupdict()
        # traitement spécifique pour la voie: type + nom
        adr_voie = " ".join(
            m_dict[x] for x in ["type_voie", "nom_voie"] if m_dict[x] is not None
        ).strip()
        if adr_voie == "":
            adr_voie = None
        #
        adr_fields = {
            "adr_num": m_adresse["num_voie"],
            "adr_ind": m_adresse["ind_voie"],
            "adr_voie": adr_voie,
            "adr_compl": None,  # TODO ajouter la détection du complément d'adresse dans la regex?
            "adr_cpostal": m_adresse["code_postal"],
            "adr_commune": m_adresse["commune"],
        }
        return adr_fields
    else:
        adr_fields = {
            "adr_num": None,
            "adr_ind": None,
            "adr_voie": None,
            "adr_compl": None,
            "adr_cpostal": None,
            "adr_commune": None,
        }
        return adr_fields


# date: extraction précise des champs
# FIXME refactoriser-déplacer vers un module dédié aux dates
RE_DATE_PREC = (
    # jour
    r"""(?P<dd>\d{1,2})"""
    + r"""[\s./-]"""
    # mois, en nombre, lettres abrégées ou toutes lettres
    + r"""(?P<mm>"""
    + r"""\d{2}"""
    + rf"""|{RE_MOIS}"""
    + r""")"""
    + r"""[\s./-]"""
    + r"""(?P<yyyy>\d{4})"""  # Peyrolles-en-Provence (en-tête)
)
M_DATE_PREC = re.compile(RE_DATE_PREC, re.MULTILINE | re.IGNORECASE)

MAP_MOIS = {
    "janvier": "01",
    "jan": "01",
    "fevrier": "02",
    "fev": "02",
    "mars": "03",
    # "mar": "03",
    "avril": "04",
    "avr": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "juil": "07",  # jul?
    "aout": "08",
    "aou": "08",
    "septembre": "09",
    "sept": "09",  # sep?
    "octobre": "10",
    "oct": "10",
    "novembre": "11",
    "nov": "11",
    "decembre": "12",
    "dec": "12",
}


def process_date_brute(arr_date: str) -> Dict:
    """Extraire les différents champs d'une date brute et la normaliser.

    Parameters
    ----------
    arr_date: str
        Date brute

    Returns
    -------
    arr_date_norm: str
        Date normalisée dd/mm/yyyy
    """
    if m_date_p := M_DATE_PREC.search(arr_date):
        m_dict = m_date_p.groupdict()
        # traitement spécifique pour le mois, qui peut être écrit en lettres
        mm_norm = MAP_MOIS.get(
            m_dict["mm"].lower().replace("é", "e").replace("û", "u"), m_dict["mm"]
        )
        return f"{m_dict['dd']}/{mm_norm}/{m_dict['yyyy']}"
    else:
        return None


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
    for i, df_row in enumerate(df_agg.itertuples()):
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
            "arr_num": (
                normalize_string(getattr(df_row, "arr_num"))
                if pd.notna(getattr(df_row, "arr_num"))
                else None
            ),
            "arr_nom": (
                normalize_string(getattr(df_row, "arr_nom"))
                if pd.notna(getattr(df_row, "arr_nom"))
                else None
            ),
            "arr_classification": (
                normalize_string(getattr(df_row, "arr_classification"))
                if pd.notna(getattr(df_row, "arr_classification"))
                else None
            ),
            "arr_proc_urgence": (
                normalize_string(getattr(df_row, "arr_proc_urgence"))
                if pd.notna(getattr(df_row, "arr_proc_urgence"))
                else None
            ),
            "arr_demolition": (
                normalize_string(getattr(df_row, "arr_demolition"))
                if pd.notna(getattr(df_row, "arr_demolition"))
                else None
            ),  # TODO affiner
            "arr_interdiction": (
                normalize_string(getattr(df_row, "arr_interdiction"))
                if pd.notna(getattr(df_row, "arr_interdiction"))
                else None
            ),  # TODO affiner
            "arr_equipcomm": (
                normalize_string(getattr(df_row, "arr_equipcomm"))
                if pd.notna(getattr(df_row, "arr_equipcomm"))
                else None
            ),  # TODO affiner
            # (métadonnées du doc)
            "arr_nom_pdf": getattr(df_row, "filename"),
            "arr_url": getattr(df_row, "fullpath"),  # TODO URL localhost?
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
        # - nettoyer a minima la commune extraite des en-tête ou pied-de-page ou de la mention du maire signataire
        adr_commune_maire = (
            normalize_string(getattr(df_row, "commune_maire"))
            if pd.notna(getattr(df_row, "commune_maire"))
            else None
        )
        # - créer une adresse normalisée ; la cohérence des champs est vérifiée
        adr_adresse = create_adresse_normalisee(adr_fields, adr_commune_maire)
        # - rassembler les champs
        doc_adr = {
            # adresse
            "adr_ad_brute": adr_ad_brute,  # adresse brute
            "adr_adresse": adr_adresse,  # adresse normalisée
            "adr_num": adr_fields["adr_num"],  # numéro de la voie
            "adr_ind": adr_fields["adr_ind"],  # indice de répétition
            "adr_voie": adr_fields["adr_voie"],  # nom de la voie
            "adr_compl": adr_fields["adr_compl"],  # complément d'adresse
            "adr_cpostal": adr_fields["adr_cpostal"],  # code postal
            "adr_ville": adr_commune_maire,  # ville
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
            "not_nom_propri": "TODO_proprietaire",  # nom des propriétaries
            "not_ide_syndic": (
                normalize_string(getattr(df_row, "syndic"))
                if pd.notna(getattr(df_row, "syndic"))
                else None
            ),  # identification du syndic
            "not_nom_syndic": "TODO_syndic",  # nom du syndic
            "not_ide_gestio": "TODO_gestio",  # identification du gestionnaire
        }
        doc_data = doc_idu | doc_arr | doc_adr | doc_par | doc_not
        doc_rows.append(doc_data)
    df_docs = pd.DataFrame.from_records(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_DATA)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
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

"""Enrichit les données avec des données supplémentaires.

Ajoute le code INSEE de la commune.
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path
import re
from typing import NamedTuple

import pandas as pd

from adresse import CP_MARSEILLE
from extract_data import DTYPE_DATA
from knowledge_bases import load_codes_insee_amp


# charger la table des codes INSEE des communes
DF_INSEE = load_codes_insee_amp()


# normalisation/simplification du nom de la commune pour aider le matching
# TODO fuzzyjoin ?
def simplify_commune(com: str) -> str:
    """Simplifier le nom d'une commune pour faciliter le matching.

    Parameters
    ----------
    com: str
        Nom de la commune

    Returns
    -------
    com_simple: str
        Nom de la commune simplifié
    """
    return com.lower().replace("é", "e").replace("-", "").replace(" ", "")


COM2INSEE = {
    simplify_commune(com): insee for com, insee in DF_INSEE.itertuples(index=False)
}


# TODO fuzzyjoin ?
def fill_codeinsee(df_row: NamedTuple) -> str:
    """Ajouter le code INSEE de la commune à une entrée.

    Parameters
    ----------
    df_row: NamedTuple
        Entrée contenant la commune et le code postal

    Returns
    -------
    df_row_enr: NamedTuple
        Entrée enrichie du code INSEE.
    """
    com = df_row.adr_ville
    if pd.isna(com):
        codeinsee = None
    elif pd.notna(df_row.adr_cpostal) and (df_row.adr_cpostal in CP_MARSEILLE):
        # TODO expectation: aucun codeinsee 13055 dans le dataset final
        codeinsee = "132" + df_row.adr_cpostal[-2:]
    else:
        codeinsee = COM2INSEE.get(
            simplify_commune(com), None
        )  # TODO robuste  # TODO code postal pour les arrondissements de Marseille
    df_row_enr = df_row._replace(adr_codeinsee=codeinsee)
    return df_row_enr


# FIXME déplacer+refactoriser vers un module spécifique cadastre
RE_CAD_ARRT_QUAR = (
    r"""(?P<arrt>2[01]\d)"""  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"""\s*"""
    + r"""(?P<quar>\d{3})"""  # code quartier
)
# toutes communes: section et numéro
RE_CAD_SEC = r"""(?P<sec>[A-Z]{1,2})"""
RE_CAD_NUM = r"""(?P<num>\d{1,4})"""
# expression complète
# - Marseille
RE_CAD_MARSEILLE = rf"""(?:(?:n°\s?){RE_CAD_ARRT_QUAR}\s+{RE_CAD_SEC}\s?{RE_CAD_NUM})"""
M_CAD_MARSEILLE = re.compile(RE_CAD_MARSEILLE, re.MULTILINE | re.IGNORECASE)
# - autres communes
RE_CAD_AUTRES = rf"""(?:(?:n°\s?)?{RE_CAD_SEC}(?:\sn°)?\s?{RE_CAD_NUM})"""
M_CAD_AUTRES = re.compile(RE_CAD_AUTRES, re.MULTILINE | re.IGNORECASE)


def generate_refcadastrale_norm(df_row: NamedTuple) -> str:
    """Génère une référence cadastrale normalisée à une entrée.

    Nécessite le code INSEE de la commune.

    Parameters
    ----------
    df_row: NamedTuple
        Entrée contenant la commune et son code INSEE.

    Returns
    -------
    df_row_enr: NamedTuple
        Entrée enrichie de la référence cadastrale normalisée.
    """
    # ajouter le préfixe du code insee
    # TODO cas particulier pour Marseille: code commune par ardt + code quartier
    codeinsee = df_row.adr_codeinsee
    if pd.isna(codeinsee):
        codeinsee = ""  # TODO vérifier si le comportement qui en découle est ok (identifiant court, à compléter manuellement par le code insee)

    # prendre la référence locale (commune)
    refcad = df_row.par_ref_cad
    if pd.isna(refcad):
        refcad = None
    elif m_mars := M_CAD_MARSEILLE.match(refcad):
        # match(): on ne garde que le 1er match
        # TODO gérer 2 ou plusieurs références cadastrales
        m_dict = m_mars.groupdict()
        arrt = m_dict["arrt"]
        if codeinsee and codeinsee != "13055":
            try:
                assert codeinsee[-3:] == arrt
            except AssertionError:
                # FIXME améliorer le warning ; écrire une expectation sur le dataset final
                logging.warning(
                    f"{df_row.arr_pdf}: conflit entre code INSEE ({codeinsee}, via code postal {df_row.adr_cpostal}) et référence cadastrale {arrt}"
                )
        else:
            codeinsee = f"13{arrt}"
        # Marseille: code insee arrondissement + code quartier (3 chiffres) + section + parcelle
        refcad = f"{codeinsee}{m_dict['quar']}{m_dict['sec']:>02}{m_dict['num']:>04}"
    elif m_autr := M_CAD_AUTRES.match(refcad):
        m_dict = m_autr.groupdict()
        # hors Marseille: code insee commune + 000 + section + parcelle
        codequartier = "000"
        refcad = f"{codeinsee}{codequartier}{m_dict['sec']:>02}{m_dict['num']:>04}"
    else:
        refcad = None
    df_row_enr = df_row._replace(par_ref_cad=refcad)
    return df_row_enr


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
        df_row_enr = fill_codeinsee(df_row)
        df_row_enr = generate_refcadastrale_norm(df_row_enr)
        doc_rows.append(df_row_enr)
    df_docs = pd.DataFrame(doc_rows)
    df_docs = df_docs.astype(dtype=DTYPE_DATA)
    return df_docs


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/enrich_data_{datetime.now().isoformat()}.log",
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
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées et données enrichies extraites des documents",
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
    df_meta = pd.read_csv(in_file, dtype=DTYPE_DATA)
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

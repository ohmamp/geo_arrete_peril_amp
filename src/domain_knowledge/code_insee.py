"""Gérer les codes INSEE par commune.

TODO créer des modules similaires pour les autres bases de connaissances:
* la table des codes postaux (TODO),
* les variantes de graphies des communes (TODO),
* une liste de syndics (TODO).
"""

from pathlib import Path

import pandas as pd

from src.domain_knowledge.adresse import CP_MARSEILLE


# dossier contenant les bases de connaissances
EXT_DIR = Path(__file__).resolve().parents[2] / "data" / "external"
# fichier contenant les codes INSEE par commune, pour les communes de la métropole
FP_INSEE = EXT_DIR / "codes_insee_amp.csv"
# type des colonnes du fichier CSV
DTYPE_INSEE = {"commune": "string", "code_insee": "string"}


def load_codes_insee_amp() -> pd.DataFrame:
    """Charger les codes INSEE des communes

    Actuellement restreint à la Métropole Aix-Marseille Provence.

    Returns
    -------
    df_insee: pd.DataFrame
        Liste des communes avec leur code INSEE.
    """
    df_insee = pd.read_csv(FP_INSEE, dtype=DTYPE_INSEE)
    return df_insee


# charger la table des codes INSEE des communes
DF_INSEE = load_codes_insee_amp()


# normaliser/simplifier le nom de la commune pour aider le matching
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
    # FIXME utiliser unicodedata.normalize
    return (
        com.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("-", "")
        .replace(" ", "")
    )


# mapping des communes simplifiées vers le code INSEE, qui pourra être importé par les autres modules
COM2INSEE = {
    simplify_commune(com): insee for com, insee in DF_INSEE.itertuples(index=False)
}


# TODO fuzzyjoin ?
def get_codeinsee(nom_commune: str, cpostal: str) -> str:
    """Récupérer le code INSEE d'une commune.

    Parameters
    ----------
    nom_commune: string
        Nom de la commune
    cpostal: string
        Code postal, utile pour les arrondissements de Marseille

    Returns
    -------
    codeinsee: string
        Code INSEE de la commune.
    """
    if pd.isna(nom_commune):
        codeinsee = None
    elif pd.notna(cpostal) and (cpostal in CP_MARSEILLE):
        # TODO expectation: aucun codeinsee 13055 dans le dataset final
        codeinsee = "132" + cpostal[-2:]
    else:
        codeinsee = COM2INSEE.get(
            simplify_commune(nom_commune), None
        )  # TODO robuste  # TODO code postal pour les arrondissements de Marseille
    return codeinsee

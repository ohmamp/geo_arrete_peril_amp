"""Gérer les bases de connaissances.

Permet de charger:
* la table des codes INSEE par commune,
* la table des codes postaux (TODO),
* les variantes de graphies des communes (TODO),
* une liste de syndics.
"""

from pathlib import Path

import pandas as pd

# dossier contenant les bases de connaissances
EXT_DIR = Path(__file__).resolve().parents[1] / "data" / "external"

# codes INSEE
FP_INSEE = EXT_DIR / "codes_insee_amp.csv"

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

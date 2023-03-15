"""Accès aux codes géographiques (codes INSEE, codes postaux) des communes.

TODO créer des modules similaires pour les autres bases de connaissances:
* les variantes de graphies des communes (TODO),
* une liste de syndics (TODO).
"""

from pathlib import Path
import re

import pandas as pd


# dossier contenant les bases de connaissances
EXT_DIR = Path(__file__).resolve().parents[2] / "data" / "external"

# codes INSEE
#
# fichier contenant les codes INSEE par commune, pour les communes de la métropole AMP
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


# codes postaux
#
# fichier contenant les codes postaux par code INSEE, pour les communes de la métropole AMP
FP_CPOSTAL = EXT_DIR / "codeinsee_codepostal.csv"
# type des colonnes du fichier CSV
DTYPE_CPOSTAL = {"CODEINSEE": "string", "Field3": "string"}


def load_codes_postaux_amp() -> pd.DataFrame:
    """Charger les codes postaux des communes, associés aux codes INSEE.

    Actuellement restreint à la Métropole Aix-Marseille Provence.

    Returns
    -------
    df_cpostal: pd.DataFrame
        Liste des codes postaux par (code INSEE de) commune.
    """
    df_cpostal = pd.read_csv(FP_CPOSTAL, dtype=DTYPE_CPOSTAL)
    return df_cpostal


# charger la table des codes postaux des communes (par code INSEE)
DF_CPOSTAL = load_codes_postaux_amp()

# liste des codes postaux de Marseille, stockée distinctement ;
# TODO ? utiliser cette liste pour changer de stratégie de reconnaissance des parcelles cadastrales
# (à Marseille: références longues incluant l'arrondissement et le quartier)
CP_MARSEILLE = [f"130{i:02}" for i in range(1, 17)]


# noms des communes (de la métropole AMP)
#
# - formes canoniques, tirées de la liste des codes INSEE
S_COMMUNES_NORM = DF_INSEE["commune"]

# - variantes de graphie: on transforme la liste des formes canoniques en une expression régulière
# qui reconnaît également les variantes de graphie les plus courantes
S_RE_COMMUNES_VARS = (
    DF_INSEE["commune"]
    # - arrondissements (sur AMP, ne concerne que Marseille): ajout d'une forme courte
    .str.replace(r"e\s+Arrondissement", r"(ème|e)(\\s+Arrondissement)?", regex=True)
    .str.replace(r"er\s+Arrondissement", r"er(\\s+Arrondissement)?", regex=True)
    # - espaces
    .str.replace(r"\s+", r"\\s+", regex=True)
    # - espaces à la place des traits d'union
    .str.replace(r"-", r"[ -]", regex=True)
    # - apostrophes
    .str.replace(r"'", r"['’ ]", regex=True)
    # - accents
    # a
    .str.replace(r"À", r"[ÀA]", regex=True)
    .str.replace(r"à", r"[àa]", regex=True)
    # e
    # ou une seule attrape-tout pour être plus robuste (quitte à être trop tolérant)?
    # eg. r"[éèêë]", r"[éèêëe]"
    .str.replace(r"É", r"[ÉE]", regex=True)
    .str.replace(r"È", r"[ÈE]", regex=True)
    .str.replace(r"Ê", r"[ÊE]", regex=True)
    .str.replace(r"Ë", r"[ËE]", regex=True)
    .str.replace(r"é", r"[ée]", regex=True)
    .str.replace(r"è", r"[èe]", regex=True)
    .str.replace(r"ê", r"[êe]", regex=True)
    .str.replace(r"ë", r"[ëe]", regex=True)
    # i
    .str.replace(r"Î", r"[ÎI]", regex=True)
    .str.replace(r"î", r"[îi]", regex=True)
    # o
    .str.replace(r"Ô", r"[ÔO]", regex=True)
    .str.replace(r"ô", r"[ôo]", regex=True)
    # u
    .str.replace(r"Ù", r"[ÙU]", regex=True)
    .str.replace(r"Û", r"[ÛU]", regex=True)
    .str.replace(r"ù", r"[ùu]", regex=True)
    .str.replace(r"û", r"[ûu]", regex=True)
)

# expression régulière avec toutes les graphies de tous les noms de communes (de la métropole AMP)
# le regex engin de python s'arrête au 1er match dans une alternative, donc on doit :
# 1. (obligatoire) remonter les arrondissements de Marseille avant "Marseille" (tout court) pour éviter que "Marseille"
# soit reconnu plutôt que la forme longue qui est plus précise,
# 2. (optionnel) trier par nombre d'occurrences décroissant (ou en proxy: par population de commune) pour accélérer l'exécution
#
# 1.
MASK_MRS_ARRTS = S_RE_COMMUNES_VARS.str.startswith("Marseille\\s+")
MASK_MRS = S_RE_COMMUNES_VARS == "Marseille"
S_RE_MARSEILLE_ARRTS = S_RE_COMMUNES_VARS[MASK_MRS_ARRTS]
S_RE_MARSEILLE = S_RE_COMMUNES_VARS[MASK_MRS]
# 2. pour le moment, on laisse les autres communes dans l'ordre du CSV source
# ordre actuel: codes INSEE (donc base alphabétique) puis communes récentes puis autres départements puis arrondissements de Marseille
S_RE_AUTRES_COMMUNES = S_RE_COMMUNES_VARS[~(MASK_MRS_ARRTS | MASK_MRS)]
# on rassemble la liste: arrondissements de Marseille, puis Marseille, puis autres communes
S_RE_COMMUNES_SORTED = pd.concat(
    [S_RE_MARSEILLE_ARRTS, S_RE_MARSEILLE, S_RE_AUTRES_COMMUNES]
)
# on crée l'expression régulière qui reconnaît l'une des communes, et on la compile
RE_COMMUNES_AMP_ALLFORMS = r"(?:" + r"|".join(S_RE_COMMUNES_SORTED.tolist()) + r")"
P_COMMUNES_AMP_ALLFORMS = re.compile(
    RE_COMMUNES_AMP_ALLFORMS, re.IGNORECASE | re.MULTILINE
)

# opérations sur les communes, utilisant les codes INSEE et codes postaux
#
# transformer le nom de la commune vers une signature simplifiée pour rendre le matching plus robuste
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


# TODO à reprendre
# mapping des communes simplifiées vers le code INSEE, qui pourra être importé par les autres modules
COM2INSEE = {
    simplify_commune(com): insee for com, insee in DF_INSEE.itertuples(index=False)
}


# TODO fuzzyjoin ?
def get_codeinsee(nom_commune: str, cpostal: str | None) -> str | None:
    """Récupérer le code INSEE d'une commune.

    Le code postal est utilisé pour les arrondissements de Marseille.

    Parameters
    ----------
    nom_commune: string
        Nom de la commune
    cpostal: string or None
        Code postal, utile pour les arrondissements de Marseille

    Returns
    -------
    codeinsee: string
        Code INSEE de la commune.
    """
    if pd.isna(nom_commune):
        return None

    nom_commune = (
        nom_commune.strip()
    )  # TODO s'assurer que strip() est fait en amont, à l'extraction de la donnée ?
    # vérifier que nom_commune est une graphie d'une commune de la métropole
    try:
        assert P_COMMUNES_AMP_ALLFORMS.match(nom_commune) or nom_commune in (
            "la",
        )  # FIXME: arrêtés mal lus
    except AssertionError:
        print(repr(nom_commune))
        raise

    if (
        nom_commune.lower() == "marseille"
        and pd.notna(cpostal)
        and (cpostal in CP_MARSEILLE)
    ):
        # NB: c'est une approximation !
        # TODO expectation: aucun codeinsee 13055 dans le dataset final (ou presque)
        codeinsee = "132" + cpostal[-2:]
    else:
        # TODO éprouver et améliorer la robustesse
        codeinsee = COM2INSEE.get(simplify_commune(nom_commune), None)

    return codeinsee

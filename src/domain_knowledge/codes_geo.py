"""Accès aux codes géographiques (codes INSEE, codes postaux) des communes.

TODO créer des modules similaires pour les autres bases de connaissances:
* les variantes de graphies des communes (TODO),
* une liste de syndics (TODO).
"""

import logging
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
    Attention, le fichier actuel (2023-03-18) utilise un séparateur ";".

    Returns
    -------
    df_cpostal: pd.DataFrame
        Liste des codes postaux par (code INSEE de) commune.
    """
    df_cpostal = pd.read_csv(FP_CPOSTAL, dtype=DTYPE_CPOSTAL, sep=";")
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
    # rendre "les" et "le" initial optionnel, ex: les Pennes Mirabeau => Fait aux Pennes Mirabeau
    .str.replace(r"^Les\s", r"(Les\\s)?", regex=True)
    .str.replace(r"^Le\s", r"(Le\\s)?", regex=True)
    # - espaces
    .str.replace(r"\s+", r"\\s+", regex=True)
    # - espaces à la place des traits d'union
    .str.replace(r"-", r"[\\s-]", regex=True)
    # - apostrophes
    .str.replace(r"'", r"['’\\s]", regex=True)
    # - accents
    # a
    .str.replace(r"À", r"[ÀA]", regex=True)
    .str.replace(r"à", r"[àa]", regex=True)
    # c
    .str.replace(r"Ç", r"[ÇC]", regex=True)
    .str.replace(r"ç", r"[çc]", regex=True)
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

VILLE_PAT_NORM = [
    (re.compile(x, re.IGNORECASE | re.MULTILINE), y)
    for x, y in zip(S_RE_COMMUNES_VARS, DF_INSEE["commune"].tolist())
]


# TODO ? Possible de faire plus rapide en adaptant le code de <https://stackoverflow.com/a/2400577>,
# en utilisant comme clé non pas la chaîne reconnue mais l'expression régulière correspondante,
# comme <https://stackoverflow.com/questions/2554185/match-groups-in-python> ?
def normalize_ville(raw_ville: str) -> str:
    """Normalise un nom de ville.

    Les formes reconnues par `S_RE_COMMUNES_VARS` sont réécrites dans la forme canonique
    tirée de `DF_INSEE["commune"]`.
    Pour les villes absentes de cette ressource externe, le nom est renvoyé tel quel.

    Parameters
    ----------
    raw_ville: str
        Nom brut de la ville, extrait du document.

    Returns
    -------
    nor_ville: str
        Forme normale, canonique, du nom de ville.
    """
    for p_ville, norm_ville in VILLE_PAT_NORM:
        if p_ville.match(raw_ville):
            return norm_ville
    else:
        # si toutes les possibilités ont été épuisées,
        # renvoyer la valeur en entrée
        return raw_ville


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
        .replace("à", "a")
        .replace("ç", "c")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("î", "i")
        .replace("ï", "i")
        .replace("ô", "o")
        .replace("û", "u")
        .replace("ÿ", "y")
        .replace("-", "")
        .replace(" ", "")
    )


# TODO à reprendre
# mapping des communes simplifiées vers le code INSEE, qui pourra être importé par les autres modules
COM2INSEE = {
    simplify_commune(com): insee for com, insee in DF_INSEE.itertuples(index=False)
}
# mapping du code INSEE vers le code postal ; aucun code postal n'est associé à 13055 (Marseille sans précision de l'arrondissement)
INSEE2POST = {
    codeinsee: cpostal for codeinsee, cpostal in DF_CPOSTAL.itertuples(index=False)
}


# TODO fuzzyjoin ?
def get_codeinsee(nom_commune: str, cpostal: str) -> str:
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
            "la Gardanne",
        )  # FIXME: arrêtés mal lus
    except AssertionError:
        # TODO détecter et exclure les communes hors Métropole en amont?
        logging.warning(
            f"Impossible de déterminer le code INSEE pour {nom_commune}, hors métropole?"
        )
        # raise
        return None

    if (
        nom_commune.lower().startswith("marseille")
        and pd.notna(cpostal)
        and (cpostal in CP_MARSEILLE)
    ):
        # NB: c'est une approximation !
        # TODO expectation: aucun codeinsee 13055 dans le dataset final (ou presque)
        codeinsee = "132" + cpostal[-2:]
    else:
        # TODO éprouver et améliorer la robustesse
        codeinsee = COM2INSEE.get(simplify_commune(nom_commune), None)
        if not codeinsee:
            logging.warning(
                f"get_codeinsee: pas de code trouvé pour {(nom_commune, cpostal)} (simplify_commune={simplify_commune(nom_commune)})."
            )

    return codeinsee


# TODO fuzzyjoin ?
def get_codepostal(nom_commune: str, codeinsee: str) -> str:
    """Récupérer le code postal d'une commune à partir de son code INSEE.

    Attention, risque d'erreurs car certaines communes étendues sont couvertes par plusieurs codes postaux:
    Marseille (1 par arrondissement, chaque arrondissement a aussi son COG)
    mais aussi Aix-en-Provence (1 COG mais 6 codes postaux: 13080, 13090, 13098, 13100, 13290, 13540),
    Martigues (codes postaux: 13117, 13500).

    TODO Le nom de la commune est-il utile?

    Parameters
    ----------
    nom_commune: string
        Nom de la commune (inutile?)
    codeinsee: string or None
        Code INSEE.

    Returns
    -------
    cpostal: string
        Code postal de la commune.
    """
    if pd.isna(nom_commune):
        return None

    nom_commune = (
        nom_commune.strip()
    )  # TODO s'assurer que strip() est fait en amont, à l'extraction de la donnée ?
    # vérifier que nom_commune est une graphie d'une commune de la métropole
    try:
        assert P_COMMUNES_AMP_ALLFORMS.match(nom_commune) or nom_commune in (
            "la Gardanne",
        )  # FIXME: arrêtés mal lus
    except AssertionError:
        # TODO détecter et exclure les communes hors Métropole en amont?
        logging.warning(
            f"Impossible de déterminer le code INSEE pour {nom_commune}, hors métropole?"
        )
        # raise
        return None

    if (
        nom_commune.lower().startswith("marseille")
        and pd.notna(codeinsee)
        and (codeinsee.startswith("132"))  # FIXME généraliser/améliorer?
    ):
        # NB: c'est une approximation !
        # TODO expectation: aucun codeinsee 13055 dans le dataset final (ou presque)
        cpostal = "130" + codeinsee[-2:]
        # 2023-03-18: a priori, cela ne devrait rien changer car le code INSEE est déterminé à partir du code postal pour les arrondissements de Marseille
    elif pd.notna(codeinsee) and (simplify_commune(nom_commune), codeinsee) in (
        ("aixenprovence", "13001"),
        ("martigues", "13056"),
    ):
        cpostal = None  # pour que create_adresse_normalisee() n'ait à gérer des valeurs pd.<NA> dont la valeur booléenne est ambigue (alors que None est faux)
        logging.warning(
            f"get_codepostal: abstention, plusieurs codes postaux possibles pour {(nom_commune, codeinsee)}."
        )
    else:
        # TODO éprouver et améliorer la robustesse
        cpostal = INSEE2POST.get(codeinsee, None)
        if pd.isna(cpostal):
            cpostal = None  # pour que create_adresse_normalisee() n'ait à gérer des valeurs pd.<NA> dont la valeur booléenne est ambigue (alors que None est faux)
            logging.warning(
                f"get_codepostal: pas de code trouvé pour {(nom_commune, codeinsee)}."
            )

    return cpostal

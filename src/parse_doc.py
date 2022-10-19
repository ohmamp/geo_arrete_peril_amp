"""Analyse le document dans son ensemble.

Découpe l'arrêté en zones.
"""

from pathlib import Path
import re

RE_AUTORITE = (
    r"("
    + r"("
    + r"("
    + r"|".join(
        [
            r"(NOUS, MAIRE D')",  # AIX-EN-PROVENCE
            r"(Nous, Maire de )",  # Marseille
            r"(NOUS, (?P<autorite_nom>.*), Maire de la commune d')",  # Allauch
            r"(Le Maire de la Commune d['’])",  # ISTRES, Auriol, Aubagne (certains)
            r"(Le Maire de la Ville de )",  # Châteauneuf-les-Martigues
            r"(Le Maire de )",  # Gardanne
        ]
    )
    + r")"
    + r"(?P<commune>.+)"
    + r")"
    # + r"|(Le Maire)"  # fallback, utile pour eg. Aubagne
    + r")"
)
P_AUTORITE = re.compile(RE_AUTORITE)


def parse_arrete(fp_txt_in: Path) -> dict:
    """Analyse un arrêté pour le découper en zones.

    Parameters
    ----------
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    content: dict
        Contenu du document, découpé en zones de texte.
    """
    # ouvrir le fichier
    with open(fp_txt_in) as f:
        txt = f.read()
    # préparer le dictionnaire à renvoyer
    content = {}
    # entete
    # objet
    # autorite
    m_autorite = P_AUTORITE.search(txt)
    if m_autorite is not None:
        content["autorite"] = m_autorite.group(0)
    # vus
    # considerants
    # articles
    # pieddepage
    return content


if __name__ == "__main__":
    # TODO argparse
    INT_TXT_DIR = Path("../data/interim/txt")
    for fp_txt in sorted(INT_TXT_DIR.glob("*.txt")):
        content = parse_arrete(fp_txt)
        print(f"{fp_txt.name}:\t{content}")

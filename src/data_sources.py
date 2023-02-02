"""Sources de données.
"""

from pathlib import Path

# chemins par défaut, arborescence cookiecutter
RAW_DATA_DIR = Path("../data/raw/")  # ici: entrée
INT_DATA_DIR = Path("../data/interim")  # ici: sortie

# lots connus: dossiers contenant des PDF texte et image
RAW_BATCHES = {
    # hors Marseille 2018-2022
    "amp-nmrs-2018-2022": RAW_DATA_DIR / "arretes_peril_hors_marseille_2018_2022",
    # Marseille 2011-2018
    "mrs-2011-2018": RAW_DATA_DIR / "arretes_peril_marseille_2011_2018",
    # Marseille 2019
    "mrs-2019": RAW_DATA_DIR / "arretes_perils_marseille_2019_2020_2021" / "2019-ok",
    # Marseille 2020
    "mrs-2020": RAW_DATA_DIR / "arretes_perils_marseille_2019_2020_2021" / "2020-ok",
    # Marseille 2021
    "mrs-2021": RAW_DATA_DIR / "arretes_perils_marseille_2019_2020_2021" / "2021-ok",
    # = legacy =
    # exports partiels actes 2022
    "2022-03": RAW_DATA_DIR / "2022-03-08_export-actes/Export_@ctes_arretes_pdf",
    "2022-04": (
        RAW_DATA_DIR
        / "2022-04-13_export-actes/extraction_actes_010122_130422_pdf/extraction_actes_pdf"
    ),
    # dl site VdM: dossier très volumineux, texte incomplet et à OCRiser
    "2018-2021-VdM": RAW_DATA_DIR / "Arretes_2018_2021" / "12_ArretesPDF_VdM",
}

# liste de fichiers à exclure du traitement car ils sortent du périmètre de traitement: diagnostics, rapports...
EXCLUDE_FILES = [
    "9, rue Tranchier MARTIGUES diag solidité.pdf",  # diagnostic
    "péril rue de la Tour.pdf",  # rapport sur état de péril
]

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
# TODO créer une heuristique pour les détecter automatiquement et les écarter
# * 1 page qui commence par "^\s*PERIMETRE\s+DE\s+SECURITE\s*$" => annexe
# * ?
EXCLUDE_FILES = [
    "9, rue Tranchier MARTIGUES diag solidité.pdf",  # diagnostic
    "péril rue de la Tour.pdf",  # rapport sur état de péril
    "10 bld de la liberté rue Lafayette annexe 1.pdf",  # annexe
    "10, rue des Bons enfants annexe 2 13006.pdf",  # annexe: plan périmètre de sécurité
    "modif 10 rue des Bons Enfants 13006 annexe.pdf",  # annexe
    "81, rue Curiol - annexe plan.pdf",  # annexe
    "4 chemin du Pont annexe 13007.pdf",  # annexe
    "GRAVE 29, rue Nau annexe .pdf",  # annexe
    "20, rue Corneille annexe 2 .pdf",  # annexe
    "60a, rue d'aubagne annexe 1 .pdf",  # annexe
    "6, traverse Bernabo annexe 2.pdf",  # annexe
    "131 133 rue du Rouet annexe 2.pdf",  # annexe
    "275 rue Saint Pierre annexe 2.pdf",  # annexe
    "72, rue Saint Pierre annexe 2 pdf.pdf",  # annexe: courrier ABF
    "73, rue Clovis Hugues annexe 1 .pdf",  # annexe: plan périmètre de sécurité
    "37 rue Fernand Pauriol annexes.pdf",  # annexe: plan périmètre de sécurité
    "mainlevée rue Fortin annexe 2.pdf",  # annexe: courrier ABF
    "62 rue Sainte Cécile annexe 13005.pdf",  # annexe: tableau des copropriétaires
    "26 bld de la Liberation annexe 2.pdf",  # annexe: plan périmètre de sécurité
    "28 bld de la Liberation annexe 2.pdf",  # annexe: plan périmètre de sécurité
    "péril 32, rue Fongate annexe 2 .pdf",  # annexe: courrier ABF
    "20, rue d'Anvers péril annexe 1.pdf",  # annexe: plan périmètre de sécurité
    "32, avenue de Saint Just annexe 13004.pdf",  # annexe: plan périmètre de sécurité
    "St Pierre de Mézoargues annexe.pdf",  # annexe: plan périmètre de sécurité
    "périmètre parking puces Oddo 13015.pdf",  # annexe: plan périmètre de sécurité
    "MENPENTI.pdf",  # annexe: plan périmètre de sécurité
    "Arrêté de péril grave et imminent annexe2- 12 rue Château du Mûrier-110619.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 15 rue du Jet d'Eau 13003 périmètre.pdf",  # annexe: plan périmètre de sécurité
    "7, rue du Village.pdf",  # annexe: plan périmètre de sécurité
]

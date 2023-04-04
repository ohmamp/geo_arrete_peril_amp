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
# * p. 1 .match(r"^ANNEXE\s+[I\dZ]+") => annexe  # "IZ" pour le 1 et 2 mal reconnus par OCR
# * p. 1 .search(r"^\s*PERIMETRE\s+DE\s+SECURITE\s*") => annexe
# * .search(r"EXTRAIT\s+DU\s+PLAN\s+CADASTRAL") => annexe
# * .search(r"^Impression non normalisée du plan cadastral$") => annexe
# * .search(r"^Cet extrait de plan vous est délivré par:") => annexe
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
    "Courrier COGEFIM 62, rue Saint Pierre.pdf",  # annexe: courrier syndic
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
    "5 rue du Village.pdf",  # annexe: plan périmètre de sécurité
    "péril 87 rue d'Aubagne 13001 annexe 2.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 2 impasse Moncault 13013 plan.pdf",  # annexe: plan périmètre de sécurité
    "18, rue d'Aix  annexe 13001.pdf",  # annexe: plan périmètre de sécurité
    "Périmètre de sécurité 2 Joliette.pdf",  # annexe: plan périmètre de sécurité
    "modif 8 et 10 impasse Croix de Regnier.pdf",  # annexe: plan périmètre de sécurité
    "39, 41, 43, rue de la Palud péril annexe 3 feuille presence AG.pdf",  # annexe: feuille de présence (liste des copropriétaires)
    "MS 93 rue le Pelletier 13016 plan.pdf",  # annexe: plan périmètre de sécurité
    "déconstruction 41 43 rue de la Palud annexe 1 .pdf",  # annexe: feuille de présence (liste des copropriétaires)
    "périmètre de sécurité rue Charvet et interdiction 17 et 26 rue Charvet annexe.pdf",  # annexe: plan périmètre de sécurité
    "Périmètre de sécurité Joliette.pdf",  # annexe: plan périmètre de sécurité
    "MS 169 rue Rabelais 13016 plan.pdf",  # annexe: plan périmètre de sécurité
    "PLAN CADASTRAL.pdf",  # annexe: plan périmètre de sécurité
    "83 rue Antoine Del Bello - annex 2 10.02.20.pdf",  # annexe: plan périmètre de sécurité
    "simple 81 rue Curiol 13001 - plan.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 25 rue de Crimée 17 bld G. Desplaces 13003 plan.pdf",  # annexe: plan périmètre de sécurité
    "modif déconstruction 535 rue Saint Pierre 13012 plan.pdf",  # annexe: plan périmètre de sécurité
    "39, 41, 43, rue de la Palud péril annexe 5 feuille présence AG.pdf",  # annexe: feuille de présence (liste des copropriétaires)
    "mise en sécurité 7 rue du Village 13006 périmètre.pdf",  # annexe: plan périmètre de sécurité
    "péril 68-70, av de SaintAntoine 13015 plan.pdf",  # annexe: plan périmètre de sécurité
    "4 rue Eugène Pottier 1 rue Hoche 13003 MS périmètre.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 275 rue Saint Pierre 13005 annexe 2.pdf",  # annexe: plan périmètre de sécurité
    "annexe 2 Plan.pdf",  # annexe: plan périmètre de sécurité
    "déconstruction 535 rue Saint Pierre 13012 schéma.pdf",  # annexe: plan périmètre de sécurité
    "périmètre de sécurité 535 rue Saint Pierre 13012.pdf",  # annexe: plan périmètre de sécurité
    "annexe main levée 19bis quai de la Joliette  13002.pdf",  # annexe: plan périmètre de sécurité
    "modif 42 bis, rue François Barbini.pdf",  # annexe: plan périmètre de sécurité
    "8 - 10 impasse Croix de Regnier.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 28 bld de la Libération 13001 périmètre.pdf",  # annexe: plan périmètre de sécurité
    "J JAURES 13006 - anexe périmètre sécurité.pdf",  # annexe: plan périmètre de sécurité
    "péril 20, rue Corneille annexe 2 13001.pdf",  # annexe: plan périmètre de sécurité
    "MS 75 cours Lieutaud 13006 annexe 2.pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 26 bld de la Libération 13001 périmètre.pdf",  # annexe: plan périmètre de sécurité
    "déconstruction 41 43 rue de la Palud annexe 2 .pdf",  # annexe: plan périmètre de sécurité
    "ordinaire 4 impasse Moncault 13013 plan.pdf",  # annexe: plan périmètre de sécurité
    "MS 13 rue de la Joliette 13002 PS.pdf",  # annexe: plan périmètre de sécurité
    "Périmètre rue F Pauriol 2.pdf",  # annexe: plan périmètre de sécurité
    "31 TRAVERSE TENERIFE etpérimètre de sécurité 13016 annexe.pdf",  # annexe: plan périmètre de sécurité
    "annexe.pdf",  # annexe: plan périmètre de sécurité
    "6, rue de la Butte.pdf",  # annexe: plan périmètre de sécurité
    "Plan avenue Camille Pelletan 13003.pdf",  # annexe: plan périmètre de sécurité
    "6_traverse_Ténérife_13016 annexe.pdf",  # annexe: plan périmètre de sécurité
    "péril 8, rue Capitaine Galinat annexe 1 .pdf",  # annexe: schéma de principe
    "plan 73 chemin de Saint Henri 13016 annexe 3.pdf",  # annexe: plan périmètre de sécurité
    "297, avenue de la Capelette.pdf",  # annexe: plan périmètre de sécurité
    "bld National2.pdf",  # annexe: plan périmètre de sécurité
    "158, avenue Roger Salengro Pér Sec.pdf",  # annexe: plan périmètre de sécurité
    "péril 4 rue Eugène Pottier annexe 2.pdf",  # id
    "ordinaire rue de la Javie 13014 plan.pdf",  # id
    "83, rue Curiol.pdf",  # id
    "11 bld Ménard annex 1 .pdf",  # id
    "21 rue Clovis Hugues impasse bleue.pdf",  # id
    "ordinaire 38 avenue F Zoccola 13015 périmètre.pdf",  # id
    "modif 4 rue Eugène Pottier.pdf",  # id
    "Annexe2 rue St Pierre.pdf",  # id
    "43-45, rue Michel Gachet 13007annexe 1 .pdf",  # id
    "3 place Sadi Carnot 11 rue Mery Périmetre sécurité.pdf",  # id
    "PS 15 rue de la Joliette 13002.pdf",  # id
    "4, impasse Montcault 13013 annexe 2.pdf",  # id
    "43-45, rue Michel Gachet 13007 annexe 2 .pdf",  # id
    "ordinaire 42 bis rue François Barbini 13003 périmètre.pdf",  # id
    "234, avenue Roger Salengro annexe.pdf",  # id
    "déconstruction 1, domaine Ventre annexe .pdf",  # id
    "39, 41, 43, rue de la Palud péril annexe 8 perimetre securité.pdf",  # id
    "péril grave 19 bis, quai de la Joliette annexe 1 .pdf",  # id
    "MenS 193 bld S. Bolivar 13015 plan.pdf",  # id
    "mise en sécurité 234 avenue Roger Salengro 13015 périmètre.pdf",  # id
    "ordinaire 40 rue St Bazile 13001 périmètre.pdf",  # id
    "33 avenue de Montolivet 13004 plan.pdf",  # id
    "MS 5 rue du Village 13006 périmètre volume 2000.pdf",  # id
    "imminent 553 rue Saint Pierre 13012 annexe.pdf",  # id
    "modif 21 rue Clovis Hugues annexe.pdf",  # id
    "périmètre de s93 rue le Pelletier 13016 annexe.pdf",  # id
    "ordinaire 12 bld de la Liberté 13001 plan.pdf",  # id
    "58, bld Guigou.pdf",  # id
    "4 rue du Bon Pasteur plan.pdf",  # id
    "20, rue Corneille annexe 2  .pdf",  # id
    "ordinaire 6a impasse Croix de Regnier 13004 périmètre.pdf",  # id
    "modif 19 rue Clovis Hugues annexe 2.pdf",  # id
    "116, avenue Camille Pelletan annexe 1 .pdf",  # id
    "4 rue du Bon Pasteur.pdf",  # id
    "131 133 rue du Rouet 21.02.20 annexe 2.pdf",  # id
    "152 avenue Roger Salengro - périmètre sécurité.pdf",  # id
    "11 rue de la Joliette 13002 périmètre.pdf",  # id
    "154 156 avenue Roger Salengro.pdf",  # id
    "emprise périmètre de sécurité.pdf",  # id
    # TODO test: ces deux documents simples devraient être exclus
    "75 rue Longue des Capucins 16 rue de la Fare annexe 1.pdf",  # TODO test de détection?
    "péril simple 75 rue Longue des Capucins 16 annexe 2.pdf",  # TODO test?
]

EXCLUDE_HORS_AMP = [
    # communes hors Métropole: ce filtrage sera-t-il fait en amont, lors de l'export des données?
    "1, rue Raspail Tarascon.pdf",  # hors AMP: Tarascon
    "arrêté de péril - 22 rue Mirabeau à Tarascon - 141220.pdf",  # hors AMP: Tarascon
    "2,rue du 4 septembre - PO.pdf",  # hors AMP: Tarascon
    "9 RUE DES JUIFS - PGI.pdf",  # hors AMP: Tarascon
    "67 rue du Jeu de Paume Tarascon - PGI 21.02.20.pdf",  # hors AMP: Tarascon
    "22 rue Mirabeau Tarascon.pdf",  # hors AMP: Tarascon
    "11bis rue du Prolétariat.pdf",  # hors AMP: Tarascon
    "2, rue du 4 septembre - PGI 12.07.19.pdf",  # hors AMP: Tarascon
    "rue des Pères de l'Observance.pdf",  # hors AMP: Barbentane
    "5 rue du Château.pdf",  # hors AMP: Barbentane
    "3 rue des Ecoles - PI 22.01.20.pdf",  # hors AMP: Barbentane
    "1, rue du Château 13570  -PI.pdf",  # hors AMP: Barbentane
    "27, place Voltaire Arles.pdf",  # hors AMP: Arles
    "9001 rue Robert Schuman.pdf",  # hors AMP: Arles
    "4 rue Desaix 13003.pdf",  # hors AMP: Arles
    "6 rue Pierre Leroux Arles - mise en sécurité .pdf",  # hors AMP: Arles
]

EXCLUDE_FIXME_FILES = [
    # FIXME fichiers problématiques
    "2, rue Kruger Gardanne - PO.pdf",  # FIXME "Considérant", "Vu", "Considérant" => autoriser ces transitions ?
    "2 rue Léon Gambetta Martigues.pdf",  # FIXME erreur "Pas de Vu en page 1" mais se produit en p. 3 !?
    "69 rue Félix Piat 13003 MARSEILLE.pdf",  # FIXME traiter spécifiquement: ré-océriser tout ou seulement la p. 2 ? la p. 2 est la carte du cadastre, qui contient du texte invisible car en sous-couche du texte principal !
    "partie de la cour intérieure 69 rue Félix Pyat 13003.pdf",  # FIXME id
    "6, bld Louis Frangin 13005.pdf",  # FIXME pas de "ARRETE" ; mais exception "pas de vu" ?
    "Arrêté d'interdiction d'occuper - 13 rue de la fare 13001.pdf",  # FIXME p. 1 vide après "nous, maire...", "vu" seulement en p. 2
    "mainlevée 14 rue Mère de Dieu Peyrolles.pdf",  # FIXME layout 2 colonnes (tous Peyrolles concernés mais celui-ci coince vraiment car peu de "Vu")
    "mainlevée rue de la Tour Peyrolles en Provence.pdf",  # FIXME layout 2 colonnes id
    "739 av Cytharista Mas de la mer.PDF",  # FIXME 2e nom de voie après un 1er nom de voie + un complément d'adresse
    "A.2019-147 Ch. du Four-Garage.pdf",  # FIXME "adresse courte en voie seule", group(0) ne capture pas le complément d'adresse "Garage" ?
]

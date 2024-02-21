"""4 tables:
* arrêté,
* adresse,
* parcelle,
* notifié
"""

import argparse
from datetime import datetime
import logging
from pathlib import Path

import pandas as pd

from src.process.extract_data import DTYPE_DATA

# dtype des tables de sortie
DTYPE_ARRETE = {
    "idu": "string",  # identifiant unique
    "date": "string",  # date de l'arrêté ; TODO type date
    "num_arr": "string",  # numéro de l'arrêté
    "nom_arr": "string",  # nom de l'arrêté
    "classe": "string",  # classification
    "urgence": "string",  # procédure d'urgence
    "demo": "string",  # démolition  ; vals = "par"(tielle), "tot"(ale), "non"
    "int_hab": "string",  # interdiction d'habiter
    "equ_com": "string",  # équipements communs
    "pdf": "string",  # = filename ; nom du PDF
    "url": "string",  # lien vers l'arrêté ; TODO URL serveur
    "codeinsee": "string",  # code insee (5 chars)
    "datemaj": "string",  # date de mise à jour de la donnée ; TODO type date
}

DTYPE_ADRESSE = {
    "idu": "string",  # identifiant unique
    "ad_brute": "string",  # adresse brute
    "num": "string",  # numéro de la voie
    "ind": "string",  # indice de répétition
    "voie": "string",  # nom de la voie
    "compl": "string",  # complément d'adresse
    "cpostal": "string",  # code postal
    "ville": "string",  # ville
    "adresse": "string",  # adresse normalisée
    "codeinsee": "string",  # code insee (5 chars)
    "datemaj": "string",  # date de mise à jour de la donnée ; TODO date
}

DTYPE_PARCELLE = {
    "idu": "string",  # identifiant unique
    "ref_cad": "string",  # référence cadastrale
    "codeinsee": "string",  # code insee (5 chars)
    "datemaj": "string",  # date de mise à jour de la donnée ; TODO date
}

DTYPE_NOTIFIE = {
    "idu": "string",  # identifiant unique
    "id_proprio": "string",  # identification du propriétaire
    "proprio": "string",  # nom des propriétaries
    "id_syndic": "string",  # identification du syndic
    "syndic": "string",  # nom du syndic
    "id_gest": "string",  # identification du gestionnaire
    "gest": "string",  # nom du gestionnaire
    "codeinsee": "string",  # code insee (5 chars)
    "datemaj": "string",  # date de mise à jour de la donnée ; TODO date
}

DTYPE_TABLES = {
    "arrete": DTYPE_ARRETE,
    "adresse": DTYPE_ADRESSE,
    "parcelle": DTYPE_PARCELLE,
    "notifie": DTYPE_NOTIFIE,
}

# association entre les tables de sortie et les préfixes des champs en entrée
PREFIX_TABLES = {
    "arrete": "arr_",
    "adresse": "adr_",
    "parcelle": "par_",
    "notifie": "not_",
}

# URL stable pour les PDF: "yyyy" sera remplacé par l'année de l'arrêté, "pdf" par le nom du fichier
FS_URL = "https://sig.ampmetropole.fr/geodata/geo_arretes/peril/{yyyy}/{pdf}"


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/export_data_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées et données normalisées extraites des documents",
    )
    parser.add_argument(
        "out_dir",
        help="Chemin vers le dossier pour les 4 fichiers CSV en sortie contenant les données extraites des documents",
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
        help="Ajoute les pages annotées aux fichiers de sortie s'ils existent dans out_dir",
    )
    args = parser.parse_args()

    # entrée: CSV de pages de texte
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de documents
    # on crée le dossier parent (récursivement) si besoin
    out_dir = Path(args.out_dir).resolve()
    out_files = {
        x: out_dir / f"paquet_{x}.csv"
        for x in ["arrete", "adresse", "parcelle", "notifie"]
    }
    if out_dir.is_dir():
        for out_file in out_files.values():
            if out_file.is_file():
                if not args.redo and not args.append:
                    # erreur si le fichier CSV existe déjà mais ni redo, ni append
                    raise ValueError(
                        f"Le fichier de sortie {out_file} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
                    )
    else:
        # créer le dossier de sortie si besoin
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(parents=True, exist_ok=True)

    # 1. ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_meta = pd.read_csv(in_file, dtype=DTYPE_DATA)
    # 2. générer une URL stable pour le champ "url" de la table des arrêtés
    if False:  # TODO activer
        df_meta = df_meta.assign(
            arr_url=FS_URL.format(yyyy=df_meta["arr_date"].year, pdf=df_meta["pdf"])
        )
    # 3. initialiser la date de mise à jour au jour du traitement: dd/mm/yyyy
    df_meta = df_meta.assign(datemaj=datetime.now().date().strftime("%d/%m/%Y"))
    # 4. sauvegarder les infos extraites dans un fichier CSV
    for out_key, out_file in out_files.items():
        # sélectionner les données
        # - colonnes à conserver
        prefix_tab = PREFIX_TABLES[out_key]
        sel_cols = (
            ["idu"]
            + [x for x in df_meta.columns if x.startswith(prefix_tab)]
            # ajout du code insee dans les tables autres qu'adresse
            + (["adr_codeinsee"] if out_key != "adresse" else [])
            # date de màj, dans toutes les tables (rmq_iteration_2.docx, 2023-02-14)
            + ["datemaj"]
        )
        # - dtypes de ces colonnes
        sel_dtype = DTYPE_TABLES[out_key]
        df_txts = df_meta[sel_cols].rename(
            columns={x: x.split("_", 1)[1] for x in sel_cols if "_" in x}
        )
        if args.append and out_file.is_file():
            # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
            df_txts_old = pd.read_csv(out_file, dtype=sel_dtype)
            df_txts = pd.concat([df_txts_old, df_txts])
        else:
            # sinon utiliser les seules nouvelles entrées
            df_proc = df_txts
        df_proc.to_csv(out_file, index=False)

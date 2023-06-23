"""Indexer un ensemble de fichiers PDF.

Calcule le hachage de chaque fichier et crée une copie
du fichier dans un dossier de travail, en faisant précéder
le nom du fichier par son hachage.
"""

# TODO ajuster le logging
# TODO détecter les fichers doublons, p. ex. "abrogation déconstruction 41 et 43 rue de la Palud 13001.pdf" et "interdiction 9 traverse Sainte Marie 13003.pdf"
# TODO transformer la blacklist sur les fichiers, importée de data_sources, en vrai script, exécuté en amont, pour exclure les documents non pertinents comme les diagnostics

import argparse
from collections import defaultdict
from datetime import datetime
import logging
from pathlib import Path
import shutil

import pandas as pd

from src.preprocess.data_sources import EXCLUDE_FILES
from src.preprocess.pdf_info import get_pdf_info
from src.utils.file_utils import get_file_digest

# colonnes des fichiers CSV d'index
DTYPE_META_BASE = {
    "pdf": "string",
    "fullpath": "string",
    "filesize": "Int64",  # FIXME Int16 ? (dtype à fixer en amont, avant le dump)
    "nb_pages": "Int64",  # FIXME Int16 ? (dtype à fixer en amont, avant le dump)
    "creatortool": "string",
    "producer": "string",
    "createdate": "string",
    "modifydate": "string",
}

# motif glob pour les fichiers PDF
PAT_PDF = "*.[Pp][Dd][Ff]"


def index_folder(
    in_dir: Path,
    out_dir: Path,
    index_csv: Path,
    new_csv: Path,
    recursive: bool = True,
    digest: str = "blake2b",
    verbose: bool = False,
):
    """Indexer un dossier: hacher et copier les fichiers PDF qu'il contient.

    Les copies sont renommées en préfixant le nom de chaque fichier par le
    hachage, afin d'éviter les conflits de noms de fichiers issus de dossiers
    différents.

    Parameters
    ----------
    in_dir: Path
        Dossier à traiter, contenant des PDF.
    out_dir: Path
        Dossier de sortie, contenant les copies des PDF dont le nom est
        précédé par le hachage.
    index_csv: Path
        Fichier d'index général des PDF.
    new_csv: Path
        Fichier d'index des nouveaux PDF indexés par cette exécution.
    recursive: bool, defaults to True
        Si True, parcourt récursivement le dossier in_dir.
    digest : str, defaults to "blake2b"
        Algorithme de hachage à utiliser
        <https://docs.python.org/3/library/hashlib.html#hash-algorithms> .
    verbose: boolean, defaults to False
        Si True, des warnings sont émis à chaque anomalie constatée dans les
        métadonnées du PDF.
    """
    # 1. lister les PDFs déjà indexés (dans le fichier CSV)
    if index_csv.is_file():
        df_index_old = pd.read_csv(index_csv, dtype=DTYPE_META_BASE)
        logging.info(f"Index CSV chargé: {df_index_old.shape[0]} entrées")
    else:
        # créer un DataFrame vide, mais aux colonnes typées
        df_index_old = pd.DataFrame(columns=DTYPE_META_BASE.keys()).astype(
            DTYPE_META_BASE
        )
        logging.info(f"Pas d'index CSV à charger")
        # df_index_csv = None  # alternative
    set_pdfs_index = set(df_index_old["pdf"])

    # 2. hacher puis copier chaque PDF du dossier d'entrée, dans le dossier destination
    pdfs_in = sorted(in_dir.rglob(PAT_PDF) if recursive else in_dir.glob(PAT_PDF))
    # exclure d'éventuels fichiers non pertinents
    # TODO transformer en vrai script ; utiliser des DataFrames pour accélérer le traitement si le nombre de fichiers concernés augmente trop?
    pdfs_in = [x for x in pdfs_in if x.name not in EXCLUDE_FILES]

    logging.info(f"Dossier {in_dir}: {len(pdfs_in)} fichier(s) PDF trouvé(s)")
    nb_files_copied = 0
    for fp_pdf in pdfs_in:
        # hash du fichier
        f_digest = get_file_digest(fp_pdf, digest=digest)
        # ajout du hash devant le nom de la copie du fichier
        fp_copy = out_dir / f"{f_digest}-{fp_pdf.name}"
        if not fp_copy.is_file():
            shutil.copy2(fp_pdf, fp_copy)
            nb_files_copied += 1
    logging.info(f"Dossier {out_dir}: {nb_files_copied} fichier(s) PDF importé(s)")

    # 3. indexer les fichiers PDFs dans le dossier destination (après les copies)
    # et absents de l'(ancien) index
    fp_pdfs_outdir = sorted(
        out_dir.rglob(PAT_PDF) if recursive else out_dir.glob(PAT_PDF)
    )  # list[PosixPath]
    pdf2path_outdir = {x.name: x for x in fp_pdfs_outdir}
    set_pdfs_outdir = set(pdf2path_outdir.keys())
    set_pdfs_new = set_pdfs_outdir - set_pdfs_index
    pdfs_new = sorted(pdf2path_outdir[x] for x in set_pdfs_new)
    logging.info(f"Fichiers PDF à indexer: {len(pdfs_new)}")
    pdf_infos = []
    for fp_pdf in pdfs_new:
        # extraire les métadonnées (étendues) des fichiers PDF
        pdf_info = get_pdf_info(fp_pdf, verbose=verbose)
        pdf_infos.append(pdf_info)
    if pdf_infos:
        # produire le fichier CSV contenant les nouvelles entrées ajoutées à l'index
        df_index_new = pd.DataFrame(pdf_infos)
        df_index_new = df_index_new.astype(dtype=DTYPE_META_BASE)
        logging.info(f"Nouvelles entrées indexées: {len(pdf_infos)} dans {new_csv}")
        # générer le fichier d'index contenant uniquement les nouvelles entrées de cette exécution
        df_index_new.to_csv(new_csv, index=False)
        # mettre à jour le fichier d'index global
        df_index = pd.concat([df_index_old, df_index_new])
        df_index.to_csv(index_csv, index=False)
    else:
        logging.warning(
            f"Aucune nouvelle entrée n'étant indexée, le fichier {new_csv} ne sera pas créé"
            + f" et le fichier {index_csv} ne sera pas mis à jour."
        )

    # 4. vérifier la qualité de l'état de l'index et du dossier destination:
    # TODO déplacer dans un utilitaire distinct, p. ex. dans quality, et qui
    # serait appelé pour générer le rapport d'erreurs ?
    #
    # - cohérence: signaler les éventuels PDFs présents dans l'index mais absents du
    # dossier destination (déplacés ou supprimés)
    pdfs_mis = sorted(set_pdfs_index - set_pdfs_outdir)
    if pdfs_mis:
        logging.warning(f"Fichiers indexés mais absents de {out_dir} : {len(pdfs_mis)}")
        # TODO marquer, voire supprimer les entrées correspondantes de l'index CSV?
    # - doublons: détecter les doublons *selon la fonction de hachage* dans tout "out_dir"
    # FIXME reprendre le hash (digest) qui est déjà disponible dans l'index CSV, colonne "blake2b"
    # (nom du digest), et calculer les doublons avec pandas?
    hash_dups = defaultdict(list)
    for pdf_path in fp_pdfs_outdir:
        pdf_digest = pdf_path.stem.split("-", 1)[0]
        hash_dups[pdf_digest].append(pdf_path.name)  # ou pdf_path complet ?
    # on repère les hashes non-uniques ; on peut facilement récupérer les groupes de
    # fichiers concernés (pour chaque hash: 1 "original" et ses doublons)
    nb_dups = 0  # nombre de doublons (cumul des fichiers surnuméraires)
    nb_typs = 0  # nombre de fichiers "originaux" ayant au moins 1 doublon
    for pdf_digest, pdf_dups in hash_dups.items():
        if len(pdf_dups) > 1:
            nb_dups += len(pdf_dups) - 1
            nb_typs += 1
    # si on ne voulait que le nombre de doublons:
    # pdfs_hash_set = set(hash_dups.keys())
    # nb_dups = len(pdfs_outdir) - len(pdfs_hash_set)
    logging.info(
        f"Doublons potentiels (même hachage): {nb_dups} ({nb_typs} distincts)"
        + f" dans {out_dir}"
    )
    if False:
        # bonus: afficher des indicateurs
        print(
            df_index[["creatortool", "producer"]]
            .value_counts(dropna=False)
            .to_frame("counts")
            .reset_index()
        )


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    if not dir_log.is_dir():
        dir_log.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=f"{dir_log}/index_pdfs_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )
    logging.captureWarnings(True)

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument("in_dir", help="Dossier contenant les PDFs à indexer")
    parser.add_argument(
        "out_dir",
        help="Dossier de sortie pour les copies des fichiers PDFs indexés avec leur hachage",
    )
    parser.add_argument("index_csv", help="Fichier CSV d'indexation des PDFs")
    parser.add_argument(
        "new_csv",
        help="Fichier CSV d'indexation des PDFs traités lors de cette exécution",
    )
    parser.add_argument(
        "--nonrecursive",
        action="store_true",
        help="Limite la recherche de fichiers PDF au dossier in_dir, sans descendre dans ses éventuels sous-dossiers",
    )
    args = parser.parse_args()

    # entrée: dossier contenant les PDFs à indexer
    in_dir = Path(args.in_dir).resolve()
    if not in_dir.is_dir():
        raise ValueError(
            f"Le dossier contenant les PDFs à indexer n'existe pas: {in_dir}"
        )

    # état persistant (entrée et sortie): dossier où les PDFs renommés sont copiés
    out_dir = Path(args.out_dir).resolve()
    logging.info(
        f"Dossier destination des PDFs: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # état persistant (entrée et sortie): fichier CSV d'index des PDFs
    index_csv = Path(args.index_csv).resolve()
    logging.info(
        f"Fichier CSV d'index des PDFs: {index_csv} {'existe déjà' if index_csv.is_file() else 'doit être créé'}."
    )

    # sortie: fichier CSV reprenant uniquement les nouvelles entrées dans le CSV d'index
    # créées par cette exécution
    new_csv = Path(args.new_csv).resolve()
    logging.info(
        f"Fichier CSV des nouveaux PDFs indexés par cette exécution: {new_csv}"
    )

    # indexer le dossier
    recursive = not args.nonrecursive
    index_folder(in_dir, out_dir, index_csv, new_csv, recursive=recursive)

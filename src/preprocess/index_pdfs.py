"""Indexer un ensemble de fichiers PDF.

Calcule le hachage de chaque fichier et crée une copie
du fichier dans un dossier de travail, en faisant précéder
le nom du fichier par son hachage.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import logging
from pathlib import Path
import shutil

from src.preprocess.data_sources import EXCLUDE_FILES
from src.utils.file_utils import get_file_digest


def index_folder(
    in_dir: Path, out_dir: Path, recursive: bool = True, digest: str = "blake2b"
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
    recursive: bool, defaults to True
        Si True, parcourt récursivement le dossier in_dir.
    digest : str, defaults to "blake2b"
        Algorithme de hachage à utiliser
        <https://docs.python.org/3/library/hashlib.html#hash-algorithms> .
    """
    # lister les PDFs dans le dossier à traiter
    logging.info(f"Ouverture du dossier {in_dir}")
    pat_pdf = "*.[Pp][Dd][Ff]"
    pdfs_in = sorted(in_dir.rglob(pat_pdf) if recursive else in_dir.glob(pat_pdf))
    if not pdfs_in:
        logging.warning(f"Aucun PDF trouvé dans {in_dir}")
    else:
        logging.info(f"Fichiers PDF à indexer: {len(pdfs_in)}")

    # pour chaque PDF, calculer son hachage et le copier dans le dossier de sortie
    for fp_pdf in pdfs_in:
        f_digest = get_file_digest(fp_pdf, digest=digest)  # hash du fichier
        # copie: ajout du hash devant le nom du fichier
        fp_copy = out_dir / f"{f_digest}-{fp_pdf.name}"
        shutil.copy2(fp_pdf, fp_copy)

    # détecter les doublons *selon la fonction de hachage* dans tout "out_dir"
    # TODO déplacer dans un utilitaire distinct, p. ex. dans quality, et qui
    # serait appelé pour générer le rapport d'erreurs ?
    pdfs_outdir = sorted(out_dir.rglob(pat_pdf) if recursive else in_dir.glob(pat_pdf))
    hash_dups = defaultdict(list)
    for pdf_path in pdfs_outdir:
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
        f"{out_dir} contient {nb_dups} doublons potentiels (fichiers de même hachage)"
        + f" concernant {nb_typs} fichiers PDF différents"
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
    parser.add_argument(
        "--nonrecursive",
        action="store_true",
        help="Limite la recherche de fichiers PDF au dossier in_dir, sans descendre dans ses éventuels sous-dossiers",
    )
    args = parser.parse_args()

    # entrée: dossier contenant les PDFs à indexer
    in_dir = Path(args.in_dir).resolve()
    if not in_dir.is_dir():
        raise ValueError(f"Le dossier {in_dir} n'existe pas")

    # sortie: dossier où les PDFs seront copiés
    out_dir = Path(args.out_dir).resolve()
    logging.info(
        f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    # indexer le dossier
    recursive = not args.nonrecursive
    index_folder(in_dir, out_dir, recursive=recursive)

"""Extraire et analyser les métadonnées des fichiers PDF.

Ce module utilise principalement pikepdf, ainsi que poppler
comme point de comparaison (temporaire?).
"""

# TODO ajuster le logging
# TODO détecter les fichers doublons, p. ex. "abrogation déconstruction 41 et 43 rue de la Palud 13001.pdf" et "interdiction 9 traverse Sainte Marie 13003.pdf"
# TODO adapter pour traiter soit les fichiers d'origine, soit les fichiers PDF-A (corrigés)

import argparse
from datetime import datetime, timedelta
from dateutil import tz
import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pikepdf
from poppler import load_from_file

from data_sources import RAW_BATCHES


# fuseau horaire de Paris
TZ_FRA = tz.gettz("Europe/Paris")


def get_pdf_info_poppler(fp_pdf_in: Path) -> dict:
    """Renvoie les infos du PDF en utilisant poppler.

    Les infos incluent un sous-ensemble des métadonnées du PDF.

    Parameters
    ----------
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.

    Returns
    -------
    infos: dict
        Dictionnaire contenant les infos du PDF.
    """
    doc = load_from_file(fp_pdf_in)  # poppler
    # métadonnées: https://cbrunet.net/python-poppler/usage.html#document-properties ;
    # infos() ne les renvoie pas toutes, et nous fixons ici l'ordre des champs
    infos = {
        "nb_pages": doc.pages,  # nombre de pages
        # métadonnées PDF
        "creatortool": doc.creator,
        "producer": doc.producer,
        # les datetime de poppler sont "timezone naive", donc il faut attacher
        # le fuseau horaire de Paris (sans ajuster l'heure)
        "createdate": (
            doc.creation_date.replace(tzinfo=TZ_FRA)
            if doc.creation_date is not None
            else None
        ),
        "modifydate": (
            doc.modification_date.replace(tzinfo=TZ_FRA)
            if doc.modification_date is not None
            else None
        ),
    }
    return infos


def get_pdf_info_pikepdf(fp_pdf_in: Path, verbose=True) -> dict:
    """Renvoie les infos du PDF en utilisant pikepdf.

    Les infos incluent un sous-ensemble des métadonnées du PDF.

    Parameters
    ----------
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.
    verbose: boolean, defaults to True
        Si True, des warnings sont émis à chaque anomalie constatée dans les
        métadonnées du PDF.

    Returns
    -------
    infos: dict
        Dictionnaire contenant les infos du PDF.
    """
    with pikepdf.open(fp_pdf_in) as f_pdf:
        with f_pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            # lire les métadonnées stockées en XMP ("nouveau" format)
            meta_base = {k: v for k, v in meta.items()}
            if verbose:
                try:
                    logging.info(
                        f"{fp_pdf_in.name}: métadonnées XMP brutes: {f_pdf.Root.Metadata.read_bytes().decode()}"
                    )
                except AttributeError:
                    logging.warning(
                        f"{fp_pdf_in.name}: absence de métadonnées XMP brutes"
                    )
                logging.info(f"{fp_pdf_in.name}: métadonnées XMP: {meta_base}")
            # lire les métadonnées stockées dans docinfo (ancien format)
            meta.load_from_docinfo(f_pdf.docinfo)
            meta_doci = {k: v for k, v in meta.items()}
            if verbose:
                logging.info(f"{fp_pdf_in.name}: docinfo: {repr(f_pdf.docinfo)}")
                logging.info(f"{fp_pdf_in.name}: métadonnées XMP+docinfo: {meta_doci}")
            # comparaison des métadonnées: XMP seul vs XMP mis à jour avec docinfo
            base_keys = set(meta_base.keys())
            doci_keys = set(meta_doci.keys())
            # vérifier que la lecture de docinfo n'a pas supprimé de champ aux métadonnées XMP
            assert (base_keys - doci_keys) == set()
            # vérifier que les champs chargés depuis docinfo  n'ont modifié aucune valeur de champ XMP
            # (pas de modification / écrasement, condition plus forte que supra)
            for key, value in meta_base.items():
                if key.endswith("Date"):
                    # traitement spécifique pour les dates: gestion de différents formats + tolérance de 2h pour les timezones
                    base_v = datetime.fromisoformat(
                        value.replace("Z", "+00:00")
                    ).astimezone(tz=TZ_FRA)
                    doci_v = datetime.fromisoformat(
                        meta_doci[key].replace("Z", "+00:00")
                    ).astimezone(tz=TZ_FRA)
                    # base_eq_doci = abs(base_v - doci_v) <= timedelta(hours=1)  # si besoin de permissivité
                    base_eq_doci = doci_v == base_v
                else:
                    # comparaison par défaut: égalité stricte
                    base_v = value
                    doci_v = meta_doci[key]
                    base_eq_doci = doci_v == base_v
                if not base_eq_doci:
                    logging.warning(
                        f"{fp_pdf_in}: metadata: {key}={base_v} (xmp) vs {doci_v} (docinfo)"
                    )

    logging.info(f"{fp_pdf_in}: pike:finalmetadata: {meta}")
    # sélection des champs et fixation de leur ordre
    infos = {
        "nb_pages": len(f_pdf.pages),  # nombre de pages
        # métadonnées PDF
        "creatortool": meta.get("xmp:CreatorTool", ""),  # string
        "producer": meta.get("pdf:Producer", ""),  # string
        "createdate": meta.get("xmp:CreateDate", None),  # date
        "modifydate": meta.get("xmp:ModifyDate", None),  # date
    }
    # analyse des dates
    if infos["createdate"] is not None:
        infos["createdate"] = datetime.fromisoformat(infos["createdate"]).astimezone(
            tz=TZ_FRA
        )
    if infos["modifydate"] is not None:
        infos["modifydate"] = datetime.fromisoformat(infos["modifydate"]).astimezone(
            tz=TZ_FRA
        )
    # WIP regarder si des champs sont toujours/souvent/jamais renseignés
    if meta.get("dc:format", None) is not None:
        assert meta.get("dc:format", None) == "application/pdf"
    #
    return infos


def get_pdf_info(fp_pdf: Path) -> Dict[str, str | int]:
    """Extraire les informations (dont métadonnées) d'un fichier PDF.

    Utilise actuellement pikepdf et poppler en parallèle, pour vérifier
    la cohérence et la complétude. À terme, devrait n'utiliser que pikepdf.

    Parameters
    ----------
    fp_pdf: Path
        Chemin du fichier PDF à traiter.

    Returns
    -------
    pdf_info: dict
        Informations (dont métadonnées) du fichier PDF d'entrée
    """
    logging.info(f"Ouverture du fichier {fp_pdf}")
    pdf_info = {
        # métadonnées du fichier lui-même
        "filename": fp_pdf.name,  # nom du fichier
        "fullpath": fp_pdf.resolve(),  # chemin complet
        "filesize": fp_pdf.stat().st_size,  # taille du fichier
        # TODO hashlib.sha1 ?
    }
    # lire les métadonnées du PDF, avec poppler et pikepdf
    meta_poppler = get_pdf_info_poppler(fp_pdf)
    meta_pike = get_pdf_info_pikepdf(fp_pdf)
    # comparer les infos extraites par poppler et pikepdf
    try:
        for k, v_popp in meta_poppler.items():
            v_pike = meta_pike[k]
            if k.endswith("date"):
                # les dates ne sont pas lues et reconstruites de la même façon (timezone)
                assert (v_popp is None) or (abs(v_popp - v_pike) <= timedelta(hours=2))
            elif k == "producer":
                # les caractères mal encodés ne sont pas nettoyés de la même façon
                assert v_popp.replace("\x92", "™") == v_pike
            else:
                assert v_popp == v_pike
    except AssertionError:
        logging.error("Différence trop importante entre poppler et pikepdf")
        logging.warning(f"meta_poppler: {meta_poppler}")
        logging.warning(f"meta_pike: {meta_pike}")
    # ajouter les métadonnées PDF à celles du fichier
    pdf_info.update(meta_pike)
    return pdf_info


def index_folder(in_dir: Path, recursive: bool = True) -> List[Dict[str, str | int]]:
    """Indexer un dossier: extraire les infos des fichiers PDF qu'il contient.

    Parameters
    ----------
    in_dir: Path
        Dossier à traiter, contenant des PDF.
    recursive: bool, defaults to True
        Si True, parcourt récursivement le dossier in_dir.

    Returns
    -------
    pdf_infos: List[Dict[str, str | int]]
        Informations (dont métadonnées) extraites des fichiers PDF.
    """
    logging.info(f"Ouverture du dossier {in_dir}")
    # lister les PDFs dans le dossier à traiter
    if recursive:
        pdfs_in = sorted(in_dir.rglob("*.[Pp][Dd][Ff]"))
    else:
        pdfs_in = sorted(in_dir.glob("*.[Pp][Dd][Ff]"))
    if not pdfs_in:
        logging.warning(f"Aucun PDF trouvé dans {in_dir}")

    #
    pdf_infos = []
    for fp_pdf in pdfs_in:
        # extraire le texte si nécessaire, corriger et convertir le PDF d'origine en PDF/A-2b
        pdf_info = get_pdf_info(fp_pdf)
        # métadonnées des fichiers PDF en entrée et sortie
        pdf_infos.append(pdf_info)
    return pdf_infos


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/extract_metadata_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )
    logging.captureWarnings(True)

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_dir", help="Nom du lot dans data/raw, ou chemin vers le dossier"
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le dossier de sortie pour le fichier CSV contenant les métadonnées",
    )
    parser.add_argument(
        "--nonrecursive",
        action="store_true",
        help="Limite la recherche de fichiers PDF au dossier in_dir, sans descendre dans ses éventuels sous-dossiers",
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
        help="Ajoute les métadonnées au fichier out_file s'il existe",
    )
    args = parser.parse_args()

    # entrée: lot connu ou chemin vers un dossier
    if args.in_dir in RAW_BATCHES:
        # nom de lot connu
        in_dir = RAW_BATCHES[args.in_dir].resolve()
        if not in_dir.is_dir():
            raise ValueError(f"Le lot {args.in_dir} n'est pas à l'emplacement {in_dir}")
    else:
        # chemin vers un dossier (nouveau lot?)
        in_dir = Path(args.in_dir).resolve()
        if not in_dir.is_dir():
            raise ValueError(f"Le dossier {in_dir} n'existe pas")

    # sortie: CSV de métadonnées
    # on crée le dossier parent (récursivement) si besoin
    out_file = Path(args.out_file).resolve()
    if out_file.is_file():
        if not args.redo and not args.append:
            # erreur si le fichier CSV existe déjà mais ni redo, ni append
            raise ValueError(
                f"Le fichier de sortie {out_file} existe déjà. Pour l'écraser, ajoutez --redo ; pour l'augmenter, ajoutez --append."
            )
    else:
        # si out_file n'existe pas, créer son dossier parent si besoin
        out_dir = out_file.parent
        logging.info(
            f"Dossier de sortie: {out_dir} {'existe déjà' if out_dir.is_dir() else 'doit être créé'}."
        )
        out_dir.mkdir(exist_ok=True)

    # indexer le dossier
    recursive = not args.nonrecursive
    pdf_infos = index_folder(in_dir, recursive=recursive)

    # sauvegarder les infos extraites dans un fichier CSV
    if pdf_infos:
        df_metas_new = pd.DataFrame(pdf_infos)
        if args.append and out_file.is_file():
            # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
            df_metas_old = pd.read_csv(out_file)
            df_metas = pd.concat([df_metas_old, df_metas_new])
        else:
            # sinon utiliser les seules nouvelles entrées
            df_metas = df_metas_new
        df_metas.to_csv(out_file, index=False)

    # bonus: afficher des indicateurs
    print(
        df_metas_new[["creatortool", "producer"]]
        .value_counts(dropna=False)
        .to_frame("counts")
        .reset_index()
    )
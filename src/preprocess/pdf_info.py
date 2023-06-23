"""Extraire les métadonnées des fichiers PDF.

Ce module utilise pikepdf.
"""

from datetime import datetime
from dateutil import tz
import logging
from pathlib import Path
from typing import Dict

import pikepdf

from src.utils.file_utils import get_file_digest


# fuseau horaire de Paris
TZ_FRA = tz.gettz("Europe/Paris")


def get_pdf_info_pikepdf(fp_pdf_in: Path, verbose: bool = False) -> dict:
    """Renvoie les infos du PDF en utilisant pikepdf.

    Les infos incluent un sous-ensemble des métadonnées du PDF.

    Parameters
    ----------
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.
    verbose: boolean, defaults to False
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
            # NB: load_from_docinfo() peut lever un UserWarning, qui est alors inclus dans le log de ce script
            # <https://github.com/pikepdf/pikepdf/blob/94c50cd408b214f7569a717c3409e36b7a996769/src/pikepdf/models/metadata.py#L438>
            # ex: "UserWarning: The metadata field /MetadataDate with value 'pikepdf.String("D:20230117110535+01'00'")' has no XMP equivalent, so it was discarded"
            meta_doci = {k: v for k, v in meta.items()}
            if verbose:
                logging.info(f"{fp_pdf_in.name}: docinfo: {repr(f_pdf.docinfo)}")
                logging.info(f"{fp_pdf_in.name}: métadonnées XMP+docinfo: {meta_doci}")
            # comparaison des métadonnées: XMP seul vs XMP mis à jour avec docinfo
            base_keys = set(meta_base.keys())
            doci_keys = set(meta_doci.keys())
            # vérifier que la lecture de docinfo n'a pas supprimé de champ aux métadonnées XMP
            assert (base_keys - doci_keys) == set()
            # vérifier que les champs chargés depuis docinfo n'ont modifié aucune valeur de champ XMP
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
    if verbose:
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


def get_pdf_info(
    fp_pdf: Path, digest: str = "blake2b", verbose: bool = False
) -> Dict[str, str | int]:
    """Extraire les informations (dont métadonnées) d'un fichier PDF.

    Utilise actuellement pikepdf.

    Parameters
    ----------
    fp_pdf : Path
        Chemin du fichier PDF à traiter.
    digest : str
        Algorithme de hachage à utiliser
        <https://docs.python.org/3/library/hashlib.html#hash-algorithms> .
    verbose: boolean, defaults to False
        Si True, des warnings sont émis à chaque anomalie constatée dans les
        métadonnées du PDF.

    Returns
    -------
    pdf_info : dict
        Informations (dont métadonnées) du fichier PDF d'entrée
    """
    logging.info(f"Ouverture du fichier {fp_pdf}")
    pdf_info = {
        # métadonnées du fichier lui-même
        "pdf": fp_pdf.name,  # nom du fichier
        "fullpath": fp_pdf.resolve(),  # chemin complet
        "filesize": fp_pdf.stat().st_size,  # taille du fichier
        digest: get_file_digest(fp_pdf, digest=digest),  # hash du fichier
    }
    # lire les métadonnées du PDF avec pikepdf
    meta_pike = get_pdf_info_pikepdf(fp_pdf, verbose=verbose)
    # ajouter les métadonnées PDF à celles du fichier
    pdf_info.update(meta_pike)
    return pdf_info

"""Traiter les métadonnées des fichiers PDF.

Les traitements permettent de:
* détecter les fichiers doublons,
* déterminer si le PDF est du texte ou image,
* déterminer si le PDF contient des tampons de télétransmission en haut des pages,
* déterminer si le PDF contient une dernière page qui est l'accusé de réception de la télétransmission.

La liste des tiers de transmission agréés pour @ctes est sur
<https://www.collectivites-locales.gouv.fr/sites/default/files/migration/2019_09_13_liste_operateurs_transmission_0.pdf> .
"""

# FIXME ? nouvelle colonne "has_bad_ocr" pour les PDF avec une mauvaise OCR, eg. "Image Capture Plus"


import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import List

import pandas as pd


def _guess_duplicates(
    df: pd.DataFrame, subset: List[str], col_res: str
) -> pd.DataFrame:
    """Détecte les doublons dans un DataFrame.

    Une colonne est ajoutée au DataFrame, qui marque les doublons.

    Les groupes de doublons, plus la première occurrence de la valeur doublonnée,
    sont écrits dans le fichier de log.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame à dédoublonner
    subset: List[str]
        Sous-ensemble des colonnes à considérer pour détecter les doublons
    col_res: str
        Nom de la colonne résultat

    Returns
    -------
    df_dup: pd.DataFrame
        DataFrame augmenté d'une colonne identifiant les doublons.
    """
    # détecter les doublons hormis la 1re occurrence ; les valeurs NA sont tolérées
    # sauf quand tout le subset est NA
    s_dups = df.duplicated(subset=subset, keep="first") & ~df[subset].isnull().all(
        axis="columns"
    )
    df_dup = df.assign(col_res=s_dups)
    # s'il y a des doublons, écrire dans le log les doublons et la 1re occurrence
    nb_dups = s_dups.sum()
    if nb_dups:
        logging.warning(f"{nb_dups} fichiers doublons sur les colonnes {subset}")
        # récupérer les groupes de doublons, incluant la première occurrence
        s_dups_all = df.duplicated(subset=subset, keep=False) & ~df[
            subset
        ].isnull().all(axis="columns")
        logging.warning(f"WIP: {s_dups_all.sum()}")
        for k, grp in df[s_dups_all].groupby(subset, sort=False, dropna=False):
            logging.warning(f"Doublons: {grp['filename'].values}")
    return df_dup


def guess_duplicates_meta(df_meta: pd.DataFrame):
    """Détermine si les fichiers PDF sont des doublons à partir de leurs métadonnées.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des fichiers PDF

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées des fichiers PDF, avec des colonnes booléennes "dup_*" indiquant les fichiers doublons.
    """
    # détection stricte: doublons sur toutes les infos (sauf "filename" et "fullpath")
    # (trop de faux négatifs?)
    cols_dups_allinfo = [
        # infos fichier
        "filesize",
        "nb_pages",
        # métadonnées pdf
        "creatortool",
        "producer",
        "createdate",
        "modifydate",
    ]
    df_mmod = _guess_duplicates(df_meta, cols_dups_allinfo, "dup_allinfo")

    # détection lâche: doublons sur la date de création
    # (trop de faux positifs)
    cols_dups_createdate = ["createdate"]
    #
    df_mmod = _guess_duplicates(df_mmod, cols_dups_createdate, "dup_createdate")

    return df_mmod


def guess_tampon_transmission(df_meta: pd.DataFrame) -> pd.DataFrame:
    """Détermine si le haut des pages contient des tampons de transmission électronique.

    Permet de traiter certains arrêtés recueillis après leur télétransmission.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des fichiers PDF

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées enrichies d'une nouvelle colonne "guess_tampon"
    """
    has_stamp = ~(
        # faux positif: MS 365 + iText utilisé pour ajouter la signature
        df_meta["producer"]
        == "Microsoft® Word pour Microsoft 365; modified using iText® 5.5.9 ©2000-2015 iText Group NV (AGPL-version)"
    ) & (
        df_meta["producer"].str.endswith(
            # tampon en haut à droite: tiers de télétransmission S2LOW (2019-06-14 - ..) et Berger Levrault (2021-02-08)
            "; modified using iText® 7.1.5 ©2000-2019 iText Group NV (AGPL-version)"
        )
        | df_meta["producer"].str.endswith(
            # tampon en haut à droite: tiers de télétransmission S2LOW (.. - 2019-02-11)
            "; modified using iText® 5.5.12 ©2000-2017 iText Group NV (AGPL-version)"
        )
        | df_meta["producer"].str.endswith(
            # tampon en bas à gauche (quel tiers?): "; modified using iText® 5.5.9 ©2000-2015 iText Group NV (AGPL-version)" (sans MS 365)
            "; modified using iText® 5.5.9 ©2000-2015 iText Group NV (AGPL-version)"
        )
    )
    #
    df_mmod = df_meta.assign(guess_tampon=has_stamp)
    return df_mmod


def guess_dernpage_transmission(df_meta: pd.DataFrame) -> pd.DataFrame:
    """Détermine si la dernière page est un accusé de réception de télétransmission.

    Permet de traiter certains arrêtés recueillis après leur télétransmission.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des fichiers PDF

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées enrichies d'une nouvelle colonne "guess_dernpage"
    """
    has_dernpage = (
        # @ctes (toute la période?)
        df_meta["producer"]
        == "iText 2.1.7 by 1T3XT"
    )
    df_mmod = df_meta.assign(guess_dernpage=has_dernpage)
    return df_mmod


def guess_badocr(df_meta: pd.DataFrame) -> pd.DataFrame:
    """Détermine si le fichier contient une couche OCR de piètre qualité.

    Arrive quand le champ "creatortool" vaut "Image Capture Plus".

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des fichiers PDF

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées enrichies d'une nouvelle colonne "guess_badocr"
    """
    has_badocr = (
        # "Image Capture Plus"
        df_meta["creatortool"]
        == "Image Capture Plus"
    )
    df_mmod = df_meta.assign(guess_badocr=has_badocr)
    return df_mmod


def guess_pdftext(df_meta: pd.DataFrame) -> pd.DataFrame:
    """Détermine si le fichier est un PDF texte (ou "numérique natif").

    Parameters
    ----------
    df_meta: pd.DataFrame
        Métadonnées des fichiers PDF

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées enrichies d'une nouvelle colonne "guess_pdftext"
    """
    is_pdftext = (
        # "Microsoft® Word 2010", "Microsoft® Word 2013", "Microsoft® Word pour Microsoft 365"
        df_meta["creatortool"].str.startswith("Microsoft® Word")
        # "Writer" (OpenOffice, LibreOffice)
        | (df_meta["creatortool"] == "Writer")
    )
    df_mmod = df_meta.assign(guess_pdftext=is_pdftext)
    return df_mmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[1] / "logs"
    logging.basicConfig(
        filename=(f"{dir_log}/process_metadata_{datetime.now().isoformat()}.log"),
        encoding="utf-8",
        level=logging.DEBUG,
    )
    logging.captureWarnings(True)

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées, à enrichir",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées, enrichi",
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

    # entrée: CSV de métadonnées à enrichir
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de métadonnées enrichi
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

    # ouvrir le fichier d'entrée
    df_metas = pd.read_csv(in_file)
    # détecter les doublons
    df_mmod = guess_duplicates_meta(df_metas)
    df_mmod = guess_tampon_transmission(df_mmod)
    df_mmod = guess_dernpage_transmission(df_mmod)
    df_mmod = guess_pdftext(df_mmod)
    df_mmod = guess_badocr(df_mmod)

    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file)
        df_proc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_mmod
    df_proc.to_csv(out_file, index=False)

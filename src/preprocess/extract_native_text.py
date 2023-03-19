"""Extraire le texte natif des fichiers PDF.

Le texte natif est extrait avec le wrapper python de l'utilitaire "pdftotext" de poppler.

Le texte natif représente:
* pour les PDF natifs ("PDF texte"), l'intégralité du texte ;
* pour les PDF non-natifs ("PDF image"), du texte extrait par OCR (de qualité variable)
ou des fragments de texte issus d'ajout d'objets natifs, eg. tampon, accusé de réception.

Le texte est normalisé en forme NFC: <https://docs.python.org/3/howto/unicode.html#comparing-strings>.
"""

# TODO layout sur 2 colonnes (ex: Peyrolles)
# TODO layout sur 1 colonne mais interprétée comme 2 colonnes par pdftotext (ex: "38, rue Puget Gardanne_interdiction d_habiter.pdf", "6, rue Aristide Briand.pdf")
# TODO détecter les première et dernière page: de "nous" + vu, considérant etc jusqu'à la signature
# pour exclure les annexes (rappel des articles du code de la construction, rapport de BE), page de garde etc.
# => ajouter un mode "early_stopping", optionnel, à l'extraction de texte
# TODO si redo='ocr', ré-OCRisation des documents (mal) OCRisés (avec un warning.info)
# TODO ajuster le logging

# alternatives testées sur les PDF image OCRisés:
# * pdftotext (xpdf ou poppler?) mélange le texte (comparé au fichier "sidecar" de ocrmypdf)
# * pdf2txt (pdfminer) mélange le texte (idem)
# * pdfplumber introduit des espaces et lignes superflus

# pour les PDF texte:
# * pdftotext extrait très rapidement un texte très propre
# * pdfminer.six extrait moins rapidement un texte moins propre
# * pymupdf ?
# * python-poppler

import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import NamedTuple

import pandas as pd

# on peut commenter les alternatives non retenues
# from src.preprocess.extract_native_text_pdfminer import extract_native_text_pdfminer
from src.preprocess.extract_native_text_pdftotext import (
    extract_native_text_pdftotext,
)

#
from src.preprocess.process_metadata import DTYPE_META_PROC

# schéma des données en entrée

DTYPE_META_NTXT = DTYPE_META_PROC | {
    "retcode_txt": "Int64",  # FIXME Int16 ? (dtype à fixer ici, avant le dump)
    "fullpath_txt": "string",
}


# TODO après cette première passe d'extraction, ré-extraire les arrêtés de
# certaines communes qui ont des layouts plus compliqués (ex: Peyrolles)
# avec soit les LAParams par défaut, soit des LAParams personnalisés par
# commune (selon le nom de la commune extrait en première passe)


# TODO type hint pour la valeur de retour: str, Literal ou LiteralString? possibilités dépendent de la version de python
def extract_native_text(
    df_row: NamedTuple,
    fp_pdf_in: Path,
    fp_txt_out: Path,
) -> int:
    """Extrait le texte natif d'un PDF.

    Parameters
    ----------
    df_row: NamedTuple
        Métadonnées et informations sur le fichier PDF à traiter.
    fp_pdf_in: Path
        Chemin du fichier PDF à traiter.
    fp_txt_out: Path
        Chemin du fichier txt contenant le texte extrait.

    Returns
    -------
    returncode: int
        Code de retour de l'extraction: 0 si un fichier TXT a été produit, 1 sinon.
    """
    logging.info(f"Extraction du texte natif: {fp_pdf_in}")
    # définir les pages à traiter:
    # pour le moment, pour le texte natif, nous traitons toutes les pages
    # (même lorsque les métadonnées semblent indiquer que la dernière page
    # serait un accusé de réception de transmission à @ctes)
    page_beg = 1
    page_end = df_row.nb_pages
    # extraire le texte avec pdftotext
    # retcode = extract_native_text_pdfminer(
    retcode = extract_native_text_pdftotext(
        fp_pdf_in, fp_txt_out, page_beg=page_beg, page_end=page_end
    )
    if retcode == 0:
        logging.info(f"Texte natif présent: {fp_pdf_in}")
    else:
        logging.info(f"Texte natif absent: {fp_pdf_in}")
    return retcode


def process_files(
    df_meta: pd.DataFrame,
    out_dir_txt: Path,
    redo: bool = False,
) -> pd.DataFrame:
    """Traiter un ensemble de fichiers PDF: convertir les PDF en PDF/A et extraire le texte.

    Parameters
    ----------
    df_meta: pd.DataFrame
        Liste de fichiers PDF à traiter, avec leurs métadonnées.
    out_dir_txt: Path
        Dossier de sortie pour les fichiers texte.
    redo: bool, defaults to False
        Si True, réanalyse les fichiers déjà traités.

    Returns
    -------
    df_mmod: pd.DataFrame
        Métadonnées des fichiers d'entrée, chemins vers les fichiers TXT produits et codes
        de retour de l'extraction de texte natif.
    """
    retcodes = []
    fullpath_txt = []
    for df_row in df_meta.itertuples():
        # fichier d'origine
        fp_pdf_in = Path(df_row.fullpath)
        # fichier à produire
        fp_txt = out_dir_txt / (fp_pdf_in.stem + ".txt")
        # si les fichiers à produire existent déjà
        if fp_txt.is_file():
            if redo:
                # ré-exécution explicitement demandée: émettre une info et traiter le fichier
                logging.info(
                    f"Re-traitement de {fp_pdf_in}, le fichier de sortie {fp_txt} existants sera écrasé."
                )
            else:
                # pas de ré-exécution demandée: émettre un warning et passer au fichier suivant
                logging.info(
                    f"{fp_pdf_in} est ignoré car le fichier {fp_txt} existe déjà."
                )
                continue
        # traiter le fichier: extraire le texte natif
        retcode = extract_native_text(df_row, fp_pdf_in, fp_txt)
        if retcode == 1:
            # erreur à l'ouverture du fichier PDF: aucun fichier TXT ne peut être produit
            # ce code d'erreur est renvoyé lorsque le PDF ne contient pas de couche de texte (PDF non-natif "pur")
            raise ValueError(f"gne {fp_pdf_in}")
        elif retcode not in (0, 1):
            print(df_row)
            print(retcode)
            raise ValueError(f"extract_native_text: code de retour inattendu {retcode}")
        # stocker le chemin vers le fichier TXT produit
        retcodes.append(retcode)
        fullpath_txt.append(fp_txt)
    # FIXME plante si le script tourne de nouveau sans "redo" ou "append": l'assignation est alors de longueur inférieure à celle du DataFrame(?)
    df_mmod = df_meta.assign(
        retcode_txt=retcodes,
        fullpath_txt=fullpath_txt,
    )
    # forcer les types des nouvelles colonnes
    df_mmod = df_mmod.astype(dtype=DTYPE_META_NTXT)
    return df_mmod


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    # NB: ne pas mettre level=logging.DEBUG, sinon pdfminer.six:extract_text() s'exécute en mode DEBUG,
    # est très lent et génère un log énorme
    # <https://github.com/pdfminer/pdfminer.six/issues/608>
    logging.basicConfig(
        filename=f"{dir_log}/extract_native_text_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.INFO,
    )

    # arguments de la commande exécutable
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "in_file",
        help="Chemin vers le fichier CSV en entrée contenant les métadonnées enrichies",
    )
    parser.add_argument(
        "out_file",
        help="Chemin vers le fichier CSV en sortie contenant les métadonnées enrichies et les chemins vers les fichiers textes",
    )
    parser.add_argument(
        "out_dir",
        help="Chemin vers le dossier de sortie contenant les fichiers de texte extraits",
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

    # entrée: CSV de métadonnées enrichi
    in_file = Path(args.in_file).resolve()
    if not in_file.is_file():
        raise ValueError(f"Le fichier en entrée {in_file} n'existe pas.")

    # sortie: CSV de métadonnées enrichi + infos fichiers produits
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

    # sortie: dossier pour TXT natifs
    out_dir = Path(args.out_dir).resolve()
    out_txt_dir = out_dir / "txt_native"
    # on le crée si besoin
    out_txt_dir.mkdir(exist_ok=True)

    # ouvrir le fichier d'entrée
    logging.info(f"Ouverture du fichier CSV {in_file}")
    df_metas = pd.read_csv(in_file, dtype=DTYPE_META_PROC)
    # traiter les fichiers
    df_mmod = process_files(df_metas, out_txt_dir, redo=args.redo)
    # sauvegarder les infos extraites dans un fichier CSV
    if args.append and out_file.is_file():
        # si 'append', charger le fichier existant et lui ajouter les nouvelles entrées
        df_mmod_old = pd.read_csv(out_file, dtype=DTYPE_META_NTXT)
        df_proc = pd.concat([df_mmod_old, df_mmod])
    else:
        # sinon utiliser les seules nouvelles entrées
        df_proc = df_mmod
    df_proc.to_csv(out_file, index=False)

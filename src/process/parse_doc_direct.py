"""Analyse un arrêté et en extrait les données.

"""

import logging
from pathlib import Path
from typing import Dict, List

from src.domain_knowledge.actes import P_ACCUSE
from src.domain_knowledge.adresse import (
    create_adresse_normalisee,
    process_adresse_brute,
)
from src.domain_knowledge.cadastre import get_parcelle
from src.domain_knowledge.codes_geo import get_codeinsee, get_codepostal
from src.domain_knowledge.logement import get_adr_doc
from src.process.extract_data import determine_commune
from src.process.parse_doc import parse_arrete_pages
from src.utils.text_utils import normalize_string
from src.utils.txt_format import load_pages_text


def extract_adresses_commune(
    fn_pdf: str, pg_txt_body: str, commune_maire: str
) -> List[Dict]:
    """Extraire les adresses visées par l'arrêté, et la commune.

    Parameters
    ----------
    fn_pdf: string
        Nom du fichier PDF de l'arrêté (pour les messages de logs: warnings et erreurs)
    pg_txt_body: string
        Corps de texte de la page
    commune_maire: string
        Mention de la commune extraite de l'autorité prenant l'arrêté,
        ou des

    Returns
    -------
    adresses: list(dict)
        Adresses visées par l'arrêté
    """
    adresses_brutes = get_adr_doc(pg_txt_body)
    if not adresses_brutes:
        return [], commune_maire
    # prendre la 1re zone d'adresses reconnue dans le texte (heuristique)
    adresse_brute = adresses_brutes[0]
    # lui appliquer un 1er niveau de normalisation: remplacer les "\n" par " " etc.
    # TODO améliorer les résultats par une collecte plus exhaustive (qui nécessiterait le dédoublonnage) ou une meilleure heuristique ?
    adresse_brute = normalize_string(adresse_brute)
    # extraire la ou les adresses de cette zone
    adresses = [
        ({"adr_ad_brute": adresse_brute} | x)
        for x in process_adresse_brute(adresse_brute)
    ]
    if not adresses:
        logging.error(
            f"{fn_pdf}: aucune adresse extraite de la zone d'adresse(s): {adresse_brute}"
        )

    # si besoin d'une alternative: déterminer commune, code INSEE et code postal pour adresses[0] et propager les valeurs aux autres adresses
    for adresse in adresses:
        # - déterminer la commune de l'adresse visée par l'arrêté en reconciliant la commune mentionnée
        # dans cette adresse avec celle extraite des mentions de l'autorité ou du template
        adresse["adr_commune"] = determine_commune(
            adresse["adr_commune"], commune_maire
        )
        if not adresse["adr_commune"]:
            logging.warning(f"{fn_pdf}: impossible de déterminer la commune")
        # - déterminer le code INSEE de la commune
        # FIXME communes hors Métropole: le filtrage sera-t-il fait en amont, lors de l'extraction depuis actes? sinon AssertionError ici
        try:
            adresse["adr_codeinsee"] = get_codeinsee(
                adresse["adr_commune"], adresse["adr_cpostal"]
            )
        except AssertionError:
            print(
                f"{fn_pdf}: get_codeinsee(): {adresse['adr_commune']}, {adresse['adr_cpostal']}"
            )
            raise
        if not adresse["adr_codeinsee"]:
            logging.warning(f"{fn_pdf}: impossible de déterminer le code INSEE")
        # - si l'adresse ne contenait pas de code postal, essayer de déterminer le code postal
        # à partir du code INSEE de la commune (ne fonctionne pas pour Aix-en-Provence)
        if not adresse["adr_cpostal"]:
            adresse["adr_cpostal"] = get_codepostal(
                adresse["adr_commune"], adresse["adr_codeinsee"]
            )
            if not adresse["adr_cpostal"]:
                logging.warning(
                    f"{fn_pdf}: Pas de code postal: adr_brute={adresse['adr_ad_brute']}, commune={adresse['adr_commune']}, code_insee={adresse['adr_codeinsee']}, get_codepostal={adresse['adr_cpostal']}"
                )
        # - créer une adresse normalisée ; la cohérence des champs est vérifiée
        adresse["adr_adresse"] = create_adresse_normalisee(adresse)

    return adresses


def parse_arrete(fp_pdf_in: Path, fp_txt_in: Path) -> dict:
    """Analyse un arrêté et extrait les données qu'il contient.

    L'arrêté est découpé en paragraphes puis les données sont
    extraites.

    Parameters
    ----------
    fp_pdf_in: Path
        Fichier PDF source (temporairement?)
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    doc_data: dict
        Données extraites du document.
    """
    pages = load_pages_text(fp_txt_in)
    if not any(pages):
        logging.warning(f"{fp_txt_in}: aucune page de texte")
        return {}

    # filtrer les pages qui sont à sortir du traitement:
    # - la ou les éventuelles pages d'accusé de réception d'actes
    pages_ar = [i for i, x in enumerate(pages, start=1) if P_ACCUSE.match(x)]
    if pages_ar:
        logging.warning(
            f"{fp_txt_in}: {len(pages_ar)} page(s) d'accusé de réception actes: {pages_ar} (sur {len(pages)})"
        )
    # - la ou les éventuelles pages d'annexes ? (TODO)
    skip_pages = pages_ar
    # remplacer les pages filtrées par une chaîne vide
    filt_pages = [
        (x if i not in skip_pages else "") for i, x in enumerate(pages, start=1)
    ]

    # analyser la structure des pages
    fn_pdf = fp_pdf_in.name  # FIXME temporaire?
    doc_content = parse_arrete_pages(fn_pdf, filt_pages)

    # extraire les données
    doc_data = {}

    # - au préalable, rassembler toutes les données en ajoutant le numéro de page (FIXME)
    pages_body = [pg_cont["body"] for pg_cont in doc_content]
    # pages_cont = [pg_cont["content"] for pg_cont in doc_content]  # future
    pages_cont = []
    for pg_num, pg_cont in enumerate(doc_content, start=1):
        # pg_template = page_cont["template"]
        # pg_content = page_cont["content"]  # future
        # FIXME ajouter "page_num" en amont, dans parse_arrete_pages()
        pages_cont.extend([({"page_num": pg_num} | x) for x in pg_cont["content"]])

    # extraire les champs un par un:
    # - commune extraite des mentions de l'autorité prenant l'arrêté, ou du template du document
    adrs_commune_maire = [x for x in pages_cont if x["span_typ"] == "adr_ville"]
    # - prendre arbitrairement la 1re mention et la nettoyer a minima
    # TODO regarder les erreurs et vérifier si un autre choix donnerait de meilleurs résultats
    if not adrs_commune_maire:
        adr_commune_maire = None
    else:
        adr_commune_maire = normalize_string(adrs_commune_maire[0]["span_txt"])
    print(f"commune: {adr_commune_maire}")
    #
    adrs_doc = []  # adresses brutes
    pars_doc = []
    for pg_txt_body in pages_body:
        if pg_txt_body:
            # extraire la ou les adresse(s) visée(s) par l'arrêté détectées sur cette page
            if not adrs_doc:
                # pour le moment, on se contente de la première page contenant au moins une zone d'adresse,
                # et sur cette page, de la première zone d'adresse trouvée ;
                # une zone peut contenir une ou plusieurs adresses obtenues par "dépliage" (ex: 12 - 14 rue X)
                # TODO examiner les erreurs et déterminer si une autre stratégie donnerait de meilleurs résultats
                adresses = extract_adresses_commune(
                    fn_pdf, pg_txt_body, adr_commune_maire
                )
                adrs_doc.extend(adresses)
            # parcelle(s) visée(s) par l'arrêté
            pars_doc.extend([get_parcelle(pg_txt_body)])  # FIXME get_parcelle:list()
    print(f"adrs_doc: {adrs_doc}")
    print(f"pars_doc: {pars_doc}")
    # RESUME HERE
    return doc_data

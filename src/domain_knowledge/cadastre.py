"""Reconnaissance et analyse de références cadastrales.

"""

# TODO récupérer dans data/externe la liste des codes INSEE des quartiers (Marseille, voire Aix et Martigues?) pour vérif et complétion
# TODO récupérer dans data/externe la liste des codes DGFIP des communes (et arrondissements de Marseille), eg. <https://deliberations.ampmetropole.fr/documents/metropole/deliberations/2018/10/18/RAPPORTDELACOMMISSION/C06HH.pdf>

# TODO améliorer la couverture:
# data_enr_struct.csv: 827 arrêtés sans référence cadastrale sur 2452 (33.73%) (2023-03-06)
# (dont 285 avec un code insee, dont 3 avec un 13055)
#

# FIXME variante "immeuble sis 44 rue Barsotti – 13003 MARSEILLE 3EME, parcelle cadastrée\nsection 813H, numéro 86"
# FIXME faux positifs
# - "parcelle *du 10* rue du ..."
# FIXME ? identifiant de parcelle mais pas concerné par le péril:
# - "limite séparative entre les parcelles 213886 E0047 et 213886 E0089" (105 chemin des Jonquilles)
# FIXME? référence de parcelle mal formée:
# csvcut -c arr_pdf,arr_nom_arr,par_ref_cad data/interim/arretes_peril_compil_data_enr_struct.csv |grep "[^,],$" |less
# - "21388O0142" => "213888O0142" ("7, bld lacordaire.pdf")
# - "2015899 H0064" => "215899 H0064" ("91 bld Oddo 13015 - Péril simple 06.03.20.pdf")
# - "23813 E0176" => "203813 E0176" ("Arrêté de péril imminent - 39, rue François Barbini - 13003.pdf")
# - "33202 B0091" => (?) "202808 B0233" (?) ("Mainlevée 34, rue Bon Pasteur 13002.pdf")
# - "33202 B0130 ET 33202 B0131" => (?) ("mainlevée 22 26 rue de la Joliette.pdf")
# - "34508 L0063" => (?) ("mainlevée 27, rue du Commandeur 13015.pdf")
# - "34503 D0031" => (?) ("mainlevée 270 avenue Roger Salengro.pdf")


# FIXME trouver un moyen de forcer le strict parallélisme avec les expressions sans groupes nommés

import logging
import re
from typing import List

import pandas as pd
from src.utils.str_date import RE_DATE

from src.utils.text_utils import RE_NO as RE_NO_BASE, normalize_string

RE_NO = rf"(?:{RE_NO_BASE}|num[ée]ro(?:s)?)"

# Marseille: préfixe = arrondissement + quartier
RE_CAD_ARRT = (
    r"(2[01]\d)"  # 3 derniers chiffres du code INSEE de l'arrondissement: 2O1 à 216
)
RE_CAD_QUAR = r"(\d{3})"  # code quartier

# toutes communes: section et numéro
RE_CAD_SEC = r"[A-Z]{1,2}"
RE_CAD_NUM = r"\d{1,4}"

# expression complète
# - Marseille
RE_CAD_MARSEILLE = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    # code arrondissement et code quartier, ou juste code quartier
    + r"(?:"
    + r"(?:131)?"  # optionnel: forme longue commençant par le code DGFIP (131201 à 131216 pour Marseille)
    + rf"(?:{RE_CAD_ARRT})"  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"\s*)?"
    # TODO accepter le nom du quartier ici, ou en fin de référence, puis le mapper vers un code (req: référentiel des codes quartiers INSEE)
    + rf"(?<![\s/-]\d){RE_CAD_QUAR}"  # code quartier  # 2023-04-28: negative lookbehind pour éviter les matches involontaires (date, liasse, article de loi etc.)
    + r"\s*"
    # negative lookahead: ne pas capturer "du", "au", "et" (désactiver ignorecase au moins pour ce bout de regex?)
    + r"(?!"
    + rf"(?:du\s+{RE_DATE})"  #  éviter match eg. "loi n°65-557 du 10 juillet 1965", "arrêté n° ... du 3 mars 2020" etc
    + rf"|(?:au\s+\d{{1,4}})"  # éviter match eg. "[parcelle n°123 au 6 rue Xxx]" etc
    # TODO ne pas capturer "et"
    + r")"
    # FIXME ne pas capturer les "P" qui deviennent des "0P..." (liasse encore?)
    # RESUME HERE
    + RE_CAD_SEC
    + rf"(?:\s*(?:(?:,\s*)?{RE_NO}\s*)?)?"
    + RE_CAD_NUM
    + r")"
)
P_CAD_MARSEILLE = re.compile(RE_CAD_MARSEILLE, re.MULTILINE | re.IGNORECASE)
# idem, avec named groups
RE_CAD_MARSEILLE_NG = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + r"(?:"
    + r"(?:131)?"  # préfixe éventuel, si la forme utilisée commence par le code DGFIP: 131201 à 1312016 pour les arrondissements de Marseille
    + rf"(?P<arrt>{RE_CAD_ARRT})"  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"\s*)?"
    # TODO accepter le nom du quartier ici, ou en fin de référence, puis le mapper vers un code (req: référentiel des codes quartiers INSEE)
    + rf"(?<![\s/-]\d)(?P<quar>{RE_CAD_QUAR})"  # code quartier  # 2023-04-28: negative lookbehind pour éviter les matches involontaires (date, liasse, article de loi etc.)
    + r"\s*"
    # negative lookahead: ne pas capturer "du", "au", "et" (désactiver ignorecase au moins pour ce bout de regex?)
    + r"(?!"
    + rf"(?:du\s+{RE_DATE})"  #  éviter match eg. "loi n°65-557 du 10 juillet 1965", "arrêté n° ... du 3 mars 2020" etc
    + rf"|(?:au\s+\d{{1,4}})"  # éviter match eg. "[parcelle n°123 au 6 rue Xxx]" etc
    # TODO ne pas capturer "et"
    + r")"
    # FIXME ne pas capturer les "P" qui deviennent des "0P..." (liasse encore?)
    # RESUME HERE
    + rf"(?P<sec>{RE_CAD_SEC})"
    + rf"(?:\s*(?:(?:,\s*)?{RE_NO}\s*)?)?"
    + rf"(?P<num>{RE_CAD_NUM})"
    + r")"
)
P_CAD_MARSEILLE_NG = re.compile(RE_CAD_MARSEILLE_NG, re.MULTILINE | re.IGNORECASE)


# récupérer les références de parcelles sans contexte gauche, à Marseille
# augmente la couverture, avec un risque faible de faux positif grâce au code insee et au code quartier
# TODO gérer les références avec préfixe factorisé, ex: "207835 E0004 / E0216"
# TODO références mal formées? "33202 B0130 ET 33202 B0131"
RE_PARCELLE_MARSEILLE_NOCONTEXT = (
    r"(?P<cadastre_id>"  # named group pour la ou les références cadastrales
    + RE_CAD_MARSEILLE  # 1re référence cadastrale
    + r"("  # 1 ou plusieurs références supplémentaires
    + r"(?:,|\s+et|\s+[&]|\s+[-])\s+"
    + RE_CAD_MARSEILLE
    + r")*"  # fin 1 ou plusieurs références supplémentaires
    + r")"  # fin named group
)
P_PARCELLE_MARSEILLE_NOCONTEXT = re.compile(
    RE_PARCELLE_MARSEILLE_NOCONTEXT, re.IGNORECASE | re.MULTILINE
)


# - autres communes
RE_CAD_AUTRES = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + RE_CAD_SEC  # section cadastrale
    + r"(?:"  # séparateur éventuel
    + r"(?:-)"  # ex: "[...] cadastrée BK-80 sise [...]"
    + rf"|(?:\s*(?:(?:,\s*)?{RE_NO}\s*)?)"
    + r")?"  # fin séparateur éventuel
    + RE_CAD_NUM  # numéro de parcelle
    + r")"
)
P_CAD_AUTRES = re.compile(RE_CAD_AUTRES, re.MULTILINE | re.IGNORECASE)
# idem, avec named groups
RE_CAD_AUTRES_NG = (
    r"(?:"
    + rf"(?:{RE_NO}\s*)?"
    + rf"(?P<sec>{RE_CAD_SEC})"
    + r"(?:"  # séparateur éventuel
    + r"(?:-)"  # ex: "[...] cadastrée BK-80 sise [...]"
    + rf"|(?:\s*(?:(?:,\s*)?{RE_NO}\s*)?)"
    + r")?"  # fin séparateur éventuel
    + rf"(?P<num>{RE_CAD_NUM})"
    + r")"
)
P_CAD_AUTRES_NG = re.compile(RE_CAD_AUTRES_NG, re.MULTILINE | re.IGNORECASE)

# Marseille ou autres communes
RE_CAD_SECNUM = r"(?:" + RE_CAD_MARSEILLE + r"|" + RE_CAD_AUTRES + r")"
P_CAD_SECNUM = re.compile(RE_CAD_SECNUM, re.IGNORECASE | re.MULTILINE)

# avec le contexte gauche
RE_PARCELLE = (
    r"(?:"  # contexte gauche
    + r"(?:cadastr[ée](?:e|es|s)?(?:\s+section)?\s+)"
    + r"|(?:r[ée]f[ée]rence(?:s)?\s+cadastrale(?:s)?\s+)"
    + r"|(?:r[ée]f[ée]renc[ée](?:e|es|s)?\s+au\s+cadastre\s+sous\s+le\s+)"  # référence au cadastre sous le (n°)
    + r"|(?:parcelle(?:s)?\s+(?:sise(?:s)?\s+)?"
    # negative lookahead: éviter de capturer des faux positifs
    + rf"(?!"
    # les seuls numéros eg. "parcelles 132 et 201"
    + rf"(?:{RE_CAD_NUM}\s+et\s+{RE_CAD_NUM})"
    # "du" n'est pas (jamais?) un code de section eg. "[parcelle ]du 12"
    + rf"|(?:du\s+{RE_CAD_NUM})"
    + r")"  # fin negative lookahead
    + r")"  # fin "parcelle(s)?( sise(s)?) "
    + r"|(?:\s+section\s+)"  # capture notamment les mentions dans une liste: ", section ...", "et section ..."
    # lookahead pur pour les références longues (Marseille), reconnaissables sans contexte gauche: (DGFIP ou arrt +) quartier + section + num
    + rf"|(?=(?:{RE_NO}\s*)?(?:(?:131)?(?:{RE_CAD_ARRT})\s*(?<![\s/-]\d){RE_CAD_QUAR}\s*(?!du\s+{RE_DATE}){RE_CAD_SEC}(?:\s*(?:(?:,\s*)?{RE_NO}\s*)?)?){RE_CAD_NUM})"
    + r")"  # fin contexte gauche
    + r"(?P<cadastre_id>"  # named group pour la ou les références cadastrales
    + RE_CAD_SECNUM  # 1re référence cadastrale
    + r"("  # 1 ou plusieurs références supplémentaires
    + r"(?:,|\s+et|\s+[-])\s+"
    + RE_CAD_SECNUM
    + r")*"  # fin 1 ou plusieurs références supplémentaires
    + r")"  # fin named group
)
P_PARCELLE = re.compile(RE_PARCELLE, re.MULTILINE | re.IGNORECASE)


def get_parcelles(page_txt: str) -> List[str]:
    """Récupère la ou les références de parcelles cadastrales.

    Parameters
    ----------
    page_txt: str
        Texte d'une page de document

    Returns
    -------
    id_parcelles: List[str]
        Références d'une ou plusieurs parcelles cadastrales si détectées dans le texte,
        liste vide sinon.
    """
    # NEW normalisation du texte
    page_txt = normalize_string(page_txt, num=True, apos=True, hyph=True, spaces=True)
    # end NEW
    id_parcelles = []  # résultat

    # WIP chercher le ou les empans distincts contenant au moins une référence à une parcelle
    if matches := list(P_PARCELLE.finditer(page_txt)):
        logging.warning(
            f"{len(matches)} empans PARCELLE: {[x.group(0) for x in matches]}"
        )
        # WIP extraire plusieurs références
        for m_parc in matches:
            # liste des identifiants de parcelles
            m_cad_str = m_parc.group("cadastre_id")
            # WIP
            if m_parcs_mrs := list(
                P_CAD_MARSEILLE_NG.finditer(
                    page_txt, m_parc.start("cadastre_id"), m_parc.end("cadastre_id")
                )
            ):
                # essayer d'abord de repérer des références Marseille, plus longues et qui peuvent générer de faux positifs si analysées
                # comme des références hors Marseille (ex: "208837 D0607 ET 208837 D0290" => "ET 2088" serait repéré comme une parcelle...)
                m_parcs = m_parcs_mrs
                if len(m_parcs) > 1:
                    logging.warning(
                        f"{len(m_parcs)} parcelles (Marseille 1) dans {m_cad_str}: {[x.group(0) for x in m_parcs]}"
                    )
            elif m_parcs_aut := list(
                P_CAD_SECNUM.finditer(
                    page_txt, m_parc.start("cadastre_id"), m_parc.end("cadastre_id")
                )
            ):
                # sinon essayer de repérer des références d'autres communes
                m_parcs = m_parcs_aut
                if len(m_parcs) > 1:
                    logging.warning(
                        f"{len(m_parcs)} parcelles (toutes communes) dans {m_cad_str}: {[x.group(0) for x in m_parcs]}"
                    )
            else:
                raise ValueError(
                    f"Pas de référence retrouvée dans la zone? {m_cad_str}"
                )
            # end WIP
            # RESUME HERE ! 2023-04-28
            id_parcelles.append(m_cad_str)
    elif (
        False
    ):  # matches := list(P_PARCELLE_MARSEILLE_NOCONTEXT.finditer(page_txt)):  # WIP
        logging.warning(
            f"{len(matches)} empans PARC_MRS: {[x.group(0) for x in matches]}"
        )
        for m_parc_mrs in matches:
            # liste des identifiants de parcelles
            m_cad_str = m_parc_mrs.group("cadastre_id")
            # WIP
            m_parcs = list(
                P_CAD_MARSEILLE_NG.finditer(
                    page_txt,
                    m_parc_mrs.start("cadastre_id"),
                    m_parc_mrs.end("cadastre_id"),
                )
            )
            if len(m_parcs) > 1:
                logging.warning(
                    f"{len(m_parcs)} parcelles (Marseille 2) dans {m_cad_str}: {[x.group(0) for x in m_parcs]}"
                )
            # end WIP
            id_parcelles.append(m_cad_str)

    return id_parcelles


def generate_refcadastrale_norm(
    codeinsee: str, refcad: str, arr_pdf: str, adr_cpostal: str
) -> str:
    """Génère une référence cadastrale normalisée à une entrée.

    Parameters
    ----------
    codeinsee: string
        Code INSEE de la commune.
    refcad: string
        Référence cadastrale brute.
    arr_pdf: string
        Nom du fichier PDF (pour exception)
    adr_cpostal: string
        Code postal de la commune

    Returns
    -------
    refcad: string
        Référence cadastrale normalisée.
    """
    # ajouter le préfixe du code insee
    # TODO cas particulier pour Marseille: code commune par ardt + code quartier
    if pd.isna(codeinsee):
        codeinsee = ""  # TODO vérifier si le comportement qui en découle est ok (identifiant court, à compléter manuellement par le code insee)

    # prendre la référence locale (commune)
    if pd.isna(refcad):
        refcad = None
    elif m_mars := P_CAD_MARSEILLE_NG.search(refcad):
        # on ne garde que le 1er match
        # TODO gérer 2 ou plusieurs références cadastrales
        #
        # Marseille: code insee arrondissement + code quartier (3 chiffres) + section + parcelle
        arrt = m_mars["arrt"]
        if not arrt and not codeinsee:
            # ni arrondissement ni code insee
            refcad = f"{m_mars['quar']}{m_mars['sec']:>02}{m_mars['num']:>04}"
            logging.error(
                f"{arr_pdf}: numéro d'arrondissement manquant pour une référence cadastrale à Marseille {refcad}"
            )
        else:
            if codeinsee and codeinsee != "13055":
                # on a bien un code INSEE
                if arrt:
                    # si on a aussi un numéro d'arrondissement, on vérifie que les deux sont cohérents
                    try:
                        assert codeinsee[-3:] == arrt
                    except AssertionError:
                        # FIXME améliorer le warning ; écrire une expectation sur le dataset final
                        # 2023-03-06: 16 conflits
                        logging.warning(
                            f"{arr_pdf}: conflit entre code INSEE ({codeinsee}, via code postal {adr_cpostal}) et référence cadastrale {arrt}"
                        )
            else:
                # on a un arrondissement: reconstruire un code INSEE
                codeinsee = f"13{arrt}"
            # référence cadastrale complète
            refcad = (
                f"{codeinsee}{m_mars['quar']}{m_mars['sec']:>02}{m_mars['num']:>04}"
            )
    elif m_autr := P_CAD_AUTRES_NG.search(refcad):
        # hors Marseille: code insee commune + 000 + section + parcelle
        codequartier = "000"
        refcad = f"{codeinsee}{codequartier}{m_autr['sec']:>02}{m_autr['num']:>04}"
    else:
        refcad = None
    return refcad

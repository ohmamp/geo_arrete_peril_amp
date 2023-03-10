"""Reconnaissance et traitement des adresses.

"""

import logging
import re
from typing import Dict

from text_utils import normalize_string


# TODO gérer "106-108 rue X *(102-104 selon cadastre)*"
# TODO gérer "24 rue X / *angle* 2 rue Y"

# TODO 47 arrêtés 13055 (dont 4 sans référence cadastrale):
# csvcut -c arr_nom_arr,adr_ad_brute,adr_codeinsee,par_ref_cad data/interim/arretes_peril_compil_data_enr_struct.csv |grep ",13055," |less

# codes postaux de Marseille
# à conserver même quand il y aura une table CSV de codes postaux ;
# cette liste permet de changer de stratégie de reconnaissance des parcelles cadastrales
# (à Marseille: références longues incluant l'arrondissement et le quartier)
CP_MARSEILLE = [f"130{i:02}" for i in range(1, 17)]

# regex générique pour ce qu'on considérera comme un "token" (plus ou moins, un mot) dans un nom de voie ou de commune
RE_TOK = r"[^,;:–(\s.]+"  # r"[A-Za-zÀ-ÿ]+"  # r"\w+"

# TODO comment gérer plusieurs numéros? ex: "10-12-14 boulevard ...""
# pour le moment on ne garde que le premier
RE_NUM_VOIE = r"(\d+)"
P_NUM_VOIE = re.compile(RE_NUM_VOIE, re.IGNORECASE | re.MULTILINE)
#
RE_IND_VOIE = r"(?:A|bis|ter)"
P_IND_VOIE = re.compile(RE_IND_VOIE, re.IGNORECASE | re.MULTILINE)
#
RE_NUM_IND = (
    RE_NUM_VOIE  # numéro  # ?P<num_voie>
    + r"("  # ?P<ind_voie>  # optionnel: 1 indicateur, ou plusieurs
    + r"\s?"
    + r"(?:"  # alternative
    + rf"(?:{RE_IND_VOIE})"  # 1 indicateur
    + rf"|(?:"  # ou une liste d'indicateurs entre parenthèses
    + r"[(]"
    + RE_IND_VOIE  # 1er indicateur
    + r"(?:"  # 2e (et éventuellement plus) indicateur
    + r"(?:(?:\s*[,-/]\s*)|(?:\s+et\s+))"  # séparateur
    + RE_IND_VOIE  # n-ième indicateur
    + r")+"  # au moins un 2e indicateur, possible plus
    + r"[)]"
    + r")"  # fin liste d'indicateurs
    + r")"  # fin alternative 1 ou + indicateurs
    + r")?"  # fin indicateur optionnel
)
P_NUM_IND = re.compile(RE_NUM_IND, re.IGNORECASE | re.MULTILINE)

# liste de numéros et indicateurs: "10-12-14 boulevard ..., 10 / 12 avenue ..."
RE_NUM_IND_LIST = (
    r"(?:"
    + RE_NUM_IND  # un numéro (et éventuellement indicateur)
    + r"(?:"  # et éventuellement d'autres numéros (éventuellement avec indicateur)
    + r"(?:(?:\s*[,-/]\s*)|(?:\s+et\s+))"  # séparateur
    + RE_NUM_IND
    + r")*"  # 0 à N numéros (et indicateurs) supplémentaires
    + r")"
)
P_NUM_IND_LIST = re.compile(RE_NUM_IND_LIST, re.IGNORECASE | re.MULTILINE)


# types de voies
RE_TYP_VOIE = (
    r"(?:\b"  # "word boundary" pour éviter les matches sur "cou*che*", "par*cours*" etc
    + r"(?:"
    + r"all[ée]e[s]?"
    + r"|ancien\s+chemin"
    + r"|avenue"
    + r"|boulevard|bld|bd"
    + r"|chemin|che|ch"
    + r"|cours"
    + r"|domaine"
    + r"|impasse"
    + r"|mont[ée]e"
    + r"|place"
    + r"|quai"
    + r"|route"
    + r"|rue"
    # + r"|voie"  # negative lookahead: \s(?:publique|de\scirculation|d['’]effondrement|d'['’]affichage|sur|le\slong|allant|précitée|administrative|électronique|dématérialisée|de\srecours|de\sconséquence|...)
    + r"|traverse"
    + r"|vc"  # "voie communale"
    + r")"
    + r")"
)

# code postal
RE_CP = r"\d{5}"
P_CP = re.compile(RE_CP)

# RE_NOM_VOIE = rf"""(?:{RE_TOK}(?:[\s-]{RE_TOK})*)"""
# TODO gérer "chemin de X *à* Y" (interférence avec "à" comme borne)
# TODO gérer "15 *à* 21 avenue de..." (interférence avec "à" comme borne)
RE_NOM_VOIE = (
    r"[\s\S]+?"  # n'importe quelle suite de caractères, vides ou non, jusqu'à un séparateur ou un code postal
    # (NB: c'est une "lookahead assertion", qui ne consomme pas les caractères)
    + r"(?=\s*,\s+"  # séparateur "," (ex: 2 rue xxx[,] 13420 GEMENOS)
    + r"|\s*–\s*"  # séparateur "–"
    + r"|\s+-\s+"  # séparateur "–"
    + r"|\s*[/]\s*"  # séparateur "/" (double adresse: "2 rue X / 31 rue Y 13001 Marseille")
    + r"|\s+et\s+"  # séparateur "et" (double adresse: "2 rue X et 31 rue Y 13001 Marseille")
    + rf"|(?:\s+(?:{RE_NUM_IND_LIST})[,]?\s+{RE_TYP_VOIE})"  # on bute directement sur une 2e adresse (rare mais ça arrive)
    + r"|(?:\s+à\s+(?!vent\s+))"  # borne droite "à", sauf "à vent" : "2 rue xxx à GEMENOS|Roquevaire" (rare, utile mais source potentielle de confusion avec les noms de voie "chemin de X à Y")
    + r"|(?<!du )b[âa]timent"  # borne droite "bâtiment", sauf si "du bâtiment" ("rue du bâtiment" existe dans certaines communes)
    + rf"|\s*{RE_CP}"  # borne droite <code_postal>
    + r")"
)

# TODO s'arrêter quand on rencontre une référence cadastrale (lookahead?)
RE_COMMUNE = (
    rf"[A-ZÀ-Ý]{RE_TOK}"  # au moins 1 token qui commence par une majuscule
    + r"(?:[ '’-]"  # séparateur: tiret, apostrophe, espace
    + rf"{RE_TOK}"
    + r"){0,4}"  # + 0 à 3 tokens après séparateur
)  # r"""[^,;]+"""  # 1 à 4 tokens au total

# complément d'adresse: résidence (+ bât ou immeuble)
RE_RESID = r"(?:r[ée]sidence|cit[ée])"
RE_BAT = (
    r"(?:B[âa]timent|B[âa]t|Immeuble)"
    + r"(?!\s+"  # negative lookahead qui commence par des espaces
    + r"(?:"  # alternative
    + r"sis"  # bâtiment|immeuble sis
    + r"|menaçant"  # bâtiment|immeuble menaçant (ruine)
    + r")"  # fin alternative
    + r")"  # fin negative lookahead
)
RE_APT = r"(?:Appartement|Appart|Apt)"

# éléments possibles de complément d'adresse
RE_ADR_COMPL_ELT = (
    r"(?:"  # groupe global
    + rf"(?:{RE_RESID}|{RE_BAT}|{RE_APT})"  # résidence | bâtiment | appartement
    + r"\s*[^,–]*?"  # \s*[^,–]+ # contenu: nom de résidence, du bâtiment, de l'appartement...
    + r")"
    # FIXME le lookahead ne fonctionne pas parfaitement ; il faut peut-être faire autrement (ex: 2e routine qui cherche un code postal et retire tout ce qui est à droite)
    # FIXME ex: "26-28 RUE DE LA BUTINEUSE / 75-83 TRAVERSE DU MOULIN À VENT BATIMENT B - 13015"
    # (NB: c'est une "lookahead assertion", qui ne consomme pas les caractères)
    + r"(?=\s*,\s+"  # séparateur "," (ex: 2 rue xxx[,] 13420 GEMENOS)
    + r"|\s*–\s*"  # séparateur "–"
    + r"|\s+-\s+"  # séparateur "-"
    # + r"|\s*[/]\s*"  # séparateur "/" (double adresse: "2 rue X / 31 rue Y 13001 Marseille")
    # + r"|\s+et\s+"  # séparateur "et" (double adresse: "2 rue X et 31 rue Y 13001 Marseille")
    + rf"|(?:\s*(?:{RE_NUM_IND_LIST})(?:\s*,)?\s+(?:{RE_TYP_VOIE}|la\s+Can[n]?ebi[èe]re))"  # on bute directement sur une 2e adresse (rare mais ça arrive)
    # + r"|(?:\s+à\s+(?!vent\s+))"  # à : "2 rue xxx à GEMENOS|Roquevaire" (rare, utile mais source potentielle de confusion avec les noms de voie "chemin de X à Y")
    + rf"|\s*{RE_CP}"  # code postal
    + r")"
)
# un complément d'adresse = un ou plusieurs éléments de complément d'adresse
RE_ADR_COMPL = (
    r"(?:"  # englobant général
    + RE_ADR_COMPL_ELT
    + r"(?:"  # éventuels blocs 2-n
    + r"(?:\s*[,–-]\s*)?"  # séparateur optionnel
    + RE_ADR_COMPL_ELT
    + r")*"  # fin éventuels blocs 2-n
    + r")"
)

# (type et) nom de voie
RE_VOIE = (
    r"(?:"
    + r"(?:"  # motif classique: <type_voie> <nom_voie>
    + rf"(?:{RE_TYP_VOIE})\s+(?:{RE_NOM_VOIE})"
    + r")"
    + r"|(?:"  # cas particulier: la canebière
    + r"la\s+Can[n]?ebi[èe]re"  # inclut l'ancienne graphie "nn"
    + r")"
    + r")"
)
P_VOIE = re.compile(RE_VOIE, re.IGNORECASE | re.MULTILINE)

# numéro, indicateur et voie
RE_NUM_IND_VOIE = (
    r"(?:"
    + rf"(?:(?:{RE_NUM_IND_LIST})(?:\s*,)?\s+)?"  # numéro et indice de répétition (ex: 1 bis)  # ?P<num_ind_list>
    + rf"({RE_VOIE})"  # type et nom de la voie (ex: rue Jean Roques ; la Canebière)  # ?P<voie>
    + r")"
)
P_NUM_IND_VOIE = re.compile(RE_NUM_IND_VOIE, re.IGNORECASE | re.MULTILINE)
# idem, avec named groups
RE_NUM_IND_VOIE_NG = (
    r"(?:"
    + rf"(?:(?P<num_ind_list>{RE_NUM_IND_LIST})[,]?\s+)?"  # numéro et indice de répétition (ex: 1 bis)
    + rf"(?P<voie>{RE_VOIE})"  # type et nom de la voie (ex: rue Jean Roques ; la Canebière)
    + r")"
)
P_NUM_IND_VOIE_NG = re.compile(RE_NUM_IND_VOIE_NG, re.IGNORECASE | re.MULTILINE)


# liste d'adresses courtes: numéro, indicateur et voie
RE_NUM_IND_VOIE_LIST = (
    r"(?:"
    # au moins 1 adresse avec voie et éventuellement numéro et indicateur
    + RE_NUM_IND_VOIE
    # plus éventuellement 1 à plusieurs adresses supplémentaires
    + r"(?:"  # et éventuellement d'autres numéros (éventuellement avec indicateur)
    + r"(?:(?:\s*[,-/]\s*)|(?:\s+et\s+)|(?:\s+))"  # séparateur (parfois juste "\s+" !)
    + RE_NUM_IND_VOIE
    + r")*"  # 0 à N numéros (et indicateurs) supplémentaires
    + r")"
)
P_NUM_IND_VOIE_LIST = re.compile(RE_NUM_IND_VOIE_LIST, re.IGNORECASE | re.MULTILINE)

# TODO double adresse: 2 rue X / 31 rue Y 13001 Marseille (RE distincte, pour les named groups)
RE_ADRESSE = (
    r"(?:"
    + rf"(?:(?:{RE_ADR_COMPL})(?:\s*[,–-])?\s*)?"  # WIP (optionnel) complément d'adresse (pré)
    + RE_NUM_IND_VOIE_LIST
    + rf"(?:(?:\s*[,–-])?\s*(?:{RE_ADR_COMPL}))?"  # WIP (optionnel) complément d'adresse (post)
    + r"(?:"  # (optionnel) code postal et/ou commune
    + r"(?:(?:\s*[,–-])|(?:\s+à))?"  # ex: 2 rue xxx[,] 13420 GEMENOS
    + rf"(?:\s*(?:{RE_CP}))?"  # \s+  # sinon: \s*–\s+ | ...  # optionnel code postal
    + rf"(?:\s*(?:{RE_COMMUNE}))?"  # optionnel commune
    + r")?"  # fin optionnel code postal et/ou commune
    + r")"
)
P_ADRESSE = re.compile(RE_ADRESSE, re.MULTILINE | re.IGNORECASE)

# idem, avec named groups
RE_ADRESSE_NG = (
    r"(?:"
    + rf"(?:(?P<compl_ini>{RE_ADR_COMPL})(?:\s*[,–-]\s*)?)?"  # WIP (optionnel complément d'adresse (pré)
    + rf"(?P<num_ind_voie_list>{RE_NUM_IND_VOIE_LIST})"  # 1 à N adresses courtes (numéro, indicateur, voie)
    + rf"(?:(?:\s*[,–-]\s*)?(?P<compl_fin>{RE_ADR_COMPL}))?"  # WIP (optionnel) complément d'adresse (post)
    + r"(?:"  # (optionnel) code postal et/ou commune
    + r"(?:(?:\s*[,–-])|(?:\s+à))?"  # ex: 2 rue xxx[,] 13420 GEMENOS
    + rf"(?:\s*(?P<code_postal>{RE_CP}))?"  # \s+  # sinon: \s*–\s+ | ...  # optionnel code postal
    + rf"(?:\s*(?P<commune>{RE_COMMUNE}))?"  # optionnel commune
    + r")?"  # fin optionnel code postal et/ou commune
    + r")"
)
P_ADRESSE_NG = re.compile(RE_ADRESSE_NG, re.MULTILINE | re.IGNORECASE)


def create_adresse_normalisee(adr_fields: Dict, adr_commune_maire: str) -> str:
    """Créer une adresse normalisée.

    L'adresse normalisée rassemble les champs extraits de l'adresse brute, et
    la commune extraite par ailleurs, qui doivent être cohérents.

    Parameters
    ----------
    adr_fields: dict
        Champs de l'adresse, extraits de l'adresse brute
    adr_commune_maire: str
        Commune de l'arrêté

    Returns
    -------
    adr_norm: str
        Adresse normalisée
    """
    adr_commune_brute = adr_fields["adr_commune"]
    # TODO retenir la graphie standard, prise par exemple dans la table des codes INSEE ?
    # croisement entre la commune qui prend l'arrêté et l'éventuelle commune extraite de l'adresse brute
    if (adr_commune_brute is None) and (adr_commune_maire is None):
        # pas de commune  # TODO émettre un warning?
        commune = None
    elif adr_commune_brute is None:
        commune = adr_commune_maire  # TODO normaliser?
    elif adr_commune_maire is None:
        commune = adr_commune_brute  # TODO normaliser?
    elif (adr_commune_brute is not None) and (adr_commune_maire is not None):
        # deux mentions potentiellement différentes de la commune ; normalement de simples variantes de graphie
        # pour le moment on retient la commune qui prend l'arrêté (commune_maire)
        # TODO comparer les graphies, définir et retenir une forme canonique
        commune = adr_commune_maire  # TODO normaliser?

    adr_norm_parts = [
        adr_fields["adr_num"],
        adr_fields["adr_ind"],
        adr_fields["adr_voie"],
        adr_fields["adr_compl"],
        adr_fields["adr_cpostal"],
        commune,
    ]
    adr_norm = " ".join(x for x in adr_norm_parts if x)  # TODO normaliser la graphie?
    adr_norm = normalize_string(adr_norm)
    return adr_norm


def process_adresse_brute(adr_ad_brute: str) -> Dict:
    """Extraire une ou plusieurs adresses d'une adresse brute.

    Chaque adresse comporte différents champs: numéro, indicateur,
    voie, (éventuellement complement d'adresse,) code postal,
    commune.

    Parameters
    ----------
    adr_ad_brute: str
        Adresse brute

    Returns
    -------
    adresses: list(dict)
        Liste d'adresses
    """
    adresses = []
    if (adr_ad_brute is not None) and (m_adresse := P_ADRESSE_NG.search(adr_ad_brute)):
        # récupérer les champs communs à toutes les adresses groupées: complément,
        # code postal et commune
        adr_compl = " ".join(
            m_adresse[x].strip() for x in ["compl_ini", "compl_fin"] if m_adresse[x]
        )  # FIXME concat?
        if adr_compl:
            logging.warning(
                f"complément d'adresse trouvé, pré: {m_adresse['compl_ini']} ; post: {m_adresse['compl_fin']} dans adr_ad_brute: {adr_ad_brute}"
            )
        cpostal = m_adresse["code_postal"]
        commune = m_adresse["commune"]

        # traitement spécifique pour la voie: type + nom (legacy?)
        # adr_voie = m_adresse["voie"].strip()
        # if adr_voie == "":
        #     adr_voie = None
        #
        # extraire la ou les adresses courtes, et les séparer s'il y en a plusieurs
        # on est obligé de réextraire depuis l'adresse brute, car le RE_VOIE est défini
        # avec un contexte droit (positive lookahead)
        # (pénible, mais pour le moment ça fonctionne comme ça)
        adr_lists = list(P_NUM_IND_VOIE_LIST.finditer(adr_ad_brute))
        # obligatoire: une liste d'adresses courtes (ou une adresse courte)
        try:
            assert len(adr_lists) == 1
        except AssertionError:
            raise ValueError(f"adr_lists: {adr_lists}")
        adr_list = adr_lists[0]
        # on vérifie qu'on travaille exactement au même endroit, pour se positionner au bon endroit
        try:
            assert adr_list.group(0) == m_adresse["num_ind_voie_list"]
        except AssertionError:
            raise ValueError(
                f"Problème sur {m_adresse.groupdict()}\nadr_list.group(0): {adr_list.group(0)} ; {m_adresse['num_ind_voie_list']}"
            )
        # on ne peut pas complètement verrouiller avec adr_list.end(), car il manquerait à nouveau le contexte droit (grmpf)
        adrs = list(P_NUM_IND_VOIE_NG.finditer(adr_ad_brute, adr_list.start()))
        if not adrs:
            raise ValueError(f"Aucune adresse NUM_IND_VOIE trouvée dans {adr_list}")
        for adr in adrs:
            # pour chaque adresse courte,
            # - récupérer la voie
            voie = adr["voie"]
            # - récupérer la liste (optionnelle) de numéros et d'indicateurs (optionnels)
            num_ind_list = adr["num_ind_list"]
            if not num_ind_list:
                # pas de liste de numéros et indicateurs:
                logging.warning(f"adresse courte en voie seule: {adr.group(0)}")
                # ajouter une adresse sans numéro (ni indicateur)
                adr_fields = {
                    "adr_num": None,
                    "adr_ind": None,
                    "adr_voie": voie,
                    "adr_compl": adr_compl,
                    "adr_cpostal": cpostal,
                    "adr_commune": commune,
                }
                adresses.append(adr_fields)
            else:
                # on a une liste de numéros (et éventuellement indicateurs)
                num_inds = list(P_NUM_IND.finditer(num_ind_list))
                if len(num_inds) > 1:
                    logging.warning(f"plusieurs numéros et indicateurs: {num_inds}")
                for num_ind in num_inds:
                    # pour chaque numéro et éventuel indicateur
                    num_ind_str = num_ind.group(0)
                    # extraire le numéro
                    m_nums = list(P_NUM_VOIE.finditer(num_ind_str))
                    assert len(m_nums) == 1
                    num = m_nums[0].group(0)
                    # extraire le ou les éventuels indicateurs
                    m_inds = list(P_IND_VOIE.finditer(num_ind_str))
                    if not m_inds:
                        # pas d'indicateur: adresse avec juste un numéro
                        adr_fields = {
                            "adr_num": num,
                            "adr_ind": None,
                            "adr_voie": voie,
                            "adr_compl": adr_compl,
                            "adr_cpostal": cpostal,
                            "adr_commune": commune,
                        }
                        adresses.append(adr_fields)
                    else:
                        # au moins un indicateur
                        if len(m_inds) > 1:
                            logging.warning(f"plusieurs indicateurs: {m_inds}")
                        for m_ind in m_inds:
                            # pour chaque indicateur, adresse avec numéro et indicateur
                            ind = m_ind.group(0)
                            adr_fields = {
                                "adr_num": num,
                                "adr_ind": ind,
                                "adr_voie": voie,
                                "adr_compl": adr_compl,
                                "adr_cpostal": cpostal,
                                "adr_commune": commune,
                            }
                            adresses.append(adr_fields)
        # WIP code postal disparait
        if (cpostal is None) and P_CP.search(adr_ad_brute):
            # WIP survient pour les adresses doubles: la fin de la 2e adresse est envoyée en commune
            # TODO détecter et analyser spécifiquement les adresses doubles
            logging.warning(
                f"aucun code postal extrait de {adr_ad_brute}: {m_adresse.groupdict()}"
            )
        # end WIP code postal
        return adresses
    else:
        adr_fields = {
            "adr_num": None,
            "adr_ind": None,
            "adr_voie": None,
            "adr_compl": None,
            "adr_cpostal": None,
            "adr_commune": None,
        }
        # TODO liste contenant un seul dict aux champs tous None, ou liste vide (à gérer) ?
        return [adr_fields]

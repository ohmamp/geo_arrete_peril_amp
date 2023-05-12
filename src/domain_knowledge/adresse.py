"""Reconnaissance et traitement des adresses.

"""

import logging
import re
from typing import Dict, List

import pandas as pd
from src.domain_knowledge.cadastre import RE_CAD_SECNUM

# from src.domain_knowledge.arrete import RE_ARRETE

# from src.domain_knowledge.cadastre import RE_CAD_MARSEILLE  # (inopérant?)
from src.domain_knowledge.codes_geo import (
    RE_COMMUNES_AMP_ALLFORMS,
)
from src.utils.text_utils import RE_NO, normalize_string


# TODO récupérer le code postal dans les cas complexes: "périmètre de sécurité 82 Hoche 105 Kleber 13003.pdf"

# TODO gérer "106-108 rue X *(102-104 selon cadastre)*"

# TODO 40 arrêtés 13055 (dont 3 sans référence cadastrale):
# csvcut -c arr_nom_arr,adr_ad_brute,adr_codeinsee,par_ref_cad data/interim/arretes_peril_compil_data_enr_struct.csv |grep ",13055," |less


# regex générique pour ce qu'on considérera comme un "token" (plus ou moins, un mot) dans un nom de voie ou de commune
# lettres non-accentuées et accentuées, majuscules et minuscules
RE_LETTERS = r"[A-Za-zÀ-ÿ]+"  # r"[^,;:–(\s.]+"  # r"\w+"
# séparateur entre deux tokens ; caractères possibles dans un token
RE_SEP = r"[\s,;:({/.–-]"
RE_NOSEP = r"[^\s,;:({/.–-]"

# TODO comment gérer plusieurs numéros? ex: "10-12-14 boulevard ...""
# pour le moment on ne garde que le premier
RE_NUM_VOIE = r"(\d+)"
P_NUM_VOIE = re.compile(RE_NUM_VOIE, re.IGNORECASE | re.MULTILINE)

# indicateurs observés: A, mais aussi B, 1155*E*, 82*L*, ...
# (sinon [A-Z]\b pour éviter de capturer à tort "12 *ET* 14"?)
RE_IND_VOIE = r"(?:bis|quater|ter|A(?!U)|[B-DF-Z]|(?:E(?!T)))"
P_IND_VOIE = re.compile(RE_IND_VOIE, re.IGNORECASE | re.MULTILINE)

# un numéro et un ou plusieurs indicateurs
RE_NUM_IND = (
    RE_NUM_VOIE  # numéro  # ?P<num_voie>
    + r"(\s*"  # ?P<ind_voie>  # optionnel: 1 indicateur, ou plusieurs
    + r"(?:"  # alternative
    # une liste d'indicateurs entre parenthèses
    + rf"(?:[(]{RE_IND_VOIE}"  # 1er indicateur
    + r"(?:"  # 2e (et éventuellement plus) indicateur
    + r"(?:(?:\s*[,/-]\s*)|(?:\s+et\s+)|(?:\s+))"  # séparateur
    + RE_IND_VOIE  # n-ième indicateur
    + r")+"  # au moins un 2e indicateur, possible plus
    + r"[)])"  # fin liste d'indicateurs
    # ou une liste d'indicateurs sans parenthèses
    + rf"|(?:{RE_IND_VOIE}"  # 1er indicateur
    + r"(?:"  # 2e (et éventuellement plus) indicateur
    + r"(?:(?:\s*[,/-]\s*)|(?:\s+et\s+)|(?:\s+))"  # séparateur
    + RE_IND_VOIE  # n-ième indicateur
    + r")+)"  # au moins un 2e indicateur, possible plus
    # fin liste d'indicateurs sans parenthèses
    # ou 1 seul indicateur
    + rf"|(?:{RE_IND_VOIE})"
    + r")"  # fin alternative 1 ou + indicateurs
    + r")?"  # fin indicateur optionnel
)
P_NUM_IND = re.compile(RE_NUM_IND, re.IGNORECASE | re.MULTILINE)

# liste de numéros et indicateurs: "10-12-14 boulevard ..., 10 / 12 avenue ..."
RE_NUM_IND_LIST = (
    r"(?:"
    + RE_NUM_IND  # un numéro (et éventuellement indicateur)
    + r"(?:"  # et éventuellement d'autres numéros (éventuellement avec indicateur)
    # séparateur: "-", "/", ",", " et ", " à "
    # TODO signaler le "à" dans le rapport => devra être déplié manuellement en plusieurs adresses
    + r"(?:(?:\s*[,/-]\s*)|(?:\s+(et|à)\s+)|(?:\s+))"  # séparateur
    + RE_NUM_IND
    + r")*"  # 0 à N numéros (et indicateurs) supplémentaires
    + r")"
)
P_NUM_IND_LIST = re.compile(RE_NUM_IND_LIST, re.IGNORECASE | re.MULTILINE)


# types de voies
RE_TYP_VOIE = (
    r"(?:\b"  # "word boundary" pour éviter les matches sur "cou*che*", "par*cours*" etc
    + r"(?:"
    + r"(?<!immeuble\ssur\s)rue"  # negative lookbehind: "immeuble sur rue"
    + r"|avenue"
    + r"|boulevard|bld|bd"
    + r"|place"
    + r"|cours"
    + r"|route"
    + r"|traverse"
    + r"|impasse"
    + r"|all[ée]e[s]?"
    + r"|quai"
    + r"|ancien\s+chemin"
    + r"|chemin|che|ch"
    + r"|mont[ée]e"
    + r"|anse"  # anse de Malmousque, anse de Maldormé etc.
    + r"|plage"  # ex: plage de l'Estaque
    + r"|vc"  # "voie communale"
    + r"|domaine"
    # + r"|voie"  # negative lookahead: \s(?:publique|de\scirculation|d['’]effondrement|d'['’]affichage|sur|le\slong|allant|précitée|administrative|électronique|dématérialisée|de\srecours|de\sconséquence|...)
    + r")"
    + r")"
)

# code postal
# negative lookbehind: ni chiffre ni lettre P, pour éviter de capturer les fins de codes postaux et les boîtes postales
# negative lookahead: pas de chiffre, pour éviter de capturer les débuts de références de parcelles cadastrales (6 chiffres de préfixe à Marseille: 3 arrondissement + 3 quartier)
RE_CP = r"(?<![\dP])\d{5}(?![\d])"  # WIP: ...(?!\d)"
P_CP = re.compile(RE_CP)

# nom de voie
# peut être n'importe quelle suite de caractères, vides ou non, jusqu'à un séparateur, un code postal
# ou une autre adresse
# - contexte droit, qui sera utilisé pour délimiter à droite un nom de voie (butée)
RE_NOM_VOIE_RCONT = (
    r"("
    + r"\s*[,;.]\s+"  # séparateur "," (ex: 2 rue xxx[,] 13420 GEMENOS)  # NEW 2023-05-12 "."
    + rf"|(\s*[.–-])*\s*{RE_CP}"  # borne droite <code_postal>  # WIP: ajout ".", ? -> *
    + r"|\s*–\s*"  # séparateur "–"
    + r"|\s+-\s*"  # séparateur "-"
    + r"|\s*[/]\s*"  # séparateur "/" (double adresse: "2 rue X / 31 rue Y 13001 Marseille")
    + r"|\s+et\s+"  # séparateur "et" (double adresse: "2 rue X et 31 rue Y 13001 Marseille")
    + rf"|(?:(\s*[-–,])?\s*(?:{RE_NUM_IND_LIST})[,]?\s+{RE_TYP_VOIE})"  # on bute directement sur une 2e adresse (rare mais ça arrive)
    + r"|(?:\s*[({][^)}]+\s+selon\s+cadastre[)}])"  # complément d'adresse ; ex: "12 rue X (18 selon cadastre)"
    + r"|(?:\s*[({]cadastré[^)}]+?[)}])"  # (cadastré <ref_cad>)
    + r"|(?:\s+[àa]\s+(?!vent\s+))"  # borne droite "à", sauf "à vent" : "2 rue xxx à GEMENOS|Roquevaire" (rare, utile mais source potentielle de confusion avec les noms de voie "chemin de X à Y")
    + r"|\s+(?<!du )b[âa]timent"  # borne droite "bâtiment", sauf si "du bâtiment" ("rue du bâtiment" existe dans certaines communes)
    + r"|\s+b[âa]t\s+"  # bât(iment)
    + r"|\s+parcelle"  # parcelle (référence cadastrale)
    + r"|\s+effectué"  # visite de l'immeuble sis [...] effectuée par [...]
    + r"|\s+ainsi[,\s]"  # ainsi que...
    + r"|(?:\n+(?:Nous|Le\s+maire|Vu|Consid[ée]rant|Article|Propriété\s+de))"
    # + rf"|\s*{RE_CAD_MARSEILLE}"  # (inopérant?) borne droite <ref parcelle> (seulement Marseille, expression longue sans grand risque de faux positif)
    # cas balai EOS (end of string): pour le moment, requiert une regex spécifique à certains appels
    # + r"|$"  # (effets indésirables) cas balai: fin de la zone de texte (nécessaire pour ré-extraire une adresse à partir de l'adresse brute)
    + r")"
)
# n'importe quelle suite de caractères, vides ou non, jusqu'à un séparateur ou un code postal
# NB: "chemin de X *à* Y" (interférence avec "à" comme borne) est géré dans RE_VOIE
# TODO gérer "15 *à* 21 avenue de..." (interférence avec "à" comme borne)
# v1: RE_NOM_VOIE = rf"""(?:{RE_TOK}(?:[\s-]{RE_TOK})*)"""
# v2: RE_NOM_VOIE = r"[\S\s]+?"  # "+?" délimité par une lookahead assertion dans la regex englobante
RE_NOM_VOIE = (
    rf"{RE_NOSEP}+"
    + rf"(?:"
    + rf"{RE_SEP}+"
    + r"(?!(?:Nous|Le\s+maire|Vu|Consid[ée]rant|Article|Propriété\s+de|parcelle|cadastr[ée]))"  # negative lookahead: éviter de capturer n'importe quoi
    + rf"{RE_NOSEP}+)*?"  # (?!{RE_CP}) (avant 2e RE_NOSEP)
)

# TODO s'arrêter quand on rencontre une référence cadastrale (lookahead?)
RE_COMMUNE = (
    r"(?:"
    # communes de la métropole AMP (y compris arrondissements de Marseille), dans leurs variantes de graphie
    + RE_COMMUNES_AMP_ALLFORMS
    # générique, pour communes hors métropole AMP
    + r"|(?:"
    + r"(?!\s*(?:Nous|Le\s+maire|Vu|Consid[ée]rant|Article|Propriété\s+de|parcelle|cadastr[ée]|effectué|figurant))"  # negative lookahead: éviter de capturer n'importe quoi
    + rf"[A-ZÀ-Ý]{RE_LETTERS}"  # au moins 1 token qui commence par une majuscule
    + r"(?:"
    + r"['’\s-]"  # séparateur: tiret, apostrophe, espace
    + r"(?!\s*(?:Nous|Le\s+maire|Vu|Consid[ée]rant|Article|Propriété\s+de|parcelle|cadastr[ée]|effectué|figurant))"  # negative lookahead: éviter de capturer n'importe quoi
    + rf"{RE_LETTERS}"
    + r"){0,4}"  # + 0 à 3 tokens après séparateur
    + r")"
    # fin générique
    + r")"
)  # r"""[^,;]+"""  # 1 à 4 tokens au total

# complément d'adresse: résidence (+ bât ou immeuble)
RE_RESID = r"(?<![^\s,-])(?:r[ée]sidence|cit[ée]|parc)(?=\s)"
RE_BAT = (
    r"(?:B[âa]timent(s)?|B[âa]t|Immeuble(s)?|Villa|Mas)"  # 2023-03-12: (?:s)? mais n'apporte rien?
    + r"(?!\s+"  # negative lookahead qui commence par des espaces
    + r"(?:"  # alternative
    + r"sis(e|es)?"  # bâtiment|immeuble sis
    + r"|menaçant"  # bâtiment|immeuble menaçant (ruine)
    + r")"  # fin alternative
    + r")"  # fin negative lookahead
)
RE_APT = r"(?:Appartement|Appart|Apt)"

# éléments possibles de complément d'adresse
# FIXME le lookahead empêche de capturer les compléments d'adresses courtes, sans code postal ni séparateur (ex: "28 BOULEVARD DE LA LIBÉRATION BÂTIMENTS A ET B")
# FIXME empêcher de capturer un nom de commune connu?
RE_ADR_COMPL_ELT = (
    r"(?:"  # groupe global
    + r"(?:"
    # + r"(?!^(?:Nous|Le\s+maire|Vu|Consid[ée]rant|Article|Propriété\s+de))"  # negative lookahead: éviter de capturer n'importe quoi  # 2023-04-11: inopérant?
    # cas particulier
    + r"(?:Les\s+Docks\s+Atrium\s+[\d.]+)"  # grand immeuble de bureaux
    + r"|(?:(?:Le\s+)?Gyptis(?:\s+I)?)"  # grand immeuble de logement
    #
    + r"|(?:Immeuble\s+sur\s+rue)"  # désignation de bâtiment sur la parcelle
    + r"|(?:garage)"  # désignation de bâtiment sur la parcelle
    + r"|(?:[(][^)]+\s+selon\s+cadastre[)])"  # ex: "12 rue X (18 selon cadastre)"  # FIXME rattacher plutôt au NUM_IND_VOIE
    # motif général
    + rf"|(?:{RE_RESID}|{RE_BAT}|{RE_APT})"  # résidence | bâtiment | appartement
    + r"\s*[^,–]*?"  # \s*[^,–]+ # contenu: nom de résidence, du bâtiment, de l'appartement...
    + r")"
    + r")"
    # FIXME le lookahead ne fonctionne pas parfaitement ; il faut peut-être faire autrement (ex: 2e routine qui cherche un code postal et retire tout ce qui est à droite)
    # FIXME ex: "26-28 RUE DE LA BUTINEUSE / 75-83 TRAVERSE DU MOULIN À VENT BATIMENT B - 13015"
    # (NB: c'est une "lookahead assertion", qui ne consomme pas les caractères)
    + r"(?="
    # éventuellement des espaces puis obligatoirement l'un des motifs suivants:
    + r"(?:"
    + r"\s*,\s+"  # séparateur "," (ex: 2 rue xxx[,] 13420 GEMENOS)
    + rf"|(\s*[-–])?\s*{RE_CP}"  # code postal
    + r"|\s*–\s*"  # séparateur "–"
    + r"|\s+-\s+"  # séparateur "-"
    # + r"|\s*[/]\s*"  # séparateur "/" (double adresse: "2 rue X / 31 rue Y 13001 Marseille")
    # + r"|\s+et\s+"  # séparateur "et" (double adresse: "2 rue X et 31 rue Y 13001 Marseille")
    + rf"|(?:\s*(?:{RE_NUM_IND_LIST})(?:\s*,)?\s+(?:la\s+Can[n]?ebi[èe]re|grand(e)?\s+rue|{RE_TYP_VOIE}))"  # on bute directement sur une 2e adresse (rare mais ça arrive)
    # + r"|(?:\s+[àa]\s+(?!vent\s+))"  # à : "2 rue xxx à GEMENOS|Roquevaire" (rare, utile mais source potentielle de confusion avec les noms de voie "chemin de X à Y")
    + r")"
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
    r"("
    # cas particulier: la canebière
    + r"(?:la\s+Can[n]?ebi[èe]re)"  # inclut l'ancienne graphie "nn"
    # exception: grand(e) rue
    + r"|(?:grand(e)?\s+rue)"
    # cas particulier: nom "double" avec un tiret ou slash (qui sinon est considéré comme séparateur avec un complément d'adresse ou une commune)
    + r"|(?:place\s+de\s+l['’\s][ée]glise\s+[-/]\s+Fran[çc]ois\s+Maleterre)"
    + r"|(?:place\s+de\s+Strasbourg\s+[-/]\s+Paul\s+Cermolacce)"
    # cas particulier: chemin de X à Y (nécessaire car "à" est une des bornes droites de RE_NOM_VOIE)
    + r"|(?:chemin\s+de\s+"
    + r"(?:"
    + r"(?:la\s+Valbarelle\s+[àa]\s+Saint\s+Marcel)"
    + r"|(?:Saint\s+Antoine\s+[àa]\s+Saint\s+Joseph)"
    + r"|(?:Saint\s+Louis\s+au\s+Rove)"
    + r"|(?:Saint\s+Menet\s+aux\s+Accates)"
    + r")"
    + r")"  # fin "chemin de X à Y"
    # motif générique: <type_voie> <nom_voie> (lookahead pour délimiter le <nom_voie>)
    + rf"|(({RE_TYP_VOIE})\s+({RE_NOM_VOIE}(?={RE_NOM_VOIE_RCONT})))"
    + r")"
)
# inutilisé
# P_VOIE = re.compile(RE_VOIE, re.IGNORECASE | re.MULTILINE)

# numéro, indicateur et voie
RE_NUM_IND_VOIE = (
    r"("
    + rf"(?:(?:{RE_NUM_IND_LIST})(?:\s*,)?\s+)?"  # numéro et indice de répétition (ex: 1 bis)  # ?P<num_ind_list>
    + rf"{RE_VOIE}"  # type et nom de la voie (ex: rue Jean Roques ; la Canebière)  # ?P<voie>
    + r")"
)
# FIXME ajouter champ: + r"|(?:[(][^)]+\s+selon\s+cadastre[)])"  # ex: "12 rue X (18 selon cadastre)"  # FIXME rattacher plutôt au NUM_IND_VOIE

# inutilisé
# P_NUM_IND_VOIE = re.compile(RE_NUM_IND_VOIE, re.IGNORECASE | re.MULTILINE)

# idem, avec named groups
RE_NUM_IND_VOIE_NG = (
    r"(?:"
    + rf"(?:(?P<num_ind_list>{RE_NUM_IND_LIST})(?:\s*,)?\s+)?"  # numéro et indice de répétition (ex: 1 bis)
    + rf"(?P<voie>{RE_VOIE})"  # type et nom de la voie (ex: rue Jean Roques ; la Canebière)
    + r")"
)
# utilisé dans process_adresse_brute()
P_NUM_IND_VOIE_NG = re.compile(RE_NUM_IND_VOIE_NG, re.IGNORECASE | re.MULTILINE)


# liste d'adresses courtes: numéro, indicateur et voie
RE_NUM_IND_VOIE_LIST = (
    r"("
    # au moins 1 adresse avec voie et éventuellement numéro et indicateur
    + RE_NUM_IND_VOIE
    # plus éventuellement 1 à plusieurs adresses supplémentaires
    + r"(?:"
    + r"(?:(?:\s*[,/–-]\s*)|(?:\s+et\s+)|(?:\s+))"  # séparateur (parfois juste "\s+" !)
    + r"(?:angle\s+)?"  # optionnel: 2 rue X / angle rue Y
    + RE_NUM_IND_VOIE
    + r")*"  # 0 à N adresses supplémentaires
    + r")"
)
P_NUM_IND_VOIE_LIST = re.compile(RE_NUM_IND_VOIE_LIST, re.IGNORECASE | re.MULTILINE)

# TODO double adresse: 2 rue X / 31 rue Y 13001 Marseille (RE distincte, pour les named groups)
# TODO "parcelle (cadastrée) ..." entre le num_ind_voie et cp_commune
RE_ADRESSE = (
    r"(?:"
    + rf"((?:{RE_ADR_COMPL})(?:\s*[,–-])?\s*)?"  # WIP (optionnel) complément d'adresse (pré)
    + RE_NUM_IND_VOIE_LIST
    + rf"((?:\s*[,–-])?\s*(?:{RE_ADR_COMPL}))?"  # WIP (optionnel) complément d'adresse (post)
    + r"(?:\s*"  # (optionnel; non capturé) référence cadastrale (préfixe)
    + r"(?:"  # référence cadastrale: alternatives
    + r"(?:[({]cadastré[^)}]+?[)}])"  # (cadastré <ref_cad>)
    + rf"|(?:[–-]\s+parcelle\s+{RE_NO}\s*{RE_CAD_SECNUM})"  # - parcelle n°<ref_cad> -
    + r")"
    + r")?"
    + r"("  # (optionnel) code postal et/ou commune
    + r"(?:(?:(?:\s*[,;.–-])+|(?:\s+[àa](?=\s))))?"  # ex: 2 rue xxx[,] 13420 GEMENOS
    + rf"(?:\s*({RE_CP}))?"  # \s+  # sinon: \s*–\s+ | ...  # optionnel code postal
    + rf"(?:\s*({RE_COMMUNE}))?"  # optionnel commune
    + r")?"  # fin optionnel code postal et/ou commune
    + r")"
)
# inutilisé
# P_ADRESSE = re.compile(RE_ADRESSE, re.MULTILINE | re.IGNORECASE)

# idem, avec named groups + une garde / "voiture balai" dans le lookahead du nom de voie ;
# la garde est nécessaire pour capturer les adresses courtes, qui se terminent par le nom
# de la voie, car si on applique l'expression NG à une zone déjà extraite, alors le
# contexte droit attendu dans le positive lookahead (séparateur, code postal, nom de commune)
# n'est plus accessible
RE_ADRESSE_NG = (
    r"(?:"
    + rf"(?:(?P<compl_ini>{RE_ADR_COMPL})(?:\s*[,–-])?\s*)?"  # WIP (optionnel complément d'adresse (pré)
    + rf"(?P<num_ind_voie_list>{RE_NUM_IND_VOIE_LIST})"  # 1 à N adresses courtes (numéro, indicateur, voie)
    + rf"(?:(?:\s*[,–-])?\s*(?P<compl_fin>{RE_ADR_COMPL}))?"  # WIP (optionnel) complément d'adresse (post)
    + r"(?:\s*"  # (optionnel; non capturé) référence cadastrale (préfixe)
    + r"(?P<cad>"  # référence cadastrale: alternatives
    + r"(?:[({]cadastré[^)}]+?[)}])"  # (cadastré <ref_cad>)
    + rf"|(?:[–-]\s+parcelle\s+{RE_NO}\s*{RE_CAD_SECNUM})"  # - parcelle n°... -
    + r")"
    + r")?"  #
    + r"(?:"  # (optionnel) code postal et/ou commune
    + r"(?P<sep>(?:(?:\s*[,;.–-])+|(?:\s+[àa](?=\s))))?"  # ex: 2 rue xxx[,] 13420 GEMENOS
    + rf"(?:\s*(?P<code_postal>{RE_CP}))?"  # \s+  # sinon: \s*–\s+ | ...  # optionnel code postal
    + rf"(?:\s*(?P<commune>{RE_COMMUNE}))?"  # optionnel commune
    + r")?"  # fin optionnel code postal et/ou commune
    + r")"
)
P_ADRESSE_NG = re.compile(RE_ADRESSE_NG, re.MULTILINE | re.IGNORECASE)


def create_adresse_normalisee(
    adr_num: str,
    adr_ind: str,
    adr_voie: str,
    adr_compl: str,
    adr_cpostal: str,
    adr_ville: str,
) -> str:
    """Créer une adresse normalisée.

    L'adresse normalisée rassemble les champs extraits de l'adresse brute, et ailleurs
    dans le document si nécessaire (eg. autorité prenant l'arrêté, template).

    Parameters
    ----------
    adr_num: str
        Numéro de l'adresse
    adr_ind: str
        Indice de l'adresse
    adr_voie: str
        Nom de la voie (incluant le type)
    adr_compl: str
        Complément d'adresse
    adr_cpostal: str
        Code postal
    adr_ville: str
        Commune

    Returns
    -------
    adr_norm: str
        Adresse normalisée
    """
    adr_norm_parts = [
        adr_num,
        adr_ind,
        adr_voie,
        adr_compl,
        adr_cpostal,
        adr_ville,
    ]
    adr_norm = " ".join(
        x for x in adr_norm_parts if pd.notna(x)
    )  # TODO normaliser la graphie?
    adr_norm = normalize_string(adr_norm, num=True, apos=True, hyph=True, spaces=True)
    return adr_norm


def process_adresse_brute(adr_ad_brute: str) -> List[Dict]:
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
    if adr_ad_brute is None:
        adr_fields = {
            "adr_num": None,
            "adr_ind": None,
            "adr_voie": None,
            "adr_compl": None,
            "adr_cpostal": None,
            "adr_ville": None,
        }
        # TODO liste contenant un seul dict aux champs tous None, ou liste vide (à gérer) ?
        return [adr_fields]

    adresses = []
    m_adresse = P_ADRESSE_NG.match(adr_ad_brute)  # was: ".search()"
    if not m_adresse:
        # retenter de chercher une adresse, après avoir ajouté une butée pour le lookahead
        # FIXME contournement sale
        adr_ad_brute = adr_ad_brute + " - "
        m_adresse = P_ADRESSE_NG.match(adr_ad_brute)  # was: .search()
    # si toujours aucune adresse extraite, on renvoie aussi une liste contenant une unique adresse vide
    if not m_adresse:
        logging.error(f"aucune adresse extraite de {adr_ad_brute} par P_ADRESSE_NG")
        # TODO factoriser avec le cas adr_ad_brute is None
        adr_fields = {
            "adr_num": None,
            "adr_ind": None,
            "adr_voie": None,
            "adr_compl": None,
            "adr_cpostal": None,
            "adr_ville": None,
        }
        # TODO liste contenant un seul dict aux champs tous None, ou liste vide (à gérer) ?
        return [adr_fields]

    logging.warning(
        f"process_adresse_brute: {m_adresse.group(0)}\n{m_adresse.groups()}\n{m_adresse.groupdict()}"
    )
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

    # extraire la ou les adresses courtes, et les séparer s'il y en a plusieurs
    # on est obligé de réextraire depuis l'adresse brute, car le RE_VOIE est défini
    # avec un contexte droit (positive lookahead)
    # (pénible, mais pour le moment ça fonctionne comme ça)
    adr_lists = list(P_NUM_IND_VOIE_LIST.finditer(adr_ad_brute))
    # obligatoire: une liste d'adresses courtes (ou une adresse courte)
    try:
        assert len(adr_lists) >= 1
    except AssertionError:
        raise ValueError(f"Aucune adresse courte détectée dans {adr_ad_brute}")
    # on vérifie qu'on travaille exactement au même endroit, pour se positionner au bon endroit
    try:
        assert adr_lists[0].group(0) == m_adresse["num_ind_voie_list"]
    except AssertionError:
        raise ValueError(
            f"Problème sur {m_adresse.groupdict()}\nadr_list.group(0): {adr_lists[0].group(0)} ; {m_adresse['num_ind_voie_list']}"
        )
    for adr_list in adr_lists:
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
                    "adr_ville": commune,
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
                            "adr_ville": commune,
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
                                "adr_ville": commune,
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


# - adresse
# contexte droit (lookahead) possible pour une adresse de document
RE_ADR_RCONT = (
    r"(?:"
    + r"section|référence|cadastré|(?<!figurant\sau)cadastre|situé"  # was: "parcelle|"...
    + r"|concernant|concerné"
    + r"|à\s+l[’']exception"
    + r"|à\s+leur\s+jonction"
    + r"|ainsi[,]?(?:\s+que)?"
    + r"|appartenant"  # NEW 2023-03-11
    + r"|assorti"
    + r"|avec\s+risque"
    + r"|ce\s+diagnostic"
    + r"|ces\s+derniers"
    + r"|condamner"
    + r"|copropriété"
    + r"|de\s+(?:mettre\s+fin|constater)"
    + r"|depuis"
    + r"|effectué"
    + r"|établi"
    + r"|(?:doit|doivent|devra|devront|il\s+devra|peut|peuvent)\s+(être|exploiter|prendre|(?:dans|sous)\s+un\s+délai)"
    + r"|(?:est|sont)\s+(?:à\s+l['’]état|de\s+nouveau|dans|à)"
    + r"|(?:est|sont)\s+(?:mis\s+en\s+demeure)"
    + r"|(?:est|sont|reste|restent)\s+((strictement\s+)?interdit|accessible|pris)"  # (?:e|s|es)?
    + r"|(?:(?:est|sont|ont\s+été|est\s+de|doit|doivent)$)"
    + r"|et(?:\s+à\s+en)?\s+interdire"
    + r"|et\s+au\s+cabinet"
    + r"|et\s+(?:concerné|donnant\s+sur)"
    + r"|et\s+de\s+l['’]appartement"  # la fin du motif évite de capturer "rue Roug*et de *Lisle"
    + r"|et\s+des\s+risques"
    + r"|et\s+installation"
    # + r"|et\s+l['’]immeuble"  # 2023-03-11
    + rf"|et\s+l['’]"  # {RE_ARRETE}"
    + r"|(?:et\s+(?:l['’]\s*|son\s+))?occupation"
    + r"|et\s+notamment"
    + r"|et\s+ordonne"
    + r"|et\s+repr[ée]sentant"
    + r"|et\s+sur\s+l"
    + r"|étaiement"
    + r"|évacuation"
    + r"|faire\s+réaliser"
    + r"|figurant"
    + r"|fragilisé"  # 2023-03-11
    + r"|il\s+sera"
    + r"|jusqu['’](?:au|à)"  # 2023-03-11
    + r"|le\s+rapport"
    + r"|leur\s+demandant"
    + r"|lors\s+de"
    + r"|menace\s+de"
    + r"|mentionné"
    + r"|mettant\s+fin"
    + r"|^Nomenclature\s+ACTES"
    + r"|n['’](?:a|ont)\s+pas"
    + r"|ne\s+présente"
    + rf"|{RE_NO}"  # WIP 2023-03-12
    + r"|ont\s+été\s+évacués"
    + r"|permettant"
    + r"|(?:pour$)"
    + r"|préconise"  # 2023-03-11
    + r"|présence\s+de"
    + r"|présente"
    + r"|pris\s+en\s+l"
    + r"|(?:pris$)"
    + r"|propri[ée]taire"
    + r"|qui\s+se\s+retrouve"
    + r"|réalisé"
    + r"|représenté"
    + r"|selon\s+les\s+hachures"
    + r"|signé"
    + r"|sur\s+une\s+largeur"
    + r"|sur\s+la\s+(?:base|parcelle)"
    + r"|susceptible"
    + r"|suivant\s+annexe"
    # + r"|(?:[.]$)"  # RESUME HERE
    + r"|(?:^Nous,\s*)|(?:^le\s+maire)|(?:^vu)|(?:^consid[ée]rant)|(?:^article)|(?:^Propri[ée]t[ée]\s+de)"  # NEW 2023-03-29 "le maire"
    + r")"
)

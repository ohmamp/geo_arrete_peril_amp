"""Reconnaissance générique des adresses.

"""

import re

# TODO gérer "106-108 rue X (102-104 selon cadastre)"

# codes postaux de Marseille
# à conserver même quand il y aura une table CSV de codes postaux ;
# cette liste permet de changer de stratégie de reconnaissance des parcelles cadastrales
# (à Marseille: références longues incluant l'arrondissement et le quartier)
CP_MARSEILLE = [f"130{i:02}" for i in range(1, 17)]

# regex générique pour ce qu'on considérera comme un "token" (plus ou moins, un mot) dans un nom de voie ou de commune
RE_TOK = r"[^,;:–(\s]+"

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
    r"(?:all[ée]e[s]?"
    + r"|avenue"
    + r"|boulevard|bd"
    + r"|(?:ancien\s*)?chemin"
    + r"|cours"
    + r"|domaine"
    + r"|impasse"
    + r"|mont[ée]e"
    + r"|place"
    + r"|quai"
    + r"|route"
    + r"|rue"
    # + r"|voie"  # negative lookahead: \s(?:publique|de\scirculation|d['’]effondrement|d'['’]affichage|sur|le\slong|allant|précitée|administrative|électronique|dématérialisée|de\srecours|de\sconséquence|...)
    + r"|traverse)"
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
    + r"|\s+à\s+"  # à : "2 rue xxx à GEMENOS|Roquevaire" (rare, utile mais source potentielle de confusion avec les noms de voie "chemin de X à Y")
    + rf"|\s*{RE_CP}"  # code postal
    + r")"
)

# TODO s'arrêter quand on rencontre une référence cadastrale (lookahead?)
RE_COMMUNE = (
    rf"[A-Z]{RE_TOK}"  # au moins 1 token qui commence par une majuscule
    + r"(?:[ -]"
    + rf"{RE_TOK}"
    + r"){0,4}"  # + 0 à 3 tokens séparés par espace ou tiret
)  # r"""[^,;]+"""  # 1 à 4 tokens séparés par des espaces?

# complément d'adresse: résidence (+ bât ou immeuble)
RE_RESID = (
    r"(?:r[ée]sidence|cit[ée])\s+[^,–]+"
    + r"(?:"
    + r"(?:\s+[,–-])?"  # séparateur optionnel
    + r"\s+(?:B[âa]timent|B[âa]t|Immeuble)\s*[^,–]+"
    + r")?"  # fin bat/imm optionnel
    + r"(?:"
    + r"(?:\s+[,–-])?"  # séparateur optionnel
    + r"\s+(?:Appartement|Appart|Apt)\s*[^,–]+"
    + r")?"  # fin bat/imm optionnel
)

RE_BAT = r"(?:B[âa]timent|B[âa]t|Immeuble)\s*[^,–]+"

RE_APT = r"(?:Appartement|Appart|Apt)\s*[^,–]+"

RE_ADR_COMPL = (
    r"(?:"  # optionnel
    + rf"{RE_BAT}|{RE_APT}"  # bâtiment | appartement
    + r"(?:\s*[,–-]\s*)?"  # séparateur optionnel
    + r")?"  # fin optionnel
    + r"(?:"  # optionnel
    + rf"{RE_BAT}|{RE_APT}"  # bâtiment | appartement
    + r"(?:\s*[,–-]\s*)?"  # séparateur optionnel
    + r")?"  # fin optionnel
    + rf"{RE_RESID}"  # résidence: obligatoire (arbitrairement décidé)
    + r"(?:"  # optionnel
    + r"(?:\s*[,–-]\s*)?"  # séparateur optionnel
    + rf"{RE_BAT}|{RE_APT}"  # bâtiment | appartement
    + r")*"  # fin optionnel
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
    + rf"(?:(?:{RE_NUM_IND_LIST})[,]?\s+)?"  # numéro et indice de répétition (ex: 1 bis)  # ?P<num_ind_list>
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
    + rf"(?:(?:{RE_ADR_COMPL})(?:\s*[,–-]\s*)?)?"  # WIP (optionnel) complément d'adresse (pré)
    + RE_NUM_IND_VOIE_LIST
    + rf"(?:(?:\s*[,–-]\s*)?(?:{RE_ADR_COMPL}))?"  # WIP (optionnel) complément d'adresse (post)
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

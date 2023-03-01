"""Reconnaissance générique des adresses.

"""

import re


# codes postaux de Marseille
# à conserver même quand il y aura une table CSV de codes postaux ;
# cette liste permet de changer de stratégie de reconnaissance des parcelles cadastrales
# (à Marseille: références longues incluant l'arrondissement et le quartier)
CP_MARSEILLE = [f"130{i:02}" for i in range(1, 17)]

# regex générique pour ce qu'on considérera comme un "token" (plus ou moins, un mot) dans un nom de voie ou de commune
RE_TOK = r"""[^,;:–(\s]+"""

# TODO comment gérer plusieurs numéros? ex: "10-12-14 boulevard ...""
# pour le moment on ne garde que le premier
RE_NUM_IND_VOIE = (
    r"""(?P<num_voie>\d+)(\s*[,-/]\s*\d+)*(\s+et\s+\d+)?"""
    + r"""(?:\s?(?P<ind_voie>A|bis|ter))?"""
)
RE_TYP_VOIE = (
    r"""(?:avenue|boulevard|bd|(?:ancien\s*)?chemin|cours|impasse|place|rue|traverse)"""
)

# code postal
RE_CP = r"""\d{5}"""

# RE_NOM_VOIE = rf"""(?:{RE_TOK}(?:[\s-]{RE_TOK})*)"""
RE_NOM_VOIE = (
    r"[\s\S]+?"  # n'importe quelle suite de caractères, vides ou non, jusqu'à un séparateur ou un code postal
    # (NB: c'est une "lookahead assertion", qui ne consomme pas les caractères)
    + r"(?=\s*,\s+|\s*–\s*|\s+-\s+"  # séparateurs: ,-– (ex: 2 rue xxx[,] 13420 GEMENOS)
    + r"|\s+à\s+"  # à : "2 rue xxx à GEMENOS" (rare et source potentielle de confusion, à valider)
    + rf"|\s*{RE_CP}"  # code postal
    + r")"
)
RE_COMMUNE = (
    rf"[A-Z]{RE_TOK}"  # au moins 1 token qui commence par une majuscule
    + r"(?:[ -]"
    + rf"{RE_TOK}"
    + r"){0,4}"  # + 0 à 3 tokens séparés par espace ou tiret
)  # r"""[^,;]+"""  # 1 à 4 tokens séparés par des espaces?

# complément d'adresse: résidence (+ bât ou immeuble)
RE_RESID = (
    r"r[ée]sidence\s+[^,–]+"
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

# contextes: "objet:" (objet de l'arrêté),
# TODO ajouter du contexte pour être plus précis? "désordres sur le bâtiment sis... ?"
RE_ADRESSE = (
    r"""(?:"""
    + rf"(?:(?P<compl_ini>{RE_ADR_COMPL})(?:\s*[,–-]\s*)?)?"  # WIP complément d'adresse
    + rf"(?P<num_ind_voie>{RE_NUM_IND_VOIE})[,]?\s+)?"
    + rf"(?P<type_voie>{RE_TYP_VOIE})"
    + rf"\s+(?P<nom_voie>{RE_NOM_VOIE})"
    + r"(?:"  # optionnel: complément d'adresse (post)
    + r"(?:\s*[,–-]\s*)?"
    + rf"(?P<compl_fin>{RE_ADR_COMPL})"
    + r")?"  # fin complément d'adresse
    + r"(?:"
    + r"(?:(?:\s*[,–-])|(?:\s+à))?"  # ex: 2 rue xxx[,] 13420 GEMENOS
    + r"\s+"  # sinon: \s*–\s+ | ...
    + r"(?:"
    + rf"(?P<code_postal>{RE_CP})"
    + r"\s+)?"
    + rf"(?P<commune>{RE_COMMUNE})?"  # WIP: ?  # RESUME HERE
    + r")?"
)
M_ADRESSE = re.compile(RE_ADRESSE, re.MULTILINE | re.IGNORECASE)

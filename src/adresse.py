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
    r"""(?P<num_voie>\d+)([,-/]\d+)*(\s+et\s+\d+)?"""
    + r"""(?:\s?(?P<ind_voie>A|bis|ter))?"""
)
RE_TYP_VOIE = r"""(?:avenue|boulevard|cours|impasse|place|rue|traverse)"""
RE_NOM_VOIE = rf"""(?:{RE_TOK}(?:\s+{RE_TOK})*)"""
RE_CP = r"""\d{5}"""
RE_COMMUNE = (
    rf"{RE_TOK}(?:[ ]{RE_TOK})" + r"{0,2}"
)  # r"""[^,;]+"""  # 1 à 3 tokens séparés par des espaces?

# contextes: "objet:" (objet de l'arrêté),
# TODO ajouter du contexte pour être plus précis? "désordres sur le bâtiment sis... ?"
RE_ADRESSE = (
    r"""(?:"""
    + rf"""(?P<num_ind_voie>{RE_NUM_IND_VOIE})[,]?\s+)?"""
    + rf"""(?P<type_voie>{RE_TYP_VOIE})"""
    + rf"""\s+(?P<nom_voie>{RE_NOM_VOIE})"""
    # TODO complément d'adresse ?
    + r"""(?:"""
    + r"""(?:(?:\s*[,–])|(?:\s+à))?"""  # ex: 2 rue xxx[,] 13420 GEMENOS
    + r"""\s+"""
    + r"""(?:"""
    + rf"""(?P<code_postal>{RE_CP})"""
    + r"""\s+)?"""
    + rf"""(?P<commune>{RE_COMMUNE})"""
    + r""")?"""
)
M_ADRESSE = re.compile(RE_ADRESSE, re.MULTILINE | re.IGNORECASE)

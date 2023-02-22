"""Modèles de documents des arrêtés.

Motifs de reconnaissance des en-têtes, pieds-de-page et annexes.
"""

import re


# en-têtes
RE_HEADERS = [
    # texte natif
    (
        "Marseille",
        r"""^Le\s+Maire\nAncien\s+Ministre\nVice-président\s+honoraire\s+du\s+Sénat$""",
    ),  # p.1 (.. - 2020-07-04)
    ("Marseille", r"""^La\s+Maire$"""),  # p.1 (2020-07-04 - 2020-12-21)
    ("Marseille", r"""^Le\s+Maire$"""),  # p.1 (2020-12-21 - ..)
    # texte extrait (image)
    (
        "Allauch",
        r"""^DEPARTEMENT\s+DES\nBOUCHES\s+DU\s+RHONE\n\nAllauch\n\nun\s+certain\s+art\s+de\s+ville""",
    ),  # p.1, logo en haut à gauche
    # ("Allauch", r""""""),  # p.2 et suiv.: num de page (-2-, -3-...)
    (
        "Châteauneuf-les-Martigues",
        r"""^[CG]ommune\s+de\s+Châteauneuf-les-Martigues\s+-\s+"""
        + r"""Arrondissement\s+d'[Il]stres\s+-\s+"""
        + r"""Bouches\s+du\s+Rhône""",
    ),  # p.1, OCR à refaire?
    (
        "Gardanne",
        r"""Arrêté\s+n°\d{4}-\d{2}-ARR-SIHI\s+""" + r"""Page\s+\d{1,2}/\d{1,2}""",
    ),  # p.2 et suiv
]
# TODO en-tête Aix-en-Provence p. 2 et suivantes: numéro de page (en haut à droite)

# reconnaissance de tous les en-têtes
RE_HEADER = r"(?P<header>" + r"|".join(r"(?:" + x + r")" for _, x in RE_HEADERS) + r")"
P_HEADER = re.compile(RE_HEADER, flags=re.MULTILINE | re.IGNORECASE | re.VERBOSE)


# pied-de-page
RE_FOOTERS = [
    (
        "Marseille",
        r"""^Ville\s+de\s+Marseille,\s+2\s+quai\s+du\s+Port\s+[–-]\s+13233\s+MARSEILLE\s+CEDEX\s+20""",
    ),  #
    ("Marseille", r"""^\d{1,2}/\d{1,2}$"""),  # numéro de page
    (
        "Aix-en-Provence",
        r"""^Hotel\s+de\s+Ville\s+13616\s+AIX-EN-PROVENCE\s+CEDEX\s+1\s+-\s+France\s+-\s+"""
        + r"""Tél[.]\s+[+]\s+33[(]0[)]4[.]42[.]91[.]90[.]00\s+-\s+"""
        + r"""Télécopie\s+[+]\s+33[(]0[)]4[.]42[.]91[.]94[.]92\s+-\s+"""
        + r"""www[.]mairie[-]aixenprovence[.]fr"""
        + r"""[.]$""",
    ),  #
    (
        "Allauch",
        r"""Hôtel\s+de\s+Ville\s+[+e]\s+"""
        + r"""Place\s+Pierre\s+Bellot\s+[+e]\s+"""
        + r"""BP\s+27\s+[+e]\s+"""
        + r"""13718\s+Allauch\s+cedex\s+[+e]\s+"""
        + r"""Tél[.]\s+04\s+91\s+10\s+48\s+00\s+[+e]\s+"""
        + r"""Fax\s+04\s+91\s+10\s+48\s+23"""
        + r"""\n"""
        + r"""Web\s+[:]\s+http[:]//www[.]allauch[.]com\s+[+e]\s+"""
        + r"""Courriel\s+[:]\s+info@allauch[.]com""",
    ),  # p.1
    # TODO Allauch footer p.1 à -2 : ".../..."
    # TODO Allauch footer p.2 à -1 : réf arrêté
    (
        "Aubagne",
        r"""Hôtel\s+de\s+Ville\s+"""
        + r"""BP\s+41465\s+13785\s+Aubagne\s+Cedex\s+"""
        + r"""T\s*04\s*42\s*18\s*19\s*19\s+"""
        + r"""F\s*04\s*42\s*18\s*18\s*18\s+"""
        + r"""www[.]aubagne[.]fr$""",
    ),  # p.1
    ("Auriol", r"""Page\s+\d{1,2}\s+sur\s+\d{1,2}$"""),
    (
        "Châteauneuf-les-Martigues",
        r"""Hôtel\s+de\s+ville\s+-\s+"""
        + r"""BP\s+70024\s+-\s+"""
        + r"""13168\s+Châteauneuf-les-Martigues\s+cedex\s+-\s+"""
        + r"""04\.42\.76\.89\.00\s+-\s+"""
        + r"""04\.42\.79\.80\.25$""",
    ),  # p. 1
    # TODO footer Istres
]

# reconnaissance de tous les pieds-de-page
RE_FOOTER = r"(?P<footer>" + r"|".join(r"(" + x + r")" for _, x in RE_FOOTERS) + r")"
P_FOOTER = re.compile(RE_FOOTER, flags=re.MULTILINE | re.IGNORECASE | re.VERBOSE)

# TODO annexes

"""Modèles de documents des arrêtés.

Motifs de reconnaissance des en-têtes, pieds-de-page et annexes.
"""

import re

from src.utils.text_utils import RE_NO

# en-têtes
RE_HEADERS = [
    # texte natif
    (
        "Marseille",
        r"^Le\s+Maire\nAncien\s+Ministre\nVice-président\s+honoraire\s+du\s+Sénat$",
    ),  # p.1 (.. - 2020-07-04)
    ("Marseille", r"^La\s+Maire$"),  # p.1 (2020-07-04 - 2020-12-21)
    ("Marseille", r"^Le\s+Maire$"),  # p.1 (2020-12-21 - ..)
    (
        "Aix-en-Provence",
        (
            r"(?:"
            + r"DEPARTEMENT\s+OPERATIONS\s+JURIDIQUES\s+COMPLEXES\s+"
            + r"ET\s+CONTROLE\s+ET\s+SUIVI\s+DES\s+PROCEDURES\s+CONTENTIEUSES\n"
            + r"|SECRETARIAT\s+GENERAL\n"
            + r")"
            + r"Direction\s+Etudes\s+Juridiques\s+&\s+Contentieux\n"
        ),
    ),  # p.1
    # ("Aix-en-Provence", r"^ARRÊTÉ\n"),  # NON! trop générique, capture des spans nécessaires ailleurs
    # texte extrait (image)
    (
        "Allauch",
        r"^DEPARTEMENT\s+DES\nBOUCHES\s+DU\s+RHONE\n\nAllauch\n\nun\s+certain\s+art\s+de\s+ville",
    ),  # p.1, logo en haut à gauche
    # ("Allauch", r""""""),  # p.2 et suiv.: num de page (-2-, -3-...)
    ("Cabriès", r"^EXTRAIT\s+DU\s+REGISTRE\s+DES\s+ARRETES\s+DU\s+MAIRE"),
    ("Cabriès", r"^MAIRIE\s+DE\s+CABRIES"),
    ("Cabriès", r"^Tel\s+:\s+04\.42\.28\.14\.00"),
    ("Cabriès", r"^Fax\s+:\s+04\.42\.28\.14\.20"),
    ("Cabriès", r"^Mail\s+:\s+maire@cabries\.fr"),
    (
        "Châteauneuf-les-Martigues",
        r"^[CG]ommune\s+de\s+Châteauneuf-les-Martigues\s+-\s+"
        + r"Arrondissement\s+d['’][Il]stres\s+-\s+"
        + r"Bouches\s+du\s+Rhône",
    ),  # p.1, OCR à refaire?
    ("Gardanne", r"^Ville\s+de\s+Gardanne$"),  # p. 1
    (
        "Gardanne",
        r"Arrêté\s+" + RE_NO + r"\d{4}-\d{2}-ARR-SIHI\s+" + r"Page\s+\d{1,2}/\d{1,2}",
    ),  # p.2 et suiv
    # TODO vérifier après OCR
    # ("La Ciotat", r"^Ville\s+de\s+La\s+Ciotat$"),  # p. 1
    ("Berre-l'Étang", r"^République\s+Française$"),  # p. 1
    (
        "Gémenos",
        r"^DÉPARTEMENT\nDES\s+BOUCHES-DU-RHÔNE\n",
    ),  # p. 1
    ("Gémenos", r"^Ville\s+de\s+Gémenos$"),  # p. 1
    (
        "Gémenos",
        r"TÉL\s*[:;]\s*04\s+42\s+32\s+89\s+00\n"  # [:;] pour les erreurs d'OCR
        + r"FAX\s*[:;]\s*04\s+42\s+32\s+71\s+41\n"
        + r"www[.-]mairie-gemenos[.-]fr",  # [.-] pour les erreurs d'OCR
    ),  # p. 1
    ("Gémenos", r"^ARRÊTÉ\s+DU\s+MAIRE$"),  # p. 1 (optionnel)
    (
        "Jouques",
        r"^REPUBLIQUE\s+FRANCAISE\n"
        + r"DEPARTEMENT\s+DES\s+BOUCHES\s+DU\s+RHONE\n"
        + r"COMMUNE\s+DE\s+JOUQUES",
    ),  # p. 1 (en haut)
    (
        "Martigues",
        r"^Département\s+des\nBouches-du-Rhône\nArrondissement\s+d['’]Istres$",
    ),  # p. 1
    (
        "Martigues",
        r"^Direction\s+des\s+Affaires\s+Civiles,\nJuridiques\s+et\s+Funéraires\nRéglementation\s+Administrative$",
    ),  # p. 1
    ("Meyrargues", r"^REPUBLIQUE\n\nFRANÇAISE$"),  # p. 1 (en haut à gauche)
    (
        "Meyrargues",
        r"^DEPARTEMENT\s+DES\s+BOUCHES-DU-RHONE\n"
        + r"CANTON\s+DE\s+TRETS\n"
        + r"ARRONDISSEMENT\s+D['’]AIX\s+EN\s+PROVENCE\n"
        + r"METROPOLE\s+D['’]AIX-MARSEILLE-PROVENCE\n"
        + r"\n"
        + r"COMMUNE\s+DE\s+MEYRARGUES\n",
    ),  # p. 1 (en haut à gauche)
    ("Peyrolles-en-Provence", r"^Mairie\s+de\s+Peyrolles-en-Provence$"),  # p. 1
    (
        "Peyrolles-en-Provence",
        r"^Affaire\s+suivie\s+par\s+:\s+[^\n]+\n(?:[^\n]+\n)?",
    ),  # p. 1
    ("Peyrolles-en-Provence", r"^Service\s+:\s+[^\n]+\n(?:[^\n]+\n)?"),  # p. 1
    ("Peyrolles-en-Provence", r"^Tél\s+:\s+\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$"),  # p. 1
    (
        "Roquevaire",
        r"^COMMUNE\s+DE\s+ROQUEVAIRE\n+"
        + r"(?:"
        + r"COMMUNE\s+DE\s+ROQUEVAIRE\n"
        + r"Liberté\s+-\s+Egalité\s+-\s+Fraternité\n+"
        + r")?"
        + r"ARRETE\n+",
    ),  # p. 1
    (
        "Roquevaire",
        r"^Secteur\s+concerné\s+:\s+Libertés\s+publiques\s+et\s+pouvoirs\s+de\s+police$",
    ),  # p. 1 (NB: peut être considéré comme une donnée à extraire dans text_structure)
]
# TODO en-tête Aix-en-Provence p. 2 et suivantes: numéro de page (en haut à droite)

# reconnaissance de tous les en-têtes
RE_HEADER = r"(?P<header>" + r"|".join(r"(?:" + x + r")" for _, x in RE_HEADERS) + r")"
P_HEADER = re.compile(RE_HEADER, flags=re.MULTILINE | re.IGNORECASE | re.VERBOSE)


# pied-de-page
RE_FOOTERS = [
    (
        "Marseille",
        r"^Ville\s+de\s+Marseille,\s+2\s+quai\s+du\s+Port\s+[–-]\s+13233\s+MARSEILLE\s+CEDEX\s+20",
    ),  #
    ("Marseille", r"^\d{1,2}/\d{1,2}$"),  # numéro de page
    (
        "Aix-en-Provence",
        r"^Hotel\s+de\s+Ville\s+13616\s+AIX-EN-PROVENCE\s+CEDEX\s+1\s+-\s+France\s+-\s+"
        + r"Tél[.]\s+[+]\s+33[(]0[)]4[.]42[.]91[.]90[.]00\s+-\s+"
        + r"Télécopie\s+[+]\s+33[(]0[)]4[.]42[.]91[.]94[.]92\s+-\s+"
        + r"www[.]mairie[-]aixenprovence[.]fr"
        + r"[.]$",
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
        "Berre-l'Étang",
        r"VILLE\s+DE\s+BERRE-L['’]ETANG\n"
        + r"HOTEL\s+DE\s+VILLE\s+-\s+B\.P\s+30221\s+-\s+13138\s+BERRE\s+L['’]ÉTANG\s+CEDEX\n"
        + r"Téléphone\s+:\s+04\.42\.74\.93\.00\s+-\s+"
        + r"Télécopie\s+:\s+04\.42\.74\.93\.02\s+-\s+"
        + r"Site\s+internet\s+:\s+www\.berreletang\.fr",
    ),  # p.1
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


# page de bordereau de formalités (en fin de document, Aix-en-Provence)
RE_BORDEREAU = r"^BORDEREAU\s+DE\s+FORMALITES$"
P_BORDEREAU = re.compile(RE_BORDEREAU, flags=re.MULTILINE | re.IGNORECASE)
# TODO annexes

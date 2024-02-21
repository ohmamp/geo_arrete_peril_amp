"""Motifs de reconnaissance des en-têtes, pieds-de-page et annexes.

TODO
- [ ] exploiter les éléments de template (discriminants) pour déterminer la ville (en complément des autres emplacements: autorité, signature)
"""

import re

from src.utils.text_utils import RE_NO

# "République Française" et devise, dans les en-têtes de plusieurs communes
RE_RF = r"R[ée]publique\s+Fran[çc]aise"
RE_RF_DEVISE = r"Libert[ée]\s*[\S]?\s*[EÉ]galit[ée]\s*[\S]?\s*Fraternit[ée]"
# département des Bouches-du-Rhône
RE_DEP_013 = r"(D[ée]partement\s+(des\s+)?)?Bouches\s*[-–]?\s*du\s*[-–]?\s*Rh[ôo]ne"
# arrondissements
RE_ARD_013 = (
    r"Arrondissement\s+"
    + r"(d['’]\s*(Aix\s*[-–]?\s*en\s*[-–]?\s*Provence|Arles|[ÎIl]stres)"
    + r"|de\s+Marseille)"
)

# en-têtes
RE_HEADERS = [
    ("RF", r"^" + RE_RF),
    ("RF", RE_RF + r"$"),
    ("RF", RE_RF_DEVISE),
    # département des bouches du rhône
    ("Dep_013", r"^" + RE_DEP_013),
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
            + r"D[ÉE]PARTEMENT\s+OP[ÉE]RATIONS\s+JURIDIQUES\s+COMPLEXES\s+"
            + r"ET\s+CONTR[ÔO]LE\s+ET\s+SUIVI\s+DES\s+PROC[ÉE]DURES\s+CONTENTIEUSES\n+"
            + r"|SECR[ÉE]TARIAT\s+G[ÉE]N[ÉE]RAL\n+"
            + r")"
            + r"Direction\s+[ÉE]tudes\s+Juridiques\s+&\s+Contentieux\s+"
        ),
    ),  # p.1
    (
        "Aix-en-Provence",
        r"(?:^D\.G\.A\.S\s+[-]\s+[ÉE]tudes\s+Juridiques,\s+March[ée]s\s+Publics\s+et\s+Patrimoine\s+Communal\s+"
        + r"Direction\s+[ÉE]tudes\s+Juridiques\s+&\s+Contentieux\s+)",
    ),  # p. 1, arrêtés
    # copie de actes:RE_STAMP_3
    (
        "Aix-en-Provence",
        r"(?:^\s*[A-Z]{2,3}(?:/[A-Z]{2,3})?[\n]+)?"
        + r"Accus[ée]\s+de\s+r[ée]ception\s+en\s+pr[ée]fecture[\n]+"
        + r"Identifiant\s+:[\n]+"
        + r"Date\s+de\s+r[ée]ception\s+:[\n]+"
        + r"Date\s+de\s+notification[\n]+"
        + r"Date\s+d[’']affichage\s+:\s+du\s+au[\n]+"
        + r"Date\s+de\s+publication\s+:[\n]+",
    ),  # p. 1, en haut à gauche
    # ("Aix-en-Provence", r"^ARRÊTÉ\n"),  # NON! trop générique, capture des spans nécessaires ailleurs
    ("Aubagne", r"^Gérard\s+GAZAY"),
    ("Aubagne", r"^Maire\s+d'Aubagne"),
    (
        "Aubagne",
        r"^Vice-Président\s+du\s+Conseil\s+Départemental\s+des\s+Bouches-du-Rh[ôo]ne",
    ),
    ("Aubagne", r"^Vice-Pr[ée]sident\s+de\s+[li]a\s+Métropole$"),
    # texte extrait (image)
    (
        "Allauch",
        rf"^{RE_DEP_013}" + r"\n\nAllauch\n\nun\s+certain\s+art\s+de\s+ville",
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
        + rf"{RE_ARD_013}\s+-\s+"
        + RE_DEP_013,
    ),  # p.1, OCR à refaire?
    ("Gardanne", r"^Ville\s+de\s+Gardanne$"),  # p. 1
    ("Gardanne", r"Commune\s+de\s+Gardanne$"),  # (ou) en-tête p.1, colonne de droite
    (
        "Gardanne",
        r"Arrêté\s+" + RE_NO + r"\d{4}-\d{2}-ARR-SIHI\s+" + r"Page\s+\d{1,2}/\d{1,2}",
    ),  # p.2 et suiv
    # TODO vérifier après OCR
    ("La Ciotat", r"^Ville\s+de\s+La\s+Ciotat(?:\s*[-–]\s*)?$"),  # p. 1
    # ("Berre-l'Étang", r"^République\s+Française$"),  # p. 1
    ("Gémenos", r"^Ville\s+de\s+G[ée]menos$"),  # p. 1
    (
        "Gémenos",
        r"^T[ÉE]L\s*[:;]\s*04\s+42\s+32\s+89\s+00",
    ),  # [:;] pour les erreurs d'OCR
    ("Gémenos", r"^FAX\s*[:;]\s*04\s+42\s+32\s+71\s+41"),
    (
        "Gémenos",
        r"www[.-]mairie-gemenos[.-]fr",  # [.-] pour les erreurs d'OCR
    ),  # p. 1
    ("Gémenos", r"^ARR[ÊE]T[ÉE]\s+DU\s+MAIRE$"),  # p. 1 (optionnel)
    (
        "Jouques",
        # r"^REPUBLIQUE\s+FRANCAISE\n"
        rf"^{RE_DEP_013}\n" + r"COMMUNE\s+DE\s+JOUQUES",
    ),  # p. 1 (en haut)
    (
        "La Ciotat",
        r"^H[ÔO]TEL\s+DE\s+VILLE\s+[-]\s+Rond[-]point\s+des\s+Messageries\s+maritimes\s+B\.P\s+161\s+[-]\s+13708\s+[-]\s+La\s+Ciotat\s+Cedex",
    ),
    (
        "La Ciotat",
        r"^Téléphone\s+:\s+04\s+42\s+08\s+88\s+00\s+[-]\s+Télécopie\s+:\s+04\s+42\s+08\s+23\s+71",
    ),
    (
        "Martigues",
        rf"^{RE_ARD_013}",
    ),
    (
        "Martigues",
        r"^Direction\s+des\s+Affaires\s+Civiles,\nJuridiques\s+et\s+Funéraires\nRéglementation\s+Administrative$",
    ),  # p. 1
    # ("Meyrargues", r"^REPUBLIQUE\s+FRANÇAISE"),  # p. 1 (en haut à gauche) ;
    (
        "Meyrargues",
        rf"^{RE_DEP_013}\n"
        + r"CANTON\s+DE\s+TRETS\n"
        + rf"{RE_ARD_013}\n"
        + r"METROPOLE\s+D['’]AIX-MARSEILLE-PROVENCE\n"
        + r"\n"
        + r"COMMUNE\s+DE\s+MEYRARGUES\n",
    ),  # p. 1 (en haut à gauche)
    (
        "Pennes Mirabeau",
        r"^CANTON\s+GARDANNE$",
    ),  # p. 1 (en haut à gauche)
    (
        "Pennes Mirabeau",
        r"^COMMUNE\s+(?:LES\s+)?PENNES\s+M[I]?RABEAU",  # I optionnel: robustesse OCR
    ),  # p. 1 (en haut à gauche)
    (
        "Pennes Mirabeau",
        r"^LIBERT[EÉ]S\s+PUBLIQUES\s+ET\s+POUVOIRS\s+DE\s+POLICE",
    ),  # p. 1 (en haut)
    (
        "Peyrolles-en-Provence",
        r"^Mairie\s+de\s+Peyrolles-en-Provence$",
    ),  # p. 1
    (
        "Peyrolles-en-Provence",
        r"^Affaire\s+suivie\s+par\s+:\s+[^\n]+\n(?:[^\n]+\n)?",
    ),  # p. 1
    (
        "Peyrolles-en-Provence",
        r"^Service\s+:\s+[^\n]+\n(?:[^\n]+\n)?",
    ),  # p. 1
    (
        "Peyrolles-en-Provence",
        r"^Tél\s+:\s+\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$",
    ),  # p. 1
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
    ("Septèmes-les-Vallons", r"^Ville\s+de\s+Septèmes-les-Vallons"),
    (
        "Trets",
        r"^&[']?\s*:\s+04[.,]42[.,]37[.,]55[.,]06",  # tél
    ),
    (
        "Trets",
        r"^Fax\s*:\s+04[.,]42[.,]37[.,]55[.,]20",  # fax
    ),
    (
        "Saint-Savournin",
        r"Ville\s+de\s+SAINT-SAVOURNIN\s+"
        + r"13119\s+"
        + r"8\s*:\s+04\s+42\s+04\s+64\s+03\s+-\s+Fax\s*:\s+04\s+42\s+72\s+43\s+08\s+"
        + r"Mail\s*:\s+mairie@mairie-stsavournin.fr\s+"
        + r"Site\s*:\s+www.mairie-stsavournin.fr",
    ),  # non enlevé actuellement car après le type d'arrêté
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
        + r"Tél[.]\s+[+]\s+33[(]0[)]4[.,]42[.,]91[.,]90[.,]00\s+-\s+"  # [.,]: robustesse OCR
        + r"Télécopie\s+[+]\s+33[(]0[)]4[.,]42[.,]91[.,]94[.,]92\s+-\s+"  # [.,]: robustesse OCR
        + r"www[.]mairie[-]aixenpr[oa]vence[.]fr"  # [oa]: robustesse OCR
        + r"[.]$",
    ),  #
    (
        "Aix-en-Provence",
        r"^Hot(?:el|sf|si)\s+de\s+Ville\s+1361[68]\s+A(?:IX|DC)[-]?EN-PROVENCE\s+CEDEX\s+[1?]\s+[–-]\s+Fran[cv]e\s+[–-]\s+"
        + r"Tél[.,]\s+[+]\s+[38]3[{(]0[)}]4[.,]42[.,]91[.,]90[.,]00\s+[+]\s+"
        + r"Té(?:k|lé)[co]op[il][aes]\s+[+]\s+[38]3[{(]0[)}]4[.,]42[.,]91[.,]04[.,]92\s+[–-]\s+"
        + r"www[.,]ma[il]r[i]?[es][-](?:ai|sl)xenpr[oa]vence[.,]f(?:r)?[.,]",
    ),  # robustesse: très mauvais OCR
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
        r"Hôtel\s+de\s+Ville\s+"
        + r"BP\s+41465\s+13785\s+Aubagne\s+Cedex\s+"
        + r"T\s*04\s*42\s*18\s*19\s*19\s+"
        + r"F\s*04\s*42\s*18\s*18\s*18\s+"
        + r"www[.]aubagne[.]fr$",
    ),  # p.1
    ("Auriol", r"""Page\s+\d{1,2}\s+sur\s+\d{1,2}$"""),
    (
        "Berre-l'Étang",
        r"VILLE\s+DE\s+BERRE-L['’]ETANG\n"
        + r"HOTEL\s+DE\s+VILLE\s+[-–]\s+B\.P\s+30221\s+[-–]\s+13138\s+BERRE\s+L['’]ÉTANG\s+CEDEX\n"
        + r"Téléphone\s+:\s+04\.42\.74\.93\.00\s+[-–]\s+"
        + r"Télécopie\s+:\s+04\.42\.74\.93\.02\s+[-–]\s+"
        + r"Site\s+internet\s+:\s+www\.berreletang\.fr",
    ),  # p.1
    (
        "Châteauneuf-les-Martigues",
        r"Hôtel\s+de\s+ville\s+[-–]\s+"
        + r"BP\s+70024\s+[-–]\s+"
        + r"13168\s+Châteauneuf-les-Martigues\s+cedex\s+[-–]\s+"
        + r"04\.42\.76\.89\.00\s+[-–]\s+"
        + r"04\.42\.79\.80\.25$",
    ),  # p. 1
    ("Gardanne", r"^Arrêté\s+[-–]\s+Secteur\s+Pouvoirs\s+de\s+Police\s+[-–]"),
    (
        "Gardanne",
        r"^Arrêté\s+[-–]\s+Libertés\s+Publiques\s+et\s+Pouvoir(?:s)?\s+de\s+Police\s+[-–]",
    ),
    # TODO footer Istres
    (
        "Mimet",
        r"Mairie\s+de\s+Mimet\s+[-–]\s+Hôtel\s+de\s+Ville\s+[-–]\s+13105\s+MIMET\s+[-–]\s+©\s+04\s+42\s+12\s+62\s+42\s+[-–]\s+Fax\s+:\s+04\s+42\s+58\s+91\s+05",
    ),
]

# reconnaissance de tous les pieds-de-page
RE_FOOTER = r"(?P<footer>" + r"|".join(r"(" + x + r")" for _, x in RE_FOOTERS) + r")"
P_FOOTER = re.compile(RE_FOOTER, flags=re.MULTILINE | re.IGNORECASE | re.VERBOSE)


# page de bordereau de formalités (en fin de document, Aix-en-Provence)
RE_BORDEREAU = r"^BORDEREAU\s+DE\s+FORMALITES$"
P_BORDEREAU = re.compile(RE_BORDEREAU, flags=re.MULTILINE | re.IGNORECASE)
# TODO annexes

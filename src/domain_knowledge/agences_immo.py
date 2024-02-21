"""Reconnaissance des noms d'agences immobilières.

- Certains noms de syndics incluent "syndic", les capturer explicitement avant le motif général permet d'éviter les conflits.
- Lister les syndics connus peut accélérer et mieux focaliser la capture.
"""

# TODO normaliser les valeurs, en utilisant le dict de reco+normalisation, avant export

import re

RE_CABINET = r"(?:cabinet|groupe|agence(?:\s+immobili[èe]re)?)"
P_CABINET = re.compile(RE_CABINET, re.IGNORECASE | re.MULTILINE)

# liste non exhaustive, à compléter par un motif générique "attrape-tout"
# expression régulière => forme canonique du nom
LISTE_NOMS_CABINETS = {
    r"FERGAN": "Fergan",
    r"TRAVERSO": "Traverso",
    # Cogefim
    r"COGEFIM\s+FOUQUE\s+COLAPINTO": "Cogefim Fouque Colapinto",
    r"COGEFIM\s+FOUQUE": "Cogefim Fouque",
    r"COGEFIM\s+MERIDIEM": "Cogefim Meridiem",
    # Foncia
    r"FONCIA\s+VIEUX[-\s]\s*PORT": "Foncia Vieux Port",
    r"FONCIA\s+SAGI": "Foncia Sagi",
    r"FONCIA\s+CAPELETTE": "Foncia Capelette",
    r"FONCIA\s+MARSEILLE": "Foncia Marseille",
    r"FONCIA": "Foncia",  # réseau => préfixe possible de cabinets (plus précis)
    # Citya
    r"CITYA\s+PARADIS(\s+IMMOBILIER)?": "Citya Paradis",
    r"CITYA\s+CARTIER": "Citya Cartier",  # ? = Casal & Villemain ?
    r"CITYA\s+PRADO": "Citya Prado",
    r"CITYA\s+CASAL\s+((et|&)\s+)?VILLEMAIN(\s+[–-]\s+CITYA\s+CARTIER)?": "Citya Casal Villemain",
    r"CITYA\s+CASAL": "Citya Casal",  # préfixe possible
    r"BERTHOZ": "Berthoz",
    r"I[.]?A[.]?G(\s+IMMOBILIER)": "IAG",
    r"LIAUTARD": "Liautard",
    r"(Immobili[èe]re\s+)?D[’'\s]\s*AGOSTINO": "D'Agostino",
    r"SIGA": "SIGA",
    r"GAUDEMARD": "Gaudemard",
    r"MICHEL\s+DE\s+CHABANNES": "Michel de Chabannes",
    r"MALLARD\s+IMMO": "Mallard Immo",
    r"LAUGIER[-\s]\s*FINE": "Laugier Fine",
    r"FOURNIER": "Fournier",
    r"ATOUT\s+Immobilier": "Atout Immobilier",
    r"ACCORD\s+COMPAGNIE\s+IMMOBILIER": "Accord Compagnie Immobilier",
    r"(Agence\s+)?[ÉE]toile": "Étoile",
    r"(Immobili[èe]re\s+)?TARIOT": "Tariot",
    r"SOGEIMA": "Sogeima",
    r"SEVENIER\s+(&|et)\s+CARLINI": "Sevenier & Carlini",
    r"PINATEL\s+FR[ÈE]RES": "Pinatel Frères",
    r"PINATEL": "Pinatel",
    r"LAPLANE": "Laplane",
    r"IMMOBILI[ÈE]RE\s+COLAPINTO": "Immobilière Colapinto",
    r"GUIS\s+IMMOBILIER": "Guis Immobilier",
    r"Agence\s+de\s+la\s+Comtesse": "Agence de la Comtesse",  # "Cabinet Agence de la Comtesse"
    r"SQUARE\s+HABITAT": "Square Habitat",
    r"POURTAL": "Pourtal",
    r"NEXIA\s+SERVICE\s+IMMOBILIER": "Nexia Service Immobilier",
    r"IMMO\s*VESTA": "Immo Vesta",
    r"GESTION\s+IMMOBILI[ÈE]RE\s+DU\s+MIDI": "Gestion Immobilière du Midi",
    r"GESPAC(\s+IMMOBILIER)?": "Gespac Immobilier",
    r"DALLAPORTA": "Dallaporta",
    r"AJ\s*Associés": "AJAssociés",
    r"ACTIV[’'\s]\s*SYNDIC": "Activ'Syndic",  # nom inclut "syndic"
    r"IMMOBILI[ÈE]RE\s+PUJOL": "Immobilière Pujol",
    r"DENIS\s+HAZ(Z)?AN": "Denis Hazzan",  # cabinet Denis Hazzan
    r"société\s+Immobilière\s+Patrimoine\s+&\s+Finances": "Immobilière Patrimoine & Finances",
    r"OTIM\s+/\s+STEYER\s+&\s+DORAT": "OTIM Steyer & Dorat",
    r"M[.]?G[.]?F(\s+Immo)?": "MGF Immo",
    r"Martini": "Martini",
    r"IPF\s+Immo": "IPF Immo",
    r"IMMOGEST": "Immogest",
    r"(Immobili[èe]re\s+)?Keisermann": "Keisermann",
    r"Georges\s+Coudre": "Georges Coudre",
    r"DEVICTOR": "Devictor",
    r"CONTI": "Conti",
    r"AXCEPIERRE": "AXCEPIERRE",
    r"AUXITIME": "AUXITIME",  # ? = Guis Immobilier ?
    r"AJILL[’'\s]\s*IMMO": "AJILL'IMMO",
    r"LE\s+BON\s+SYNDIC": "Le Bon Syndic",  # nom inclut "syndic"
}

RE_NOMS_CABINETS = r"(?:" + r"|".join(LISTE_NOMS_CABINETS.keys()) + r")"
P_NOMS_CABINETS = re.compile(RE_NOMS_CABINETS, re.IGNORECASE | re.MULTILINE)


def normalize_nom_cabinet(nom_cab: str) -> str:
    """Normalise un nom de cabinet.

    La version actuelle requiert une déclaration explicite dans
    LISTE_NOMS_CABINETS, mais des traitements de normalisation
    standard pourraient être définis en complément.

    Parameters
    ----------
    nom_cab: str
        Nom du cabinet ou de l'agence.

    Returns
    -------
    nom_nor: str
        Nom normalisé.
    """
    if nom_cab is None:
        return None
    #
    for re_nom, norm in LISTE_NOMS_CABINETS.items():
        # dès qu'on a un match sur un nom de cabinet, on renvoie la forme normalisée
        if re.search(re_nom, nom_cab, flags=(re.IGNORECASE | re.MULTILINE)):
            return norm
    else:
        # si aucun match, on renvoie le nom en entrée tel quel
        return nom_cab

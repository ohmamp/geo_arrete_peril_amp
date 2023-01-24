"""Éléments dénotant la structure du texte.

"""

import re

# TODO récupérer les champs?
# ex:
# Envoyé en préfecture le 09/02/2021
# Reçu en préfecture le 09/02/2021
# Affiché le
# ID : 013-211301106-20210201-1212-AI
RE_STAMP = r"""Envoyé en préfecture le 09/02/2021\n
Reçu en préfecture le \d{2}/\d{2}/\d{4}\n
Affiché le\n
ID : \d{3}-\d{9}-\d{8}-[^-]+-AI"""
M_STAMP = re.compile(RE_STAMP, re.MULTILINE)

# TODO récupérer les champs?
# ex:
# Accusé de réception
# Acte reçu par: Préfecture des Bouches du Rhône
# Nature transaction: AR de transmission d'acte
# Date d'émission de l'accusé de réception: 2021-06-02(GMT+1)
# Nombre de pièces jointes: 1
# Nom émetteur: 4 martigues
# N° de SIREN: 211300561
# Numéro Acte de la collectivité locale: RA21_21646
# Objet acte: LE MAIRE SIGNE - Arrêté Municipal n. 446.2021prononcant une interdiction temporaire d
# acces et d habiter 2 rue leon gambetta à Martigues
# Nature de l'acte: Actes individuels
# Matière: 6.1-Police municipale
# Identifiant Acte: 013-211300561-20210602-RA21_21646-AI
RE_ACCUSE = r"""Accusé de réception\n
Acte reçu par: Préfecture des Bouches du Rhône\n
Nature transaction: AR de transmission d'acte\n
Date d'émission de l'accusé de réception: \d{4}-\d{4}-\d{4}(GMT+\d)\n
Nombre de pièces jointes: \d+\n
Nom émetteur: [^\n]+\n
N° de SIREN: \d{9}\n
Numéro Acte de la collectivité locale: [^n]+\n
Objet acte: [^\n]+\n
([^\n]+\n)?
Nature de l'acte: Actes individuels\n
Matière: \d.\d-[^n]+\n
Identifiant Acte: \d{3}-\d{3}-\d{3}-\d{3}-AI"""
M_ACCUSE = re.compile(RE_ACCUSE, re.MULTILINE)

RE_VU = r"""^VU [^\n]+"""
M_VU = re.compile(RE_VU, re.MULTILINE)

RE_CONSIDERANT = r"""^CONSID[EÉ]RANT [^\n]+"""
M_CONSIDERANT = re.compile(RE_CONSIDERANT, re.MULTILINE)
"""Traces de télétransmission de documents par @ctes.

Tampon et page d'accusé de réception.
"""

import re

# @ctes
#
RE_DATE_SL = r"\d{2}/\d{2}/\d{4}"
RE_ACTES_ID = r"\d{3}-\d{9}-\d{8}-[^-]+-(AI|AR)"
# TODO récupérer les champs?
# ex:
# Envoyé en préfecture le 09/02/2021
# Reçu en préfecture le 09/02/2021
# Affiché le
# ID : 013-211301106-20210201-1212-AI
RE_STAMP_1 = rf"""Envoyé en préfecture le {RE_DATE_SL}
Reçu en préfecture le {RE_DATE_SL}
Affiché le
ID : {RE_ACTES_ID}"""
# ex:
# Accusé de réception en préfecture
# 013-211300561-20211025-RA21_23060-AR
# Date de télétransmission : 25/10/2021
# Date de réception préfecture : 25/10/2021
RE_STAMP_2 = rf"""Accusé de réception en préfecture
{RE_ACTES_ID}
Date de télétransmission : {RE_DATE_SL}
Date de réception préfecture : {RE_DATE_SL}
"""
RE_STAMP = rf"(?:(?:{RE_STAMP_1})|(?:{RE_STAMP_2}))"
M_STAMP = re.compile(RE_STAMP, re.MULTILINE)

# TODO motif complet sur l'accusé de réception ; parsing dédié pour vérifier/croiser avec les données extraites dans le reste du document
# "Objet acte:" (page d'accusé de réception de transmission @actes)
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
RE_ACCUSE = r"""Accusé de réception
Acte reçu par: Préfecture des Bouches du Rhône
Nature transaction: AR de transmission d'acte
Date d'émission de l'accusé de réception: \d{4}-\d{2}-\d{2}[(]GMT[+-]\d[)]
Nombre de pièces jointes: \d+
Nom émetteur: [^\n]+
N° de SIREN: \d{9}
Numéro Acte de la collectivité locale: [^\n]+
Objet acte: (?:[\s\S]+?)
Nature de l'acte: (?P<nature_acte>Actes individuels|Actes réglementaires|Autres)
Matière: \d[.]\d-[^\n]+
Identifiant Acte: \d{3}-\d{9}-\d{8}-[^-]+-(?P<nature_abr>AI|AR|AU)"""
# actes individuels: ...-AI, actes réglementaires: ...-AR, autres: ...-AU
# (?P<nature_acte>Actes individuels|Actes réglementaires)\n
# (?P<nature_abr>[^\n]+)
M_ACCUSE = re.compile(RE_ACCUSE, re.MULTILINE)

# TODO vérifier les matières ;
# grep -h "Matière:" data/interim/txt_native/*.txt |sort |uniq -c
# renvoie:
#      1 Matière: 1.7-Actes speciaux et divers
#      3 Matière: 2.1-Documents d urbanisme
#      8 Matière: 3.6-Autres actes de gestion du domaine prive
#     47 Matière: 6.1-Police municipale
#     14 Matière: 6.4-Autres actes reglementaires
#      2 Matière: 8.5-Politique de la ville-habitat-logement
#      5 Matière: 9.1-Autres domaines de competences des communes
#
# 1.7: "travaux de mise en sécurité 2 rue Aharonian La Ciotat.pdf" décision du conseil municipal sur un marché attribué pour la CSPS des travaux de mise en sécurité (à exclure?)
# 2.1: "21 cours Carnot Châteaurenard.pdf" mise en demeure de travaux conformes au règlement sanitaire départemental (à exclure?),
#      "MenS 44 rue de la République Aubagne.pdf" MSU (à garder),
#      "Retrait 1687 avenue de la Croix d'Or Bouc Bel Air.pdf" : retrait de péril imminent (= ML ?) (à garder?)
# 3.6: "12 rue Parmentier Gardanne - MS.pdf": MSU (à garder)
#      "mainlevée 21 rue Martinot Aubagne.pdf": ML (à garder)
#      "mainlevée 4 bis cours Foch Aubagne.pdf": mainlevée (à garder)
#      "mise en sécurité 15 rue de la Mairie Peyrolles en Provence.pdf": MSU (à garder)
#      "mise en sécurité 21 rue Martinot Aubagne.pdf": MS (à garder)
#      "mise en sécurité 4 rue de l'Huveaune Aubagne.pdf": MS (à garder)
#      "mise en sécurité 6 rue de l'Huveaune Aubagne.pdf": MS (à garder)
#      "MS 39 rue de la République Aubagne.pdf": MS (à garder)
# 8.5: "19 av du Docteur Perrier Châteaurenard.pdf": mise en demeure de travaux conformes au règlement sanitaire départemental (à exclure?),
#      "7 rue Paulet Ceyreste.pdf": MSU (à garder)
# 9.1: "mainlevée 12 rue Frédéric Mistral Aubagne.pdf": mainlevée (à garder)
#      "mainlevée 22 rue Mirabeau Tarascon.pdf": mainlevée (à garder)
#      "mise en sécurité 14 rue de l'Egalité Aubagne.pdf": MSU (à garder)
#      "mise en sécurité 16 rue Frédéric Mistral Aubagne.pdf": MS (à garder)
#      "MS 14 16 rue Frédéric Mistral Aubagne.pdf": MS (à garder)

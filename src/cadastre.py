"""Reconnaissance et analyse de références cadastrales.

"""

import re

# Marseille: préfixe = arrondissement + quartier
RE_CAD_ARRT_QUAR = (
    r"""(2[01]\d)"""  # 3 derniers chiffres du code INSEE de l'arrondissement
    + r"""\s*"""
    + r"""(\d{3})"""  # code quartier
)
# toutes communes: section et numéro
RE_CAD_SEC = r"""[A-Z]{1,2}"""
RE_CAD_NUM = r"""\d{1,4}"""
# expression complète
# - Marseille
RE_CAD_MARSEILLE = rf"""(?:(?:n°\s?){RE_CAD_ARRT_QUAR}\s+{RE_CAD_SEC}\s?{RE_CAD_NUM})"""
M_CAD_MARSEILLE = re.compile(RE_CAD_MARSEILLE, re.MULTILINE | re.IGNORECASE)
# - autres communes
RE_CAD_AUTRES = rf"""(?:(?:n°\s?)?{RE_CAD_SEC}(?:\sn°)?\s?{RE_CAD_NUM})"""
M_CAD_AUTRES = re.compile(RE_CAD_AUTRES, re.MULTILINE | re.IGNORECASE)
# Marseille ou autres communes
RE_CAD_SECNUM = (
    r"""(?:""" + rf"""{RE_CAD_MARSEILLE}""" + rf"""|{RE_CAD_AUTRES}""" + r""")"""
)
# avec le contexte gauche
RE_PARCELLE = (
    r"""(?:"""
    + r"""cadastré(?:e|es)(?:\s+section)?"""
    + r"""|référence(?:s)?\s+cadastrale(?:s)?"""
    + r"""|parcelle(?:s)?"""
    + r""")\s+"""
    + r"""(?P<cadastre_id>"""
    + rf"""{RE_CAD_SECNUM}"""
    + r"""("""
    + r"""(?:,|\s+et|\s+[-])\s+"""
    + rf"""{RE_CAD_SECNUM}"""
    + r""")*"""
    + r""")"""
)
M_PARCELLE = re.compile(RE_PARCELLE, re.MULTILINE | re.IGNORECASE)

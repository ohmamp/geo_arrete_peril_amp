"""Références au cadre réglementaire.

"""

import re

# arrêtés spécifiques:
# - entités du contexte réglementaire
# CGCT
RE_CGCT = r"""Code\s+Général\s+des\s+Collectivités\s+Territoriales"""
M_CGCT = re.compile(RE_CGCT, re.MULTILINE | re.IGNORECASE)
#
RE_CGCT_ART = r"""articles(?:\s)L[. ]*2131-1,(?:\s)L[. ]*2212-4(?:\s)et(?:\s)L[. ]*2215-1"""  # TODO généraliser
# TODO L.2212-2 et L.2213-24 ?
M_CGCT_ART = re.compile(RE_CGCT_ART, re.MULTILINE | re.IGNORECASE)
# CCH
RE_CCH = r"""Code\s+de\s+la\s+Construction\s+et\s+de\s+l’Habitation"""
M_CCH = re.compile(RE_CCH, re.MULTILINE | re.IGNORECASE)
# L111-6-1: <https://www.legifrance.gouv.fr/codes/id/LEGIARTI000028808282/2014-03-27> (en vigueur jusque 2021-07-01)
RE_CCH_L111 = r"""L[. ]*111(?:-[\d]){0,2}"""
M_CCH_L111 = re.compile(RE_CCH_L111, re.MULTILINE | re.IGNORECASE)
# L511-1 à L511-22 du CCH
RE_CCH_L511 = r"""L[. ]*511-1(?:\s)(?:(?:à(?:\s)?L[. ]*511-[\d]{1,2})|(?:et\s+suivants))"""  # TODO trop général ?
M_CCH_L511 = re.compile(RE_CCH_L511, re.MULTILINE | re.IGNORECASE)
# 521-1, 521-2, 521-3-[1-4], 521-4
# 521-3: relogement
# 521-4: sanctions
RE_CCH_L521 = r"""L[. ]*521-1(?:\s)à(?:\s)?L[. ]*521-[\d](?:-[\d])?"""  # TODO affiner ?
M_CCH_L521 = re.compile(RE_CCH_L521, re.MULTILINE | re.IGNORECASE)
RE_CCH_L541 = r"""L[. ]*541-2"""
M_CCH_L541 = re.compile(RE_CCH_L541, re.MULTILINE | re.IGNORECASE)
# R511-1 à R511-13 du CCH
RE_CCH_R511 = r"""R[. ]*511-1(?:\s)à(?:\s)?R[. ]*511-[\d]{1,2}"""  # TODO trop général ?
M_CCH_R511 = re.compile(RE_CCH_R511, re.MULTILINE | re.IGNORECASE)
# CC
RE_CC = r"""Code\s+Civil"""
M_CC = re.compile(RE_CC, re.MULTILINE | re.IGNORECASE)
#
RE_CC_ART = r"""articles(?:\s)2384-1,(?:\s)2384-3"""  # TODO généraliser
M_CC_ART = re.compile(RE_CC_ART, re.MULTILINE | re.IGNORECASE)

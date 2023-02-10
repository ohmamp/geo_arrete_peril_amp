"""Reconnaissance et mise en forme des dates.

"""

import re

RE_MOIS = (
    r"""(?:"""
    + r"""janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"""
    + r"""|"""
    + r"""jan|f[ée]v|mars|avr|mai|juin|juil|aou|sep|oct|nov|d[ée]c"""
    + r""")"""
)

RE_DATE = (
    r"""(?:"""
    + r"""\d{2}[.]\d{2}[.]\d{4}|"""  # Peyrolles-en-Provence (en-tête)
    + r"""\d{2}/\d{2}/\d{4}|"""  # ?
    + r"""\d{1,2} """
    + rf"""{RE_MOIS}"""
    + r""" \d{4}"""  # Roquevaire (fin), Martigues (fin)
    + r""")"""
)

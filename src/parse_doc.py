"""Analyse le document dans son ensemble.

Découpe l'arrêté en zones.
"""

from pathlib import Path
import re

# header: Gardanne

RE_FOOTER_AIX = r"""
Hotel[ ]de[ ]Ville[ ]13616[ ]AIX-EN-PROVENCE[ ]CEDEX[ ]1[ ]-[ ]France[ ]-
[ ]Tél[.][ ][+][ ]33[(]0[)]4[.]42[.]91[.]90[.]00[ ]-
[ ]Télécopie[ ][+][ ]33[(]0[)]4[.]42[.]91[.]94[.]92[ ]-
[ ]www[.]mairie[-]aixenprovence[.]fr
[.]
"""
RE_FOOTER_ALLAUCH = r"""
Hôtel[ ]de[ ]Ville[ ][+][ ]Place[ ]Pierre[ ]Bellot[ ]e[ ]BP[ ]27[ ][+][ ]13718[ ]Allauch[ ]cedex[ ]e
[ ]Tél[.][ ]04[ ]91[ ]10[ ]48[ ]00[ ][+]
[ ]Fax[ ]04[ ]91[ ]10[ ]48[ ]23
\nWeb[ ][:][ ]http[:]//www[.]allauch[.]com[ ][+]
[ ]Courriel[ ][:][ ]info@allauch[.]com
"""
RE_FOOTER_AUBAGNE = r"""
Hôtel[ ]de[ ]Ville[ ]BP[ ]41465[ ]13785[ ]Aubagne[ ]Cedex
[ ]T[ ]?04[ ]?42[ ]?18[ ]?19[ ]?19
[ ]F[ ]?04[ ]?42[ ]?18[ ]?18[ ]?18
[ ]www.aubagne.fr
"""
RE_FOOTER_AURIOL = r"""
(Certifié[ ]exécutoire[,][ ]compte[ ]tenu[ ]de[ ]la[ ]transmission[ ]en[ ]Préfecture[ ]et[ ]de[ ]la[ ]publication[ ]le[ ][:][ ]\d{2}/\d{2}/\d{4}[ ])?
Page[ ]\d{1,2}[ ]sur[ ]\d{1,2}
"""
# Châteauneuf-les-Martigues: pas de footer détecté dans l'OCR d'origine ; TODO retester avec OCR refait
# Gardanne: pas de footer
# TODO footer RE_ISTRES
RE_FOOTER_MARSEILLE = r"""
Ville[ ]de[ ]Marseille[,][ ]2[ ]quai[ ]du[ ]Port[ ][–][ ]13233[ ]MARSEILLE[ ]CEDEX[ ]20
"""
RE_FOOTER = (
    r"|".join(
        r"(" + x + r")"
        for x in [
            RE_FOOTER_AIX,
            RE_FOOTER_ALLAUCH,
            RE_FOOTER_AUBAGNE,
            RE_FOOTER_AURIOL,
            RE_FOOTER_MARSEILLE,
        ]
    )
    + r"[^\f]*[\f]"
)
P_FOOTER = re.compile(RE_FOOTER, flags=re.MULTILINE | re.VERBOSE)

RE_AUTORITE = (
    r"\s*(?P<autorite>"
    + r"("
    + r"("
    + r"|".join(
        [
            r"(NOUS,[ ]MAIRE D')",  # AIX-EN-PROVENCE
            r"(Nous,[ ]Maire[ ]de[ ])",  # Marseille
            r"(NOUS,[ ](?P<autorite_nom>.*),[ ]Maire[ ]de[ ]la[ ]commune[ ]d')",  # Allauch
            r"(Le[ ]Maire[ ]de[ ]la[ ]Commune[ ]d['’])",  # ISTRES, Auriol, Aubagne (certains)
            r"(Le[ ]Maire[ ]de[ ]la[ ]Ville[ ]de[ ])",  # Châteauneuf-les-Martigues
            r"(Le[ ]Maire[ ]de[ ])",  # Gardanne
        ]
    )
    + r")"
    + r"(?P<commune>.+)"
    + r")"
    # + r"|(Le Maire)"  # fallback, utile pour certains arrêtés d'Aubagne
    + r")"
)
P_AUTORITE = re.compile(RE_AUTORITE, re.MULTILINE | re.VERBOSE)

RE_VU = r"^\s*(?P<vu>V[Uu][, ](.+))"
P_VU = re.compile(RE_VU, flags=re.MULTILINE | re.VERBOSE)

RE_CONSIDERANT = r"^\s*(?P<considerant>(Considérant|CONSIDERANT)[, ](.+))"
P_CONSIDERANT = re.compile(RE_CONSIDERANT, flags=re.MULTILINE | re.VERBOSE)

RE_ARRETE = r"^\s*(ARR[ÊE]TE|ARR[ÊE]TONS)"
P_ARRETE = re.compile(RE_ARRETE, flags=re.MULTILINE | re.VERBOSE)

RE_PREAMBULE = r"""
{re_autorite}\n
(^\s*$)*
""".format(
    re_autorite=RE_AUTORITE
)
P_PREAMBULE = re.compile(RE_PREAMBULE, flags=re.MULTILINE | re.VERBOSE)


def parse_arrete(fp_txt_in: Path) -> dict:
    """Analyse un arrêté pour le découper en zones.

    Parameters
    ----------
    fp_txt_in: Path
        Fichier texte à analyser.

    Returns
    -------
    content: dict
        Contenu du document, découpé en zones de texte.
    """
    # ouvrir le fichier
    with open(fp_txt_in) as f:
        txt = f.read()
    # nettoyer en-tête et pied-de-page
    m_footer = P_FOOTER.search(txt)
    if m_footer is not None:
        print(fp_txt_in.name, m_footer)
    else:
        print(fp_txt_in.name)
    # préparer le dictionnaire à renvoyer
    content = {}
    return content
    # WIP
    m_preambule = P_PREAMBULE.search(txt)
    if m_preambule is not None:
        print(fp_txt_in.name, "\tPREAMBULE ", m_preambule)
    else:
        for line in txt.split("\n"):
            m_autorite = P_AUTORITE.match(line)
            if m_autorite is not None:
                print(fp_txt_in.name, "\tAUTORITE  ", m_autorite)
                break
        else:
            raise ValueError(f"{fp_txt_in.name}")
    # end WIP
    # chercher le point de référence "ARRETE|ARRÊTE|ARRÊTONS"
    m_arrete = P_ARRETE.search(txt)
    if m_arrete is not None:
        content["arrete"] = m_arrete.groups()
    else:
        print(repr(txt))
        raise ValueError(f"{fp_txt_in.name}:\t !?")
    # avant ARRETE, on trouve l'en-tête, l'objet, l'autorité, les "vu" et les "considérant"
    # entete
    # objet
    # autorite
    m_autorite = P_AUTORITE.search(txt)
    if m_autorite is not None:
        content["autorite"] = m_autorite.group(0)
    # vus
    m_vu = P_VU.findall(txt)
    content["vu"] = m_vu
    # considerants
    m_considerant = P_CONSIDERANT.findall(txt)
    content["considerant"] = m_considerant
    if not m_considerant:
        if fp_txt_in.name not in (
            "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).txt",  # mainlevée => optionnel ?
            "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.txt",  # mainlevée => optionnel ?
        ):
            raise ValueError(fp_txt_in.name)
    # articles
    # pieddepage
    return content


if __name__ == "__main__":
    # TODO argparse
    INT_TXT_DIR = Path("../data/interim/txt")
    for fp_txt in sorted(INT_TXT_DIR.glob("*.txt")):
        content = parse_arrete(fp_txt)
        # print(f"{fp_txt.name}:\t{content}")

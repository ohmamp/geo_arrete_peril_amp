"""Valide les zones repérées.

* Tous les en-têtes commencent à 0 ;
* Tous les pieds-de-pages terminent à la longueur du document ;
* En-tête et pied-de-page sont disjoints ;

"""

# TODO ajouter expectations:
# - 1 adresse => 1 référence cadastrale (quelle proportion?)
#   * 1 traverse Saint Bazile: les premiers arrêtés ont la référence 201802 C0133, qui est la parcelle du 1 rue Saint Bazile ; l'arrêté 2020_01533_VDM a la bonne référence 201802 C0114 dans le texte (mais pas dans l'annexe 2 !)
#

# TODO trouver les trous dans la raquette pour le cadastre:
# cd data/interim/txt_native ; grep -il "cadastr\|parcell" *.txt |sort |uniq > ../../fn_cadastr_parcell.txt
# cd ../.. ; csvgrep -c par_ref_cad -r "^." runs/2023-03-06T17:10/arretes_peril_compil_data_enr_struct.csv |csvcut -c arr_pdf |sed -e 's/.pdf/.txt/ ; s/^"// ; s/"$// ;' |sort > fn_refcad.txt
# meld fn_cadastr_parcell.txt fn_refcad.txt


import pandas as pd


def expect_header_beg_zero(df: pd.DataFrame) -> bool:
    """Vérifie que les en-têtes commencent tous à 0.

    Ignore les valeurs manquantes (aucun en-tête détecté).

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les zones repérées dans les documents.

    Returns
    -------
    success: bool
        True si tous les en-têtes détectés commencent à 0.
    """
    return (df["header_beg"].dropna() == 0).all()


def expect_footer_end_len(df: pd.DataFrame) -> bool:
    """Vérifie que les en-têtes commencent tous à 0.

    Ignore les valeurs manquantes (aucun en-tête détecté).

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les zones repérées dans les documents.

    Returns
    -------
    success: bool
        True si tous les en-têtes détectés commencent à 0.
    """
    return (df["footer_end"].dropna() == len()).all()


# WIP validation de la structure extraite par process.parse_doc
def examine_doc_content(fn_pdf: str, doc_content: list[dict]):
    """Vérifie des hypothèses de bonne formation sur le contenu extrait du document.

    Parameters
    ----------
    doc_content: list[dict]
        Empans de contenu extraits du document
    """
    # filtrer les pages absentes
    pg_conts = [x for x in doc_content if (pd.notna(x) and x["content"] is not None)]
    # paragraphes
    par_typs = [
        x["span_typ"]
        for pg_content in pg_conts
        for x in pg_content["content"]
        if (pd.notna(x) and x["span_typ"].startswith("par_"))
    ]
    # "considérant" obligatoire sauf pour certains arrêtés?
    # TODO déterminer si les assertions ne s'appliquent qu'à certaines classes d'arrêtés
    if par_typs:
        # chaque arrêté contient au moins un "vu"
        if "par_vu" not in par_typs:
            raise ValueError(f"{fn_pdf}: pas de vu")
        # chaque arrêté contient au moins un "considérant"
        # * sauf dans les mainlevées et abrogations où dans la pratique ce n'est pas le cas
        if "par_considerant" not in par_typs:
            if fn_pdf not in (
                "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).pdf",  # mainlevée => optionnel ?
                "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.pdf",  # mainlevée => optionnel ?
                "abrogation interdiction d'occuper 35, bld Barbieri.pdf",  # abrogation => optionnel ?
                "abrogation 232 et 236 rue Roger Salengro 13003.pdf",  # abrogation => optionnel ?
                "abrogation 79, rue de Rome.pdf",  # abrogation => optionnel ?
                "abrogation 19 24 rue Moustier 13001.pdf",  # abrogation => optionnel ?
                "102, rue d'Aubagne abrogation.pdf",  # abrogation => optionnel ?
                "9, rue Brutus ABROGATION.pdf",  # abrogation
                "ABROGATION 73, rue d'Aubagne.pdf",  # abrogation
                "abrogation 24, rue des Phocéens 13002.pdf",  # abrogation
                "abrogation.pdf",  # abrogation
                "abrogation 19, rue d'Italie 13006.pdf",  # abrogation
                "ABROGATION 54, bld Dahdah.pdf",  # abrogation
                "abrogation 3, rue Loubon 13003.pdf",  # abrogation
                "abrogation 35, rue de Lodi.pdf",  # abrogation
                "abrogation 4 - 6 rue Saint Georges.pdf",  # abrogation
                "abrogation 23, bld Salvator.pdf",  # abrogation
                "abrogation 25, rue Nau.pdf",  # abrogation
                "abrogation 51 rue Pierre Albrand.pdf",  # abrogation
                "abrogation 80 a, rue Longue des Capucins.pdf",  # abrogation
                "abrogation 36, cours Franklin Roosevelt.pdf",  # abrogation
                "abrogation 356, bld National.pdf",  # abrogation
                "abrogation 57, bld Dahdah.pdf",  # abrogation
                "abrogation 86, rue Longue des Capucins.pdf",  # abrogation
                "abrogation 26, bld Battala.pdf",  # abrogation
                "abrogation 24, rue Montgrand.pdf",  # abrogation
                "mainlevée 102 bld Plombières 13014.pdf",  # mainlevée (Marseille)
                "mainlevée 29 bld Michel 13016.pdf",  # mainlevée (Marseille)
                "mainlevée 7 rue de la Tour Peyrolles.pdf",  # mainlevée (Peyrolles)
                "mainlevée de péril ordinaire 8 rue Longue Roquevaire.pdf",  # mainlevée (Roquevaire)
                "mainlevée 82L chemin des Lavandières Roquevaire.pdf",  # mainlevée (Roquevaire)
                "mainlevée de péril ordinaire 8-8 bis avenue de Lambesc-26012021.pdf",  # mainlevée (Rognes)
                "8, rue Maréchal Foch Roquevaire.PDF",  # PGI ! (Roquevaire)
                "grave 31 rue du Calvaire Roquevaire.pdf",  # PGI ! (Roquevaire)
                "PGI rue docteur Paul Gariel -15122020.PDF",  # PGI ! (Roquevaire)
                "modif Maréchal Foch.PDF",  # modif PGI ! (Roquevaire)
            ):
                # FIXME détecter la classe au lieu d'une liste d'exclusion => ne pas appliquer pour abrogations et mainlevées
                raise ValueError(f"{fn_pdf}: pas de considérant")
        # chaque arrêté contient exactement 1 "Arrête"
        try:
            assert len([x for x in par_typs if x == "par_arrete"]) == 1
        except AssertionError:
            if fn_pdf not in (
                "16, rue de la République Gemenos.pdf",  # OCR p.1 seulement => à ré-océriser
                "mainlevée 6, rue des Jaynes Gemenos.pdf",  # OCR p.1 seulement => à ré-océriser
            ):
                raise ValueError(f"{fn_pdf}: pas de vu")
        # l'ordre relatif (vu < considérant < arrête < article) est vérifié au niveau des transitions admissibles

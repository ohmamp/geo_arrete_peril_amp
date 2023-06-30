"""Valide les zones repérées.

* Tous les en-têtes commencent à 0 ;
* Tous les pieds-de-pages terminent à la longueur du document ;
* En-tête et pied-de-page sont disjoints ;

"""

# TODO ajouter expectations:
# - 1 adresse => 1 référence cadastrale (quelle proportion?)
#   * 1 traverse Saint Bazile: les premiers arrêtés ont la référence 201802 C0133, qui est la parcelle du 1 rue Saint Bazile ; l'arrêté 2020_01533_VDM a la bonne référence 201802 C0114 dans le texte (mais pas dans l'annexe 2 !)
#
# - 1 considérant, sauf :
# "99_AR-013-211300058-20220131-310122_01-AR-1-1_1 (1).pdf",  # mainlevée => optionnel ?
# "99_AR-013-211300058-20220318-180322_01-AR-1-1_1.pdf",  # mainlevée => optionnel ?
# "abrogation interdiction d'occuper 35, bld Barbieri.pdf",  # abrogation => optionnel ?
# "abrogation 232 et 236 rue Roger Salengro 13003.pdf",  # abrogation => optionnel ?
# "abrogation 79, rue de Rome.pdf",  # abrogation => optionnel ?
# "abrogation 19 24 rue Moustier 13001.pdf",  # abrogation => optionnel ?
# "102, rue d'Aubagne abrogation.pdf",  # abrogation => optionnel ?
# "9, rue Brutus ABROGATION.pdf",  # abrogation
# "ABROGATION 73, rue d'Aubagne.pdf",  # abrogation
# "abrogation 24, rue des Phocéens 13002.pdf",  # abrogation
# "abrogation.pdf",  # abrogation
# "abrogation 19, rue d'Italie 13006.pdf",  # abrogation
# "ABROGATION 54, bld Dahdah.pdf",  # abrogation
# "abrogation 3, rue Loubon 13003.pdf",  # abrogation
# "abrogation 35, rue de Lodi.pdf",  # abrogation
# "abrogation 4 - 6 rue Saint Georges.pdf",  # abrogation
# "abrogation 23, bld Salvator.pdf",  # abrogation
# "abrogation 25, rue Nau.pdf",  # abrogation
# "abrogation 51 rue Pierre Albrand.pdf",  # abrogation
# "abrogation 80 a, rue Longue des Capucins.pdf",  # abrogation
# "abrogation 36, cours Franklin Roosevelt.pdf",  # abrogation
# "abrogation 356, bld National.pdf",  # abrogation
# "abrogation 57, bld Dahdah.pdf",  # abrogation
# "abrogation 86, rue Longue des Capucins.pdf",  # abrogation
# "abrogation 26, bld Battala.pdf",  # abrogation
# "abrogation 24, rue Montgrand.pdf",  # abrogation
# "mainlevée 102 bld Plombières 13014.pdf",  # mainlevée (Marseille)
# "mainlevée 29 bld Michel 13016.pdf",  # mainlevée (Marseille)
# "mainlevée 7 rue de la Tour Peyrolles.pdf",  # mainlevée (Peyrolles)
# "mainlevée de péril ordinaire 8 rue Longue Roquevaire.pdf",  # mainlevée (Roquevaire)
# "mainlevée 82L chemin des Lavandières Roquevaire.pdf",  # mainlevée (Roquevaire)
# "mainlevée de péril ordinaire 8-8 bis avenue de Lambesc-26012021.pdf",  # mainlevée (Rognes)
# "11 av des goums - main levee.pdf",  # mainlevée (Aubagne)
# "8, rue Maréchal Foch Roquevaire.PDF",  # PGI ! (Roquevaire)
# "grave 31 rue du Calvaire Roquevaire.pdf",  # PGI ! (Roquevaire)
# "PGI rue docteur Paul Gariel -15122020.PDF",  # PGI ! (Roquevaire)
# "modif Maréchal Foch.PDF",  # modif PGI ! (Roquevaire)


# TODO trouver les trous dans la raquette pour le cadastre:
# cd data/interim/txt_nat ; grep -il "cadastr\|parcell" *.txt |sort |uniq > ../../fn_cadastr_parcell.txt
# cd ../.. ; csvgrep -c par_ref_cad -r "^." runs/2023-03-06T17:10/arretes_peril_compil_data_enr_struct.csv |csvcut -c arr_pdf |sed -e 's/.pdf/.txt/ ; s/^"// ; s/"$// ;' |sort > fn_refcad.txt
# meld fn_cadastr_parcell.txt fn_refcad.txt

import logging

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
def examine_doc_content(fn_pdf: str, doc_content: "list[dict]"):
    """Vérifie des hypothèses de bonne formation sur le contenu extrait du document.

    Parameters
    ----------
    doc_content: list[dict]
        Empans de contenu extraits du document
    """
    # filtrer les pages absentes
    pg_conts = [x for x in doc_content if (pd.notna(x) and x["content"] is not None)]
    # paragraphes
    pars = [
        x
        for pg_content in pg_conts
        for x in pg_content["content"]
        if (pd.notna(x) and x["span_typ"].startswith("par_"))
    ]
    par_typs = [x["span_typ"] for x in pars]
    # "considérant" obligatoire sauf pour certains arrêtés?
    # TODO déterminer si les assertions ne s'appliquent qu'à certaines classes d'arrêtés
    if par_typs:
        # chaque arrêté contient au moins un "vu"
        if "par_vu" not in par_typs:
            logging.warning(
                f"{fn_pdf}: pas de 'vu' trouvé (vérifier la nature du document ?)"
            )

        # chaque arrêté contient au moins un "considérant"
        # * sauf dans les mainlevées et abrogations où dans la pratique ce n'est pas le cas
        if "par_considerant" not in par_typs:
            # FIXME détecter la classe => ne pas appliquer pour abrogations et mainlevées
            logging.warning(
                f"{fn_pdf}: pas de 'considérant' trouvé (vérifier la nature du document ?)"
            )
        # chaque arrêté contient exactement 1 "Arrête"
        try:
            assert len([x for x in par_typs if x == "par_arrete"]) == 1
        except AssertionError:
            logging.warning(
                f"{fn_pdf}: pas de 'Arrête' trouvé (vérifier la qualité de l'OCR ?)"
            )
        # l'ordre relatif (vu | considérant)+ < arrête < (article)+ est vérifié au niveau des transitions admissibles


def error_codeinsee_manquant(df_arr: pd.DataFrame) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés dont le code INSEE est manquant.

    Le code INSEE est déterminé sur base du nom de la commune, croisé avec
    la table des codes communes dans data/external/ (actuellement restreint
    au périmètre de la métropole Aix-Marseille Provence).

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame des arrêtés, contenant les codes INSEE.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées dont le code INSEE est vide.
    """
    return ("Code INSEE manquant", df_arr[df_arr["codeinsee"].isna()])


def error_codeinsee_13055(df_arr: pd.DataFrame) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés dont le code INSEE est 13055.

    13055 est le code pour tout Marseille, alors que l'on devrait
    avoir le code propre à l'arrondissement (13201 à 13216).

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame des arrêtés, contenant les codes INSEE.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées dont le code INSEE vaut 13055.
    """
    return ("Code INSEE 13055", df_arr[df_arr["codeinsee"].dropna() == "13055"])


def error_date_manquante(df_arr: pd.DataFrame) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés dont la date n'a pu être déterminée.

    La cause la plus fréquente est une erreur d'OCR sur une date manuscrite
    ou tamponnée, ou un document mal numérisé ; il est possible que le script
    échoue à extraire la date dans certaines tournures de rédaction.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame des arrêtés.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées dont la date n'a pu être déterminée.
    """
    return ("Date manquante", df_arr[df_arr["date"].isna()])


def error_classe_manquante(df_arr: pd.DataFrame) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés dont la classe n'a pu être déterminée.

    Les causes les plus fréquentes sont une erreur d'OCR sur un document mal
    numérisé, ou une mise en page du document sur plusieurs colonnes qui
    n'est pas explicitement gérée par les scripts actuels, et dont le
    résultat ne permet pas la reconnaissance des motifs recherchés.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame des arrêtés.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées dont la classe n'a pu être déterminée.
    """
    return ("Classe manquante", df_arr[df_arr["classe"].isna()])


def error_urgence_manquante(df_arr: pd.DataFrame) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés dont l'urgence n'a pu être déterminée.

    La cause la plus fréquente est une classe d'arrêté qui ne donne pas
    explicitement cette information.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame des arrêtés.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées dont l'urgence n'a pu être déterminée.
    """
    return ("Urgence manquante", df_arr[df_arr["urgence"].isna()])


def error_voie_manquante(
    df_arr: pd.DataFrame, df_adr: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les adresses d'arrêtés sans voie.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), auquel cas cette information doit être recherchée puis
    renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_par: pd.DataFrame
        DataFrame contenant les parcelles.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les adresses sans voie.
    """
    df_adr_no_voie = df_adr[df_adr["voie"].isna()]
    return ("Adresses sans voie", df_adr_no_voie)


def error_num_voie_manquant(
    df_arr: pd.DataFrame, df_adr: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les adresses d'arrêtés sans numéro de voie.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), auquel cas cette information doit être recherchée puis
    renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement ou totalement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_adr: pd.DataFrame
        DataFrame contenant les adresses.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les adresses sans numéro de voie.
    """
    df_adr_no_num = df_adr[df_adr["num"].isna()]
    return ("Adresses sans numéro de voie", df_adr_no_num)


def error_cpostal_manquant(
    df_arr: pd.DataFrame, df_adr: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les adresses d'arrêtés sans ville.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), ou pas d'adresse incluant la ville, auquel cas la
    ville est déterminée selon d'autres indices (ex: lieu de signature),
    sinon recherchée puis renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_par: pd.DataFrame
        DataFrame contenant les parcelles.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les adresses sans ville.
    """
    df_adr_no_voie = df_adr[df_adr["cpostal"].isna()]
    return ("Adresses sans code postal", df_adr_no_voie)


def error_ville_manquante(
    df_arr: pd.DataFrame, df_adr: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les adresses d'arrêtés sans ville.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), ou pas d'adresse incluant la ville, auquel cas la
    ville est déterminée selon d'autres indices (ex: lieu de signature),
    sinon recherchée puis renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_par: pd.DataFrame
        DataFrame contenant les parcelles.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les adresses sans ville.
    """
    df_adr_no_voie = df_adr[df_adr["ville"].isna()]
    return ("Adresses sans ville", df_adr_no_voie)


def warn_adresse_empty(
    df_arr: pd.DataFrame, df_adr: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés sans aucune adresse.

    Certains arrêtés ne contiennent pas d'adresse (ex: mainlevée,
    abrogation), auquel cas cette information doit être recherchée
    puis renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses
    que les scripts échouent à repérer.

    Ignore les valeurs manquantes.

    C'est une erreur pour l'utilisateur final mais un warning du point de vue
    du script, car la probabilité que l'adresse ne soit pas dans l'arrêté,
    sachant qu'aucune adresse n'a été extraite, est relativement élevée.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_adr: pd.DataFrame
        DataFrame contenant les adresses.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées sans adresse.
    """
    # récupérer toutes les adresses
    df_adr_noadr_idus = set(df_adr[df_adr["ad_brute"].fillna("") == ""]["idu"])
    df_arr_no_adr = df_arr[df_arr["idu"].isin(df_adr_noadr_idus)]
    return ("Aucune adresse", df_arr_no_adr)


def warn_par_ref_cad_empty(
    df_arr: pd.DataFrame, df_par: pd.DataFrame
) -> "tuple[str, pd.DataFrame]":
    """Signale les arrêtés sans aucune référence de parcelle cadastrale.

    Certains arrêtés ne contiennent pas de référence cadastrale, auquel
    cas cette information doit être recherchée puis renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs références cadastrales
    que les scripts échouent à repérer.

    Ignore les valeurs manquantes.

    C'est une erreur pour l'utilisateur final mais un warning du point de vue
    du script, car la probabilité que la référence ne soit pas dans l'arrêté,
    sachant qu'aucune référence n'a été extraite, est élevée.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.
    df_par: pd.DataFrame
        DataFrame contenant les parcelles.

    Returns
    -------
    err: string
        Description de l'erreur
    df_err: pd.DataFrame
        DataFrame contenant les entrées sans parcelle.
    """
    df_par_idus = set(df_par["idu"])
    df_arr_no_par = df_arr[~df_arr["idu"].isin(df_par_idus)]
    return ("Aucune référence cadastrale", df_arr_no_par)


def generate_html_report(
    run: str,
    df_adr: pd.DataFrame,
    df_arr: pd.DataFrame,
    df_not: pd.DataFrame,
    df_par: pd.DataFrame,
) -> str:
    """Générer un rapport d'erreurs en HTML

    Parameters
    ----------
    run: string
        Identifiant de l'exécution
    df_adr: pd.DataFrame
        Adresses
    df_arr: pd.DataFrame
        Arrêtés
    df_not: pd.DataFrame
        Notifiés
    df_par: pd.DataFrame
        Parcelles

    Returns
    -------
    html_report: string
        Rapport HTML
    """
    nb_arretes = len(df_arr)
    # options de mise en forme
    render_links = True
    #
    res = []
    # début et bloc de titre
    res.append("<html>")
    res.append(f"<title>Rapport d'erreurs {run}</title>")
    res.append(f"<h1>Rapport d'erreurs {run}</h1>")

    # informations générales sur le lot analysé
    res.append("<div>")
    res.append(f"Nombre d'arrêtés analysés: {nb_arretes}")
    res.append("</div>")

    ## erreurs graves
    # aucune adresse
    res.append(f"<h2>Aucune adresse</h2>")
    _, df_war = warn_adresse_empty(df_arr, df_adr)
    res.append(f"{df_war.shape[0]} / {nb_arretes}")
    if not df_war.empty:
        res.append(df_war.to_html(render_links=render_links))

    # aucune parcelle
    res.append(f"<h2>Aucune parcelle</h2>")
    _, df_war = warn_par_ref_cad_empty(df_arr, df_par)
    res.append(f"{df_war.shape[0]} / {nb_arretes}")
    if not df_war.empty:
        res.append(df_war.to_html(render_links=render_links))

    # pas de date
    res.append(f"<h2>Date manquante</h2>")
    _, df_err = error_date_manquante(df_arr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # pas de classe
    res.append(f"<h2>Classe manquante</h2>")
    _, df_err = error_classe_manquante(df_arr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # pas de nom de rue
    res.append(f"<h2>Aucun nom de voie</h2>")
    _, df_err = error_voie_manquante(df_arr, df_adr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # pas de code postal
    res.append(f"<h2>Aucun code postal</h2>")
    _, df_err = error_cpostal_manquant(df_arr, df_adr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # pas de ville
    res.append(f"<h2>Aucun nom de ville</h2>")
    _, df_err = error_ville_manquante(df_arr, df_adr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # + code INSEE manquant
    res.append(f"<h2>Code INSEE manquant</h2>")
    _, df_err = error_codeinsee_manquant(df_arr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # + code INSEE 13055
    res.append(f"<h2>Code INSEE 13055</h2>")
    _, df_err = error_codeinsee_13055(df_arr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    ## points d'attention
    # plusieurs parcelles
    # FL: 2023-06-29: inutile?

    # plusieurs adresses
    # FL: 2023-06-29: inutile?

    # pas de numéro de voie
    res.append(f"<h2>Aucun numéro de voie</h2>")
    _, df_err = error_num_voie_manquant(df_arr, df_adr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # pas de procédure urgente
    res.append(f"<h2>Statut inconnu: urgence de la procédure</h2>")
    _, df_err = error_urgence_manquante(df_arr)
    res.append(f"{df_err.shape[0]} / {nb_arretes}")
    if not df_err.empty:
        res.append(df_err.to_html(render_links=render_links))

    # fin du document
    res.append("</html>")
    html_report = "\n".join(res)
    return html_report

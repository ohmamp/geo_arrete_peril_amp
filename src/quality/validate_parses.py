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

import re

ERROR_KEYS = [
    "aucune_date",
    "aucune_classe",
    "manque_urgence",
    "aucun_codeinsee",
    "codeinsee_13055",
    "aucune_parcelle",
    "aucune_adresse",
    "aucun_num_voie",
    "aucune_voie",
    "aucun_cpostal",
    "aucune_ville",
]


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


def error_codeinsee_manquant(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les arrêtés dont le code INSEE est manquant.

    Le code INSEE est déterminé sur base du nom de la commune, croisé avec
    la table des codes communes dans data/external/ (actuellement restreint
    au périmètre de la métropole Aix-Marseille Provence).

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucun_codeinsee"] = df.apply(
        lambda row: 1 if pd.isnull(row.codeinsee) else 0, axis=1
    )
    return df


def error_codeinsee_13055(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les arrêtés dont le code INSEE est 13055.

    13055 est le code pour tout Marseille, alors que l'on devrait
    avoir le code propre à l'arrondissement (13201 à 13216).

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["codeinsee_13055"] = df.apply(
        lambda row: 1
        if not pd.isnull(row.codeinsee) and row.codeinsee == "13055"
        else 0,
        axis=1,
    )
    return df


def error_date_manquante(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les arrêtés dont la date n'a pu être déterminée.

    La cause la plus fréquente est une erreur d'OCR sur une date manuscrite
    ou tamponnée, ou un document mal numérisé ; il est possible que le script
    échoue à extraire la date dans certaines tournures de rédaction.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucune_date"] = df.apply(lambda row: 1 if pd.isnull(row.date) else 0, axis=1)
    return df


def error_classe_manquante(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les arrêtés dont la classe n'a pu être déterminée.

    Les causes les plus fréquentes sont une erreur d'OCR sur un document mal
    numérisé, ou une mise en page du document sur plusieurs colonnes qui
    n'est pas explicitement gérée par les scripts actuels, et dont le
    résultat ne permet pas la reconnaissance des motifs recherchés.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucune_classe"] = df.apply(
        lambda row: 1 if pd.isnull(row.classe) else 0, axis=1
    )
    return df


def error_urgence_manquante(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les arrêtés dont l'urgence n'a pu être déterminée.

    La cause la plus fréquente est une classe d'arrêté qui ne donne pas
    explicitement cette information.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["manque_urgence"] = df.apply(
        lambda row: 1 if pd.isnull(row.urgence) else 0, axis=1
    )
    return df


def error_voie_manquante(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les adresses d'arrêtés sans voie.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), auquel cas cette information doit être recherchée puis
    renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucune_voie"] = df.apply(lambda row: 1 if pd.isnull(row.voie) else 0, axis=1)
    return df


def error_num_voie_manquant(df: pd.DataFrame) -> pd.DataFrame:
    """Signale les adresses d'arrêtés sans numéro de voie.

    Certains arrêtés ne contiennent pas d'adresse (ex: certaines mainlevées
    ou abrogations), auquel cas cette information doit être recherchée puis
    renseignée manuellement.
    D'autres arrêtés contiennent une ou plusieurs adresses que les scripts
    échouent à repérer ou à analyser correctement ou totalement.

    Ignore les valeurs manquantes.

    Parameters
    ----------
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucun_num_voie"] = df.apply(lambda row: 1 if pd.isnull(row.num) else 0, axis=1)
    return df


def error_cpostal_manquant(df: pd.DataFrame) -> pd.DataFrame:
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
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucun_cpostal"] = df.apply(
        lambda row: 1 if pd.isnull(row.cpostal) else 0, axis=1
    )
    return df


def error_ville_manquante(df: pd.DataFrame) -> pd.DataFrame:
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
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucune_ville"] = df.apply(lambda row: 1 if pd.isnull(row.ville) else 0, axis=1)
    return df


def warn_adresse_empty(df: pd.DataFrame) -> pd.DataFrame:
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
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    # récupérer toutes les adresses
    df["aucune_adresse"] = df.apply(
        lambda row: 1 if pd.isnull(row.ad_brute) else 0, axis=1
    )
    return df


def warn_par_ref_cad_empty(df: pd.DataFrame) -> pd.DataFrame:
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
    df: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df: pd.DataFrame
        DataFrame contenant avec une colonne indiquant si cette erreur est présente.
    """
    df["aucune_parcelle"] = df.apply(
        lambda row: 1 if pd.isnull(row.ref_cad) else 0, axis=1
    )
    return df


def drop_no_errors_arr(df_arr: pd.DataFrame) -> pd.DataFrame:
    """Supprime les arrêtés sans erreur.

    Parameters
    ----------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés.

    Returns
    -------
    df_arr: pd.DataFrame
        DataFrame contenant les arrêtés sans erreurs.
    """

    df_arr = df_arr.copy()
    # if none of the keys is equal to 1, then the row has no error
    df_arr["has_error"] = df_arr[ERROR_KEYS].sum(axis=1) > 0
    # delete all the row without error
    df_arr = df_arr[df_arr["has_error"]]
    return df_arr


# Define a function to apply the desired styling
def highlight_value_red(value):
    if value == 1:
        return f'<b><span style="color: red">{value}</span></b>'
    return value


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

    # --- TODO bricolage pour fusionner en aval --- #
    # Merge dataframes based on 'idu' column
    merged_df = (
        df_adr.merge(df_arr, on="idu", how="outer", suffixes=("_df1", "_df2"))
        .merge(df_not, on="idu", how="outer", suffixes=("_df12", "_df3"))
        .merge(df_par, on="idu", how="outer", suffixes=("_df123", "_df4"))
    )

    # fuse duplicate columns
    for index, row in merged_df.iterrows():
        for col in merged_df.columns:
            # Check if the column matches the pattern r".*_df.*"
            if re.match(r".*_df\d+", col):
                # Extract the column name excluding the "df" number
                col_name = re.sub(r"_df\d+", "", col)

                # Check if there are other columns with the same name excluding the "df" number
                matching_cols = [
                    c for c in merged_df.columns if re.match(col_name + r"_df\d+", c)
                ]

                # Find the first non-null value among the matching columns
                non_null_cell = next(
                    (c for c in matching_cols if row[c] is not None), None
                )

                # Assign the value from the first non-null column to the corresponding col_name column
                merged_df.at[index, col_name] = row[non_null_cell]

                # Drop the other matching columns
                merged_df.drop(
                    [c for c in matching_cols if c != non_null_cell],
                    axis=1,
                    inplace=True,
                )

    # drop row with duplicate idu
    merged_df.drop_duplicates(subset="idu", keep="first", inplace=True)

    # reset ID
    merged_df.reset_index(drop=True, inplace=True)

    nb_arretes = len(merged_df)
    # options de mise en forme
    render_links = True

    res = []
    # début et bloc de titre
    res.append("<html>")
    res.append(f"<title>Rapport d'erreurs {run}</title>")
    res.append(f"<h1>Rapport d'erreurs {run}</h1>")

    # informations générales sur le lot analysé
    res.append("<div>")
    res.append(f"Nombre d'arrêtés analysés: {nb_arretes}")
    res.append("</div>")

    # adding error columns to the dataframe, 1 = there is an error, 0 = no error
    # --- aucune adresse --- #
    merged_df = warn_adresse_empty(merged_df)

    # --- aucune parcelle --- #
    merged_df = warn_par_ref_cad_empty(merged_df)

    # --- aucune date --- #
    merged_df = error_date_manquante(merged_df)

    # --- aucune classe --- #
    merged_df = error_classe_manquante(merged_df)

    # --- aucune voie --- #
    merged_df = error_voie_manquante(merged_df)

    # --- aucun code postal --- #
    merged_df = error_cpostal_manquant(merged_df)

    # --- aucune ville --- #
    merged_df = error_ville_manquante(merged_df)

    # --- aucun code INSEE --- #
    merged_df = error_codeinsee_manquant(merged_df)

    # --- code INSEE 13055 --- #
    merged_df = error_codeinsee_13055(merged_df)

    # --- aucun numéro de voie --- #
    merged_df = error_num_voie_manquant(merged_df)

    # --- manquance_urgence --- #
    merged_df = error_urgence_manquante(merged_df)

    # drop rows without errors
    merged_df = drop_no_errors_arr(merged_df)

    # only keep the columns we want to display
    merged_df = merged_df[["idu", *ERROR_KEYS]]

    res.append("<h1>Infos manquantes</h1>")

    """
    ## points d'attention
    # plusieurs parcelles
    # FL: 2023-06-29: inutile?

    # plusieurs adresses
    # FL: 2023-06-29: inutile?
    """

    # --- adding red to errors --- #
    # Apply the styling to the DataFrame
    styled_df = merged_df.applymap(highlight_value_red)

    # remove any 0 and make the cell empty instead
    styled_df = styled_df.replace(0, "")

    # Convert the styled DataFrame to HTML with red highlighting
    html_table = styled_df.to_html(escape=False, render_links=render_links)

    res.append(html_table)

    # fin du document
    res.append("</html>")
    return "\n".join(res)

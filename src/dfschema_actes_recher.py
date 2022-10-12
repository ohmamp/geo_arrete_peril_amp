from pandera import DataFrameSchema, Column, Check, Index, MultiIndex

schema = DataFrameSchema(
    columns={
        "N° Acte": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Nature": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["Actes réglementaires"])],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Matière": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(
                    allowed_values=[
                        "6.1 - Police municipale",
                        "6.4 - Autres actes reglementaires",
                    ]
                )
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Objet": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "État de l'acte": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(allowed_values=["A examiner", "Demande de pièce(s)"])
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Caractère prioritaire": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=[])],
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Mode de transmission": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["Télétransmis"])],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Acte contrôlé": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["1"])],
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Acte annulé": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=[])],
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Service attributaire": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(
                    allowed_values=[
                        "Domaine départemental - CL - Préfecture des Bouches du Rhône"
                    ]
                )
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Date de transmission du courrier simple": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Date de transmission de la lettre d'observation": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Date de demande de transmission complémentaire": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Date de saisie de l'expert": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Date Réponse Expert": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Nature réponse Expert": Column(
            dtype=pandera.engines.pandas_engine.STRING,
            checks=None,
            nullable=True,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Libellé émetteur (ACTES)": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(
                    allowed_values=[
                        "1 meyreuil mairie",
                        "1 trets mairie",
                        "3  ALLAUCH       MAIRIE",
                        "3 AUBAGNE   MAIRIE",
                        "3 LA CIOTAT     MAIRIE",
                        "3 MARSEILLE  MAIRIE",
                        "3 ROQUEVAIRE  MAIRIE",
                        "3 auriol mairie",
                        "4 COMMUNE DE BERRE L ETANG",
                        "4 istres",
                    ]
                )
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Nature émetteur": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(allowed_values=["3-1 - Commune ou commune nouvelle"])
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Tiers de transmission": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(
                    allowed_values=[
                        "Berger Levrault",
                        "DOCAPOSTE  FAST",
                        "Dematis",
                        "OMNIKLES Certeurope",
                    ]
                )
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Département": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["13"])],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Arrondissement": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["3"])],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Région": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[Check.isin(allowed_values=["Provence-Alpes-Côte-d'Azur"])],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
        "Strate": Column(
            dtype=pandera.engines.pandas_engine.Category,
            checks=[
                Check.isin(
                    allowed_values=[
                        "Population supérieure ou égale  à 1 000 000 habitants"
                    ]
                )
            ],
            nullable=False,
            unique=False,
            coerce=False,
            required=True,
            regex=False,
        ),
    },
    index=Index(
        dtype=pandera.engines.numpy_engine.Int64,
        checks=[
            Check.greater_than_or_equal_to(min_value=0.0),
            Check.less_than_or_equal_to(max_value=113.0),
        ],
        nullable=False,
        coerce=False,
        name=None,
    ),
    coerce=True,
    strict=False,
    name=None,
)

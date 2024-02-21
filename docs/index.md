# Index

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence.

## Installation

Veuillez suivre les instructions du [guide d'installation](install).

## Utilisation

### Lancement du script

Dans le terminal WSL (ou l'invite de commande Ubuntu):

Les dossier d'entrées et de sorties sont configurables dans le fichier `scripts/process.sh`.

```sh
conda activate geo-arretes
scripts/process.sh
```

Plusieurs scripts sont définis pour faciliter certaines actions : [scripts](Scripts/scripts).

### Planification de tâches

Le script [runner.bat](https://github.com/ohmamp/geo_arrete_peril_amp/blob/main/runner.bat) est un exemple de script permettant de lancer le script `process.sh` (présent dans le WSL) depuis le Task Scheduler de Windows.

### Logs

Deux types de logs sont disponibles :

- `batch-logs` : dans le dossier `batch-logs` sont stockés un court état des lieux de chaque lancé de script.
- `logs` : dans le dossier `logs` sont stockés les logs détaillés de chaque traitement dans le pipeline du script `process.sh`.

## Documentation

La documentation générée à partir du code source est disponible à l'adresse suivante : [https://geo-arretes.github.io/geo-arretes/](https://ohmamp.github.io/geo_arrete_peril_amp/).

Elle utilise [mkdocs](https://www.mkdocs.org/) et [mkdocstrings](https://mkdocstrings.github.io/) pour automatiquement générer la documentation à partir des docstrings des fonctions et des classes du code source.

```sh
pip install mkdocs==1.5.3 mkdocstrings==0.23.0 mkdocs-material==9.5.10
```

Pour prévisualiser la documentation localement, il suffit d'utiliser la commande suivante :

```sh
mkdocs serve
```

La documentation est alors accessible par défaut à l'adresse suivante : [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Pour déployer la documentation sur une branche, il suffit d'utiliser la commande suivante :

```sh
mkdocs gh-deploy
```

Cela déploiera la documentation sur la branche `gh-pages` du dépôt, qui est automatiquement servie par GitHub Pages.

## Project layout

```sh
data/                   # Datasets
    raw/                    # The original, immutable data dump.
    processed/              # The final, canonical data sets for modeling.
    interim/                # Intermediate data that has been transformed.
    external/               # Data from third party sources.
docs/                   # Documentation
    index.md                # The documentation homepage.
    ...                     # Other markdown pages, images and other files .
    ...                     # that follow the same structure as the project.
notebooks/              # Jupyter notebooks to explore the data and the code.
    explore_actes.ipynb
    test_pds_image.ipynb
src/                    # Source code of this project.
    domain_knowledge/       # Regex pattern and dictionaries used for data extraction.
    preprocess/             # Functions for preprocessing PDF files.
    process/                # Functions for processing PDF files.
    quality/                # Functions for quality control.
    utils/                  # Utility functions.
.gitignore              # Specifies intentionally untracked files to ignore.
environment-prod.yml    # Conda environment file for production.
environment.yml         # Conda environment file for development.
LICENSE                 # MIT Licence.
README.md               # The top level README for developers using this project.
setup.py                # Make this project pip installable with `pip install -e`
```

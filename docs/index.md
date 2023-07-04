# Index

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence

## Installation

### Installation commune: Ubuntu (natif ou Windows Subsystem for Linux)

Dans le terminal WSL (invite de commande Ubuntu):

1. Installer le modèle de Tesseract pour le français

    - `sudo apt update`
    - `sudo apt install tesseract-ocr-fra`

2. [Installer Mambaforge](https://github.com/conda-forge/miniforge#mambaforge):

    - `curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"`
    - `bash Mambaforge-$(uname)-$(uname -m).sh`

3. Créer un environnement virtuel conda à partir du fichier de spécifications `environment-prod.yml`

    ```sh
    mamba env create --file environment-prod.yml
    ```

4. Installer ocrmypdf (maintenant que ses dépendances ont été installées à la
création de l'environnement).

```sh
conda activate geo-arretes
# installer ocrmypdf qui ne pouvait pas être installé en même temps que ses dépendances...
mamba install ocrmypdf
# depuis le dossier où se trouve le code source du projet
pip install -e .
# désactiver et réactiver l'environnement virtuel car tesseract, installé par ocrmypdf,
# a déposé ses fichiers de langage dans un sous-dossier
# `$HOME/mambaforge/envs/geo-arretes/share/tessdata`
# (sinon ils ne seront visibles...)
conda deactivate
```

### Résolution de problèmes

A la création de l'environnement conda, si l'installation d'un paquet échoue avec une erreur étrange, eg. le paquet `vs2015_runtime`, suivre la procédure dans <https://stackoverflow.com/a/65728405>

## Utilisation

```sh
conda activate geo-arretes
scripts/process.sh
```

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
notebooks/              # Jupyter notebooks
    explore_actes.ipynb     # 
    test_pds_image.ipynb    #
src/                    # Source code of this project.
    domain_knowledge/       #
    preprocess/             #
    process/                #
    quality/                #
    utils/                  #
.gitignore              # Specifies intentionally untracked files to ignore.
environment-prod.yml    # Conda environment file for production.
environment.yml         # Conda environment file for development.
LICENSE                 # MIT Licence.
README.md               # The top level README for developers using this project.
setup.py                # Make this project pip installable with `pip install -e`
```

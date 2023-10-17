# Index

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence.

## Installation

### Installation commune: Ubuntu (natif ou Windows Subsystem for Linux)

Dans le terminal WSL (ou l'invite de commande Ubuntu):

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

Sur des serveurs Windows 2019 ou plus anciens, il peut être nécessaire d'installer le WSL via une procédure manuelle décrite [ici](https://learn.microsoft.com/en-us/windows/wsl/install-manual).

En résumé il faut :

- Activer la fonctionnalité Windows "Windows Subsystem for Linux" via la commande `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux`. Un redémarrage du système est nécessaire.
- Télécharger la distribution [Ubuntu 20.04](https://learn.microsoft.com/en-us/windows/wsl/install-manual#downloading-distributions)
- Renommer le fichier `.AppxBundle` téléchargé en `.zip` : `Rename-Item .\CanonicalGroupLimited.UbunutuonWindows_2004.2021.825.0.AppxBundle .\ubuntu.zip`
- Extraire le fichier zip dans un dossier `ubuntu` : `Expand-Archive .\ubuntu.zip .\ubuntu`
- Se déplacer dans le dossier `ubuntu` : `cd .\ubuntu`
- Lancer l'archive correspondant à votre architecture (par exemple, x64) : `Expand-Archive .\Ubuntu_2004.2021.825.0_x64.zip .\ubuntu`
- Ajouter le dossier `Ubuntu` à la variable d'environnement `PATH` : `$userenv = [System.Environment]::GetEnvironmentVariable("Path", "User")` puis `[System.Environment]::SetEnvironmentVariable("PATH", $userenv + ";D:\Logiciels\Ubuntu\Ubuntu", "User")`
- Redémarrer le terminal PowerShell, l'ouvrir en tant qu'administrateur
- Lancer le fichier `ubuntu.exe` contenu dans le dossier `Ubuntu` : `.\ubuntu\ubuntu\ubuntu.exe`

## Utilisation

Dans le terminal WSL (ou l'invite de commande Ubuntu):

Les dossier d'entrées et de sorties sont configurables dans le fichier `scripts/process.sh`.

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
    explore_actes.ipynb     # TODO
    test_pds_image.ipynb    # TODO
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

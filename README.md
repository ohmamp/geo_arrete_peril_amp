# agperils-amp

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence

## Installation

### Installation commune: Ubuntu (natif ou Windows Subsystem for Linux)

Dans le terminal WSL (invite de commande Ubuntu):
1. Installer le modèle de Tesseract pour le français
  * `sudo apt update`
  * `sudo apt install tesseract-ocr-fra`
2. [Installer Mambaforge](https://github.com/conda-forge/miniforge#mambaforge):
  * `curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"`
  * `bash Mambaforge-$(uname)-$(uname -m).sh`
3. Créer un environnement virtuel conda à partir du fichier de spécifications `environment-prod.yml`
```sh
mamba env create --file environment-prod.yml
```
4. Installer ocrmypdf (maintenant que ses dépendances ont été installées à la
création de l'environnement).
```sh
conda activate agperils-amp
# installer ocrmypdf qui ne pouvait pas être installé en même temps que ses dépendances...
mamba install ocrmypdf
# depuis le dossier où se trouve le code source du projet
pip install -e .
# désactiver et réactiver l'environnement virtuel car tesseract, installé par ocrmypdf,
# a déposé ses fichiers de langage dans un sous-dossier
# `$HOME/mambaforge/envs/agperils-amp/share/tessdata`
# (sinon ils ne seront visibles...)
conda deactivate
```

## Utilisation

```sh
conda activate agperils-amp
scripts/preprocess.sh  # FIXME redo
scripts/parsebest.sh  # FIXME parse_doc_direct + redo
time python src/process/parse_doc_direct.py data/raw/actes_2022_traites data/interim/txt_native data/interim/ocr_txt data/processed/actes_2022_traites_ntxt_otxt --redo
```

## Legacy (TODO cleanup)

### Préliminaires Windows (legacy ; broken)

* installer MSVC++ build tools : <https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/>
  * changer les chemins d'installation si nécessaire (ex: sous-dossiers de `D:\Logiciels\`)

* [? Installer ImageMagick pour Wand](https://docs.wand-py.org/en/0.6.2/guide/install.html#install-imagemagick-on-windows)

### Résolution de problèmes

* à la création de l'environnement conda, si l'installation d'un paquet échoue avec une erreur étrange, eg. le paquet `vs2015_runtime`, suivre la procédure dans <https://stackoverflow.com/a/65728405>

# agperils-amp

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence

## Installation

### Installation commune: Ubuntu (natif ou Windows Subsystem for Linux)

1. Dans le terminal WSL, [installer Mambaforge](https://github.com/conda-forge/miniforge#mambaforge):
  * `curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh"`
  * `bash Mambaforge-$(uname)-$(uname -m).sh`

* Créer un environnement virtuel conda à partir du fichier de spécifications `environment-prod.yml`

```sh
mamba env create --file environment-prod.yml
```

* Installer ocrmypdf

Il faut installer séparément ocrmypdf, après ses dépendances installées à la
création de l'environnement par Mamba.

```sh
conda activate agperils-amp
# installer ocrmypdf qui ne pouvait pas être installé en même temps que ses dépendances...
mamba install ocrmypdf
# depuis le dossier où se trouve le code source du projet
pip install -e .
```

## Utilisation

```sh
conda activate agperils-amp
scripts/preprocess.sh  # FIXME redo
scripts/parsebest.sh  # FIXME parse_doc_direct + redo
time python src/process/parse_doc_direct.py data/raw/actes_2022_traites data/interim/txt_native data/interim/ocr_txt data/processed/actes_2022_traites_ntxt_otxt --redo
```

## Legacy (TODO cleanup)

### Windows (legacy), via Windows Subsystem for Linux

1. Installer Ubuntu 22.04 pour le Windows Subsystem for Linux
2. Dans le terminal WSL / Ubuntu (<https://ocrmypdf.readthedocs.io/en/latest/installation.html#ubuntu-lts-latest>):
  * `sudo apt-get update`
  * `sudo apt-get -y install ocrmypdf python3-pip`
  * `pip install --user --upgrade ocrmypdf`
  * `pip install Pillow==9.1.0`
3. Dans l'invite de commande Windows (utile?):
  * `wsl sudo ln -s  /home/$USER/.local/bin/ocrmypdf /usr/local/bin/ocrmypdf`

### Préliminaires Windows (legacy ; broken)

* installer MSVC++ build tools : <https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/>
  * changer les chemins d'installation si nécessaire (ex: sous-dossiers de `D:\Logiciels\`)

* [? Installer ImageMagick pour Wand](https://docs.wand-py.org/en/0.6.2/guide/install.html#install-imagemagick-on-windows)

### Résolution de problèmes

* à la création de l'environnement conda, si l'installation d'un paquet échoue avec une erreur étrange, eg. le paquet `vs2015_runtime`, suivre la procédure dans <https://stackoverflow.com/a/65728405>

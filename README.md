# agperils-amp

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence

## Installation

### Préliminaires Windows

* installer MSVC++ build tools : <https://visualstudio.microsoft.com/fr/visual-cpp-build-tools/>
  * changer les chemins d'installation si nécessaire (ex: sous-dossiers de `D:\Logiciels\`)

* [? Installer ImageMagick pour Wand](https://docs.wand-py.org/en/0.6.2/guide/install.html#install-imagemagick-on-windows)

### Installation commune

* [Installer Mambaforge](https://github.com/conda-forge/miniforge#mambaforge)

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
```

## Utilisation

```sh
conda activate agperils-amp
scripts/preprocess.sh
scripts/parsebest.sh
```

### Résolution de problèmes

* à la création de l'environnement conda, si l'installation d'un paquet échoue avec une erreur étrange, eg. le paquet `vs2015_runtime`, suivre la procédure dans <https://stackoverflow.com/a/65728405>

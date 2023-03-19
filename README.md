# agperils-amp

Analyse et géolocalisation des arrêtés de périls sur le territoire de la métropole Aix-Marseille Provence

## Installation

### Préliminaires Windows

* [Installer ImageMagick pour Wand](https://docs.wand-py.org/en/0.6.2/guide/install.html#install-imagemagick-on-windows)

### Installation commune

1. [Installer Mambaforge](https://github.com/conda-forge/miniforge#mambaforge)

2. Créer un environnement virtuel conda à partir du fichier de spécifications `environment.yml`

```sh
mamba env create --file environment-prod.yml
```

3. Compléter l'installation (à défaire !)

(RESUME HERE)
Erreur CMake: "cmake error at cmakelists.txt generator nmake makefiles does not support platform specification but platform x64 was specified"

* ajouter CMake à la variable d'environnement système PATH: "C:\Program Files\CMake\bin" (trouver le chemin de Cmake sur D: !)
* `pip install dlib` <https://stackoverflow.com/a/52803626>

(end RESUME HERE)

4. Installer ocrmypdf

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
```

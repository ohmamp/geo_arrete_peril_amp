# Scripts

Le dossier `scripts` contient des scripts shell pour automatiser certaines tâches.  
Chacun de ces scripts contient des paramètres d'entrée à configurer en début de fichier.

Le script principal permettant de lancer tout les traitements :

- `process.sh`

Plusieurs scripts pour faciliter le nettoyage des données en cas de problème ou pendant les développements :

- `cleanall.sh` : supprime les fichiers sources et les fichiers générés par les scripts.
- `cleanbest.sh` : supprime les fichiers temporaires et les fichiers générés par les scripts.
- `cleanfast.sh` : supprime uniquement les fichiers temporaires pouvant bloquer les prochains lancements de scripts.
- `cleanpreprocess.sh` : supprime les fichiers temporaraires.

Des scripts pour lancer les scripts de prétraitement des données :

- `parsebest.sh` : lance les scripts de prétraitements des données avec les paramètres aux meilleures performances.
- `parsefast.sh` : lance les scripts de prétraitements des données avec les paramètres les plus rapides.

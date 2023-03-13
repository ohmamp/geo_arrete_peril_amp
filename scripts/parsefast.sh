#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed
#
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# BATCH=hors_marseille_2018_2022
DIR_IN=${DATA_RAW}/arretes_peril_compil
BATCH=arretes_peril_compil

# 6. analyser le texte natif des PDF (pages vides, tampons, accusés de réception), pour déterminer si l'OCR doit être faite (ou refaite)
# (2 entrées: CSV de métadonnées 1 ligne par fichier + CSV de pages de texte 1 ligne par page ;
# 1 sortie: CSV de métadonnées enrichies et données, 1 ligne par page)
python src/process/parse_native_pages.py ${DATA_INT}/${BATCH}_meta_ntxt_filt.csv ${DATA_INT}/${BATCH}_ntxt_pages_filt.csv ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv

# 7. rassembler les données extraites dans chaque document
# 1 entrée: CSV de métadonnées enrichies et données, 1 ligne par page
# 1 sortie: CSV de métadonnées et données 1 ligne par document
python src/process/aggregate_pages.py ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv ${DATA_INT}/${BATCH}_meta_ntxt_doc.csv

# 10. extraire les champs voulus
# (1 entrée: CSV de métadonnées et données ; 1 sortie: CSV de métadonnées et données)
python src/process/extract_data.py ${DATA_INT}/${BATCH}_meta_ntxt_doc.csv ${DATA_INT}/${BATCH}_data.csv

# 11. enrichir les données avec des bases externes
# (1 entrée: CSV de métadonnées et données ; 1 sortie: CSV de métadonnées et données)
python src/process/enrich_data.py ${DATA_INT}/${BATCH}_data.csv ${DATA_INT}/${BATCH}_data_enr.csv

# 12. exporter les données en 4 fichiers CSV pour l'intégration au SIG
python src/process/export_data.py ${DATA_INT}/${BATCH}_data_enr.csv ${DATA_PRO}/${BATCH}
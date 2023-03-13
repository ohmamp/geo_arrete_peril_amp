#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed
#
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# BATCH=hors_marseille_2018_2022
DIR_IN=${DATA_RAW}/arretes_peril_compil
BATCH=arretes_peril_compil

# 1. extraire les métadonnées des fichiers PDF
python src/preprocess/extract_metadata.py ${DIR_IN} ${DATA_INT}/${BATCH}_meta_base.csv

# 2. traiter les métadonnées pour déterminer si ce sont des PDF natifs (textes) ou images
python src/preprocess/process_metadata.py ${DATA_INT}/${BATCH}_meta_base.csv ${DATA_INT}/${BATCH}_meta_proc.csv

# 3. extraire le texte natif des PDF ; 2 sorties: CSV de métadonnées enrichies + dossier pour les fichiers texte natif
python src/preprocess/extract_native_text.py ${DATA_INT}/${BATCH}_meta_proc.csv ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}

# 4. rassembler les pages de texte natif dans un dataframe
python src/preprocess/separate_pages.py ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}/${BATCH}_ntxt_pages.csv

# 5. filtrer les documents qui sont hors périmètre (plan de périmètre de sécurité), et les annexes
python src/preprocess/filter_docs.py ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}/${BATCH}_ntxt_pages.csv ${DATA_INT}/${BATCH}_meta_ntxt_filt.csv ${DATA_INT}/${BATCH}_ntxt_pages_filt.csv

# 8. extraire le texte des PDF par OCR si pertinent, et convertir les PDF originaux en PDF/A archivables contenant du texte natif
# (1 entrée: CSV de métadonnées ; 2 sorties: CSV de métadonnées enrichies (PDF/A et OCR) + dossier pour les fichiers (PDF/A et TXT sidecar OCR))
## python src/preprocess/extract_text_ocr.py ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv ${DATA_INT}/${BATCH}_meta_otxt.csv ${DATA_INT}
# TODO create_pages_dataframe.py ??? RESUME HERE
#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
#
DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
BATCH=hors_marseille_2018_2022
# 1. extraire les métadonnées des fichiers PDF
python src/extract_metadata.py ${DIR_IN} ${DATA_INT}/${BATCH}_meta_base.csv
# 2. traiter les métadonnées pour déterminer si ce sont des PDF natifs (textes) ou images
python src/process_metadata.py ${DATA_INT}/${BATCH}_meta_base.csv ${DATA_INT}/${BATCH}_meta_proc.csv
# 3. extraire le texte natif des PDF ; 2 sorties: CSV de métadonnées enrichies + dossier pour les fichiers texte natif
python src/extract_native_text.py ${DATA_INT}/${BATCH}_meta_proc.csv ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}
# 4. rassembler les pages de texte natif dans un dataframe
python src/separate_pages.py ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}/${BATCH}_ntxt_pages.csv
# 5. analyser le texte natif des PDF (pages vides, tampons, accusés de réception), pour déterminer si l'OCR doit être faite (ou refaite)
# (2 entrées: CSV de métadonnées 1 ligne par fichier + CSV de pages de texte 1 ligne par page ;
# 1 sortie: CSV de métadonnées enrichies et données, 1 ligne par page)
python src/parse_native_pages.py ${DATA_INT}/${BATCH}_meta_ntxt.csv ${DATA_INT}/${BATCH}_ntxt_pages.csv ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv
# 6. rassembler les données extraites dans chaque document
# 1 entrée: CSV de métadonnées enrichies et données, 1 ligne par page
# 1 sortie: CSV de métadonnées et données 1 ligne par document
python src/aggregate_pages.py ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv ${DATA_INT}/${BATCH}_meta_ntxt_doc.csv
# RESUME HERE
# 7. extraire le texte des PDF par OCR si pertinent, et convertir les PDF originaux en PDF/A archivables contenant du texte natif
# (1 entrée: CSV de métadonnées ; 2 sorties: CSV de métadonnées enrichies (PDF/A et OCR) + dossier pour les fichiers (PDF/A et TXT sidecar OCR))
# python src/extract_text_ocr.py ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv ${DATA_INT}/${BATCH}_meta_otxt.csv ${DATA_INT}
# TODO create_pages_dataframe.py ??? RESUME HERE
# 8. extraire la structure du texte: en-têtes, pieds-de-pages, VUs, CONSIDERANTs, ARTICLEs etc.
# (1 entrée: CSV de métadonnées ; 2 sorties: CSV de métadonnées enrichies (?) et CSV d'annotations de structure)
# python src/parse_text_structure.py ${DATA_INT}/${BATCH}_meta_otxt.csv ${DATA_INT}/${BATCH}_meta_pars.csv ${DATA_INT}/${BATCH}_stru.csv
# 9. extraire les champs voulus et générer les 4 tables pour l'intégration au SIG
# (2 entrées: CSV de métadonnées)
# python src/parse_data.py ${DATA_INT}/${BATCH}_meta_pars.csv ${DATA_INT}/${BATCH}_stru.csv ${DATA_INT}/${BATCH}_data.csv
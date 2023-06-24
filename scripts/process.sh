#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed
#
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# DIR_IN=${DATA_RAW}/arretes_peril_compil
# DIR_IN=${DATA_RAW}/actes_2022_traites
DIR_IN=${DATA_RAW}/envoi_amp_arretes_1er_trim_2023/arretes_01_2023
RUN=`date +%FT%T`  # date au format "Y-m-dTH:M:S" (ex: "2023-06-17T12:31:44")

# 1. indexer les fichiers PDF dans le dossier d'entrée:
# calculer le hash de chaque fichier et en faire une copie dans data/interim/pdf-index ,
# extraire les métadonnées et les ajouter à l'index CSV,
# générer un fichier CSV avec les seuls fichiers nouvellement ajoutés
python src/preprocess/index_pdfs.py ${DIR_IN} ${DATA_INT}/pdf-index ${DATA_INT}/pdf-index.csv ${DATA_INT}/pdf-index_new_${RUN}.csv
# RESUME HERE
# TODO arrêter là si aucun nouvel index n'a été généré

# 2. traiter les métadonnées pour déterminer si ce sont des PDF natifs (textes) ou images
python src/preprocess/process_metadata.py ${DATA_INT}/pdf-index_new_${RUN}.csv ${DATA_INT}/meta_${RUN}_proc.csv

# 3. extraire le texte natif des PDF ; 2 sorties: CSV de métadonnées enrichies + dossier pour les fichiers texte natif
python src/preprocess/extract_native_text.py ${DATA_INT}/meta_${RUN}_proc.csv ${DATA_INT}/meta_${RUN}_ntxt.csv ${DATA_INT} 

# 4. déterminer le type des fichiers PDF natifs ("texte") ou non ("image")
# TODO ajouter des indicateurs au niveau de la page? après separate_pages?
python src/preprocess/determine_pdf_type.py ${DATA_INT}/meta_${RUN}_ntxt.csv ${DATA_INT}/meta_${RUN}_ntxt_pdftype.csv 

# 5. rassembler les pages de texte natif dans un dataframe
python src/preprocess/separate_pages.py ${DATA_INT}/meta_${RUN}_ntxt_pdftype.csv ${DATA_INT}/pages_${RUN}_ntxt.csv 

# 6. filtrer les documents qui sont hors périmètre (plan de périmètre de sécurité), et les annexes
python src/preprocess/filter_docs.py ${DATA_INT}/meta_${RUN}_ntxt_pdftype.csv ${DATA_INT}/pages_${RUN}_ntxt.csv ${DATA_INT}/meta_${RUN}_ntxt_filt.csv ${DATA_INT}/pages_${RUN}_ntxt_filt.csv 

# 7. convertir les PDF natifs ("texte") en PDF/A  # (seulement si on ajoute "--keep_pdfa")
python src/preprocess/convert_native_pdf_to_pdfa.py ${DATA_INT}/meta_${RUN}_ntxt_filt.csv ${DATA_INT}/meta_${RUN}_ntxt_pdfa.csv ${DATA_INT} 

# 8. extraire le texte des PDF non natifs par OCR
# (1 entrée: CSV de métadonnées ; 2 sorties: CSV de métadonnées enrichies (OCR) + dossier pour les fichiers (PDF/A et TXT sidecar OCR))
python src/preprocess/extract_text_ocr.py ${DATA_INT}/meta_${RUN}_ntxt_pdfa.csv ${DATA_INT}/meta_${RUN}_otxt.csv ${DATA_INT} 

# 9. analyser le texte des PDF et produire les fichiers paquet_*.csv
python src/process/parse_doc_direct.py data/interim/meta_${RUN}_otxt.csv ${DATA_PRO}
#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed
#
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# DIR_IN=${DATA_RAW}/arretes_peril_compil
# DIR_IN=${DATA_RAW}/actes_2022_traites
DIR_IN=${DATA_RAW}/envoi_amp_arretes_1er_trim_2023/arretes_02_2023
RUN=`date +%FT%T`  # date au format "Y-m-dTH:M:S" (ex: "2023-06-17T12:31:44")

# 0. indexer les fichiers PDF en entrée: copier chaque fichier dans data/interim/pdf-index
# et ajouter le hachage au début du nom du fichier
python src/preprocess/index_pdfs.py ${DIR_IN} ${DATA_INT}/pdf-index ${DATA_INT}/pdf-index.csv ${DATA_INT}/pdf-index_new_${RUN}.csv

# 1. extraire les métadonnées des fichiers PDF
python src/preprocess/extract_metadata.py ${DIR_IN} ${DATA_INT}/${RUN}_meta_base.csv --append

# 2. traiter les métadonnées pour déterminer si ce sont des PDF natifs (textes) ou images
python src/preprocess/process_metadata.py ${DATA_INT}/${RUN}_meta_base.csv ${DATA_INT}/${RUN}_meta_proc.csv --append

# 3. extraire le texte natif des PDF ; 2 sorties: CSV de métadonnées enrichies + dossier pour les fichiers texte natif
python src/preprocess/extract_native_text.py ${DATA_INT}/${RUN}_meta_proc.csv ${DATA_INT}/${RUN}_meta_ntxt.csv ${DATA_INT} --append

# 5. déterminer le type des fichiers PDF natifs ("texte") ou non ("image")
# TODO ajouter des indicateurs au niveau de la page? après separate_pages?
python src/preprocess/determine_pdf_type.py ${DATA_INT}/${RUN}_meta_ntxt.csv ${DATA_INT}/${RUN}_meta_ntxt_pdftype.csv --append

# 4. rassembler les pages de texte natif dans un dataframe
python src/preprocess/separate_pages.py ${DATA_INT}/${RUN}_meta_ntxt_pdftype.csv ${DATA_INT}/${RUN}_ntxt_pages.csv --append

# 6. filtrer les documents qui sont hors périmètre (plan de périmètre de sécurité), et les annexes
python src/preprocess/filter_docs.py ${DATA_INT}/${RUN}_meta_ntxt_pdftype.csv ${DATA_INT}/${RUN}_ntxt_pages.csv ${DATA_INT}/${RUN}_meta_ntxt_filt.csv ${DATA_INT}/${RUN}_ntxt_pages_filt.csv --append

# 7. convertir les PDF natifs ("texte") en PDF/A
python src/preprocess/convert_native_pdf_to_pdfa.py ${DATA_INT}/${RUN}_meta_ntxt_filt.csv ${DATA_INT}/${RUN}_meta_ntxt_pdfa.csv ${DATA_INT} --append

# 8. extraire le texte des PDF non natifs par OCR
# (1 entrée: CSV de métadonnées ; 2 sorties: CSV de métadonnées enrichies (OCR) + dossier pour les fichiers (PDF/A et TXT sidecar OCR))
python src/preprocess/extract_text_ocr.py ${DATA_INT}/${RUN}_meta_ntxt_pdfa.csv ${DATA_INT}/${RUN}_meta_otxt.csv ${DATA_INT} --append

# TODO create_pages_dataframe.py ?
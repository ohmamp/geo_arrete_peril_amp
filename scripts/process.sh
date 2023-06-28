#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed

# local
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# DIR_IN=${DATA_RAW}/arretes_peril_compil
# DIR_IN=${DATA_RAW}/actes_2022_traites_test
DIR_IN=${DATA_RAW}/envoi_amp_arretes_1er_trim_2023/arretes_01_2023_test
DIR_OUT=${DATA_PRO}
#
# serveur  # TODO dotenv
# dossier contenant les PDF à analyser
# DIR_IN=/mnt/d/Fichiers/geo_arretes/peril/pdf_a_analyser
# dossier de sortie:
# - les 4 fichiers paquet_*.csv sont stockés à la racine, et écrasés à chaque exécution,
# - les 4 fichiers paquet avec la date d'exécution sont stockés dans un sous-dossier csv/,
# - les fichiers PDF traités correctement sont dans un dossier par commune, puis année (ex: 13201/2023),
# - les fichiers PDF à reclasser sont dans un dossier temporaire pdf_a_reclasser/
# - les fichiers TXT sont dans le sous-dossier txt/
# DIR_OUT=/mnt/d/Fichiers/geo_arretes/peril

#
RUN=`date +%FT%T`  # date au format "Y-m-dTH:M:S" (ex: "2023-06-17T12:31:44")

# 1. indexer les fichiers PDF dans le dossier d'entrée:
# calculer le hash de chaque fichier et en faire une copie dans data/interim/pdf-index ,
# extraire les métadonnées et les ajouter à l'index CSV,
# générer un fichier CSV avec les seuls fichiers nouvellement ajoutés
NEW_INDEX=${DATA_INT}/pdf-index_new_${RUN}.csv
python src/preprocess/index_pdfs.py ${DIR_IN} ${DATA_INT}/pdf-index ${DATA_INT}/pdf-index.csv ${NEW_INDEX}
# arrêter là si aucun nouveau fichier d'index n'a été généré,
# car aucun PDF dans ${DIR_IN} n'était nouveau
if [ ! -f "${NEW_INDEX}" ]; then
    echo "Arrêt immédiat: aucun nouveau PDF à analyser dans ${DIR_IN}"
    exit 0
fi

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
python src/process/parse_doc_direct.py data/interim/meta_${RUN}_otxt.csv ${DIR_OUT}
#!/usr/bin/env bash
# 1. extraire les métadonnées des fichiers PDF
python src/extract_metadata.py data/raw/arretes_peril_hors_marseille_2018_2022 data/interim/meta_hors_marseille_2018_2022.csv
# 2. traiter les métadonnées pour déterminer si ce sont des PDF natifs (textes) ou images
python src/process_metadata.py data/interim/meta_hors_marseille_2018_2022.csv data/interim/meta_hors_marseille_2018_2022_processed.csv
# 3. extraire le texte natif des PDF
python src/extract_native_text.py data/interim/meta_hors_marseille_2018_2022_processed.csv data/interim/meta_hors_marseille_2018_2022_native_text.csv data/interim
# 4. rassembler les pages de texte natif dans un dataframe
python src/create_pages_dataframe.py data/interim/meta_hors_marseille_2018_2022_native_text.csv data/interim/hors_marseille_2018_2022_native_pages.csv
# 5. évaluer le texte natif des PDF (pages vides, tampons, accusés de réception), pour déterminer si l'OCR doit être faite (ou refaite)
python src/evaluate_native_text.py data/interim/meta_hors_marseille_2018_2022_native_text.csv data/interim/hors_marseille_2018_2022_native_pages.csv data/interim/meta_hors_marseille_2018_2022_native_processed.csv
# 6. extraire le texte des PDF par OCR si pertinent, et convertir les PDF originaux en PDF/A archivables contenant du texte natif
python src/extract_text_ocr.py data/interim/meta_hors_marseille_2018_2022_processed.csv data/interim/meta_hors_marseille_2018_2022_text.csv data/interim
# 7. 
# 8. 
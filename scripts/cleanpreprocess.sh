#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
DATA_PRO=data/processed
#
# DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
# BATCH=hors_marseille_2018_2022
DIR_IN=${DATA_RAW}/arretes_peril_compil
BATCH=arretes_peril_compil

# fichiers produits par parsefast.sh
rm ${DATA_INT}/${BATCH}_meta_base.csv
rm ${DATA_INT}/${BATCH}_meta_proc.csv
rm ${DATA_INT}/${BATCH}_meta_ntxt.csv
rm -Rf data/interim/txt_native/*.txt
rm ${DATA_INT}/${BATCH}_ntxt_pages.csv
rm ${DATA_INT}/${BATCH}_meta_ntxt_filt.csv ${DATA_INT}/${BATCH}_ntxt_pages_filt.csv

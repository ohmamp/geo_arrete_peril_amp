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
rm ${DATA_INT}/${BATCH}_meta_ntxt_proc.csv
rm ${DATA_INT}/${BATCH}_meta_ntxt_doc.csv
rm ${DATA_INT}/${BATCH}_data.csv
rm ${DATA_INT}/${BATCH}_data_enr.csv
rm -Rf ${DATA_PRO}/${BATCH}

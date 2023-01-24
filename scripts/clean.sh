#!/usr/bin/env bash
DATA_RAW=data/raw
DATA_INT=data/interim
#
DIR_IN=${DATA_RAW}/arretes_peril_hors_marseille_2018_2022
BATCH=hors_marseille_2018_2022
#
rm data/interim/${BATCH}_*.csv
rm -Rf data/interim/txt_native/*.txt

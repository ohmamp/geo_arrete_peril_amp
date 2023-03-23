"""Tester parse_doc_direct"""

from pathlib import Path

from src.preprocess.data_sources import EXCLUDE_FILES
from src.process.parse_doc_direct import parse_arrete

DATA_RAW = Path("data/raw")
DATA_INT = Path("data/interim")


fps_pdf = list((DATA_RAW / "arretes_peril_compil").glob("*"))
fps_txt = []
for fp_pdf in fps_pdf:
    # dossier ocr
    fp_txt = DATA_INT / "ocr_txt" / f"{fp_pdf.stem}.txt"
    if fp_txt.is_file():
        fps_txt.append(fp_txt)
        continue
    # sinon dossier txt natif
    fp_txt = DATA_INT / "txt_native" / f"{fp_pdf.stem}.txt"
    if fp_txt.is_file():
        fps_txt.append(fp_txt)

for fp_pdf, fp_txt in zip(fps_pdf, fps_txt):
    if fp_pdf.name not in EXCLUDE_FILES:
        print(fp_pdf)
        x = parse_arrete(fp_pdf, fp_txt)
        print(x)

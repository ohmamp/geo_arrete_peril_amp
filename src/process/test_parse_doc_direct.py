"""Tester parse_doc_direct"""

from datetime import datetime
import logging
from pathlib import Path

from src.preprocess.data_sources import EXCLUDE_FILES
from src.process.parse_doc_direct import parse_arrete

DATA_RAW = Path("data/raw")
DATA_INT = Path("data/interim")


if __name__ == "__main__":
    # log
    dir_log = Path(__file__).resolve().parents[2] / "logs"
    logging.basicConfig(
        filename=f"{dir_log}/test_parse_doc_direct_{datetime.now().isoformat()}.log",
        encoding="utf-8",
        level=logging.DEBUG,
    )

    # filtrage en deux temps, car glob() est case-sensitive (sur linux en tout cas)
    # et l'extension de certains fichiers est ".PDF" plutôt que ".pdf"
    fps_pdf = [
        x
        for x in (DATA_RAW / "arretes_peril_compil").glob("*")
        if x.suffix.lower() == ".pdf"
    ]
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
    assert len(fps_pdf) == len(fps_txt)

    for fp_pdf, fp_txt in zip(fps_pdf, fps_txt):
        if fp_pdf.name not in EXCLUDE_FILES:
            # print(f"---------\n{fp_pdf}")  # DEBUG
            x = parse_arrete(fp_pdf, fp_txt)
            # print(x)  # DEBUG

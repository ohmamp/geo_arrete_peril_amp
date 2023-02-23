from pathlib import Path

from data_sources import EXCLUDE_FILES
from parse_doc import parse_arrete

fps = Path("../data/interim/txt_native/").glob("*.txt")

for i, fp in enumerate(fps):
    if fp.stem + ".pdf" not in EXCLUDE_FILES:
        print(i)
        c = parse_arrete(fp)
        # print(c)

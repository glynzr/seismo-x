import sys
from pathlib import Path
from src.parquet.forensic import extract_flag

src = Path(sys.argv[1])
out = Path(sys.argv[2])

flag = extract_flag(src)
if flag:
    with out.open("a") as f:
        f.write(flag + "\n")
    print(f"[FLAG] {flag}")

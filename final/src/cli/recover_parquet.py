import sys
from pathlib import Path
from src.parquet.recovery import recover_parquet

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

result = recover_parquet(src, dst)
print(result)

#!/bin/bash
set -euo pipefail


if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"


# Absolute path to this script (solutions/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Project root 
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Output directory 
OUT_DIR="$PROJECT_ROOT/processed_data/archive_batch_seismic_readings-parquet"
FLAG_FILE="$OUT_DIR/flag.txt"

# SAFE DIRECTORY CREATION
if [[ -e "$OUT_DIR" && ! -d "$OUT_DIR" ]]; then
  echo "[!] ERROR: $OUT_DIR exists but is not a directory"
  exit 1
fi

mkdir -p "$OUT_DIR"

# Reset flags for THIS run only
: > "$FLAG_FILE"

echo "[*] Input directory : $DATA_DIR"
echo "[*] Output directory: $OUT_DIR"
echo

#processing files
find "$DATA_DIR" -type f -name "*.parquet" | while read -r FILE; do
  BASENAME="$(basename "$FILE")"
  FIXED_FILE="$OUT_DIR/${BASENAME%.parquet}.fixed.parquet"

  echo "=============================================="
  echo "[+] Processing file:"
  echo "    Source : $FILE"

  python3 << EOF
import re
from pathlib import Path

src_path = Path("$FILE")
out_path = Path("$FIXED_FILE")
flag_path = Path("$FLAG_FILE")

data = src_path.read_bytes()

# -------- FLAG EXTRACTION (LOG ONLY) --------
flag_match = re.search(rb"FLAG\{[^}]+\}", data)
if flag_match:
    flag = flag_match.group(0).decode(errors="ignore")
    with flag_path.open("a") as f:
        f.write(f"{flag}\n")
    print("    [FLAG FOUND]")
    print(f"        {flag}")
else:
    print("    [NO FLAG FOUND]")

# -------- PARQUET VALIDATION / RECOVERY --------
last_par1 = data.rfind(b"PAR1")
if last_par1 == -1:
    print("    [SKIPPED] No valid PAR1 footer found")
else:
    fixed_data = data[: last_par1 + 4]
    removed = len(data) - len(fixed_data)

    if removed == 0:
        print("    [PARQUET OK : NO REPAIR NEEDED]")
    else:
        out_path.write_bytes(fixed_data)
        print("    [PARQUET REPAIRED]")
        print(f"        Removed bytes : {removed}")

    if removed > 0:
        print(f"        Output : {out_path}")
EOF

  echo
done

echo "=============================================="
echo "[✓] Processing complete"
echo "[✓] Flags saved to      : $FLAG_FILE"
echo "[✓] Fixed parquet files : $OUT_DIR"

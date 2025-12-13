#!/bin/bash
set -euo pipefail

# ------------------ ARGUMENT CHECK ------------------
if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"

# ------------------ RESOLVE REAL SCRIPT LOCATION ------------------
SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

OUT_DIR="$PROJECT_ROOT/processed_data/recovered-parquet"

# ------------------ SAFE DIRECTORY CREATION ------------------
if [[ -e "$OUT_DIR" && ! -d "$OUT_DIR" ]]; then
  echo "[!] ERROR: $OUT_DIR exists but is not a directory"
  exit 1
fi

mkdir -p "$OUT_DIR"

# ------------------ PYTHON MODULE VISIBILITY ------------------
export PYTHONPATH="$PROJECT_ROOT"

echo "[*] Script location : $SCRIPT_DIR"
echo "[*] Project root    : $PROJECT_ROOT"
echo "[*] Input directory : $DATA_DIR"
echo "[*] Output directory: $OUT_DIR"
echo

# ------------------ PROCESS FILES ------------------
find "$DATA_DIR" -type f -name "*.parquet" | while read -r FILE; do
  BASENAME="$(basename "$FILE")"
  FIXED_FILE="$OUT_DIR/${BASENAME%.parquet}-fixed.parquet"

  echo "=============================================="
  echo "[+] Processing:"
  echo "    Source : $FILE"

  python3 - << EOF
from pathlib import Path
from src.parquet_recovery import recover_parquet

src = Path("$FILE")
dst = Path("$FIXED_FILE")

result = recover_parquet(src, dst)

status = result["status"]
removed = result["removed_bytes"]

if status == "invalid":
    print("    [SKIPPED] No PAR1 footer found")
elif status == "ok":
    print("    [OK] Parquet file already valid")
else:
    print("    [REPAIRED]")
    print(f"        Removed bytes : {removed}")
    print(f"        Output        : {dst}")
EOF

  echo
done

echo "=============================================="
echo "[✓] Parquet recovery completed successfully"
echo "[✓] Output directory : $OUT_DIR"

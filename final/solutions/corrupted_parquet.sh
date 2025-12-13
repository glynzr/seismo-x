#!/bin/bash
set -euo pipefail

if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_ROOT/processed_data/recovered-parquet"

mkdir -p "$OUT_DIR"
export PYTHONPATH="$PROJECT_ROOT"

find "$DATA_DIR" -type f -name "*.parquet" | while read -r FILE; do
  BASENAME="$(basename "$FILE")"
  python3 -m src.cli.recover_parquet "$FILE" "$OUT_DIR/$BASENAME"
done

echo "[✓] Parquet recovery completed"

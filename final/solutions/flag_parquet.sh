#!/bin/bash
set -euo pipefail

if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_ROOT/processed_data/flag"
FLAG_FILE="$OUT_DIR/flag.txt"

mkdir -p "$OUT_DIR"
: > "$FLAG_FILE"

export PYTHONPATH="$PROJECT_ROOT"

find "$DATA_DIR" -type f -name "*.parquet" | while read -r FILE; do
  python3 -m src.cli.extract_flag "$FILE" "$FLAG_FILE"
done

echo "[✓] Flag extraction completed"

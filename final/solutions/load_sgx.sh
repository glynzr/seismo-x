#!/bin/bash
set -euo pipefail

if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_ROOT/processed_data/sgx_converted"

mkdir -p "$OUT_DIR"
export PYTHONPATH="$PROJECT_ROOT"

python3 -m src.cli.load_sgx "$DATA_DIR" "$OUT_DIR"

echo "[✓] SGX conversion completed"

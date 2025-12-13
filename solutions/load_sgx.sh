#!/bin/bash


set -e

# Parse arguments
if [[ "${1:-}" != "--data-dir" || -z "${2:-}" ]]; then
  echo "Usage: $0 --data-dir <directory>"
  exit 1
fi

DATA_DIR="$2"

OUTPUT_DIR="processed_data/sgx_converted"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Run Python script to convert .sgx files
python3 << PYTHON_SCRIPT
import sys
import os
sys.path.insert(0, "$PROJECT_ROOT")

from src.sgx_parser import batch_convert_sgx
import pandas as pd

data_dir = "$DATA_DIR"
output_dir = "$PROJECT_ROOT/processed_data/sgx_converted"

os.makedirs(output_dir, exist_ok=True)

print(f"Converting .sgx files in: {data_dir}")
print(f"Output directory: {output_dir}")

combined_df = batch_convert_sgx(data_dir, output_dir)

if not combined_df.empty:
    # Save combined file
    combined_path = os.path.join(output_dir, 'all_sgx_data.parquet')
    combined_df.to_parquet(combined_path, index=False)
    print(f"\nCombined data saved to: {combined_path}")
    print(f"Total records: {len(combined_df)}")
    print(f"\nData summary:")
    print(combined_df.describe())
else:
    print("No .sgx files found or converted")

PYTHON_SCRIPT

echo ".sgx conversion complete!"


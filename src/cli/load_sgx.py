import sys
from pathlib import Path
import pandas as pd
from src.sgx.parser import parse_traces

data_dir = Path(sys.argv[1])
out_dir = Path(sys.argv[2])

out_dir.mkdir(parents=True, exist_ok=True)

all_rows = []

for sgx_file in data_dir.rglob("*.sgx"):
    raw = sgx_file.read_bytes()

    # ---- HEADER PARSING ----
    survey_type = int.from_bytes(raw[8:10], "little")

    # ---- TRACE PARSING ----
    rows = parse_traces(raw[16:], survey_type)

    if not rows:
        print(f"[SKIPPED] {sgx_file.name} (no valid traces)")
        continue

    df = pd.DataFrame(
        rows,
        columns=["well_id", "depth", "amplitude", "quality", "survey_type"],
    )

    # ---- WRITE PER-FILE PARQUET ----
    out_file = out_dir / f"{sgx_file.stem}.parquet"
    df.to_parquet(out_file, index=False)

    print(f"[OK] {sgx_file.name} → {out_file.name} ({len(df)} rows)")

    all_rows.extend(rows)

# ---- WRITE COMBINED PARQUET ----
if all_rows:
    combined_df = pd.DataFrame(
        all_rows,
        columns=["well_id", "depth", "amplitude", "quality", "survey_type"],
    )

    combined_path = out_dir / "all_sgx.parquet"
    combined_df.to_parquet(combined_path, index=False)

    print(f"\n[✓] Combined parquet written: {combined_path}")
    print(f"[✓] Total records: {len(combined_df)}")
else:
    print("[!] No SGX data converted")

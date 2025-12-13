from pathlib import Path
from deltalake import DeltaTable

DELTA_FACT = Path("delta_lake") / "fact_seismic_readings"

def main():
    # Latest version
    dt_latest = DeltaTable(str(DELTA_FACT))
    latest_version = dt_latest.version()
    latest_count = len(dt_latest.to_pandas())
    print(f"LATEST version: {latest_version} | rows: {latest_count}")

    # Version 0
    dt_v0 = DeltaTable(str(DELTA_FACT), version=0)
    v0_count = len(dt_v0.to_pandas())
    print(f"VERSION 0 | rows: {v0_count}")

    # Simple proof they differ
    print("Row difference (latest - v0) =", latest_count - v0_count)

if __name__ == "__main__":
    main()

from pathlib import Path
import duckdb
from datetime import datetime, timezone

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    base_dir = Path("data/track1_recovered")
    parquet_files = list(base_dir.glob("*.parquet"))

    if not parquet_files:
        raise RuntimeError("No recovered parquet files found in data/track1_recovered")

    load_ts = datetime.now(timezone.utc).isoformat()
    record_source = "track1_recovered"

    con.execute("""
        CREATE OR REPLACE TABLE sat_track1_readings AS
        SELECT
            well_id,
            survey_type_id,
            sensor_id,
            depth_ft,
            amplitude,
            timestamp,
            quality_flag,
            ? AS load_timestamp,
            ? AS record_source,
            filename AS source_file
        FROM read_parquet(?, filename=true)
    """, [load_ts, record_source, str(base_dir / "*.parquet")])

    print(
        "sat_track1_readings rows =",
        con.execute("SELECT COUNT(*) FROM sat_track1_readings").fetchone()[0]
    )

    con.close()

if __name__ == "__main__":
    main()

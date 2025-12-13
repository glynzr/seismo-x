from pathlib import Path
import duckdb
from deltalake import write_deltalake

DB_PATH = Path("warehouse") / "seismic.duckdb"
DELTA_DIR = Path("delta_lake")

def main():
    con = duckdb.connect(str(DB_PATH))

    # Append a small batch to create a NEW VERSION (Version 1)
    df = con.execute("""
        SELECT * FROM fact_seismic_readings
        LIMIT 10
    """).fetchdf()

    write_deltalake(
        str(DELTA_DIR / "fact_seismic_readings"),
        df,
        mode="append"
    )

    print(f"Appended {len(df)} rows to Delta fact_seismic_readings (new version created).")

    con.close()

if __name__ == "__main__":
    main()

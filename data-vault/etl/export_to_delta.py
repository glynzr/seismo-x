from pathlib import Path
import duckdb
import pandas as pd
from deltalake import write_deltalake

DB_PATH = Path("warehouse") / "seismic.duckdb"
DELTA_DIR = Path("delta_lake")

def export_table(con, table_name: str, delta_table_name: str, mode: str):
    df = con.execute(f"SELECT * FROM {table_name}").fetchdf()
    write_deltalake(
        str(DELTA_DIR / delta_table_name),
        df,
        mode=mode  # "overwrite" for first export; "append" for new versions
    )
    print(f"Delta write complete: {delta_table_name} | rows={len(df)} | mode={mode}")

def main():
    DELTA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    # First time: overwrite to create VERSION 0
    export_table(con, "fact_seismic_readings", "fact_seismic_readings", mode="overwrite")
    export_table(con, "mart_well_performance", "mart_well_performance", mode="overwrite")
    export_table(con, "mart_sensor_analysis", "mart_sensor_analysis", mode="overwrite")
    export_table(con, "mart_survey_summary", "mart_survey_summary", mode="overwrite")

    con.close()

if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
import duckdb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default="data/masters",
        help="Path to folder containing master_*.csv (default: data/masters)"
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"--data-dir does not exist: {data_dir}")

    # DuckDB file stored inside your project folder
    db_path = Path("warehouse") / "seismic.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    # Expected master files (CSV)
    wells_csv = data_dir / "master_wells.csv"
    sensors_csv = data_dir / "master_sensors.csv"
    surveys_csv = data_dir / "master_surveys.csv"

    for p in [wells_csv, sensors_csv, surveys_csv]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required file: {p}")

    # Load CSVs into DuckDB tables
    con.execute("CREATE OR REPLACE TABLE stg_master_wells AS SELECT * FROM read_csv_auto(?)", [str(wells_csv)])
    con.execute("CREATE OR REPLACE TABLE stg_master_sensors AS SELECT * FROM read_csv_auto(?)", [str(sensors_csv)])
    con.execute("CREATE OR REPLACE TABLE stg_master_surveys AS SELECT * FROM read_csv_auto(?)", [str(surveys_csv)])

    # Quick validation (row counts)
    wells_count = con.execute("SELECT COUNT(*) FROM stg_master_wells").fetchone()[0]
    sensors_count = con.execute("SELECT COUNT(*) FROM stg_master_sensors").fetchone()[0]
    surveys_count = con.execute("SELECT COUNT(*) FROM stg_master_surveys").fetchone()[0]

    print("Loaded masters into DuckDB successfully:")
    print(f"  stg_master_wells   rows = {wells_count}")
    print(f"  stg_master_sensors rows = {sensors_count}")
    print(f"  stg_master_surveys rows = {surveys_count}")

    con.close()


if __name__ == "__main__":
    main()

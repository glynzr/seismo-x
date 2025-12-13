import duckdb
from pathlib import Path

def main():
    # Portable path
    base_dir = Path("data/track1_recovered")

    parquet_files = list(base_dir.glob("*.parquet"))
    print(f"Found {len(parquet_files)} parquet files\n")

    if not parquet_files:
        print("No parquet files found. Check base_dir path.")
        return

    con = duckdb.connect()

    for p in parquet_files[:3]:
        print("=" * 80)
        print("FILE:", p)
        df = con.execute(
            f"SELECT * FROM read_parquet('{p}') LIMIT 5"
        ).fetchdf()
        print(df)
        print("\nCOLUMNS:")
        print(df.dtypes)

    con.close()

if __name__ == "__main__":
    main()

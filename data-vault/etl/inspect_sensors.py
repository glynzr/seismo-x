import duckdb
import pandas as pd

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    # 1) Columns + types
    desc = con.execute("DESCRIBE stg_master_sensors").fetchdf()
    print("\n=== DESCRIBE stg_master_sensors ===")
    print(desc.to_string(index=False))

    # 2) First rows
    df = con.execute("SELECT * FROM stg_master_sensors LIMIT 10").fetchdf()
    print("\n=== SAMPLE stg_master_sensors (10 rows) ===")
    print(df.to_string(index=False))

    con.close()

if __name__ == "__main__":
    main()

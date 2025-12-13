import duckdb

def show_schema(con, table_name: str):
    print("\n" + "=" * 80)
    print(f"TABLE: {table_name}")
    print("=" * 80)

    # Column names + data types
    rows = con.execute(f"DESCRIBE {table_name}").fetchall()
    for col_name, col_type, *_ in rows:
        print(f"{col_name:<30} {col_type}")

    # Show first 5 rows (so we see example values)
    print("\nSample rows:")
    sample = con.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf()
    print(sample)

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    show_schema(con, "stg_master_wells")
    show_schema(con, "stg_master_sensors")
    show_schema(con, "stg_master_surveys")

    con.close()

if __name__ == "__main__":
    main()

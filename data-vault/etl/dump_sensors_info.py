import duckdb
from pathlib import Path

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    out_path = Path("tests") / "sensors_info.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    desc_df = con.execute("DESCRIBE stg_master_sensors").fetchdf()
    sample_df = con.execute("SELECT * FROM stg_master_sensors LIMIT 20").fetchdf()

    with out_path.open("w", encoding="utf-8") as f:
        f.write("=== DESCRIBE stg_master_sensors ===\n")
        f.write(desc_df.to_string(index=False))
        f.write("\n\n=== SAMPLE stg_master_sensors (20 rows) ===\n")
        f.write(sample_df.to_string(index=False))
        f.write("\n")

    con.close()
    print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()

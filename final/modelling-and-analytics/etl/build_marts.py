from __future__ import annotations
from pathlib import Path
import os
import duckdb

DB_PATH = Path(os.getenv("DB_PATH", "seismo_raw_vault.duckdb"))

def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS mart;")
    con.execute("CREATE SCHEMA IF NOT EXISTS dm;")

    source_format_case = """
      CASE
        WHEN lower(source_file) LIKE '%.parquet' THEN 'parquet'
        WHEN lower(source_file) LIKE '%.sgx' OR lower(source_file) LIKE '%sgx%' THEN 'sgx'
        WHEN lower(source_file) LIKE '%.csv' THEN 'csv'
        ELSE 'unknown'
      END
    """

    con.execute("DROP TABLE IF EXISTS mart.mart_well_performance;")
    con.execute(f"""
      CREATE TABLE mart.mart_well_performance AS
      SELECT
        f.well_key,
        w.well_id,
        w.well_name,
        {source_format_case} AS source_format,
        COUNT(*) AS total_readings,
        AVG(f.amplitude) AS avg_amplitude,
        AVG(CASE WHEN f.quality_flag IS NULL OR f.quality_flag = 0 THEN 1.0 ELSE 0.0 END) AS data_quality_rate,
        MIN(f.event_ts) AS first_ts,
        MAX(f.event_ts) AS last_ts
      FROM dm.fact_sensor_readings f
      LEFT JOIN dm.dim_well w ON f.well_key = w.well_key
      GROUP BY 1,2,3,4;
    """)

    con.execute("DROP TABLE IF EXISTS mart.mart_sensor_analysis;")
    con.execute("""
      CREATE TABLE mart.mart_sensor_analysis AS
      SELECT
        s.sensor_type,
        COUNT(*) AS total_readings,
        AVG(f.amplitude) AS avg_amplitude,
        AVG(CASE WHEN f.quality_flag IS NULL OR f.quality_flag = 0 THEN 1.0 ELSE 0.0 END) AS data_quality_rate,
        MIN(f.event_ts) AS first_ts,
        MAX(f.event_ts) AS last_ts
      FROM dm.fact_sensor_readings f
      LEFT JOIN dm.dim_sensor s ON f.sensor_key = s.sensor_key
      GROUP BY 1;
    """)

    con.execute("DROP TABLE IF EXISTS mart.mart_survey_summary;")
    con.execute(f"""
      CREATE TABLE mart.mart_survey_summary AS
      SELECT
        f.survey_type_key,
        t.survey_type_id,
        t.survey_type,
        {source_format_case} AS source_format,
        COUNT(DISTINCT f.well_key) AS wells_surveyed,
        COUNT(*) AS total_readings,
        AVG(f.amplitude) AS avg_amplitude,
        MIN(f.event_ts) AS first_ts,
        MAX(f.event_ts) AS last_ts
      FROM dm.fact_sensor_readings f
      LEFT JOIN dm.dim_survey_type t ON f.survey_type_key = t.survey_type_key
      GROUP BY 1,2,3,4;
    """)

    print("✅ marts built:")
    for name in ["mart.mart_well_performance", "mart.mart_sensor_analysis", "mart.mart_survey_summary"]:
        c = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f" - {name}: {c} rows")

    con.close()

if __name__ == "__main__":
    main()

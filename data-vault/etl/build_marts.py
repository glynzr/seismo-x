import duckdb
from pathlib import Path
from deltalake import write_deltalake
import shutil

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    # Ensure output folder exists (required by hackathon)
    out_dir = Path("processed_data")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Delta Lake directory
    delta_dir = Path("delta_lake")
    delta_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------
    # mart_well_performance (required)
    # -------------------------------
    # Data quality rate = avg(quality_flag) since quality_flag is 0/1
    con.execute("""
        CREATE OR REPLACE TABLE mart_well_performance AS
        SELECT
            w.well_id,
            w.well_name,
            w.operator,
            f.record_source AS data_source_format,
            COUNT(*) AS total_readings,
            AVG(f.amplitude) AS avg_amplitude,
            AVG(CASE WHEN f.quality_flag IN (0,1) THEN f.quality_flag ELSE NULL END) AS data_quality_rate
        FROM fact_seismic_readings f
        JOIN dim_well w ON f.well_id = w.well_id
        GROUP BY
            w.well_id, w.well_name, w.operator, f.record_source
        ORDER BY w.well_id, f.record_source
    """)

    # -------------------------------
    # mart_sensor_analysis (required)
    # -------------------------------
    con.execute("""
        CREATE OR REPLACE TABLE mart_sensor_analysis AS
        SELECT
            s.sensor_type,
            f.record_source AS data_source_format,
            COUNT(*) AS total_readings,
            AVG(f.amplitude) AS avg_amplitude,
            AVG(CASE WHEN f.quality_flag IN (0,1) THEN f.quality_flag ELSE NULL END) AS data_quality_rate
        FROM fact_seismic_readings f
        JOIN dim_sensor s ON f.sensor_id = s.sensor_id
        GROUP BY s.sensor_type, f.record_source
        ORDER BY s.sensor_type, f.record_source
    """)

    # -------------------------------
    # mart_survey_summary (required)
    # -------------------------------
    # Summarizes data acquisition for different survey types.
    # Counts wells surveyed, total readings, average amplitude, and timestamps,
    # also breaking down data source formats.
    con.execute("""
        CREATE OR REPLACE TABLE mart_survey_summary AS
        SELECT
            st.survey_type_id,
            st.survey_type,
            f.record_source AS data_source_format,
            COUNT(DISTINCT f.well_id) AS wells_surveyed,
            COUNT(*) AS total_readings,
            AVG(f.amplitude) AS avg_amplitude,
            MIN(f.timestamp) AS first_timestamp,
            MAX(f.timestamp) AS last_timestamp
        FROM fact_seismic_readings f
        JOIN dim_survey_type st ON f.survey_type_id = st.survey_type_id
        GROUP BY st.survey_type_id, st.survey_type, f.record_source
        ORDER BY st.survey_type_id, f.record_source
    """)

    # -------------------------------
    # Export marts to processed_data/ as parquet
    # -------------------------------
    con.execute(f"COPY mart_well_performance TO '{out_dir / 'mart_well_performance.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY mart_sensor_analysis TO '{out_dir / 'mart_sensor_analysis.parquet'}' (FORMAT PARQUET)")
    con.execute(f"COPY mart_survey_summary TO '{out_dir / 'mart_survey_summary.parquet'}' (FORMAT PARQUET)")

    # Print row counts for sanity
    print("mart_well_performance rows =", con.execute("SELECT COUNT(*) FROM mart_well_performance").fetchone()[0])
    print("mart_sensor_analysis rows =", con.execute("SELECT COUNT(*) FROM mart_sensor_analysis").fetchone()[0])
    print("mart_survey_summary rows =", con.execute("SELECT COUNT(*) FROM mart_survey_summary").fetchone()[0])
    print(f"Exported parquet files to: {out_dir.resolve()}")

    # -------------------------------
    # Export to Delta Lake for time travel (BONUS)
    # -------------------------------
    print("\nExporting to Delta Lake for time travel...")
    
    # Remove existing Delta Lake tables to avoid schema mismatch errors
    delta_fact_dir = delta_dir / "fact_seismic_readings"
    if delta_fact_dir.exists():
        shutil.rmtree(delta_fact_dir)
        print(f"  Removed existing fact_seismic_readings Delta table")
    
    delta_mwp_dir = delta_dir / "mart_well_performance"
    if delta_mwp_dir.exists():
        shutil.rmtree(delta_mwp_dir)
    
    delta_msa_dir = delta_dir / "mart_sensor_analysis"
    if delta_msa_dir.exists():
        shutil.rmtree(delta_msa_dir)
    
    delta_mss_dir = delta_dir / "mart_survey_summary"
    if delta_mss_dir.exists():
        shutil.rmtree(delta_mss_dir)
    
    # Export fact table to Delta (for time travel)
    fact_df = con.execute("SELECT * FROM fact_seismic_readings").fetchdf()
    write_deltalake(
        str(delta_dir / "fact_seismic_readings"),
        fact_df,
        mode="overwrite"
    )
    print(f"  ✓ Exported fact_seismic_readings to Delta Lake: {len(fact_df)} rows")
    
    # Export marts to Delta Lake
    mwp_df = con.execute("SELECT * FROM mart_well_performance").fetchdf()
    write_deltalake(
        str(delta_dir / "mart_well_performance"),
        mwp_df,
        mode="overwrite"
    )
    print(f"  ✓ Exported mart_well_performance to Delta Lake: {len(mwp_df)} rows")
    
    msa_df = con.execute("SELECT * FROM mart_sensor_analysis").fetchdf()
    write_deltalake(
        str(delta_dir / "mart_sensor_analysis"),
        msa_df,
        mode="overwrite"
    )
    print(f"  ✓ Exported mart_sensor_analysis to Delta Lake: {len(msa_df)} rows")
    
    mss_df = con.execute("SELECT * FROM mart_survey_summary").fetchdf()
    write_deltalake(
        str(delta_dir / "mart_survey_summary"),
        mss_df,
        mode="overwrite"
    )
    print(f"  ✓ Exported mart_survey_summary to Delta Lake: {len(mss_df)} rows")
    print(f"\nDelta Lake tables available at: {delta_dir.resolve()}")

    con.close()

if __name__ == "__main__":
    main()

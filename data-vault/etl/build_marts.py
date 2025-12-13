import duckdb
from pathlib import Path

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    # Ensure output folder exists (required by hackathon)
    out_dir = Path("processed_data")
    out_dir.mkdir(parents=True, exist_ok=True)

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
        FROM (
            SELECT
                well_id, sensor_id, survey_type_id,
                depth_ft, amplitude, quality_flag,
                source_file, record_source,
                CAST(date AS DATE) AS date,
                -- reconstruct timestamp from sat table via join if needed; but we have timestamp in sat_track1_readings
                -- so we will join back to sat_track1_readings on keys later if needed.
                NULL::TIMESTAMP AS timestamp
            FROM fact_seismic_readings
        ) f
        JOIN dim_survey_type st ON f.survey_type_id = st.survey_type_id
        GROUP BY st.survey_type_id, st.survey_type, f.record_source
        ORDER BY st.survey_type_id, f.record_source
    """)

    # The fact table currently doesn't store timestamp; it stores date only.
    # For mart_survey_summary we want min/max timestamps, so we rebuild it directly from sat_track1_readings:
    con.execute("""
        CREATE OR REPLACE TABLE mart_survey_summary AS
        SELECT
            st.survey_type_id,
            st.survey_type,
            r.record_source AS data_source_format,
            COUNT(DISTINCT r.well_id) AS wells_surveyed,
            COUNT(*) AS total_readings,
            AVG(r.amplitude) AS avg_amplitude,
            MIN(r.timestamp) AS first_timestamp,
            MAX(r.timestamp) AS last_timestamp
        FROM sat_track1_readings r
        JOIN dim_survey_type st ON r.survey_type_id = st.survey_type_id
        GROUP BY st.survey_type_id, st.survey_type, r.record_source
        ORDER BY st.survey_type_id, r.record_source
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

    con.close()

if __name__ == "__main__":
    main()

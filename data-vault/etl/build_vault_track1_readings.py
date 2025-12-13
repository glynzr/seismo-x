from pathlib import Path
import duckdb
from datetime import datetime, timezone

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    base_dir = Path("data/track1_recovered")
    parquet_files = list(base_dir.glob("*.parquet"))

    if not parquet_files:
        raise RuntimeError("No recovered parquet files found in data/track1_recovered")

    load_ts = datetime.now(timezone.utc).isoformat()
    record_source = "track1_recovered"

    # First, create staging table with checksum calculation
    con.execute("""
        CREATE OR REPLACE TABLE stg_track1_readings AS
        SELECT
            well_id,
            survey_type_id,
            sensor_id,
            depth_ft,
            amplitude,
            timestamp,
            quality_flag,
            filename AS source_file,
            -- Create a composite key for checksum calculation
            MD5(CONCAT(COALESCE(CAST(well_id AS VARCHAR), ''), '|',
                       COALESCE(CAST(sensor_id AS VARCHAR), ''), '|',
                       COALESCE(CAST(survey_type_id AS VARCHAR), ''), '|',
                       COALESCE(CAST(depth_ft AS VARCHAR), ''), '|',
                       COALESCE(CAST(amplitude AS VARCHAR), ''), '|',
                       COALESCE(CAST(timestamp AS VARCHAR), ''), '|',
                       COALESCE(CAST(quality_flag AS VARCHAR), ''))) AS data_checksum
        FROM read_parquet(?, filename=true)
    """, [str(base_dir / "*.parquet")])

    # SATELLITE: track1 readings with provenance
    con.execute("""
        CREATE OR REPLACE TABLE sat_track1_readings AS
        SELECT
            well_id,
            survey_type_id,
            sensor_id,
            depth_ft,
            amplitude,
            timestamp,
            quality_flag,
            ? AS load_timestamp,
            ? AS record_source,
            source_file,
            data_checksum
        FROM stg_track1_readings
    """, [load_ts, record_source])

    # LINK: connects well, sensor, and survey_type for each reading
    # This creates a many-to-many relationship link table
    con.execute("""
        CREATE OR REPLACE TABLE link_well_sensor_survey AS
        SELECT DISTINCT
            well_id,
            sensor_id,
            survey_type_id,
            ? AS load_timestamp,
            ? AS record_source
        FROM sat_track1_readings
    """, [load_ts, record_source])

    # SATELLITE for the link (carries metadata about the relationship)
    con.execute("""
        CREATE OR REPLACE TABLE sat_link_well_sensor_survey AS
        SELECT
            well_id,
            sensor_id,
            survey_type_id,
            COUNT(*) AS total_readings,
            MIN(timestamp) AS first_reading_time,
            MAX(timestamp) AS last_reading_time,
            AVG(amplitude) AS avg_amplitude,
            AVG(CASE WHEN quality_flag IN (0,1) THEN quality_flag ELSE NULL END) AS avg_quality_flag,
            ? AS load_timestamp,
            ? AS record_source
        FROM sat_track1_readings
        GROUP BY well_id, sensor_id, survey_type_id
    """, [load_ts, record_source])

    print("Data Vault Track1 Readings:")
    print(" sat_track1_readings rows =", con.execute("SELECT COUNT(*) FROM sat_track1_readings").fetchone()[0])
    print(" link_well_sensor_survey rows =", con.execute("SELECT COUNT(*) FROM link_well_sensor_survey").fetchone()[0])
    print(" sat_link_well_sensor_survey rows =", con.execute("SELECT COUNT(*) FROM sat_link_well_sensor_survey").fetchone()[0])

    con.close()

if __name__ == "__main__":
    main()

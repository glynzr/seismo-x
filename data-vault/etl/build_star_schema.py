import duckdb

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    # -----------------------
    # Dimensions
    # -----------------------

    con.execute("""
        CREATE OR REPLACE TABLE dim_well AS
        SELECT
            well_id,
            well_name,
            location_lat,
            location_long,
            operator,
            spud_date
        FROM sat_well_details
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dim_sensor AS
        SELECT
            sensor_id,
            sensor_type,
            calibration_date
        FROM sat_sensor_details
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dim_survey_type AS
        SELECT
            survey_type_id,
            survey_type
        FROM sat_survey_type_details
    """)

    # Time dimension from timestamps in readings
    con.execute("""
        CREATE OR REPLACE TABLE dim_time AS
        SELECT DISTINCT
            CAST(timestamp AS DATE) AS date,
            EXTRACT(year FROM timestamp) AS year,
            EXTRACT(month FROM timestamp) AS month,
            EXTRACT(day FROM timestamp) AS day
        FROM sat_track1_readings
        WHERE timestamp IS NOT NULL
    """)

    # -----------------------
    # Fact table (built from Data Vault)
    # -----------------------
    con.execute("""
        CREATE OR REPLACE TABLE fact_seismic_readings AS
        SELECT
            r.well_id,
            r.sensor_id,
            r.survey_type_id,
            CAST(r.timestamp AS DATE) AS date,
            r.timestamp,
            r.depth_ft,
            r.amplitude,
            r.quality_flag,
            r.source_file,
            r.record_source,
            r.load_timestamp,
            r.data_checksum
        FROM sat_track1_readings r
    """)

    # Print counts for sanity
    print("dim_well rows =", con.execute("SELECT COUNT(*) FROM dim_well").fetchone()[0])
    print("dim_sensor rows =", con.execute("SELECT COUNT(*) FROM dim_sensor").fetchone()[0])
    print("dim_survey_type rows =", con.execute("SELECT COUNT(*) FROM dim_survey_type").fetchone()[0])
    print("dim_time rows =", con.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0])
    print("fact_seismic_readings rows =", con.execute("SELECT COUNT(*) FROM fact_seismic_readings").fetchone()[0])

    con.close()

if __name__ == "__main__":
    main()

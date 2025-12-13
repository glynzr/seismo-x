import duckdb
from datetime import datetime, timezone

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    load_ts = datetime.now(timezone.utc).isoformat()
    record_source = "master_csv"

    # HUB: sensor
    con.execute("""
        CREATE OR REPLACE TABLE hub_sensor AS
        SELECT DISTINCT
            sensor_id,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_sensors
    """, [load_ts, record_source])

    # SAT: sensor details with checksum
    con.execute("""
        CREATE OR REPLACE TABLE sat_sensor_details AS
        SELECT
            sensor_id,
            sensor_type,
            calibration_date,
            MD5(CONCAT(COALESCE(CAST(sensor_id AS VARCHAR), ''), '|',
                       COALESCE(CAST(sensor_type AS VARCHAR), ''), '|',
                       COALESCE(CAST(calibration_date AS VARCHAR), ''))) AS data_checksum,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_sensors
    """, [load_ts, record_source])

    # Quick counts
    print("Created sensor Data Vault tables:")
    print(" hub_sensor =", con.execute("SELECT COUNT(*) FROM hub_sensor").fetchone()[0])
    print(" sat_sensor_details =", con.execute("SELECT COUNT(*) FROM sat_sensor_details").fetchone()[0])

    con.close()

if __name__ == "__main__":
    main()

import duckdb
from datetime import datetime, timezone

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")
    load_ts = datetime.now(timezone.utc).isoformat()
    record_source = "master_csv"

    # HUB: well
    con.execute("""
        CREATE OR REPLACE TABLE hub_well AS
        SELECT
            well_id,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_wells
    """, [load_ts, record_source])

    # SAT: well details (descriptive attributes + provenance)
    con.execute("""
        CREATE OR REPLACE TABLE sat_well_details AS
        SELECT
            well_id,
            well_name,
            location_lat,
            location_long,
            operator,
            spud_date,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_wells
    """, [load_ts, record_source])

    # HUB: survey type
    con.execute("""
        CREATE OR REPLACE TABLE hub_survey_type AS
        SELECT
            survey_type_id,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_surveys
    """, [load_ts, record_source])

    # SAT: survey type details
    con.execute("""
        CREATE OR REPLACE TABLE sat_survey_type_details AS
        SELECT
            survey_type_id,
            survey_type,
            ? AS load_timestamp,
            ? AS record_source
        FROM stg_master_surveys
    """, [load_ts, record_source])

    # Quick counts
    print("Created Data Vault tables:")
    print(" hub_well =", con.execute("SELECT COUNT(*) FROM hub_well").fetchone()[0])
    print(" sat_well_details =", con.execute("SELECT COUNT(*) FROM sat_well_details").fetchone()[0])
    print(" hub_survey_type =", con.execute("SELECT COUNT(*) FROM hub_survey_type").fetchone()[0])
    print(" sat_survey_type_details =", con.execute("SELECT COUNT(*) FROM sat_survey_type_details").fetchone()[0])

    con.close()

if __name__ == "__main__":
    main()


import duckdb

def assert_query_zero(con, sql: str, msg: str):
    val = con.execute(sql).fetchone()[0]
    assert val == 0, f"{msg}. Found {val} bad rows."

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    # 1) No NULL IDs
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_well WHERE well_id IS NULL", "NULL well_id in hub_well")
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_sensor WHERE sensor_id IS NULL", "NULL sensor_id in hub_sensor")
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_survey_type WHERE survey_type_id IS NULL", "NULL survey_type_id in hub_survey_type")

    # 2) Uniqueness of IDs in hubs
    assert_query_zero(con, """
        SELECT COUNT(*) FROM (
            SELECT well_id FROM hub_well GROUP BY well_id HAVING COUNT(*) > 1
        )
    """, "Duplicate well_id in hub_well")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM (
            SELECT sensor_id FROM hub_sensor GROUP BY sensor_id HAVING COUNT(*) > 1
        )
    """, "Duplicate sensor_id in hub_sensor")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM (
            SELECT survey_type_id FROM hub_survey_type GROUP BY survey_type_id HAVING COUNT(*) > 1
        )
    """, "Duplicate survey_type_id in hub_survey_type")

    # 3) Latitude/Longitude sanity checks
    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_well_details
        WHERE location_lat < -90 OR location_lat > 90 OR location_lat IS NULL
    """, "Invalid or NULL location_lat")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_well_details
        WHERE location_long < -180 OR location_long > 180 OR location_long IS NULL
    """, "Invalid or NULL location_long")

    print("All data quality tests PASSED.")
    con.close()

if __name__ == "__main__":
    main()

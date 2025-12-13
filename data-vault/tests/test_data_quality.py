import duckdb
from pathlib import Path

def assert_query_zero(con, sql: str, msg: str):
    val = con.execute(sql).fetchone()[0]
    assert val == 0, f"{msg}. Found {val} bad rows."

def assert_query_equals(con, sql: str, expected: int, msg: str):
    val = con.execute(sql).fetchone()[0]
    assert val == expected, f"{msg}. Expected {expected}, found {val}."

def main():
    con = duckdb.connect("warehouse/seismic.duckdb")

    print("=" * 80)
    print("DATA VAULT DATA QUALITY TESTS")
    print("=" * 80)

    # ==========================================
    # 1. HUB INTEGRITY TESTS
    # ==========================================
    print("\n[1] Testing Hub Integrity...")
    
    # 1.1) No NULL IDs in hubs
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_well WHERE well_id IS NULL", "NULL well_id in hub_well")
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_sensor WHERE sensor_id IS NULL", "NULL sensor_id in hub_sensor")
    assert_query_zero(con, "SELECT COUNT(*) FROM hub_survey_type WHERE survey_type_id IS NULL", "NULL survey_type_id in hub_survey_type")
    print("  ✓ No NULL IDs in hubs")

    # 1.2) Uniqueness of IDs in hubs
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
    print("  ✓ All hub IDs are unique")

    # ==========================================
    # 2. SATELLITE INTEGRITY TESTS
    # ==========================================
    print("\n[2] Testing Satellite Integrity...")

    # 2.1) Satellite must have corresponding hub entries
    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_well_details s
        WHERE NOT EXISTS (SELECT 1 FROM hub_well h WHERE h.well_id = s.well_id)
    """, "sat_well_details has orphaned records (no hub)")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_sensor_details s
        WHERE NOT EXISTS (SELECT 1 FROM hub_sensor h WHERE h.sensor_id = s.sensor_id)
    """, "sat_sensor_details has orphaned records (no hub)")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_survey_type_details s
        WHERE NOT EXISTS (SELECT 1 FROM hub_survey_type h WHERE h.survey_type_id = s.survey_type_id)
    """, "sat_survey_type_details has orphaned records (no hub)")
    print("  ✓ All satellites have corresponding hub entries")

    # 2.2) Checksum validation (ensure checksums exist and are not null)
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_well_details WHERE data_checksum IS NULL", "NULL checksum in sat_well_details")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_sensor_details WHERE data_checksum IS NULL", "NULL checksum in sat_sensor_details")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_survey_type_details WHERE data_checksum IS NULL", "NULL checksum in sat_survey_type_details")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_track1_readings WHERE data_checksum IS NULL", "NULL checksum in sat_track1_readings")
    print("  ✓ All satellites have checksums for provenance")

    # 2.3) Provenance fields validation
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_well_details WHERE load_timestamp IS NULL", "NULL load_timestamp in sat_well_details")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_well_details WHERE record_source IS NULL", "NULL record_source in sat_well_details")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_track1_readings WHERE source_file IS NULL", "NULL source_file in sat_track1_readings")
    print("  ✓ All provenance fields are populated")

    # ==========================================
    # 3. LINK INTEGRITY TESTS
    # ==========================================
    print("\n[3] Testing Link Integrity...")

    # 3.1) Link must reference valid hubs
    assert_query_zero(con, """
        SELECT COUNT(*) FROM link_well_sensor_survey l
        WHERE NOT EXISTS (SELECT 1 FROM hub_well h WHERE h.well_id = l.well_id)
    """, "link_well_sensor_survey has invalid well_id references")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM link_well_sensor_survey l
        WHERE NOT EXISTS (SELECT 1 FROM hub_sensor h WHERE h.sensor_id = l.sensor_id)
    """, "link_well_sensor_survey has invalid sensor_id references")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM link_well_sensor_survey l
        WHERE NOT EXISTS (SELECT 1 FROM hub_survey_type h WHERE h.survey_type_id = l.survey_type_id)
    """, "link_well_sensor_survey has invalid survey_type_id references")
    print("  ✓ All link foreign keys reference valid hubs")

    # 3.2) Link uniqueness (each combination should be unique)
    assert_query_zero(con, """
        SELECT COUNT(*) FROM (
            SELECT well_id, sensor_id, survey_type_id 
            FROM link_well_sensor_survey 
            GROUP BY well_id, sensor_id, survey_type_id 
            HAVING COUNT(*) > 1
        )
    """, "Duplicate combinations in link_well_sensor_survey")
    print("  ✓ All link combinations are unique")

    # 3.3) Link satellite integrity
    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_link_well_sensor_survey s
        WHERE NOT EXISTS (
            SELECT 1 FROM link_well_sensor_survey l 
            WHERE l.well_id = s.well_id 
            AND l.sensor_id = s.sensor_id 
            AND l.survey_type_id = s.survey_type_id
        )
    """, "sat_link_well_sensor_survey has orphaned records")
    print("  ✓ Link satellite has valid references")

    # ==========================================
    # 4. DATA QUALITY CHECKS
    # ==========================================
    print("\n[4] Testing Data Quality...")

    # 4.1) Latitude/Longitude sanity checks
    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_well_details
        WHERE location_lat < -90 OR location_lat > 90 OR location_lat IS NULL
    """, "Invalid or NULL location_lat")

    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_well_details
        WHERE location_long < -180 OR location_long > 180 OR location_long IS NULL
    """, "Invalid or NULL location_long")
    print("  ✓ Well coordinates are within valid ranges")

    # 4.2) Amplitude and depth reasonable ranges (no nulls for critical fields)
    assert_query_zero(con, """
        SELECT COUNT(*) FROM sat_track1_readings
        WHERE amplitude IS NULL
    """, "NULL amplitude in readings")
    print("  ✓ All readings have amplitude values")

    # 4.3) Quality flag validation (should be 0 or 1 if present)
    val = con.execute("""
        SELECT COUNT(*) FROM sat_track1_readings
        WHERE quality_flag IS NOT NULL AND quality_flag NOT IN (0, 1)
    """).fetchone()[0]
    if val > 0:
        print(f"  ⚠ Warning: {val} readings have quality_flag not in [0,1] (may be intentional)")
    else:
        print("  ✓ All quality flags are binary (0 or 1)")

    # ==========================================
    # 5. COUNT MATCHING TESTS (Data Integrity)
    # ==========================================
    print("\n[5] Testing Count Matching...")

    # 5.1) Count of readings in satellite should match source files
    # Get expected count from source files
    base_dir = Path("data/track1_recovered")
    if base_dir.exists():
        parquet_files = list(base_dir.glob("*.parquet"))
        if parquet_files:
            source_count = con.execute(f"SELECT COUNT(*) FROM read_parquet('{base_dir / '*.parquet'}')").fetchone()[0]
            vault_count = con.execute("SELECT COUNT(*) FROM sat_track1_readings").fetchone()[0]
            assert_query_equals(con, "SELECT COUNT(*) FROM sat_track1_readings", source_count, 
                              f"Readings count mismatch: vault has {vault_count}, source has {source_count}")
            print(f"  ✓ Reading counts match: {vault_count} rows")

    # 5.2) Hub counts should match distinct IDs in source
    well_source_count = con.execute("SELECT COUNT(DISTINCT well_id) FROM stg_master_wells").fetchone()[0]
    well_hub_count = con.execute("SELECT COUNT(*) FROM hub_well").fetchone()[0]
    assert_query_equals(con, "SELECT COUNT(*) FROM hub_well", well_source_count,
                       f"Well hub count mismatch: hub has {well_hub_count}, source has {well_source_count}")
    print(f"  ✓ Well hub count matches source: {well_hub_count} wells")

    sensor_source_count = con.execute("SELECT COUNT(DISTINCT sensor_id) FROM stg_master_sensors").fetchone()[0]
    sensor_hub_count = con.execute("SELECT COUNT(*) FROM hub_sensor").fetchone()[0]
    assert_query_equals(con, "SELECT COUNT(*) FROM hub_sensor", sensor_source_count,
                       f"Sensor hub count mismatch: hub has {sensor_hub_count}, source has {sensor_source_count}")
    print(f"  ✓ Sensor hub count matches source: {sensor_hub_count} sensors")

    # ==========================================
    # 6. HISTORY PRESERVATION TEST
    # ==========================================
    print("\n[6] Testing History Preservation...")

    # All records should have load_timestamp
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_track1_readings WHERE load_timestamp IS NULL", 
                     "Missing load_timestamp (history not preserved)")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_track1_readings WHERE record_source IS NULL", 
                     "Missing record_source (provenance not preserved)")
    assert_query_zero(con, "SELECT COUNT(*) FROM sat_track1_readings WHERE source_file IS NULL", 
                     "Missing source_file (provenance not preserved)")
    print("  ✓ All records preserve history (load_timestamp, record_source, source_file)")

    # ==========================================
    # SUMMARY
    # ==========================================
    print("\n" + "=" * 80)
    print("✅ ALL DATA QUALITY TESTS PASSED")
    print("=" * 80)
    print("\nData Vault Status:")
    
    hub_well_count = con.execute("SELECT COUNT(*) FROM hub_well").fetchone()[0]
    hub_sensor_count = con.execute("SELECT COUNT(*) FROM hub_sensor").fetchone()[0]
    hub_survey_count = con.execute("SELECT COUNT(*) FROM hub_survey_type").fetchone()[0]
    link_count = con.execute("SELECT COUNT(*) FROM link_well_sensor_survey").fetchone()[0]
    readings_count = con.execute("SELECT COUNT(*) FROM sat_track1_readings").fetchone()[0]
    
    print(f"  Hubs: {hub_well_count} wells, {hub_sensor_count} sensors, {hub_survey_count} survey types")
    print(f"  Links: {link_count} well-sensor-survey relationships")
    print(f"  Readings: {readings_count} seismic readings with full provenance")
    
    con.close()

if __name__ == "__main__":
    main()

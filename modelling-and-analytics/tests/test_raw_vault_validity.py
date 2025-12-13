from pathlib import Path
import duckdb
import sys

DB_PATH = Path("seismo_raw_vault.duckdb")

def fail(msg: str):
    print(f"[-]TEST FAILED: {msg}")
    sys.exit(1)

def ok(msg: str):
    print(f"[+]{msg}")

con = duckdb.connect(str(DB_PATH))

# A) COUNT RECONCILIATION
stg_archive = con.execute("SELECT COUNT(*) FROM stg.stg_archive_readings").fetchone()[0]
sat_archive = con.execute("SELECT COUNT(*) FROM dv.sat_readings").fetchone()[0]
if stg_archive != sat_archive:
    fail(f"Archive readings count mismatch: STG={stg_archive}, SAT={sat_archive}")
ok("Archive readings counts match")

stg_sgx = con.execute("SELECT COUNT(*) FROM stg.stg_sgx_traces").fetchone()[0]
sat_sgx = con.execute("SELECT COUNT(*) FROM dv.sat_legacy_traces").fetchone()[0]
if stg_sgx != sat_sgx:
    fail(f"SGX trace count mismatch: STG={stg_sgx}, SAT={sat_sgx}")
ok("SGX trace counts match")

# B) HUB UNIQUENESS
dupe_wells = con.execute("""
    SELECT well_hk FROM dv.hub_well
    GROUP BY well_hk HAVING COUNT(*) > 1
""").fetchall()
if dupe_wells:
    fail("Duplicate well_hk found in hub_well")
ok("hub_well hash keys are unique")

dupe_sensors = con.execute("""
    SELECT sensor_hk FROM dv.hub_sensor
    GROUP BY sensor_hk HAVING COUNT(*) > 1
""").fetchall()
if dupe_sensors:
    fail("Duplicate sensor_hk found in hub_sensor")
ok("hub_sensor hash keys are unique")

# C) REFERENTIAL INTEGRITY
orphan_links = con.execute("""
    SELECT COUNT(*) FROM dv.link_well_sensor_survey l
    LEFT JOIN dv.hub_well w ON l.well_hk = w.well_hk
    LEFT JOIN dv.hub_sensor s ON l.sensor_hk = s.sensor_hk
    LEFT JOIN dv.hub_survey_type t ON l.survey_type_hk = t.survey_type_hk
    WHERE w.well_hk IS NULL OR s.sensor_hk IS NULL OR t.survey_type_hk IS NULL
""").fetchone()[0]
if orphan_links > 0:
    fail(f"{orphan_links} orphan records found in link_well_sensor_survey")
ok("No orphan records in link_well_sensor_survey")

orphan_sats = con.execute("""
    SELECT COUNT(*) FROM dv.sat_readings r
    LEFT JOIN dv.link_well_sensor_survey l ON r.wss_hk = l.wss_hk
    WHERE l.wss_hk IS NULL
""").fetchone()[0]
if orphan_sats > 0:
    fail(f"{orphan_sats} orphan satellite readings found")
ok("All satellite readings linked correctly")

# D) PROVENANCE COMPLETENESS
null_provenance = con.execute("""
    SELECT COUNT(*) FROM dv.sat_readings
    WHERE source_file IS NULL OR ingest_dts IS NULL OR file_checksum_sha256 IS NULL
""").fetchone()[0]
if null_provenance > 0:
    fail(f"{null_provenance} satellite records missing provenance")
ok("All satellite records contain full provenance")

# E) HASHDIFF VALIDITY
null_hashdiff = con.execute("""
    SELECT COUNT(*) FROM dv.sat_readings
    WHERE hashdiff IS NULL OR hashdiff = ''
""").fetchone()[0]
if null_hashdiff > 0:
    fail(f"{null_hashdiff} records have missing hashdiff")
ok("All satellite records have valid hashdiffs")

# F) BASIC HISTORY SAFETY (append-only expectation)
# (A strict proof requires audit logs; this is a lightweight sanity check)
bad_ts = con.execute("""
    SELECT COUNT(*) FROM dv.sat_readings
    WHERE load_dts IS NULL OR ingest_dts IS NULL
""").fetchone()[0]
if bad_ts > 0:
    fail("Some sat_readings records missing load_dts/ingest_dts")
ok("Append-only metadata present (load_dts/ingest_dts)")

con.close()
print("\nALL RAW VAULT VALIDITY TESTS PASSED")

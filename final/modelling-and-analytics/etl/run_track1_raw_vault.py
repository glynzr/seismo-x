from __future__ import annotations
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone
import duckdb

# -----------------------
# Config (override via env)
# -----------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

MASTER_WELLS   = Path(os.getenv("DATASET_MASTER_WELLS", DATA_DIR / "master_wells.csv"))
MASTER_SENSORS = Path(os.getenv("DATASET_MASTER_SENSORS", DATA_DIR / "master_sensors.csv"))
MASTER_SURVEYS = Path(os.getenv("DATASET_MASTER_SURVEYS", DATA_DIR / "master_surveys.csv"))

ARCHIVE_RECOVERED = Path(os.getenv("DATASET_ARCHIVE_RECOVERED", DATA_DIR / "archive_batch_seismic_readings.parquet"))
ARCHIVE_BATCH2    = Path(os.getenv("DATASET_ARCHIVE_BATCH2", DATA_DIR / "archive_batch_seismic_readings_2.parquet"))
SGX_ALL           = Path(os.getenv("DATASET_SGX_ALL", DATA_DIR / "all_sgx.parquet"))

DB_PATH = Path(os.getenv("DB_PATH", "seismo_raw_vault.duckdb"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_exists(p: Path):
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p.resolve()}")


def main():
    ingest_dts = datetime.now(timezone.utc).isoformat()

    # Validate inputs
    for f in [MASTER_WELLS, MASTER_SENSORS, MASTER_SURVEYS, ARCHIVE_RECOVERED, ARCHIVE_BATCH2, SGX_ALL]:
        require_exists(f)

    con = duckdb.connect(str(DB_PATH))
    con.execute("PRAGMA threads=4;")

    # ---------------------------
    # 0) SCHEMAS
    # ---------------------------
    con.execute("CREATE SCHEMA IF NOT EXISTS stg;")
    con.execute("CREATE SCHEMA IF NOT EXISTS dv;")

    # ---------------------------
    # 1) PROVENANCE (file-level)
    # ---------------------------
    con.execute("""
        CREATE TABLE IF NOT EXISTS stg.stg_file_provenance (
            source_file VARCHAR,
            checksum_sha256 VARCHAR,
            ingest_dts TIMESTAMP,
            PRIMARY KEY (source_file, checksum_sha256, ingest_dts)
        );
    """)

    files = [MASTER_WELLS, MASTER_SENSORS, MASTER_SURVEYS, ARCHIVE_RECOVERED, ARCHIVE_BATCH2, SGX_ALL]
    for f in files:
        con.execute(
            "INSERT INTO stg.stg_file_provenance VALUES (?, ?, ?)",
            [f.name, sha256_file(f), ingest_dts],
        )

    # ---------------------------
    # 2) STAGING LOADS
    # ---------------------------
    con.execute("DROP TABLE IF EXISTS stg.stg_master_wells;")
    con.execute(f"""
        CREATE TABLE stg.stg_master_wells AS
        SELECT * FROM read_csv_auto('{MASTER_WELLS.as_posix()}', header=true);
    """)

    con.execute("DROP TABLE IF EXISTS stg.stg_master_sensors;")
    con.execute(f"""
        CREATE TABLE stg.stg_master_sensors AS
        SELECT * FROM read_csv_auto('{MASTER_SENSORS.as_posix()}', header=true);
    """)

    con.execute("DROP TABLE IF EXISTS stg.stg_master_surveys;")
    con.execute(f"""
        CREATE TABLE stg.stg_master_surveys AS
        SELECT * FROM read_csv_auto('{MASTER_SURVEYS.as_posix()}', header=true);
    """)

    # Archive readings: union recovered + batch2
    con.execute("DROP TABLE IF EXISTS stg.stg_archive_readings;")
    con.execute(f"""
        CREATE TABLE stg.stg_archive_readings AS
        SELECT well_id, survey_type_id, sensor_id, depth_ft, amplitude, timestamp, quality_flag, '{ARCHIVE_RECOVERED.name}' AS source_file
        FROM read_parquet('{ARCHIVE_RECOVERED.as_posix()}')
        UNION ALL
        SELECT well_id, survey_type_id, sensor_id, depth_ft, amplitude, timestamp, quality_flag, '{ARCHIVE_BATCH2.name}' AS source_file
        FROM read_parquet('{ARCHIVE_BATCH2.as_posix()}');
    """)

    # SGX traces
    con.execute("DROP TABLE IF EXISTS stg.stg_sgx_traces;")
    con.execute(f"""
    CREATE TABLE stg.stg_sgx_traces AS
    SELECT
        well_id,
        survey_type AS survey_type_id,
        depth,
        amplitude,
        quality AS quality_flag,
        '{SGX_ALL.name}' AS source_file
    FROM read_parquet('{SGX_ALL.as_posix()}');
""")



    # ---------------------------
    # 3) DV TABLES
    # ---------------------------
    con.execute("""
        CREATE TABLE IF NOT EXISTS dv.hub_well (
            well_hk VARCHAR PRIMARY KEY,
            well_id BIGINT,
            load_dts TIMESTAMP,
            record_source VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.sat_well_details (
            well_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR,
            hashdiff VARCHAR,
            well_name VARCHAR,
            location_lat DOUBLE,
            location_long DOUBLE,
            operator VARCHAR,
            spud_date VARCHAR,
            source_file VARCHAR,
            ingest_dts TIMESTAMP,
            file_checksum_sha256 VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.hub_sensor (
            sensor_hk VARCHAR PRIMARY KEY,
            sensor_id BIGINT,
            load_dts TIMESTAMP,
            record_source VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.sat_sensor_details (
            sensor_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR,
            hashdiff VARCHAR,
            sensor_type VARCHAR,
            calibration_date VARCHAR,
            source_file VARCHAR,
            ingest_dts TIMESTAMP,
            file_checksum_sha256 VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.hub_survey_type (
            survey_type_hk VARCHAR PRIMARY KEY,
            survey_type_id BIGINT,
            load_dts TIMESTAMP,
            record_source VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.sat_survey_type_details (
            survey_type_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR,
            hashdiff VARCHAR,
            survey_type VARCHAR,
            source_file VARCHAR,
            ingest_dts TIMESTAMP,
            file_checksum_sha256 VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.link_well_sensor_survey (
            wss_hk VARCHAR PRIMARY KEY,
            well_hk VARCHAR,
            sensor_hk VARCHAR,
            survey_type_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.sat_readings (
            wss_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR,
            hashdiff VARCHAR,
            event_ts TIMESTAMP,
            depth_ft DOUBLE,
            amplitude DOUBLE,
            quality_flag BIGINT,
            source_file VARCHAR,
            ingest_dts TIMESTAMP,
            file_checksum_sha256 VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.link_well_survey (
            ws_hk VARCHAR PRIMARY KEY,
            well_hk VARCHAR,
            survey_type_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR
        );

        CREATE TABLE IF NOT EXISTS dv.sat_legacy_traces (
            ws_hk VARCHAR,
            load_dts TIMESTAMP,
            record_source VARCHAR,
            hashdiff VARCHAR,
            depth DOUBLE,
            amplitude DOUBLE,
            quality_flag BIGINT,
            legacy_source_file VARCHAR,
            ingest_dts TIMESTAMP,
            file_checksum_sha256 VARCHAR
        );
    """)

    # ---------------------------
    # 4) LOAD HUBS
    # ---------------------------
    con.execute(f"""
        INSERT INTO dv.hub_well
        SELECT DISTINCT
            sha256(CAST(well_id AS VARCHAR)) AS well_hk,
            well_id,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_wells' AS record_source
        FROM stg.stg_master_wells
        WHERE well_id IS NOT NULL
        AND sha256(CAST(well_id AS VARCHAR)) NOT IN (SELECT well_hk FROM dv.hub_well);
    """)

    con.execute(f"""
        INSERT INTO dv.hub_sensor
        SELECT DISTINCT
            sha256(CAST(sensor_id AS VARCHAR)) AS sensor_hk,
            sensor_id,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_sensors' AS record_source
        FROM stg.stg_master_sensors
        WHERE sensor_id IS NOT NULL
        AND sha256(CAST(sensor_id AS VARCHAR)) NOT IN (SELECT sensor_hk FROM dv.hub_sensor);
    """)

    con.execute(f"""
        INSERT INTO dv.hub_survey_type
        SELECT DISTINCT
            sha256(CAST(survey_type_id AS VARCHAR)) AS survey_type_hk,
            survey_type_id,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_surveys' AS record_source
        FROM stg.stg_master_surveys
        WHERE survey_type_id IS NOT NULL
        AND sha256(CAST(survey_type_id AS VARCHAR)) NOT IN (SELECT survey_type_hk FROM dv.hub_survey_type);
    """)

    # ---------------------------
    # 5) LOAD SATS (masters)
    # ---------------------------
    con.execute(f"""
        INSERT INTO dv.sat_well_details
        SELECT
            sha256(CAST(w.well_id AS VARCHAR)) AS well_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_wells' AS record_source,
            sha256(concat_ws('|',
                COALESCE(w.well_name, ''),
                COALESCE(CAST(w.location_lat AS VARCHAR), ''),
                COALESCE(CAST(w.location_long AS VARCHAR), ''),
                COALESCE(w.operator, ''),
                COALESCE(CAST(w.spud_date AS VARCHAR), '')
            )) AS hashdiff,
            w.well_name, w.location_lat, w.location_long, w.operator, CAST(w.spud_date AS VARCHAR) AS spud_date,
            '{MASTER_WELLS.name}' AS source_file,
            '{ingest_dts}'::TIMESTAMP AS ingest_dts,
            (SELECT checksum_sha256 FROM stg.stg_file_provenance WHERE source_file='{MASTER_WELLS.name}' ORDER BY ingest_dts DESC LIMIT 1) AS file_checksum_sha256
        FROM stg.stg_master_wells w;
    """)

    con.execute(f"""
        INSERT INTO dv.sat_sensor_details
        SELECT
            sha256(CAST(s.sensor_id AS VARCHAR)) AS sensor_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_sensors' AS record_source,
            sha256(concat_ws('|', COALESCE(s.sensor_type,''), COALESCE(CAST(s.calibration_date AS VARCHAR),''))) AS hashdiff,
            s.sensor_type, CAST(s.calibration_date AS VARCHAR) AS calibration_date,
            '{MASTER_SENSORS.name}' AS source_file,
            '{ingest_dts}'::TIMESTAMP AS ingest_dts,
            (SELECT checksum_sha256 FROM stg.stg_file_provenance WHERE source_file='{MASTER_SENSORS.name}' ORDER BY ingest_dts DESC LIMIT 1) AS file_checksum_sha256
        FROM stg.stg_master_sensors s;
    """)

    con.execute(f"""
        INSERT INTO dv.sat_survey_type_details
        SELECT
            sha256(CAST(t.survey_type_id AS VARCHAR)) AS survey_type_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'master_surveys' AS record_source,
            sha256(COALESCE(t.survey_type,'')) AS hashdiff,
            t.survey_type,
            '{MASTER_SURVEYS.name}' AS source_file,
            '{ingest_dts}'::TIMESTAMP AS ingest_dts,
            (SELECT checksum_sha256 FROM stg.stg_file_provenance WHERE source_file='{MASTER_SURVEYS.name}' ORDER BY ingest_dts DESC LIMIT 1) AS file_checksum_sha256
        FROM stg.stg_master_surveys t;
    """)

    # ---------------------------
    # 6) LOAD LINKS + SATS (archive readings)
    # ---------------------------
    con.execute(f"""
        INSERT INTO dv.link_well_sensor_survey
        SELECT DISTINCT
            sha256(concat_ws('|',
                CAST(well_id AS VARCHAR),
                CAST(sensor_id AS VARCHAR),
                CAST(survey_type_id AS VARCHAR)
            )) AS wss_hk,
            sha256(CAST(well_id AS VARCHAR)) AS well_hk,
            sha256(CAST(sensor_id AS VARCHAR)) AS sensor_hk,
            sha256(CAST(survey_type_id AS VARCHAR)) AS survey_type_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'archive_readings' AS record_source
        FROM stg.stg_archive_readings
        WHERE well_id IS NOT NULL AND sensor_id IS NOT NULL AND survey_type_id IS NOT NULL
        AND sha256(concat_ws('|', CAST(well_id AS VARCHAR), CAST(sensor_id AS VARCHAR), CAST(survey_type_id AS VARCHAR)))
            NOT IN (SELECT wss_hk FROM dv.link_well_sensor_survey);
    """)

    con.execute(f"""
        INSERT INTO dv.sat_readings
        SELECT
            sha256(concat_ws('|', CAST(r.well_id AS VARCHAR), CAST(r.sensor_id AS VARCHAR), CAST(r.survey_type_id AS VARCHAR))) AS wss_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'archive_readings' AS record_source,
            sha256(concat_ws('|',
                COALESCE(CAST(r.timestamp AS VARCHAR),''),
                COALESCE(CAST(r.depth_ft AS VARCHAR),''),
                COALESCE(CAST(r.amplitude AS VARCHAR),''),
                COALESCE(CAST(r.quality_flag AS VARCHAR),'')
            )) AS hashdiff,
            r.timestamp AS event_ts,
            r.depth_ft, r.amplitude, r.quality_flag,
            r.source_file,
            '{ingest_dts}'::TIMESTAMP AS ingest_dts,
            (SELECT checksum_sha256 FROM stg.stg_file_provenance p
             WHERE p.source_file = r.source_file ORDER BY ingest_dts DESC LIMIT 1) AS file_checksum_sha256
        FROM stg.stg_archive_readings r
        WHERE r.well_id IS NOT NULL AND r.sensor_id IS NOT NULL AND r.survey_type_id IS NOT NULL;
    """)

    # ---------------------------
    # 7) LOAD LINKS + SATS (SGX legacy traces)
    # ---------------------------
    con.execute(f"""
        INSERT INTO dv.link_well_survey
        SELECT DISTINCT
            sha256(concat_ws('|', CAST(well_id AS VARCHAR), CAST(survey_type_id AS VARCHAR))) AS ws_hk,
            sha256(CAST(well_id AS VARCHAR)) AS well_hk,
            sha256(CAST(survey_type_id AS VARCHAR)) AS survey_type_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'sgx_traces' AS record_source
        FROM stg.stg_sgx_traces
        WHERE well_id IS NOT NULL AND survey_type_id IS NOT NULL
        AND sha256(concat_ws('|', CAST(well_id AS VARCHAR), CAST(survey_type_id AS VARCHAR)))
            NOT IN (SELECT ws_hk FROM dv.link_well_survey);
    """)

    con.execute(f"""
        INSERT INTO dv.sat_legacy_traces
        SELECT
            sha256(concat_ws('|', CAST(t.well_id AS VARCHAR), CAST(t.survey_type_id AS VARCHAR))) AS ws_hk,
            '{ingest_dts}'::TIMESTAMP AS load_dts,
            'sgx_traces' AS record_source,
            sha256(concat_ws('|',
                COALESCE(CAST(t.depth AS VARCHAR),''),
                COALESCE(CAST(t.amplitude AS VARCHAR),''),
                COALESCE(CAST(t.quality_flag AS VARCHAR),''),
                COALESCE(t.source_file,'')
            )) AS hashdiff,
            t.depth, t.amplitude, t.quality_flag,
            t.source_file AS legacy_source_file,
            '{ingest_dts}'::TIMESTAMP AS ingest_dts,
            (SELECT checksum_sha256 FROM stg.stg_file_provenance
             WHERE source_file='{SGX_ALL.name}' ORDER BY ingest_dts DESC LIMIT 1) AS file_checksum_sha256
        FROM stg.stg_sgx_traces t;
    """)

    # ---------------------------
    # 8) QUICK COUNTS
    # ---------------------------
    checks = con.execute("""
        SELECT
          (SELECT COUNT(*) FROM stg.stg_master_wells) AS stg_wells,
          (SELECT COUNT(*) FROM dv.hub_well)          AS hub_wells,
          (SELECT COUNT(*) FROM stg.stg_master_sensors) AS stg_sensors,
          (SELECT COUNT(*) FROM dv.hub_sensor)          AS hub_sensors,
          (SELECT COUNT(*) FROM stg.stg_master_surveys) AS stg_surveys,
          (SELECT COUNT(*) FROM dv.hub_survey_type)     AS hub_surveys,
          (SELECT COUNT(*) FROM stg.stg_archive_readings) AS stg_archive_rows,
          (SELECT COUNT(*) FROM dv.sat_readings)          AS sat_archive_rows,
          (SELECT COUNT(*) FROM stg.stg_sgx_traces) AS stg_sgx_rows,
          (SELECT COUNT(*) FROM dv.sat_legacy_traces) AS sat_sgx_rows;
    """).fetchall()[0]

    print("✅ Raw Vault built:", DB_PATH.resolve())
    print("Counts:", checks)

    con.close()


if __name__ == "__main__":
    main()

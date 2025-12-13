from __future__ import annotations
import os
from pathlib import Path
import duckdb

DB_PATH = Path(os.getenv("DB_PATH", "seismo_raw_vault.duckdb"))

def main():
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE SCHEMA IF NOT EXISTS dm;")

    # dim_well (latest sat per hub)
    con.execute("DROP TABLE IF EXISTS dm.dim_well;")
    con.execute("""
        CREATE TABLE dm.dim_well AS
        SELECT
            h.well_hk                                  AS well_key,
            h.well_id                                  AS well_id,
            w.well_name                                AS well_name,
            w.location_lat                             AS lat,
            w.location_long                            AS lon,
            w.operator                                 AS operator,
            w.spud_date                                AS spud_date
        FROM dv.hub_well h
        LEFT JOIN (
            SELECT *
            FROM dv.sat_well_details
            QUALIFY ROW_NUMBER() OVER (PARTITION BY well_hk ORDER BY load_dts DESC) = 1
        ) w ON h.well_hk = w.well_hk;
    """)

    # dim_sensor
    con.execute("DROP TABLE IF EXISTS dm.dim_sensor;")
    con.execute("""
        CREATE TABLE dm.dim_sensor AS
        SELECT
            h.sensor_hk                                AS sensor_key,
            h.sensor_id                                AS sensor_id,
            s.sensor_type                              AS sensor_type,
            s.calibration_date                         AS calibration_date
        FROM dv.hub_sensor h
        LEFT JOIN (
            SELECT *
            FROM dv.sat_sensor_details
            QUALIFY ROW_NUMBER() OVER (PARTITION BY sensor_hk ORDER BY load_dts DESC) = 1
        ) s ON h.sensor_hk = s.sensor_hk;
    """)

    # dim_survey_type
    con.execute("DROP TABLE IF EXISTS dm.dim_survey_type;")
    con.execute("""
        CREATE TABLE dm.dim_survey_type AS
        SELECT
            h.survey_type_hk                           AS survey_type_key,
            h.survey_type_id                           AS survey_type_id,
            t.survey_type                              AS survey_type
        FROM dv.hub_survey_type h
        LEFT JOIN (
            SELECT *
            FROM dv.sat_survey_type_details
            QUALIFY ROW_NUMBER() OVER (PARTITION BY survey_type_hk ORDER BY load_dts DESC) = 1
        ) t ON h.survey_type_hk = t.survey_type_hk;
    """)

    # dim_time (from readings)
    con.execute("DROP TABLE IF EXISTS dm.dim_time;")
    con.execute("""
        CREATE TABLE dm.dim_time AS
        SELECT DISTINCT
            CAST(event_ts AS DATE)                     AS date_key,
            EXTRACT(YEAR FROM event_ts)                AS year,
            EXTRACT(MONTH FROM event_ts)               AS month,
            EXTRACT(DAY FROM event_ts)                 AS day,
            EXTRACT(DOW FROM event_ts)                 AS day_of_week,
            EXTRACT(HOUR FROM event_ts)                AS hour
        FROM dv.sat_readings
        WHERE event_ts IS NOT NULL;
    """)

    # dim_strata (derived bands, 100ft)
    con.execute("DROP TABLE IF EXISTS dm.dim_strata;")
    con.execute("""
        CREATE TABLE dm.dim_strata AS
        WITH bands AS (
          SELECT DISTINCT
            CAST(FLOOR(depth_ft / 100) * 100 AS BIGINT) AS band_start_ft
          FROM dv.sat_readings
          WHERE depth_ft IS NOT NULL
        )
        SELECT
          band_start_ft                                 AS strata_key,
          band_start_ft                                 AS depth_from_ft,
          band_start_ft + 100                           AS depth_to_ft,
          CONCAT(CAST(band_start_ft AS VARCHAR), '-', CAST(band_start_ft + 100 AS VARCHAR), ' ft') AS strata_label
        FROM bands;
    """)

    # fact_sensor_readings
    con.execute("DROP TABLE IF EXISTS dm.fact_sensor_readings;")
    con.execute("""
        CREATE TABLE dm.fact_sensor_readings AS
        SELECT
            CAST(r.event_ts AS DATE)                     AS date_key,
            l.well_hk                                    AS well_key,
            l.sensor_hk                                  AS sensor_key,
            l.survey_type_hk                             AS survey_type_key,
            CAST(FLOOR(r.depth_ft / 100) * 100 AS BIGINT) AS strata_key,
            r.event_ts                                   AS event_ts,
            r.depth_ft                                   AS depth_ft,
            r.amplitude                                  AS amplitude,
            r.quality_flag                               AS quality_flag,
            r.source_file                                AS source_file,
            r.ingest_dts                                 AS ingest_dts,
            r.file_checksum_sha256                       AS file_checksum_sha256
        FROM dv.sat_readings r
        JOIN dv.link_well_sensor_survey l ON r.wss_hk = l.wss_hk;
    """)

    # fact_survey_events
    con.execute("DROP TABLE IF EXISTS dm.fact_survey_events;")
    con.execute("""
        CREATE TABLE dm.fact_survey_events AS
        SELECT
            CAST(r.event_ts AS DATE)                     AS date_key,
            l.well_hk                                    AS well_key,
            l.survey_type_hk                             AS survey_type_key,
            COUNT(*)                                     AS reading_count,
            AVG(r.amplitude)                             AS avg_amplitude,
            MIN(r.amplitude)                             AS min_amplitude,
            MAX(r.amplitude)                             AS max_amplitude,
            SUM(CASE WHEN r.quality_flag IS NOT NULL AND r.quality_flag != 0 THEN 1 ELSE 0 END) AS nonzero_quality_count
        FROM dv.sat_readings r
        JOIN dv.link_well_sensor_survey l ON r.wss_hk = l.wss_hk
        WHERE r.event_ts IS NOT NULL
        GROUP BY 1,2,3;
    """)

    # fact_anomalies (quality flag != 0 OR 3-sigma outlier per sensor)
    con.execute("DROP TABLE IF EXISTS dm.fact_anomalies;")
    con.execute("""
        CREATE TABLE dm.fact_anomalies AS
        WITH stats AS (
          SELECT
            l.sensor_hk AS sensor_key,
            AVG(r.amplitude) AS mu,
            STDDEV_SAMP(r.amplitude) AS sigma
          FROM dv.sat_readings r
          JOIN dv.link_well_sensor_survey l ON r.wss_hk = l.wss_hk
          WHERE r.amplitude IS NOT NULL
          GROUP BY 1
        )
        SELECT
            CAST(r.event_ts AS DATE)                     AS date_key,
            l.well_hk                                    AS well_key,
            l.sensor_hk                                  AS sensor_key,
            l.survey_type_hk                             AS survey_type_key,
            CAST(FLOOR(r.depth_ft / 100) * 100 AS BIGINT) AS strata_key,
            r.event_ts                                   AS event_ts,
            r.depth_ft                                   AS depth_ft,
            r.amplitude                                  AS amplitude,
            r.quality_flag                               AS quality_flag,
            CASE
              WHEN r.quality_flag IS NOT NULL AND r.quality_flag != 0 THEN 'QUALITY_FLAG'
              WHEN s.sigma IS NOT NULL AND ABS(r.amplitude - s.mu) > 3*s.sigma THEN 'AMPLITUDE_OUTLIER_3SIGMA'
              ELSE 'UNKNOWN'
            END AS anomaly_type,
            r.source_file                                AS source_file,
            r.ingest_dts                                 AS ingest_dts,
            r.file_checksum_sha256                       AS file_checksum_sha256
        FROM dv.sat_readings r
        JOIN dv.link_well_sensor_survey l ON r.wss_hk = l.wss_hk
        LEFT JOIN stats s ON l.sensor_hk = s.sensor_key
        WHERE (r.quality_flag IS NOT NULL AND r.quality_flag != 0)
           OR (s.sigma IS NOT NULL AND ABS(r.amplitude - s.mu) > 3*s.sigma);
    """)

    counts = con.execute("""
      SELECT
        (SELECT COUNT(*) FROM dm.fact_sensor_readings) AS fact_readings,
        (SELECT COUNT(*) FROM dm.fact_survey_events)  AS fact_events,
        (SELECT COUNT(*) FROM dm.fact_anomalies)      AS fact_anomalies,
        (SELECT COUNT(*) FROM dm.dim_well)            AS dim_well,
        (SELECT COUNT(*) FROM dm.dim_sensor)          AS dim_sensor,
        (SELECT COUNT(*) FROM dm.dim_survey_type)     AS dim_survey_type,
        (SELECT COUNT(*) FROM dm.dim_time)            AS dim_time,
        (SELECT COUNT(*) FROM dm.dim_strata)          AS dim_strata;
    """).fetchone()

    print("✅ Dimensional model built in schema dm.*")
    print("Counts:", counts)

    con.close()

if __name__ == "__main__":
    main()

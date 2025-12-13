from __future__ import annotations
import os
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st
import pydeck as pdk
import plotly.express as px

DB_PATH = Path(os.getenv("DB_PATH", "seismo_raw_vault.duckdb"))

st.set_page_config(page_title="SeismoX | Well & Sensor Dashboard", layout="wide")

# ---------------------------
# Helpers
# ---------------------------
@st.cache_data(ttl=30)
def get_available_load_times():
    con = duckdb.connect(str(DB_PATH))
    times = con.execute("""
        SELECT DISTINCT load_dts
        FROM dv.sat_readings
        ORDER BY load_dts DESC
    """).df()
    con.close()
    return times["load_dts"].tolist()

def query_df(sql: str, params=None) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH))
    df = con.execute(sql, params or []).df()
    con.close()
    return df


st.title("SeismoX Dashboard (Raw Vault → Dimensional → Marts)")

# ---------------------------
# BONUS: Time travel selector
# ---------------------------
load_times = get_available_load_times()
if load_times:
    as_of = st.sidebar.selectbox("Time travel (as-of DV load_dts)", load_times)
else:
    as_of = None
    st.sidebar.warning("No load_dts found in dv.sat_readings (did you ingest?)")

st.sidebar.markdown("---")
well_filter = st.sidebar.text_input("Filter well name (contains)", "")
show_only_anomalies = st.sidebar.checkbox("Show only anomalies", value=False)

ASOF_FILTER = "TRUE"
params = []
if as_of is not None:
    ASOF_FILTER = "r.load_dts <= ?"
    params = [as_of]

# ---------------------------
# Facts (as-of snapshot)
# ---------------------------
fact_sql = f"""
WITH readings_asof AS (
  SELECT *
  FROM dv.sat_readings r
  WHERE {ASOF_FILTER}
),
latest_readings AS (
  SELECT *
  FROM readings_asof
  QUALIFY ROW_NUMBER()
    OVER (PARTITION BY wss_hk, event_ts, depth_ft ORDER BY load_dts DESC) = 1
)
SELECT
  l.well_hk        AS well_key,
  l.sensor_hk      AS sensor_key,
  l.survey_type_hk AS survey_type_key,
  CAST(r.event_ts AS DATE) AS date_key,
  r.event_ts,
  r.depth_ft,
  r.amplitude,
  r.quality_flag,
  r.source_file
FROM latest_readings r
JOIN dv.link_well_sensor_survey l
  ON r.wss_hk = l.wss_hk;
"""
facts = query_df(fact_sql, params)

# ---------------------------
# Well dimension (latest as-of)
# ---------------------------
dim_well_sql = f"""
WITH wells_asof AS (
  SELECT * FROM dv.sat_well_details
  {"WHERE load_dts <= ?" if as_of is not None else ""}
),
latest_wells AS (
  SELECT *
  FROM wells_asof
  QUALIFY ROW_NUMBER()
    OVER (PARTITION BY well_hk ORDER BY load_dts DESC) = 1
)
SELECT
  h.well_hk AS well_key,
  h.well_id,
  w.well_name,
  w.location_lat  AS lat,
  w.location_long AS lon,
  w.operator
FROM dv.hub_well h
LEFT JOIN latest_wells w
  ON h.well_hk = w.well_hk;
"""
dim_well = query_df(dim_well_sql, [as_of] if as_of is not None else [])

if well_filter.strip():
    dim_well = dim_well[
        dim_well["well_name"].fillna("").str.contains(well_filter, case=False)
    ]

# ---------------------------
# Derived flags
# ---------------------------
facts["is_anomaly"] = (
    facts["quality_flag"].fillna(0).astype(int).ne(0)
    | facts["amplitude"].isna()
)

if show_only_anomalies:
    facts = facts[facts["is_anomaly"]]

facts["source_format"] = facts["source_file"].fillna("").str.lower().apply(
    lambda s:
        "parquet" if s.endswith(".parquet")
        else "csv" if s.endswith(".csv")
        else "sgx" if ("sgx" in s or s.endswith(".sgx"))
        else "unknown"
)

# ---------------------------
# KPI row
# ---------------------------
col1, col2, col3, col4 = st.columns(4)

total_wells = dim_well["well_key"].nunique()
total_readings = len(facts)
quality_rate = float((facts["quality_flag"].fillna(0) == 0).mean()) if total_readings else 0.0
anomaly_count = int(facts["is_anomaly"].sum()) if total_readings else 0

col1.metric("Number of Wells", f"{total_wells}")
col2.metric("Total Readings", f"{total_readings:,}")
col3.metric("Data Quality Rate", f"{quality_rate * 100:.1f}%")
col4.metric("Anomalies", f"{anomaly_count:,}")

st.markdown("---")

# ---------------------------
# Wells map
# ---------------------------
st.subheader("Wells Map & Well Details")

map_df = dim_well.dropna(subset=["lat", "lon"]).copy()

if map_df.empty:
    st.info("No lat/lon found in master wells.")
else:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_radius=500,
        pickable=True,
    )
    view_state = pdk.ViewState(
        latitude=float(map_df["lat"].mean()),
        longitude=float(map_df["lon"].mean()),
        zoom=6,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{well_name}\nOperator: {operator}\nWell ID: {well_id}"},
        )
    )

with st.expander("Show well table"):
    st.dataframe(dim_well.sort_values("well_id"), use_container_width=True)

st.markdown("---")

# ---------------------------
# Well state: distributions + heatmap
# ---------------------------
st.subheader("📊 Well State, Distributions, and Anomaly Heatmaps")

left, right = st.columns(2)

with left:
    fig_hist = px.histogram(
        facts.dropna(subset=["amplitude"]),
        x="amplitude",
        nbins=60,
        title="Amplitude Distribution",
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with right:
    q = facts["quality_flag"].fillna(0).astype(int)
    df_q = (
        q.value_counts()
         .rename_axis("quality_flag")
         .reset_index(name="count")
    )
    fig_q = px.bar(
        df_q,
        x="quality_flag",
        y="count",
        title="Quality Flag Counts",
    )
    st.plotly_chart(fig_q, use_container_width=True)

if not facts.empty:
    facts["strata_key"] = (facts["depth_ft"].fillna(0) // 100 * 100).astype(int)
    heat = (
        facts.groupby(["well_key", "strata_key"])["is_anomaly"]
        .sum()
        .reset_index()
        .merge(dim_well[["well_key", "well_name"]], on="well_key", how="left")
    )
    fig_heat = px.density_heatmap(
        heat,
        x="strata_key",
        y="well_name",
        z="is_anomaly",
        title="Anomaly Heatmap (Well x Depth Band)",
        nbinsx=30,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# ---------------------------
# Data Marts
# ---------------------------
st.subheader("Data Marts")

tab1, tab2, tab3 = st.tabs(
    ["mart_well_performance", "mart_sensor_analysis", "mart_survey_summary"]
)

with tab1:
    df = query_df("SELECT * FROM mart.mart_well_performance ORDER BY total_readings DESC;")
    st.dataframe(df, use_container_width=True)

with tab2:
    df = query_df("SELECT * FROM mart.mart_sensor_analysis ORDER BY total_readings DESC;")
    st.dataframe(df, use_container_width=True)

with tab3:
    df = query_df("SELECT * FROM mart.mart_survey_summary ORDER BY total_readings DESC;")
    st.dataframe(df, use_container_width=True)

st.markdown("---")

# ---------------------------
# Drill-down: Well
# ---------------------------
st.subheader("🔍 Drill-down: Well Analysis")

well_options = dim_well[["well_key", "well_name"]].dropna().sort_values("well_name")

if not well_options.empty:
    selected_well = st.selectbox(
        "Select a well",
        well_options["well_key"].tolist(),
        format_func=lambda k: well_options.set_index("well_key").loc[k, "well_name"],
    )
    well_facts = facts[facts["well_key"] == selected_well]
    well_name = well_options.set_index("well_key").loc[selected_well, "well_name"]

    if not well_facts.empty:
        c1, c2 = st.columns(2)

        with c1:
            fig_ts = px.line(
                well_facts.sort_values("event_ts"),
                x="event_ts",
                y="amplitude",
                title=f"Amplitude Over Time — {well_name}",
                markers=True,
            )
            fig_ts.add_scatter(
                x=well_facts.loc[well_facts["is_anomaly"], "event_ts"],
                y=well_facts.loc[well_facts["is_anomaly"], "amplitude"],
                mode="markers",
                name="Anomaly",
            )
            st.plotly_chart(fig_ts, use_container_width=True)

        with c2:
            fig_depth = px.scatter(
                well_facts,
                x="depth_ft",
                y="amplitude",
                color="is_anomaly",
                title=f"Amplitude vs Depth — {well_name}",
            )
            st.plotly_chart(fig_depth, use_container_width=True)

st.markdown("---")

# ---------------------------
# Drill-down: Sensor type
# ---------------------------
st.subheader("🔍 Drill-down: Sensor Reliability")

sensor_dim = query_df("SELECT sensor_key, sensor_type FROM dm.dim_sensor")
sensor_types = sorted(sensor_dim["sensor_type"].dropna().unique())

if sensor_types:
    selected_sensor_type = st.selectbox("Select sensor type", sensor_types)
    sensor_facts = facts.merge(sensor_dim, on="sensor_key", how="left")
    sensor_facts = sensor_facts[sensor_facts["sensor_type"] == selected_sensor_type]

    if not sensor_facts.empty:
        fig_sensor = px.histogram(
            sensor_facts.dropna(subset=["amplitude"]),
            x="amplitude",
            color="is_anomaly",
            nbins=50,
            title=f"Amplitude Distribution — Sensor Type: {selected_sensor_type}",
        )
        st.plotly_chart(fig_sensor, use_container_width=True)

st.markdown("---")

# ---------------------------
# Exports
# ---------------------------
st.subheader("⬇️ Export Data")

@st.cache_data
def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

c1, c2, c3 = st.columns(3)

with c1:
    st.download_button(
        "Download current facts (CSV)",
        to_csv(facts),
        "fact_sensor_readings_filtered.csv",
        "text/csv",
    )

with c2:
    if "well_facts" in locals() and not well_facts.empty:
        st.download_button(
            "Download selected well (CSV)",
            to_csv(well_facts),
            f"well_{well_name}.csv",
            "text/csv",
        )

with c3:
    mart_wp = query_df("SELECT * FROM mart.mart_well_performance")
    st.download_button(
        "Download mart_well_performance (CSV)",
        to_csv(mart_wp),
        "mart_well_performance.csv",
        "text/csv",
    )

st.markdown("---")
st.subheader("Time Travel (Table View)")
st.dataframe(facts.head(200), use_container_width=True)

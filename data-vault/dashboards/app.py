from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="SOCAR Hackathon EP2 Dashboard", layout="wide")

DB_PATH = Path("warehouse") / "seismic.duckdb"
OUT_DIR = Path("processed_data")

@st.cache_data
def load_from_duckdb(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(sql).fetchdf()
    con.close()
    return df

@st.cache_data
def load_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)

st.title("CaspianPetro — Seismic Analytics Dashboard (EP2)")

if not DB_PATH.exists():
    st.error(f"Missing DuckDB database: {DB_PATH}. Run ETL scripts first.")
    st.stop()

mwp_path = OUT_DIR / "mart_well_performance.parquet"
msa_path = OUT_DIR / "mart_sensor_analysis.parquet"
mss_path = OUT_DIR / "mart_survey_summary.parquet"

missing = [str(p) for p in [mwp_path, msa_path, mss_path] if not p.exists()]
if missing:
    st.error("Missing mart parquet outputs:\n" + "\n".join(missing) + "\nRun: python etl/build_marts.py")
    st.stop()

# Load core tables
dim_well = load_from_duckdb("""
    SELECT well_id, well_name, location_lat, location_long, operator, spud_date
    FROM dim_well
""")

dim_survey = load_from_duckdb("SELECT survey_type_id, survey_type FROM dim_survey_type")

fact = load_from_duckdb("""
    SELECT well_id, sensor_id, survey_type_id, depth_ft, amplitude, quality_flag, record_source, date
    FROM fact_seismic_readings
""")

mart_well_perf = load_parquet(mwp_path)
mart_sensor = load_parquet(msa_path)
mart_survey = load_parquet(mss_path)

# Sidebar filters
st.sidebar.header("Filters")
operators = ["All"] + sorted(dim_well["operator"].dropna().unique().tolist())
op_choice = st.sidebar.selectbox("Operator", operators, index=0)

sources = ["All"] + sorted(fact["record_source"].dropna().unique().tolist())
source_choice = st.sidebar.selectbox("Data source format", sources, index=0)

# Apply filters
wells_filtered = dim_well.copy()
if op_choice != "All":
    wells_filtered = wells_filtered[wells_filtered["operator"] == op_choice]

fact_filtered = fact.copy()
if source_choice != "All":
    fact_filtered = fact_filtered[fact_filtered["record_source"] == source_choice]
if op_choice != "All":
    fact_filtered = fact_filtered.merge(wells_filtered[["well_id"]], on="well_id", how="inner")

# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Number of wells (master)", int(wells_filtered["well_id"].nunique()))
c2.metric("Total readings", int(fact_filtered.shape[0]))
c3.metric("Avg amplitude", float(fact_filtered["amplitude"].mean()) if len(fact_filtered) else 0.0)
c4.metric("Quality rate", float(fact_filtered["quality_flag"].mean()) if len(fact_filtered) else 0.0)

st.divider()

# Required map
st.subheader("Wells Map (Required)")
map_df = wells_filtered.dropna(subset=["location_lat", "location_long"]).copy()

if map_df.empty:
    st.warning("No well locations available after filters.")
else:
    fig_map = px.scatter_mapbox(
        map_df,
        lat="location_lat",
        lon="location_long",
        hover_name="well_name",
        hover_data=["well_id", "operator", "spud_date"],
        zoom=5,
        height=450
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# Required “well state” overview
st.subheader("Well State Overview (Required)")

left, right = st.columns(2)
with left:
    st.markdown("**Amplitude distribution**")
    fig_hist = px.histogram(fact_filtered, x="amplitude", nbins=40)
    st.plotly_chart(fig_hist, use_container_width=True)

with right:
    st.markdown("**Quality rate by survey type**")
    tmp = fact_filtered.merge(dim_survey, on="survey_type_id", how="left")
    grp = tmp.groupby("survey_type", dropna=False)["quality_flag"].mean().reset_index()
    fig_q = px.bar(grp, x="survey_type", y="quality_flag")
    st.plotly_chart(fig_q, use_container_width=True)

st.divider()

# Required marts (display)
st.subheader("Required Marts")

t1, t2, t3 = st.tabs(["mart_well_performance", "mart_sensor_analysis", "mart_survey_summary"])
with t1:
    st.dataframe(mart_well_perf, use_container_width=True)
with t2:
    st.dataframe(mart_sensor, use_container_width=True)
with t3:
    st.dataframe(mart_survey, use_container_width=True)

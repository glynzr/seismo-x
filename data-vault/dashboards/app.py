from pathlib import Path
import warnings
import duckdb
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Suppress Plotly deprecation warnings about config
warnings.filterwarnings("ignore", message=".*keyword arguments.*deprecated.*config.*", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*Use config instead to specify Plotly.*", category=FutureWarning)

st.set_page_config(page_title="SOCAR Hackathon EP2 Dashboard", layout="wide")

# Plotly configuration - using dict constructor to avoid any keyword argument deprecation
# This ensures all Plotly config options are passed correctly
PLOTLY_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': []
}

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
    SELECT well_id, sensor_id, survey_type_id, depth_ft, amplitude, quality_flag, record_source, date, timestamp
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
st.subheader("Wells Map")
map_df = wells_filtered.dropna(subset=["location_lat", "location_long"]).copy()

if map_df.empty:
    st.warning("No well locations available after filters.")
else:
    fig_map = px.scatter_map(
        map_df,
        lat="location_lat",
        lon="location_long",
        hover_name="well_name",
        hover_data=["well_id", "operator", "spud_date"],
        zoom=5,
        height=450
    )
    fig_map.update_layout(map_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig_map, width='stretch', config=PLOTLY_CONFIG)

st.divider()

# Required "well state" overview
st.subheader("Well State Overview")

# Calculate anomaly indicators (readings with extreme amplitude values)
fact_filtered_with_anomaly = fact_filtered.copy()
if len(fact_filtered) > 0:
    q1 = fact_filtered["amplitude"].quantile(0.25)
    q3 = fact_filtered["amplitude"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    fact_filtered_with_anomaly["is_anomaly"] = (
        (fact_filtered_with_anomaly["amplitude"] < lower_bound) | 
        (fact_filtered_with_anomaly["amplitude"] > upper_bound)
    )

# Top row: Key metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Wells", int(wells_filtered["well_id"].nunique()))
with col2:
    anomaly_count = int(fact_filtered_with_anomaly["is_anomaly"].sum()) if len(fact_filtered_with_anomaly) > 0 else 0
    st.metric("Anomaly Count", anomaly_count)
with col3:
    quality_rate = float(fact_filtered["quality_flag"].mean()) if len(fact_filtered) else 0.0
    st.metric("Overall Quality Rate", f"{quality_rate:.2%}")
with col4:
    total_readings = int(fact_filtered.shape[0])
    st.metric("Total Readings", total_readings)

# Second row: Amplitude distribution and Quality by survey
left, right = st.columns(2)
with left:
    st.markdown("**Amplitude Distribution**")
    fig_hist = px.histogram(
        fact_filtered, 
        x="amplitude", 
        nbins=40,
        labels={"amplitude": "Amplitude", "count": "Frequency"},
        title="Distribution of Seismic Amplitudes"
    )
    fig_hist.update_layout(showlegend=False)
    st.plotly_chart(fig_hist, width='stretch', config=PLOTLY_CONFIG)

with right:
    st.markdown("**Quality Rate by Survey Type**")
    tmp = fact_filtered.merge(dim_survey, on="survey_type_id", how="left")
    grp = tmp.groupby("survey_type", dropna=False, observed=True)["quality_flag"].mean().reset_index()
    grp.columns = ["survey_type", "quality_rate"]
    fig_q = px.bar(
        grp, 
        x="survey_type", 
        y="quality_rate",
        labels={"survey_type": "Survey Type", "quality_rate": "Quality Rate"},
        title="Data Quality by Survey Type"
    )
    fig_q.update_layout(yaxis_tickformat=".0%")
    st.plotly_chart(fig_q, width='stretch', config=PLOTLY_CONFIG)

# Third row: Anomaly Heatmap and Well Performance
st.markdown("### Anomaly Analysis")
anom_col1, anom_col2 = st.columns(2)

with anom_col1:
    st.markdown("**Anomaly Heatmap by Well and Depth**")
    if len(fact_filtered_with_anomaly) > 0 and "is_anomaly" in fact_filtered_with_anomaly.columns:
        # Create depth bins for heatmap
        fact_filtered_with_anomaly["depth_bin"] = pd.cut(
            fact_filtered_with_anomaly["depth_ft"], 
            bins=10, 
            labels=[f"{i*100}-{(i+1)*100}" for i in range(10)]
        )
        
        # Merge with well names
        fact_with_wells = fact_filtered_with_anomaly.merge(
            wells_filtered[["well_id", "well_name"]], 
            on="well_id", 
            how="left"
        )
        
        # Aggregate anomaly rate by well and depth bin
        heatmap_data = fact_with_wells.groupby(["well_name", "depth_bin"], observed=True)["is_anomaly"].mean().reset_index()
        heatmap_pivot = heatmap_data.pivot(index="well_name", columns="depth_bin", values="is_anomaly")
        
        if not heatmap_pivot.empty:
            fig_heat = px.imshow(
                heatmap_pivot,
                labels=dict(x="Depth (ft)", y="Well", color="Anomaly Rate"),
                title="Anomaly Rate Heatmap",
                aspect="auto",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig_heat, width='stretch', config=PLOTLY_CONFIG)
        else:
            st.info("Insufficient data for heatmap visualization")
    else:
        st.info("No anomaly data available")

with anom_col2:
    st.markdown("**Amplitude by Well and Data Source**")
    fact_with_wells = fact_filtered.merge(
        wells_filtered[["well_id", "well_name"]], 
        on="well_id", 
        how="left"
    )
    well_amplitude = fact_with_wells.groupby(["well_name", "record_source"], observed=True)["amplitude"].mean().reset_index()
    fig_box = px.box(
        fact_with_wells,
        x="well_name",
        y="amplitude",
        color="record_source",
        labels={"well_name": "Well", "amplitude": "Amplitude", "record_source": "Data Source"},
        title="Amplitude Distribution by Well"
    )
    fig_box.update_xaxes(tickangle=45)
    st.plotly_chart(fig_box, width='stretch', config=PLOTLY_CONFIG)

# Fourth row: Time Series Analysis
if "timestamp" in fact_filtered.columns and fact_filtered["timestamp"].notna().sum() > 0:
    st.markdown("### Temporal Analysis")
    ts_col1, ts_col2 = st.columns(2)
    
    with ts_col1:
        st.markdown("**Readings Over Time**")
        fact_ts = fact_filtered.copy()
        fact_ts["timestamp"] = pd.to_datetime(fact_ts["timestamp"], errors="coerce")
        fact_ts = fact_ts.dropna(subset=["timestamp"])
        if len(fact_ts) > 0:
            fact_ts["date"] = fact_ts["timestamp"].dt.date
            daily_readings = fact_ts.groupby("date", observed=True).size().reset_index()
            daily_readings.columns = ["date", "count"]
            fig_ts = px.line(
                daily_readings,
                x="date",
                y="count",
                labels={"date": "Date", "count": "Number of Readings"},
                title="Daily Reading Count"
            )
            st.plotly_chart(fig_ts, width='stretch', config=PLOTLY_CONFIG)
    
    with ts_col2:
        st.markdown("**Average Amplitude Over Time**")
        if len(fact_ts) > 0:
            daily_amp = fact_ts.groupby("date", observed=True)["amplitude"].mean().reset_index()
            fig_amp_ts = px.line(
                daily_amp,
                x="date",
                y="amplitude",
                labels={"date": "Date", "amplitude": "Average Amplitude"},
                title="Daily Average Amplitude Trend"
            )
            st.plotly_chart(fig_amp_ts, width='stretch', config=PLOTLY_CONFIG)

st.divider()

# Required marts (display)
st.divider()
st.subheader("Analytics Marts")

t1, t2, t3 = st.tabs(["mart_well_performance", "mart_sensor_analysis", "mart_survey_summary"])

with t1:
    st.markdown("**Well Performance Summary**")
    st.markdown("*Total readings, average amplitude, and data quality rate for each well, broken down by data source format*")
    
    # Add visualizations for well performance
    perf_col1, perf_col2 = st.columns(2)
    with perf_col1:
        if "total_readings" in mart_well_perf.columns:
            fig_perf1 = px.bar(
                mart_well_perf.groupby("well_name", observed=True)["total_readings"].sum().reset_index(),
                x="well_name",
                y="total_readings",
                labels={"well_name": "Well", "total_readings": "Total Readings"},
                title="Total Readings by Well"
            )
            fig_perf1.update_xaxes(tickangle=45)
            st.plotly_chart(fig_perf1, width='stretch', config=PLOTLY_CONFIG)
    
    with perf_col2:
        if "data_quality_rate" in mart_well_perf.columns:
            # Use absolute value for size since Plotly requires non-negative values
            perf_data = mart_well_perf.copy()
            perf_data["abs_avg_amplitude"] = perf_data["avg_amplitude"].abs()
            
            fig_perf2 = px.scatter(
                perf_data,
                x="total_readings",
                y="data_quality_rate",
                size="abs_avg_amplitude",
                color="data_source_format",
                hover_name="well_name",
                hover_data=["avg_amplitude"],  # Show actual amplitude in hover
                labels={
                    "total_readings": "Total Readings",
                    "data_quality_rate": "Data Quality Rate",
                    "abs_avg_amplitude": "Avg Amplitude (abs)",
                    "avg_amplitude": "Avg Amplitude",
                    "data_source_format": "Data Source"
                },
                title="Quality vs Volume Analysis"
            )
            fig_perf2.update_layout(yaxis_tickformat=".0%")
            st.plotly_chart(fig_perf2, width='stretch', config=PLOTLY_CONFIG)
    
    st.dataframe(mart_well_perf, width='stretch')

with t2:
    st.markdown("**Sensor Analysis Summary**")
    st.markdown("*Total readings, data quality rate, and average amplitude for each sensor type*")
    
    # Add visualization for sensor analysis
    if "sensor_type" in mart_sensor.columns:
        fig_sensor = px.bar(
            mart_sensor,
            x="sensor_type",
            y="data_quality_rate",
            color="data_source_format",
            labels={
                "sensor_type": "Sensor Type",
                "data_quality_rate": "Data Quality Rate",
                "data_source_format": "Data Source"
            },
            title="Sensor Reliability by Type",
            barmode="group"
        )
        fig_sensor.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig_sensor, width='stretch', config=PLOTLY_CONFIG)
    
    st.dataframe(mart_sensor, width='stretch')

with t3:
    st.markdown("**Survey Summary**")
    st.markdown("*Data acquisition summary: wells surveyed, total readings, average amplitude, and timestamps, broken down by data source format*")
    
    # Add visualization for survey summary
    if "survey_type" in mart_survey.columns:
        surv_col1, surv_col2 = st.columns(2)
        with surv_col1:
            fig_surv1 = px.bar(
                mart_survey,
                x="survey_type",
                y="wells_surveyed",
                color="data_source_format",
                labels={
                    "survey_type": "Survey Type",
                    "wells_surveyed": "Wells Surveyed",
                    "data_source_format": "Data Source"
                },
                title="Wells Surveyed by Type",
                barmode="group"
            )
            st.plotly_chart(fig_surv1, width='stretch', config=PLOTLY_CONFIG)
        
        with surv_col2:
            fig_surv2 = px.bar(
                mart_survey,
                x="survey_type",
                y="total_readings",
                color="data_source_format",
                labels={
                    "survey_type": "Survey Type",
                    "total_readings": "Total Readings",
                    "data_source_format": "Data Source"
                },
                title="Total Readings by Survey Type",
                barmode="group"
            )
            st.plotly_chart(fig_surv2, width='stretch', config=PLOTLY_CONFIG)
    
    st.dataframe(mart_survey, width='stretch')

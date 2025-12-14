# SeismoX — Seismic Data Recovery & Analytics Platform

This repository provides a complete workflow for **seismic data recovery, reconstruction, modeling, and analytics**.  
It addresses corrupted Parquet files, legacy SGX binary formats, and builds an analytical platform using a **Raw Data Vault**, data quality tests, dimensional models, marts, and a visualization layer.

---

## Prerequisites

- Python 3.9+
- Docker
- Docker Compose

---

## Environment Setup

Create and activate a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## The Parquet Enigma

### Make scripts executable

```bash
chmod +x solutions/*.sh
```

---

### Extract flag from Parquet files

```bash
solutions/flag_parquet.sh --data-dir <data-folder>
```

**Output:**
```
processed_data/flag/flag.txt
```

---

### Recover corrupted Parquet file

Only **one Parquet file is corrupted** and requires recovery.

```bash
solutions/corrupted_parquet.sh --data-dir <data-folder>
```

**Recovered file location:**
```
processed_data/recovered-parquet
```

---

### SGX to Parquet Conversion

Converted files (from SGX to Parquet) are stored in:

```
processed_data/sgx_converted
```

To convert SGX files:

```bash
solutions/load_sgx.sh --data-dir <path-to-caspian_hackathon_assets>
```

---

## Seismic Data Reconstruction & Modeling

For this stage, required data files must be copied into the analytics workspace.

```bash
cp /path/to/caspian_hackathon_assets/*.csv modelling-and-analytics/data
cp /path/to/caspian_hackathon_assets/track_1_forensics/archive_batch_seismic_readings_2.parquet modelling-and-analytics/data
cp /path/to/processed_data/sgx_converted/all_sgx.parquet modelling-and-analytics/data
cp /path/to/processed_data/recovered-parquet/archive_batch_seismic_readings.parquet modelling-and-analytics/data
```

---

## Raw Data Vault Ingestion

```bash
cd modelling-and-analytics
python3 etl/run_track1_raw_vault.py
```

**Output:**
```
seismo_raw_vault.duckdb
```

---

## Data Quality Tests

```bash
python3 tests/test_raw_vault_validity.py
```

---

## Dimensional Modeling

```bash
python3 etl/build_dimensional_model.py
```

---

## Building Data Marts

```bash
python3 etl/build_marts.py
```

---

## Dashboard

```bash
streamlit run dashboard/app.py
```

---

## The Platform (Docker & Airflow)

```bash
cd modelling-and-analytics
sudo docker compose up --build -d
```

### Create Airflow user

```bash
sudo docker compose exec airflow-webserver airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
```

---

## Output Artifacts Summary

```
processed_data/
├── flag/flag.txt
├── recovered-parquet/
├── sgx_converted/all_sgx.parquet

modelling-and-analytics/
└── seismo_raw_vault.duckdb
```

---


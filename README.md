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
cd modelling-and-analytics
python3 tests/test_raw_vault_validity.py
```

---

## Dimensional Modeling

```bash
cd modelling-and-analytics
python3 etl/build_dimensional_model.py
```

---

## Building Data Marts

```bash
cd modelling-and-analytics
python3 etl/build_marts.py
```

---

## Dashboard

```bash
cd modelling-and-analytics
nohup /home/hackathon/seismo-x1/venv/bin/python -m streamlit run dashboard/app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  > streamlit.log 2>&1 &

```

Open dashboard on http://IP:8501


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

Airflow will be available on http:IP:8080 and login after creating user.

## Project Structure

```
seismo-x/
├── src/                          # Core source code
│   ├── cli/                      # Command-line tools
│   │   ├── extract_flag.py      # Extract flags from Parquet files
│   │   ├── load_sgx.py          # Convert SGX files to Parquet
│   │   └── recover_parquet.py   # Recover corrupted Parquet files
│   ├── parquet/                  # Parquet utilities
│   │   ├── forensic.py          # Forensic analysis tools
│   │   └── recovery.py          # Parquet recovery logic
│   └── sgx/                      # SGX format parser
│       ├── parser.py            # Trace parsing logic
│       └── spec.py              # SGX format specification
│
├── modelling-and-analytics/      # Data warehouse and analytics
│   ├── airflow/                  # Airflow configuration
│   │   └── requirements.txt     # Airflow dependencies
│   ├── dags/                     # Airflow DAGs
│   │   └── seismic_etl_dag.py  # Main ETL pipeline DAG
│   ├── etl/                      # ETL scripts
│   │   ├── run_track1_raw_vault.py      # Raw vault ingestion
│   │   ├── build_dimensional_model.py   # Dimensional model builder
│   │   └── build_marts.py               # Data mart builder
│   ├── dashboard/                # Streamlit dashboard
│   │   └── app.py               # Main dashboard application
│   ├── tests/                    # Test suite
│   │   └── test_raw_vault_validity.py
│   ├── docker-compose.yml        # Docker Compose configuration
│   └── Dockerfile               # Airflow Docker image
│
├── solutions/                    # Utility scripts
│   ├── load_sgx.sh             # SGX loading script
│   ├── recover_parquet.sh      # Parquet recovery script
│   └── flag_parquet.sh         # Flag extraction script
│
├── requirements.txt              # Python dependencies
├── installation_script.sh        # System setup script
└── README.md                     # This file
```


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
## Architecture

For detailed architecture information, see  
[Architecture Diagram & Explanation](ARCHITECTURE_DIAGRAM.md)


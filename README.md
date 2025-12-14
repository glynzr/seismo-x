# setting up env
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

# The Parquet Enigma

Make scripts executable:
```
chmod +x solutions/*.sh

```

Run script for getting flag:
```
solutions/flag_parquet.sh --data-dir <data folder>
```

flag.txt will be in processed_data/flag


Only 1 parquet file is corrupted . For recovery run this script:
```
solutions/corrupted_parquet.sh --data-dir <data folder>
```

Recovered parquet file will be stored in processed_data/recovered-parquet


Converted files(from sgx to parquet) will be stored in processed_data/sgx_converted
For converting:
```
solutions/load_sgx.sh --data-dir <path to caspian_hackathon_assets>
```

# Seismic Data Reconstruction & Modeling
For this part, it is needed to copy required data files to modelling-and-analytics/data folder.
```
cp /path/to/caspian_hackathon_assets/*.csv modelling-and-analytics/data
cp /path/to/caspian_hackathon_assets/track_1_forensics/archive_batch_seismic_readings_2.parquet
cp /path/to/processed_data/sgx_converted/all_sgx.parquet modelling-and-analytics/data
cp /path/to/processed_data/recovered-parquet/archive_batch_seismic_readings.parquet modelling-and-analytics/data

```

Run necessary scripts:
```
cd modelling-and-analytics
```

Raw Data Vault ingestion:
```
python3 etl/run_track1_raw_vault.py
```

seismo_raw_vault.duckdb will be created on modelling-and-analytics folder.

Data Quality Tests
```
python3 tests/test_raw_vault_validity.py
```

Building dimensional model:
```
python3 etl/build_dimensional_model.py
```

Building marts:
```
python3 etl/build_marts.py
```

Dashboard:
```
streamlit run dashboard/app.py
```

# The platform
Docker and docker compose should be installed on the system
```
cd modelling-and-analytics
sudo docker compose up --build -d
```

Create user on airflow:
```
cd modelling-and-analytics
sudo docker compose exec airflow-webserver airflow users create   --username admin   --password admin   --firstname Admin   --lastname User   --role Admin   --email admin@example.com
```


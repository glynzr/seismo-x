# Seismo-X1 Architecture Diagram

## Overview

This document describes the architecture of the Seismo-X1 project, which processes seismic data through a multi-stage pipeline from raw data recovery to visualization.

## Architecture Diagram

```mermaid
graph TB
    subgraph "I. TASK 1: Data Recovery Layer"
        RawData[Raw Data Sources<br/>Corrupted .parquet<br/>Legacy .sgx / CSV]
        Scripts[Data Processing Scripts<br/>corrupted_parquet.sh<br/>flag_parquet.sh<br/>load_sgx.sh]
        Libraries[Processing Libraries<br/>src/parquet/<br/>forensic.py, recovery.py<br/>src/sgx/<br/>parser.py, spec.py]
        Processed[Processed Data<br/>processed_data/<br/>recovered-parquet/<br/>sgx_converted/]
        
        RawData -->|--data-dir| Scripts
        Scripts -->|uses| Libraries
        Libraries -->|outputs| Processed
    end
    
    subgraph "II. TASK 2: Data Modeling Layer"
        InputData[Input Data<br/>modelling-and-analytics/data/]
        RawVault[ETL: Raw Data Vault<br/>run_track1_raw_vault.py]
        QualityTests[Data Quality Tests<br/>test_raw_vault_validity.py]
        Dimensional[ETL: Dimensional Model<br/>build_dimensional_model.py]
        Marts[ETL: Analytics Marts<br/>build_marts.py]
        Dashboard[Streamlit Dashboard<br/>dashboard/app.py]
        
        InputData -->|ingest| RawVault
        RawVault -->|validate| QualityTests
        QualityTests -->|transform| Dimensional
        Dimensional -->|aggregate| Marts
        Marts -->|visualize| Dashboard
    end
    
    subgraph "III. Data Storage Layer"
        DuckDB[(DuckDB Database<br/>seismo_raw_vault.duckdb)]
        
        subgraph "Schema: stg.*"
            Staging[Staging Tables<br/>stg_file_provenance<br/>stg_master_wells<br/>stg_archive_readings<br/>stg_sgx_traces]
        end
        
        subgraph "Schema: dv.*"
            DataVault[Data Vault<br/>Hubs, Links, Satellites<br/>hub_well, hub_sensor<br/>link_well_sensor_survey<br/>sat_readings<br/>sat_well_details<br/>sat_legacy_traces]
        end
        
        subgraph "Schema: dm.*"
            DimensionalModel[Dimensional Model<br/>Star Schema<br/>dim_well, dim_sensor<br/>dim_survey_type, dim_time<br/>fact_sensor_readings<br/>fact_anomalies]
        end
        
        subgraph "Schema: mart.*"
            AnalyticsMarts[Analytics Marts<br/>mart_well_performance<br/>mart_sensor_analysis<br/>mart_survey_summary]
        end
        
        RawVault -->|writes| Staging
        Staging -->|reads/writes| DataVault
        DataVault -->|reads| DimensionalModel
        Dimensional -->|writes| DimensionalModel
        DimensionalModel -->|reads/writes| AnalyticsMarts
        Marts -->|writes| AnalyticsMarts
        AnalyticsMarts -->|reads| Dashboard
    end
    
    subgraph "IV. TASK 3: Orchestration Platform"
        DockerCompose[Docker Compose Infrastructure<br/>docker-compose.yml<br/>Dockerfile]
        PostgreSQL[(PostgreSQL<br/>Airflow Metadata)]
        Webserver[Airflow Webserver<br/>Port 8080]
        Scheduler[Airflow Scheduler<br/>LocalExecutor]
        DAG[Airflow DAG<br/>seismic_data_pipeline<br/>seismic_etl_dag.py]
        
        DockerCompose -->|runs| PostgreSQL
        DockerCompose -->|runs| Webserver
        DockerCompose -->|runs| Scheduler
        PostgreSQL -->|stores state| Scheduler
        Webserver -->|orchestrates| DAG
        Scheduler -->|executes| DAG
        
        DAG -->|executes| RawVault
        DAG -->|executes| QualityTests
        DAG -->|executes| Dimensional
        DAG -->|executes| Marts
    end
    
    Processed -->|feeds| InputData
    
    style RawData fill:#ffcccc
    style Processed fill:#ccffcc
    style RawVault fill:#cce5ff
    style QualityTests fill:#ffffcc
    style Dimensional fill:#cce5ff
    style Marts fill:#cce5ff
    style Dashboard fill:#ffccff
    style DuckDB fill:#ffe5cc
    style Staging fill:#ffffff
    style DataVault fill:#cce5ff
    style DimensionalModel fill:#ffffff
    style AnalyticsMarts fill:#ffffff
    style DockerCompose fill:#e5ccff
    style PostgreSQL fill:#ffffff
    style Webserver fill:#ffffff
    style Scheduler fill:#ffffff
    style DAG fill:#ffffff
```

## Component Descriptions

### I. Data Recovery Layer

**Raw Data Sources**
- Corrupted .parquet files
- Legacy .sgx files
- CSV files

**Data Processing Scripts** (`solutions/`)
- `corrupted_parquet.sh`: Recovers corrupted parquet files
- `flag_parquet.sh`: Extracts flags from parquet files
- `load_sgx.sh`: Converts SGX files to parquet format

**Processing Libraries** (`src/`)
- `src/parquet/forensic.py`: Parquet file analysis
- `src/parquet/recovery.py`: Parquet file recovery
- `src/sgx/parser.py`: SGX file parsing
- `src/sgx/spec.py`: SGX file specifications

**Processed Data**
- Output stored in `processed_data/` directory
- Recovered parquet files
- Converted SGX data

### II. Data Modeling Layer

**ETL: Raw Data Vault** (`modelling-and-analytics/etl/run_track1_raw_vault.py`)
- Ingests data from processed sources
- Creates staging tables (stg.*)
- Builds Data Vault structure (dv.*)
- Implements hubs, links, and satellites pattern

**Data Quality Tests** (`modelling-and-analytics/tests/test_raw_vault_validity.py`)
- Validates data integrity
- Checks count reconciliation
- Verifies referential integrity
- Ensures provenance completeness

**ETL: Dimensional Model** (`modelling-and-analytics/etl/build_dimensional_model.py`)
- Transforms Data Vault to star schema
- Creates dimension tables (dim_*)
- Creates fact tables (fact_*)
- Implements time and strata dimensions

**ETL: Analytics Marts** (`modelling-and-analytics/etl/build_marts.py`)
- Aggregates data for analytics
- Creates well performance mart
- Creates sensor analysis mart
- Creates survey summary mart

**Streamlit Dashboard** (`modelling-and-analytics/dashboard/app.py`)
- Visualizes data from marts
- Provides interactive exploration
- Time travel functionality
- Anomaly detection and analysis

### III. Data Storage Layer

**DuckDB Database** (`seismo_raw_vault.duckdb`)
- Single-file analytical database
- Stores all schemas and data

**Schema: stg.* (Staging)**
- Temporary staging area
- Raw data as-is from sources
- File provenance tracking

**Schema: dv.* (Data Vault)**
- Hubs: Business keys (well, sensor, survey_type)
- Links: Relationships between hubs
- Satellites: Descriptive attributes with history

**Schema: dm.* (Dimensional Model)**
- Star schema design
- Dimension tables: well, sensor, survey_type, time, strata
- Fact tables: sensor_readings, survey_events, anomalies

**Schema: mart.* (Analytics Marts)**
- Pre-aggregated analytics tables
- Optimized for dashboard queries
- Well performance metrics
- Sensor reliability analysis
- Survey summaries

### IV. Orchestration Platform

**Docker Compose Infrastructure**
- Containerized environment
- Defined in `docker-compose.yml`
- Custom Dockerfile for Airflow

**PostgreSQL**
- Stores Airflow metadata
- Tracks DAG runs and task states
- Maintains execution history

**Airflow Webserver**
- Web UI on port 8080
- DAG visualization and monitoring
- Task execution control

**Airflow Scheduler**
- Executes DAGs using LocalExecutor
- Manages task dependencies
- Coordinates workflow execution

**Airflow DAG** (`modelling-and-analytics/dags/seismic_etl_dag.py`)
- Defines pipeline workflow
- Orchestrates ETL tasks in sequence:
  1. Ingest Raw Vault
  2. Test Raw Vault Validity
  3. Build Dimensional Model
  4. Build Analytics Marts

## Data Flow

1. **Recovery**: Raw corrupted/legacy files → Processing scripts → Libraries → Processed data
2. **Ingestion**: Processed data → Raw Vault ETL → Staging tables → Data Vault
3. **Validation**: Data Vault → Quality tests → Validation results
4. **Transformation**: Data Vault → Dimensional Model ETL → Star schema
5. **Aggregation**: Dimensional Model → Analytics Marts ETL → Pre-aggregated marts
6. **Visualization**: Analytics Marts → Streamlit Dashboard → User interface

## Execution Flow

The Airflow DAG orchestrates the entire pipeline:
1. `ingest_raw_vault` → Loads data into Data Vault
2. `test_raw_vault_validity` → Validates data quality
3. `build_dimensional_model` → Creates dimensional model
4. `build_marts` → Builds analytics marts

Each step depends on the previous one completing successfully.

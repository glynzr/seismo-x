from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {"owner": "data-engineering", "retries": 1}

with DAG(
    dag_id="seismic_data_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["seismic", "data-vault", "etl"],
) as dag:

    ingest_raw_vault = BashOperator(
        task_id="ingest_raw_vault",
        bash_command="python /opt/airflow/etl/run_track1_raw_vault.py",
    )

    test_raw_vault = BashOperator(
        task_id="test_raw_vault_validity",
        bash_command="python /opt/airflow/tests/test_raw_vault_validity.py",
    )

    build_dimensional_model = BashOperator(
        task_id="build_dimensional_model",
        bash_command="python /opt/airflow/etl/build_dimensional_model.py",
    )

    build_marts = BashOperator(
        task_id="build_marts",
        bash_command="python /opt/airflow/etl/build_marts.py",
    )

    ingest_raw_vault >> test_raw_vault >> build_dimensional_model >> build_marts

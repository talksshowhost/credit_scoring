import logging
import os

from datetime import datetime
from airflow import DAG
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator

logging.basicConfig(filename='clear_data.log', level=logging.INFO)
_LOG = logging.getLogger()
_LOG.addHandler(logging.StreamHandler())

DAG_ID = "clear_data"
default_args = {
    'owner': 'Balabanov'
}

def download_data() -> None:
    BUCKET = 'raw-data'
     
    hook = S3Hook('s3_connection')
    file_path = hook.download_file(key=f'cs-training.csv', bucket_name=BUCKET)
    
    _LOG.info('Data downloaded')
    
    return file_path

def transform_and_load_data(**kwargs):
    import io
    import pandas as pd
    
    TABLE = 'clean_table'
    
    ti = kwargs['ti']
    file_path = ti.xcom_pull(task_ids='task_download_data')
    
    df = pd.read_csv(file_path)
    
    buffer = io.StringIO()
    df[['age']].to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    
    hook = PostgresHook(postgres_conn_id='postgres_connection')
    
    with hook.get_conn() as connection:
        with connection.cursor() as cursor:
            cursor.copy_expert(sql=f"COPY {TABLE} FROM STDIN WITH CSV", file=buffer)
            connection.commit()
    
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    max_active_runs=1,
    concurrency=3,
    schedule_interval="0 4 * * *",
    start_date=datetime.today(),
    tags=["ETL"]
) as dag:
    
    task_download_data = PythonOperator(task_id="task_download_data",
                                 python_callable=download_data)
    
    task_transform_and_load_data = PythonOperator(task_id='task_transform_and_load_data',
                                                  python_callable=transform_and_load_data, provide_context=True)
    
    task_download_data >> task_transform_and_load_data
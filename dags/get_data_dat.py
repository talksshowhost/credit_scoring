import logging

from airflow import DAG
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, date

import requests
import io

logging.basicConfig(filename='get_data.log', level=logging.INFO)
_LOG = logging.getLogger()
_LOG.setLevel(logging.INFO)

today = date.today()

TODAY = date.strftime(today, '%d-%m-%Y')
YEAR = date.strftime(today, '%Y')
MONTH = date.strftime(today, '%m')

DAG_ID = 'get_data'
default_args = {
    'owner': 'Balabanov',
}

def get_file():
    URL = Variable.get(key='get_data_url', default_var='http://data-server:4444')
    
    response = requests.get(URL + '/data')
    response.raise_for_status()
    filebuffer = io.BytesIO(response.content)
    
    _LOG.info('Файл скачен')
    
    BUCKET = Variable.get(key='raw_data_bucket', default_var='raw-data')
    
    hook = S3Hook('s3_connection')
    hook.load_file_obj(file_obj=filebuffer, key=f'{YEAR}/{MONTH}/{TODAY}.csv', bucket_name=BUCKET, replace=True)
    _LOG.info('Файл загружен в S3')
    
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    max_active_runs=1,
    concurrency=3,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    tags=['Load'],
    catchup=False
) as dag:
    
    task_get_file = PythonOperator(task_id='task_get_file',
                                 python_callable=get_file)
    
    task_get_file
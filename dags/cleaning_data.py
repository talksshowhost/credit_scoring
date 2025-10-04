from airflow.sdk import task
from airflow.sdk import DAG
from datetime import datetime, timedelta
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import pandas as pd

with DAG(dag_id='get_dag',
          schedule=None,
          start_date=datetime(2025, 1, 1),
          catchup=False,
          tags=['extract', 'load']
    ) as dag:
     
     @task
     def get_raw_data():
          hook = S3Hook(aws_conn_id='s3_connection')

          hook.download_file(
               key='raw-data/cs-training.csv',
               bucket_name='raw-data',
          )

          data = pd.read_csv('cs-training.csv')
          clean_file = 'clean_data.csv'
          data['age'].to_csv(clean_file, index=False)

          hook.load_file(
               filename=clean_file,
               key='clean_data.csv',
               bucket_name='raw-dt',
               replace=True
          )

     get_raw_data()
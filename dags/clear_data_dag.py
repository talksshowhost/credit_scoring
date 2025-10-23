import logging
import pathlib

from datetime import datetime
from datetime import date
from airflow import DAG
from airflow.models import Variable
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator

logging.basicConfig(filename='clear_data.log', level=logging.INFO)
_LOG = logging.getLogger()
_LOG.setLevel(logging.INFO)

DAG_ID = 'clear_data'
default_args = {
    'owner': 'Balabanov'
}   
    
def preparation(dataframe) -> None:
    import pickle
    
    dataframe.drop(columns='Unnamed: 0', inplace=True)
    mean_age = 52 # Среднее взято из data_preparation.ipynb
    dataframe['age'] = dataframe['age'].replace(0, mean_age)
    
    mode_dependents = 0 # Мода взята из data_preparation.ipynb
    dataframe['NumberOfDependents'] = dataframe['NumberOfDependents'].fillna(mode_dependents).astype(int)
    
    with open(pathlib.Path('filler_model.pkl'), 'rb') as f:
        filler_model = pickle.load(f)
        
    X_empty = dataframe.loc[dataframe['MonthlyIncome'].isna()].drop(columns=['MonthlyIncome', 'SeriousDlqin2yrs'])
    y_fill = filler_model.predict(X_empty)
    y_fill[y_fill < 0] = 0
    
    dataframe.loc[dataframe['MonthlyIncome'].isna(), 'MonthlyIncome'] = y_fill
    
    dataframe['HasLoans'] = dataframe['NumberOfOpenCreditLinesAndLoans'] + dataframe['NumberRealEstateLoansOrLines']
    dataframe['HasAlotLoans'] = dataframe['HasLoans'].map(lambda x: 1 if x > 5 else 0)
    dataframe.drop(columns=['HasLoans', 'NumberOfOpenCreditLinesAndLoans', 'NumberRealEstateLoansOrLines'], inplace=True)
    
    dataframe['NumbersOfLate'] = dataframe['NumberOfTime30-59DaysPastDueNotWorse'] + dataframe['NumberOfTime60-89DaysPastDueNotWorse'] + dataframe['NumberOfTimes90DaysLate']
    dataframe['HasLatePayments'] = dataframe['NumbersOfLate'].map(lambda x: 1 if x > 0 else 0)
    dataframe.drop(columns=['NumbersOfLate','NumberOfTime30-59DaysPastDueNotWorse', 'NumberOfTime60-89DaysPastDueNotWorse', 'NumberOfTimes90DaysLate'], inplace=True)
    
def download_data() -> None:
    today = date.today()
    TODAY = date.strftime(today, '%d-%m-%Y')
    YEAR = date.strftime(today, '%Y')
    MONTH = date.strftime(today, '%m')
    
    BUCKET = Variable.get('raw_data_bucket')
    
    hook = S3Hook('s3_connection')
    file_path = hook.download_file(key=f'{YEAR}/{MONTH}/{TODAY}.csv', bucket_name=BUCKET)
    
    _LOG.info('Данные загружены')
    
    return file_path

def transform_and_load_data(**kwargs):
    import io
    import pandas as pd
    
    TABLE = Variable.get('postgres_clean_table')
    
    ti = kwargs['ti']
    file_path = ti.xcom_pull(task_ids='task_download_data')
    
    df = pd.read_csv(file_path)
    
    preparation(df)
    
    filebuffer = io.StringIO()
    df.to_csv(filebuffer, index=False, header=False)
    filebuffer.seek(0)
    
    hook = PostgresHook(postgres_conn_id='postgres_connection')
    
    with hook.get_conn() as connection:
        with connection.cursor() as cursor:
            
            cursor.execute(f"""
                SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = '{TABLE}'
                );
                """)
            
            exists = cursor.fetchone()[0]
            
            if not exists:
                _LOG.info(f'Таблица {TABLE} не найдена. Создаём...')
                
                cursor.execute(f"""
                    CREATE TABLE {TABLE} (
                    is_delinquent_2yrs INT NOT NULL,
                    revolving_utilization NUMERIC,
                    age INT,
                    debt_ratio NUMERIC,
                    monthly_income NUMERIC,
                    dependents_count INT,
                    has_many_loans INT,
                    has_late_payments INT
                );
                """)
                _LOG.info(f'Таблица {TABLE} успешно создана')
            
            else:
                _LOG.info(f'Таблица {TABLE} уже существует')

            cursor.copy_expert(sql=f'COPY {TABLE} FROM STDIN WITH CSV', file=filebuffer)
            connection.commit()
            _LOG.info(f'Данные загружены в таблицу {TABLE}')
    
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    max_active_runs=1,
    concurrency=3,
    schedule_interval='@daily',
    start_date=datetime(2025, 1, 1),
    tags=['ETL'],
    catchup=False
) as dag:
    
    task_download_data = PythonOperator(task_id='task_download_data',
                                python_callable=download_data)
    
    task_transform_and_load_data = PythonOperator(task_id='task_transform_and_load_data',
                                                python_callable=transform_and_load_data)
    
    task_download_data >> task_transform_and_load_data
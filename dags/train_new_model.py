import logging
from datetime import datetime, date

from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.models import Variable

logging.basicConfig(filename='train_new_model.log', level=logging.INFO)
_LOG = logging.getLogger()
_LOG.setLevel(logging.INFO)

DAG_ID = 'train_new_model'
default_args = {
    'owner': 'Balabanov'
}

def train_model():
    import pandas as pd
    import mlflow
    import optuna
    from sklearn.model_selection import cross_val_predict
    from sklearn.metrics import f1_score, roc_auc_score, recall_score, precision_score
    from lightgbm import LGBMClassifier
    
    import io
    
    TODAY = date.today().strftime('%d-%m-%Y')
    TABLE = Variable.get(key='postgres_clean_table', default_var='clean_table')
    SCORE = float(Variable.get(key='last_best_score', default_var='0'))
    hook = PostgresHook('postgres_connection')
    
    with hook.get_conn() as connection:
        with connection.cursor() as cursor:
            
            filebuffer = io.StringIO()
            cursor.copy_expert(
                sql=f'COPY {TABLE} TO STDOUT WITH CSV HEADER',
                file=filebuffer
            )
            
            filebuffer.seek(0)
            data = pd.read_csv(filebuffer)
            _LOG.info('Данные из таблицы загружены')
            
    X = data.drop(columns='is_delinquent_2yrs')
    y = data['is_delinquent_2yrs']
    
    mlflow.set_tracking_uri('http://mlflow-service:5000')
    mlflow.set_experiment('New Classifier Model')
    
    _LOG.info('Эксперимент начат')
    
    def model_objective(trial):
        with mlflow.start_run(run_name=f'trial_{trial.number}', nested=True):
            
            learning_rate = trial.suggest_float('learning_rate', 0.001, 1)
            n_estimators = trial.suggest_int('n_estimators', 50, 500)
            max_depth = trial.suggest_int('max_depth', 2, 10)
            num_leaves = trial.suggest_int('num_leaves', 10, 150)
            
            mlflow.log_params({
                'learning_rate': learning_rate,
                'n_estimators': n_estimators,
                'max_depth': max_depth,
                'num_leaves': num_leaves
            })

            model = LGBMClassifier(
                learning_rate=learning_rate,
                n_estimators=n_estimators,
                max_depth=max_depth,
                num_leaves=num_leaves,
                class_weight='balanced',
                verbosity=-1,
                random_state=42
            )
        
            preds = cross_val_predict(model, X, y, cv=5)
            preds_proba = cross_val_predict(model, X, y, cv=5, method='predict_proba')
            f1 = f1_score(y, preds)
            roc_auc = roc_auc_score(y, preds_proba[:, 1])
            recall = recall_score(y, preds)
            precision = precision_score(y, preds)
            
            mlflow.log_metrics({
                'f1': f1,
                'roc_auc': roc_auc,
                'recall': recall,
                'precision': precision
            }, step=trial.number)
            
            return f1
        
    with mlflow.start_run(run_name=f'LGBM Classifier_{TODAY}') as run:
        run_id = run.info.run_id
        study = optuna.create_study(direction='maximize')
        study.optimize(model_objective, n_trials=10)
        mlflow.log_metric('f1', study.best_value)
        mlflow.log_params(study.best_params)
        
        if study.best_value > SCORE:
            _LOG.info(f'Модель улучшила предыдущий результат, f1 = {study.best_value}')
            
            client = mlflow.tracking.MlflowClient()
            model_name = 'CreditScoringModel'
            
            model = LGBMClassifier(**study.best_params)
            model.fit(X, y)
            mlflow.lightgbm.log_model(model, model_name)
            
            result = mlflow.register_model(
                model_uri=f'runs:/{run_id}/{model_name}',
                name=model_name)
            
            _LOG.info('Новая модель сохранена')
            
            client.transition_model_version_stage(
                name=model_name,
                version=result.version,
                stage='Production',
                archive_existing_versions=True
            )
            
            Variable.set('last_best_score', f'{study.best_value}')
            _LOG.info('Новый результат сохранен')
            
        else:
            _LOG.info('Предыдущий результат не превзойден')
        
        mlflow.set_tag('Optimizer', 'Optuna')
        
        return study.best_value > SCORE
        

def reload_model():
    import requests
    response = requests.post("http://application:5555/reload")
    if response.status_code != 200:
        _LOG.error(f"Не удалось обновить модель, статус: {response.status_code}")
    _LOG.info('Модель в API обновлена')
        
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    max_active_runs=1,
    concurrency=3,
    schedule_interval='@weekly',
    start_date=datetime(2025, 1, 1),
    tags=['train'],
    catchup=False
) as dag:
    
    train_model_task = ShortCircuitOperator(task_id='train_model_task', 
                                    python_callable=train_model)
    
    reload_model_task = PythonOperator(task_id="reload_model_task",
                                 python_callable=reload_model)
    
    train_model_task >> reload_model_task
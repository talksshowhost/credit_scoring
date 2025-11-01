from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import mlflow

model = None

def reload_model():
    global model
    model = mlflow.pyfunc.load_model('models:/CreditScoringModel/Production')
    
class PredictionInput(BaseModel):
    RevolvingUtilizationOfUnsecuredLines: float
    age: int
    DebtRatio: float
    MonthlyIncome: float
    NumberOfDependents: int
    HasAlotLoans: bool
    HasLatePayments: bool

app = FastAPI()

@app.get('/health')
def health():
    return {'status': 'OK'}

@app.post('/reload')
def reload():
    reload_model()
    print('Модель успешно обновлена')
    return {'status': 'Модель обновилась до последней версии'}

@app.post('/predict')
def predict(input_data: PredictionInput):
    data = pd.DataFrame({
        'RevolvingUtilizationOfUnsecuredLines': [input_data.RevolvingUtilizationOfUnsecuredLines],
        'age': [input_data.age],
        'DebtRatio': [input_data.DebtRatio],
        'MonthlyIncome': [input_data.MonthlyIncome],
        'NumberOfDependents': [input_data.NumberOfDependents],
        'HasAlotLoans': [input_data.HasAlotLoans],
        'HasLatePayments': [input_data.HasLatePayments]
    })
    
    if model != None:
        prediction = model.predict(data)[0]
        decision = 'Принять' if prediction == 0 else 'Отклонить'
        
        return f'{decision} запрос клиента'
    
    else:
        return 'На сервере не обновлена модель'

if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(app, host='0.0.0.0', port=5555)
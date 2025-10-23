from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import pickle
import mlflow.lightgbm

model_uri = 'runs:/f6b876de53694c468c9f00b04ab79c7d/Model_With_Better_Score'

mlflow.set_tracking_uri('http://mlflow-service:5000')
model = mlflow.lightgbm.load_model(model_uri)

# with open('prediction_model.pkl', 'rb') as file:
#     model = pickle.load(file)
    
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
    
    prediction = 'Reject' if model.predict(data) == 0 else 'Accept'
    
    return f'{prediction} client\'s request'

if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(app, host='0.0.0.0', port=5555)
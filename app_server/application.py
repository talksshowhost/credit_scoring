from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import pickle

with open('model.pkl', 'rb') as file:
    model = pickle.load(file)
    
class PredictionInput(BaseModel):
    RevolvingUtilizationOfUnsecuredLines: float
    age: int
    DebtRatio: float
    MonthlyIncome: float
    NumberOfDependents: float
    HasPastDue: int
    HasCreditLoanOrLine: int

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
        'HasPastDue': [input_data.HasPastDue],
        'HasCreditLoanOrLine': [input_data.HasCreditLoanOrLine]
    })
    
    prediction = 'Reject' if model.predict(data) == 1 else 'Accept'
    
    return f'{prediction} client\'s request'

if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(app, host='0.0.0.0', port=5555)
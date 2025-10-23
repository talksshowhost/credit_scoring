from fastapi import FastAPI
from fastapi.responses import FileResponse
from datetime import date

today = date.today().strftime('%d-%m-%Y')

app = FastAPI()

@app.get('/health')
def health():
    return {'status': 'OK'}

@app.get('/data')
def get_data():
    return FileResponse('cs-training.csv', media_type='text/csv', filename=f'{today}.csv')

if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(app, host='0.0.0.0', port=4444)
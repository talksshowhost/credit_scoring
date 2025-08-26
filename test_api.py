import pytest
import requests

URL = 'http://127.0.0.1:5555'

@pytest.fixture(scope='function')
def resource_setup(request):
    print('SETUP: Getting test data...')
    
    data_test_0 = {
            'RevolvingUtilizationOfUnsecuredLines': 0.766127,
            'age': 45,
            'DebtRatio': 0.802982,
            'MonthlyIncome': 9120.0,
            'NumberOfDependents': 2.0,
            'HasPastDue': 1,
            'HasCreditLoanOrLine': 1
    }
    
    def resource_teardown():
        print("\nTEARDOWN")
        
    request.addfinalizer(resource_teardown)
    
    return data_test_0



def test_health(resource_setup):
    response = requests.get(URL + '/health')
    assert response.json().get('status') == 'OK'
    
def test_prediction_1(resource_setup):
    print('STARTING test_prediction_1...')
    
    response = requests.post(URL + '/predict', json=resource_setup)
    
    print(response.json())
    
    assert response.json() == "Accept client's request"
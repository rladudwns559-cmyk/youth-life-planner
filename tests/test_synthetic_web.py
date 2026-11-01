"""M3.0 HTTP 경계와 기존 core 결과의 연결 검증. 기존 fixture는 읽기 전용."""
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.web.app import app
from backend.web.schemas import SimulationInput
from backend.web.service import simulate
from backend.cashflow import CashflowInput
from backend.cashflow.calculator import calculate_cashflow
from backend.policy_engine import EvaluationContext, UserProfile, evaluate_policies, load_policy_set, load_profile

ROOT = Path(__file__).resolve().parents[1]
URL = '/api/synthetic/simulate'

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def payload():
    return dict(age=24, region='안산시', student_status=True, employment_status='employed',
                monthly_income=1500000, monthly_rent=450000, monthly_fixed_expenses=200000,
                other_monthly_expenses=350000, user_savings_capacity=300000)

def statuses(body):
    return [p['overall_status'] for p in body['policies']]

def test_health_and_no_store(client):
    response = client.get('/api/health')
    assert response.json() == dict(status='ok', synthetic=True, test_only=True)
    assert response.headers['cache-control'] == 'no-store'

def test_existing_fixture_and_cli_contract(client, payload):
    profile = load_profile(ROOT/'data/synthetic/profile.json')
    policies = load_policy_set(ROOT/'data/synthetic/policies.json')
    expected = evaluate_policies(profile, policies, EvaluationContext(date(2026,10,20),policies.dataset_version))
    response = client.post(URL,json=payload)
    assert response.status_code == 200
    body=response.json()
    assert body['synthetic'] is True and body['test_only'] is True
    assert statuses(body)==['PASS','FAIL','UNKNOWN']
    assert body['dataset_version']=='synthetic-v1'
    for item, evaluation, policy in zip(body['policies'],expected,policies.policies,strict=True):
        assert item == dict(evaluation.to_dict(),policy_name=policy.policy_name)

@pytest.mark.parametrize('employment,income,rent,cap,expected_status,surplus,savable',[
    ('unemployed',1500000,450000,300000,['PASS','PASS','UNKNOWN'],500000,300000),
    ('employed',1800000,550000,500000,['PASS','FAIL','UNKNOWN'],700000,500000),
])
def test_proposal_scenarios(client,payload,employment,income,rent,cap,expected_status,surplus,savable):
    payload.update(employment_status=employment,monthly_income=income,monthly_rent=rent,user_savings_capacity=cap)
    body=client.post(URL,json=payload).json()
    assert statuses(body)==expected_status
    assert body['cashflow']['disposable_after_policy']==surplus
    assert body['cashflow']['savable_amount']==savable
    assert body['cashflow']['policy_benefit_applied']==0

@pytest.mark.parametrize('changes',[
    {}, {'monthly_income':0}, {'monthly_income':100000,'user_savings_capacity':None},
    {'user_savings_capacity':0}, {'user_savings_capacity':None},
    {'monthly_income':10**12,'monthly_rent':10**12,'monthly_fixed_expenses':10**12,'other_monthly_expenses':10**12},
])
def test_core_cashflow_exact_equality_and_no_rent_double_subtraction(client,payload,changes):
    payload.update(changes)
    body=client.post(URL,json=payload).json()
    values={k:payload[k] for k in ('monthly_income','monthly_rent','monthly_fixed_expenses','other_monthly_expenses','user_savings_capacity')}
    expected=calculate_cashflow(CashflowInput(**values,monthly_policy_cash_benefit=0)).to_dict()
    assert body['cashflow']==expected
    assert body['cashflow']['total_monthly_expenses']==payload['monthly_rent']+payload['monthly_fixed_expenses']+payload['other_monthly_expenses']
    assert body['input_summary']==payload

def test_negative_disposable_preserved(client,payload):
    payload['monthly_income']=100000
    cash=client.post(URL,json=payload).json()['cashflow']
    assert cash['disposable_before_policy']==cash['disposable_after_policy']==-900000
    assert cash['savable_amount']==0

def test_capacity_none_zero_are_distinct(client,payload):
    payload['user_savings_capacity']=None
    assert client.post(URL,json=payload).json()['cashflow']['savable_amount']==500000
    payload['user_savings_capacity']=0
    assert client.post(URL,json=payload).json()['cashflow']['savable_amount']==0

def test_missing_policy_inputs_unknown_and_income_not_household(client,payload):
    payload.update(age=None,region=None,student_status=None,employment_status=None,monthly_income=10**12)
    body=client.post(URL,json=payload).json()
    assert statuses(body)==['UNKNOWN']*3
    assert body['policies'][0]['missing_fields']==['age','region']
    assert body['policies'][1]['missing_fields']==['employment_status']
    assert body['policies'][2]['missing_fields']==['household_income','region']

@pytest.mark.parametrize('age,status',[(18,'FAIL'),(19,'PASS'),(34,'PASS'),(35,'FAIL'),(None,'UNKNOWN')])
def test_age_boundaries(client,payload,age,status):
    payload['age']=age
    assert client.post(URL,json=payload).json()['policies'][0]['overall_status']==status

@pytest.mark.parametrize('region,status',[('서울시','FAIL'),(' 안산시 ','PASS'),('', 'UNKNOWN')])
def test_region(client,payload,region,status):
    payload['region']=region
    assert client.post(URL,json=payload).json()['policies'][0]['overall_status']==status

@pytest.mark.parametrize('field,value',[
    ('monthly_income',-1),('monthly_income',True),('monthly_income',1.5),('monthly_income','1500000'),
    ('monthly_income',None),('monthly_income',10**12+1),('monthly_rent',-1),
    ('monthly_fixed_expenses',False),('other_monthly_expenses',-1),('user_savings_capacity',-1),
    ('age',True),('age',121),('employment_status','student'),('student_status','true'),('region','가'*81),
    ('monthly_policy_cash_benefit',100000),('household_income',2000000),('policy_facts',[]),
])
def test_invalid_input_or_benefit_injection_rejected(client,payload,field,value):
    payload[field]=value
    response=client.post(URL,json=payload)
    assert response.status_code==422
    assert response.headers['cache-control']=='no-store'
    assert all(set(e)=={'loc','type'} for e in response.json()['errors'])
    assert 'input' not in response.json()

def test_missing_required_and_malformed_json(client,payload):
    del payload['monthly_income']
    assert client.post(URL,json=payload).status_code==422
    response=client.post(URL,content='{bad',headers={'Content-Type':'application/json'})
    assert response.status_code==422
    assert '{bad' not in response.text

def test_service_request_isolation_and_reproducibility(payload):
    first=simulate(SimulationInput(**payload)).model_dump()
    simulate(SimulationInput(**dict(payload,monthly_income=0,employment_status='unemployed')))
    assert simulate(SimulationInput(**payload)).model_dump()==first
    assert UserProfile().policy_facts==()

def test_core_functions_are_really_called(monkeypatch,client,payload):
    import backend.web.service as service
    calls=[]
    original_policy=service.evaluate_policies
    original_cash=service.calculate_cashflow
    def policy(*args):
        calls.append(('policy',args[0]))
        return original_policy(*args)
    def cash(value):
        calls.append(('cash',value))
        return original_cash(value)
    monkeypatch.setattr(service,'evaluate_policies',policy)
    monkeypatch.setattr(service,'calculate_cashflow',cash)
    assert client.post(URL,json=payload).status_code==200
    assert [c[0] for c in calls]==['policy','cash']
    assert calls[0][1].policy_facts==()
    assert calls[1][1].monthly_policy_cash_benefit==0

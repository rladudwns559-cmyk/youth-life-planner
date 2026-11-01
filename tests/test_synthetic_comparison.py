"""M3.1: 기존 코어와 연결된 비교 경계의 계약을 검증한다."""
import copy
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.web.app import app
from backend.web.comparison import compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from backend.web.schemas import SimulationInput
from backend.web.service import simulate
from backend.policy_engine import EvaluationContext, UserProfile, evaluate_policies, load_policy_set
from backend.cashflow import CashflowInput
from backend.cashflow.calculator import calculate_cashflow
from datetime import date

URL='/api/synthetic/compare'
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def client():
    with TestClient(app) as value:yield value

@pytest.fixture
def profile():
    return dict(age=24,region='안산시',student_status=True,employment_status='unemployed',monthly_income=1500000,
        monthly_rent=450000,monthly_fixed_expenses=200000,other_monthly_expenses=350000,user_savings_capacity=300000)

def request(client,before,after):
    response=client.post(URL,json=dict(before=before,after=after))
    assert response.status_code==200,response.text
    return response.json()

def test_same_inputs_zero_deltas_and_no_changes(client,profile):
    body=request(client,profile,profile)
    assert body['before']==body['after']
    assert not body['changed_input_fields']
    assert all(v==0 for v in body['numeric_deltas'].values())
    assert all(not t['status_changed'] for t in body['policy_transitions'])
    assert '변경한 입력이 없어' in body['explanations'][0]

@pytest.mark.parametrize('field,value,expected',[
    ('monthly_income',1800000,dict(monthly_income=300000,disposable_after_policy=300000,savable_amount=0)),
    ('monthly_rent',550000,dict(monthly_rent=100000,disposable_after_policy=-100000,savable_amount=0)),
    ('user_savings_capacity',400000,dict(disposable_after_policy=0,savable_amount=100000,user_savings_capacity=100000)),
    ('employment_status','employed',dict(disposable_after_policy=0,savable_amount=0)),
    ('monthly_fixed_expenses',0,dict(monthly_fixed_expenses=-200000,disposable_after_policy=200000)),
    ('other_monthly_expenses',0,dict(other_monthly_expenses=-350000,disposable_after_policy=350000)),
])
def test_single_variable_changes(client,profile,field,value,expected):
    after=dict(profile,**{field:value})
    body=request(client,profile,after)
    assert body['changed_input_fields']==[dict(field=field,before=profile[field],after=value)]
    for key,amount in expected.items():assert body['numeric_deltas'][key]==amount

def test_proposal_four_changes_exact(client,profile):
    after=dict(profile,employment_status='employed',monthly_income=1800000,monthly_rent=550000,user_savings_capacity=500000)
    body=request(client,profile,after)
    assert {i['field'] for i in body['changed_input_fields']}=={'employment_status','monthly_income','monthly_rent','user_savings_capacity'}
    assert body['before']['cashflow']['disposable_after_policy']==500000
    assert body['after']['cashflow']['disposable_after_policy']==700000
    assert body['numeric_deltas']['disposable_after_policy']==200000
    assert body['numeric_deltas']['savable_amount']==200000
    assert body['numeric_deltas']['monthly_income']==300000
    assert body['numeric_deltas']['monthly_rent']==100000
    assert [(p['before_status'],p['after_status']) for p in body['policy_transitions']]==[('PASS','PASS'),('PASS','FAIL'),('UNKNOWN','UNKNOWN')]
    assert body['before']['cashflow']['savable_amount']==300000
    assert body['after']['cashflow']['savable_amount']==500000
    assert '취업상태 입력이 미취업에서 취업' in body['policy_transitions'][1]['explanation']
    assert '가구소득' in body['policy_transitions'][2]['explanation']
    assert '월 여유자금이 200,000원 증가했습니다.' in body['explanations']
    assert '월세가 100,000원 증가했습니다.' in body['explanations']

@pytest.mark.parametrize('b,a,transition',[
    ('unemployed','unemployed',('PASS','PASS')),
    ('unemployed','employed',('PASS','FAIL')),
    ('employed','unemployed',('FAIL','PASS')),
    (None,None,('UNKNOWN','UNKNOWN')),
    ('unemployed',None,('PASS','UNKNOWN')),
    (None,'unemployed',('UNKNOWN','PASS')),
])
def test_real_fixture_six_transitions(client,profile,b,a,transition):
    body=request(client,dict(profile,employment_status=b),dict(profile,employment_status=a))
    policy=body['policy_transitions'][1]
    assert (policy['before_status'],policy['after_status'])==transition
    rule=policy['rules'][0]
    assert (rule['before']['status'],rule['after']['status'])==transition
    assert rule['input_changed']==(b!=a)

def test_unknown_and_income_causality(client,profile):
    body=request(client,profile,dict(profile,monthly_income=10**12))
    policy=body['policy_transitions'][2]
    assert policy['before_status']==policy['after_status']=='UNKNOWN'
    assert not any(r['input_changed'] for r in policy['rules'])
    assert policy['rules'][1]['before']['reason_code']==policy['rules'][1]['after']['reason_code']=='MISSING_FIELD'
    assert body['unknown_information'][0]['after_missing_fields']==['household_income']
    assert all(not t['status_changed'] for t in body['policy_transitions'])

def test_fail_can_keep_missing_information(client,profile):
    body=request(client,profile,dict(profile,region='서울시'))
    info=body['unknown_information'][0]
    assert info['after_status']=='FAIL'
    assert info['after_missing_fields']==['household_income']
    assert body['policy_transitions'][0]['after_status']=='FAIL'

@pytest.mark.parametrize('b,a,delta,b_save,a_save',[
    (None,None,None,500000,500000),(None,0,None,500000,0),(0,None,None,0,500000),
    (0,0,0,0,0),(300000,500000,200000,300000,500000),
])
def test_capacity_none_zero(client,profile,b,a,delta,b_save,a_save):
    body=request(client,dict(profile,user_savings_capacity=b),dict(profile,user_savings_capacity=a))
    assert body['numeric_deltas']['user_savings_capacity']==delta
    assert body['before']['cashflow']['savable_amount']==b_save
    assert body['after']['cashflow']['savable_amount']==a_save
    assert body['numeric_deltas']['savable_amount']==a_save-b_save

def test_negative_disposable_and_negative_delta(client,profile):
    body=request(client,profile,dict(profile,monthly_income=100000))
    assert body['after']['cashflow']['disposable_after_policy']==-900000
    assert body['numeric_deltas']['disposable_after_policy']==-1400000
    assert body['numeric_deltas']['savable_amount']==-300000
    assert body['after']['cashflow']['savable_amount']==0

def test_core_and_existing_simulation_full_results(client,profile):
    after=dict(profile,employment_status='employed',monthly_income=1800000,monthly_rent=550000,user_savings_capacity=500000)
    body=request(client,profile,after)
    policies=load_policy_set(ROOT/'data/synthetic/policies.json')
    for key,data in [('before',profile),('after',after)]:
        assert body[key]==simulate(SimulationInput(**data)).model_dump()
        p=UserProfile(**{k:data[k] for k in ('age','region','student_status','employment_status','monthly_income')})
        expected=evaluate_policies(p,policies,EvaluationContext(date(2026,10,20),policies.dataset_version))
        assert body[key]['policies']==[dict(r.to_dict(),policy_name=policy.policy_name) for r,policy in zip(expected,policies.policies)]
        cash=CashflowInput(**{k:data[k] for k in ('monthly_income','monthly_rent','monthly_fixed_expenses','other_monthly_expenses','user_savings_capacity')})
        assert body[key]['cashflow']==calculate_cashflow(cash).to_dict()

def test_adapter_and_cores_called_twice_independently(monkeypatch,client,profile):
    from backend.web import service
    adapter,engine,calculator=service.simulate,service.evaluate_policies,service.calculate_cashflow
    calls=[]
    def simulation(data):calls.append(('adapter',data.monthly_income));return adapter(data)
    def policy(user,*args):calls.append(('policy',user.monthly_income));assert user.policy_facts==();return engine(user,*args)
    def cash(value):calls.append(('cash',value.monthly_income));assert value.monthly_policy_cash_benefit==0;return calculator(value)
    monkeypatch.setattr(service,'simulate',simulation)
    monkeypatch.setattr(service,'evaluate_policies',policy)
    monkeypatch.setattr(service,'calculate_cashflow',cash)
    request(client,profile,dict(profile,monthly_income=1800000))
    assert calls==[('adapter',1500000),('policy',1500000),('cash',1500000),('adapter',1800000),('policy',1800000),('cash',1800000)]

def test_input_and_result_independence(profile):
    raw=dict(before=profile,after=dict(profile,monthly_income=0,employment_status=None))
    original=copy.deepcopy(raw);data=ComparisonInput.model_validate(raw);snapshot=data.model_dump()
    first=compare_scenarios(data).model_dump()
    assert raw==original and data.model_dump()==snapshot
    assert first['before']['input_summary']==profile
    first['after']['input_summary']['monthly_income']=999
    assert compare_scenarios(data).model_dump()['after']['input_summary']['monthly_income']==0

@pytest.mark.parametrize('side',['before','after'])
@pytest.mark.parametrize('field,value',[('monthly_income',-1),('monthly_income','1500000'),('monthly_rent',True),('user_savings_capacity',-1),('age',121),('employment_status','student'),('household_income',0),('monthly_policy_cash_benefit',100000)])
def test_nested_validation(client,profile,side,field,value):
    data=dict(before=copy.deepcopy(profile),after=copy.deepcopy(profile));data[side][field]=value
    response=client.post(URL,json=data)
    assert response.status_code==422
    assert response.headers['cache-control']=='no-store'
    assert any(e['loc'][:2]==['body',side] for e in response.json()['errors'])
    assert all(set(e)=={'loc','type'} for e in response.json()['errors'])

@pytest.mark.parametrize('data',[{},dict(before={}),dict(before=None,after=None),dict(before={},after={},extra=True)])
def test_required_scenarios(client,data):assert client.post(URL,json=data).status_code==422

def test_invalid_after_does_not_start_before(monkeypatch,client,profile):
    from backend.web import service
    def forbidden(*args):raise AssertionError('Validation must precede both calculations')
    monkeypatch.setattr(service,'simulate',forbidden)
    assert client.post(URL,json=dict(before=profile,after=dict(profile,monthly_income=-1))).status_code==422

def test_after_failure_never_returns_partial_result(monkeypatch,profile):
    from backend.web import service
    original=service.simulate;calls=[]
    def fail_after(data):
        calls.append(data)
        if len(calls)==2:raise RuntimeError('SYNTHETIC_TEST_FAILURE')
        return original(data)
    monkeypatch.setattr(service,'simulate',fail_after)
    with TestClient(app,raise_server_exceptions=False) as client:
        response=client.post(URL,json=dict(before=profile,after=dict(profile,monthly_income=1800000)))
    assert response.status_code==500
    assert 'SYNTHETIC_TEST_FAILURE' not in response.text
    assert 'before' not in response.text and '1500000' not in response.text

def test_zero_benefit_facts_disclaimer_and_original_endpoint(client,profile):
    body=request(client,profile,dict(profile,monthly_income=1800000))
    assert body['synthetic'] is body['test_only'] is True
    assert body['benefit_applied_krw']==body['numeric_deltas']['policy_benefit_applied']==0
    assert body['before']['cashflow']['policy_benefit_applied']==body['after']['cashflow']['policy_benefit_applied']==0
    assert body['explanation_facts']['cashflow']['numeric_deltas']==body['numeric_deltas']
    assert '합성' in body['disclaimer'] and '보장하지 않습니다' in body['disclaimer']
    assert client.post('/api/synthetic/simulate',json=profile).json()==body['before']

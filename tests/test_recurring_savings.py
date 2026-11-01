"""M3.2: 가상 정액적금 계산·반올림·기존 월 예산 연결 계약."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from decimal import Decimal,Inexact,Rounded,localcontext
import pytest
from fastapi.testclient import TestClient
from backend.finance.recurring import (RecurringSavingsInput,SavingsValidationError,calculate_recurring_savings)
from backend.web.app import app
from backend.web.schemas import SimulationInput
from backend.web import service

PROFILE=dict(age=24,region='안산시',student_status=True,employment_status='unemployed',
 monthly_income=1500000,monthly_rent=450000,monthly_fixed_expenses=200000,
 other_monthly_expenses=350000,user_savings_capacity=300000)
REQUEST=dict(profile=PROFILE,monthly_payment=200000,term_months=12,annual_base_rate_percent='3')
client=TestClient(app)

def calc(p=200000,n=12,r='3'):
    return calculate_recurring_savings(RecurringSavingsInput(p,n,Decimal(r)))

def post(**changes):return client.post('/api/synthetic/savings/recurring',json={**deepcopy(REQUEST),**changes})

def test_required_example():
    result=calc()
    assert (result.total_principal_krw,result.estimated_interest_before_tax_krw,result.estimated_maturity_before_tax_krw)==(2400000,39000,2439000)
    assert result.annual_rate_ratio=='0.03'

@pytest.mark.parametrize('rate,expected',[('9.9999',0),('10',1),('10.0001',1)])
def test_half_won_boundary(rate,expected):
    assert calc(60,1,rate).estimated_interest_before_tax_krw==expected

def test_round_once_after_total_not_per_installment():
    assert calc(1,3,'100').unrounded_interest_krw=='0.5'
    assert calc(1,3,'100').estimated_interest_before_tax_krw==1

@pytest.mark.parametrize('payment,months,rate,principal,interest',[
 (0,12,'3',0,0),(200000,12,'0',2400000,0),(200000,12,'3.1250',2400000,40625),
 (120000,1,'0.1',120000,10),(1000000000000,120,'100',120000000000000,605000000000000)])
def test_rates_terms_and_limits(payment,months,rate,principal,interest):
    result=calc(payment,months,rate)
    assert result.total_principal_krw==principal
    assert result.estimated_interest_before_tax_krw==interest
    assert result.estimated_maturity_before_tax_krw==principal+interest<2**53

@pytest.mark.parametrize('payment',[-1,1000000000001,1.5,'1',True,None])
def test_invalid_payment(payment):
    with pytest.raises(SavingsValidationError):RecurringSavingsInput(payment,12,Decimal('3'))

@pytest.mark.parametrize('months',[0,-1,121,1.0,'12',True,None])
def test_invalid_term(months):
    with pytest.raises(SavingsValidationError):RecurringSavingsInput(1,months,Decimal('3'))

@pytest.mark.parametrize('rate',[3.0,'3',True,None,Decimal('NaN'),Decimal('sNaN'),Decimal('Infinity'),Decimal('-1'),Decimal('100.0001'),Decimal('0.00001')])
def test_invalid_rate(rate):
    with pytest.raises(SavingsValidationError):RecurringSavingsInput(1,12,rate)

def test_pure_immutable_independent_decimal_context():
    data=RecurringSavingsInput(200000,12,Decimal('3'))
    with localcontext() as context:
        context.prec=2;context.traps[Inexact]=True;context.traps[Rounded]=True
        expected=calc();result=calculate_recurring_savings(data)
        assert result==expected and context.prec==2 and context.traps[Inexact]
    with pytest.raises(FrozenInstanceError):data.monthly_payment=0
    with pytest.raises(FrozenInstanceError):result.total_principal_krw=0
    separate=result.to_dict();separate['total_principal_krw']=0
    assert result.total_principal_krw==2400000

def test_unsupported_input_type_and_method():
    with pytest.raises(SavingsValidationError):calculate_recurring_savings({})
    with pytest.raises(SavingsValidationError,match='UNSUPPORTED_ASSUMPTION'):
        RecurringSavingsInput(1,12,Decimal('3'),'COMPOUND')

def test_http_real_result_and_existing_cashflow(monkeypatch):
    calls=[];original=service.calculate_cashflow
    def record(data):calls.append(data);return original(data)
    monkeypatch.setattr(service,'calculate_cashflow',record)
    original_request=deepcopy(REQUEST)
    response=post();assert response.status_code==200
    out=response.json()
    assert REQUEST==original_request
    assert out['estimated_maturity_before_tax_krw']==2439000
    assert len(calls)==1 and calls[0].monthly_policy_cash_benefit==0
    assert out['cashflow']==service.simulate(SimulationInput(**PROFILE)).cashflow
    assert out['budget_comparison']['policy_benefit_applied']==0
    assert out['synthetic'] is True and out['test_only'] is True
    assert out['assumptions']['tax']=='PRE_TAX'
    assert out['assumptions']['deposit_timing']=='BEGINNING_OF_MONTH'
    assert out['rounding']['stage']=='TOTAL_INTEREST_ONCE'
    assert len(out['unsupported_conditions'])==9
    assert '실제 은행 상품' in out['disclaimer']

@pytest.mark.parametrize('payment,exceeds,excess',[(299999,False,0),(300000,False,0),(300001,True,1)])
def test_budget_boundary_no_auto_reduction(payment,exceeds,excess):
    out=post(monthly_payment=payment).json();budget=out['budget_comparison']
    assert budget['exceeds_budget_cap'] is exceeds and budget['excess_krw']==excess
    assert out['monthly_payment']==payment and out['total_principal_krw']==payment*12
    assert budget['savings_capacity_mode']=='EXPLICIT_LIMIT'
    assert all(value not in ('PASS','FAIL','UNKNOWN') for value in budget.values())

@pytest.mark.parametrize('capacity,cap,mode',[(None,500000,'UNSPECIFIED'),(0,0,'EXPLICIT_ZERO')])
def test_none_and_zero_differ(capacity,cap,mode):
    out=post(profile={**PROFILE,'user_savings_capacity':capacity}).json()
    assert out['budget_comparison']['savable_amount_krw']==cap
    assert out['budget_comparison']['savings_capacity_mode']==mode
    assert out['cashflow']['user_savings_capacity']==capacity

def test_deficit_retained_and_never_promises_affordability():
    out=post(profile={**PROFILE,'monthly_income':0,'user_savings_capacity':None}).json()
    assert out['cashflow']['disposable_after_policy']==-1000000
    assert out['budget_comparison']['has_deficit'] is True
    assert out['budget_comparison']['savable_amount_krw']==0
    assert out['estimated_maturity_before_tax_krw']==2439000
    assert '보장하지 않습니다' in out['budget_comparison']['message']

@pytest.mark.parametrize('field,value',[
 ('monthly_payment',-1),('monthly_payment',True),('monthly_payment','200000'),('monthly_payment',1.1),
 ('monthly_payment',1000000000001),('term_months',0),('term_months',121),('term_months','12'),('term_months',True),
 ('annual_base_rate_percent',3),('annual_base_rate_percent',3.1),('annual_base_rate_percent',''),
 ('annual_base_rate_percent','NaN'),('annual_base_rate_percent','Infinity'),('annual_base_rate_percent','1e1'),
 ('annual_base_rate_percent','3,0'),('annual_base_rate_percent','-1'),('annual_base_rate_percent','100.0001'),
 ('annual_base_rate_percent','0.00001'),('annual_base_rate_percent','03'),('annual_base_rate_percent',' 3'),
 ('monthly_policy_cash_benefit',100000),('savable_amount',1000000),('tax_rate',0),('compound',True)])
def test_http_strict_validation(field,value):
    assert post(**{field:value}).status_code==422

@pytest.mark.parametrize('method',['COMPOUND','ACTUAL_DAYS','AFTER_TAX','EARLY_TERMINATION','VARIABLE_RATE','FLEXIBLE','GOVERNMENT_MATCH','RENEWAL',None,5])
def test_http_unsupported_error_explicit(method):
    response=post(calculation_method=method)
    assert response.status_code==422
    assert response.json()['errors'][0]['type']=='UNSUPPORTED_ASSUMPTION'

@pytest.mark.parametrize('field',['profile','monthly_payment','term_months','annual_base_rate_percent'])
def test_missing_required(field):
    data=deepcopy(REQUEST);del data[field]
    assert client.post('/api/synthetic/savings/recurring',json=data).status_code==422

def test_profile_extra_policy_or_household_money_cannot_be_injected():
    for key in ('monthly_policy_cash_benefit','household_income','savable_amount'):
        assert post(profile={**PROFILE,key:999999}).status_code==422

def test_http_rounding_real_decimal_string():
    out=post(monthly_payment=60,term_months=1,annual_base_rate_percent='10').json()
    assert out['unrounded_interest_krw']=='0.5'
    assert out['estimated_interest_before_tax_krw']==1
    assert out['estimated_maturity_before_tax_krw']==61

"""입력/기존 예산 adapter/순수 적금 계산 연결. 실제 상품은 취급하지 않는다."""
import re
from decimal import Decimal
from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from pydantic_core import PydanticCustomError
from backend.finance.recurring import METHOD,MAX_TERM_MONTHS,RecurringSavingsInput,calculate_recurring_savings
from .schemas import Money,SimulationInput
from . import service

UNSUPPORTED=('복리','실제 일수 기준 이자','중도해지','우대금리 자동 충족','세후 실수령액','변동금리','자유적립식','정책형 적금 정부 기여금','재가입·장기 전망')

class RecurringSavingsRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)
    profile:SimulationInput
    monthly_payment:Money
    term_months:Annotated[int,Field(strict=True,ge=1,le=MAX_TERM_MONTHS)]
    annual_base_rate_percent:Annotated[str,Field(strict=True,max_length=8)]
    calculation_method:Literal['MONTHLY_BEGINNING_FIXED_SIMPLE_PRETAX']=METHOD

    @field_validator('annual_base_rate_percent')
    @classmethod
    def rate(cls,value):
        if not re.fullmatch(r'(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?',value) or Decimal(value)>100:
            raise PydanticCustomError('INVALID_RATE','0~100의 십진수 문자열, 소수4자리 이내가 필요합니다')
        return value

    @field_validator('calculation_method',mode='before')
    @classmethod
    def supported(cls,value):
        if value!=METHOD:raise PydanticCustomError('UNSUPPORTED_ASSUMPTION','지원하지 않는 계산 방식입니다')
        return value

class BudgetComparison(BaseModel):
    savable_amount_krw:int
    requested_monthly_payment_krw:int
    exceeds_budget_cap:bool
    excess_krw:int
    has_deficit:bool
    savings_capacity_mode:Literal['UNSPECIFIED','EXPLICIT_ZERO','EXPLICIT_LIMIT']
    user_savings_capacity_krw:int|None
    policy_benefit_applied:Literal[0]=0
    message:str

class RecurringSavingsResponse(BaseModel):
    synthetic:Literal[True]=True
    test_only:Literal[True]=True
    monthly_payment:int
    term_months:int
    annual_base_rate_percent:str
    annual_rate_ratio:str
    total_principal_krw:int
    estimated_interest_before_tax_krw:int
    estimated_maturity_before_tax_krw:int
    unrounded_interest_krw:str
    calculation_method:Literal['MONTHLY_BEGINNING_FIXED_SIMPLE_PRETAX']=METHOD
    assumptions:dict[str,str]
    rounding:dict[str,str]
    unsupported_conditions:list[str]
    cashflow:dict
    budget_comparison:BudgetComparison
    disclaimer:str

def simulate_recurring_savings(data:RecurringSavingsRequest)->RecurringSavingsResponse:
    # 클라이언트의 계산된 상한을 신뢰하지 않고 기존 adapter로 다시 계산한다.
    cash=service.simulate(data.profile).cashflow
    result=calculate_recurring_savings(RecurringSavingsInput(data.monthly_payment,data.term_months,
        Decimal(data.annual_base_rate_percent),data.calculation_method))
    cap=cash['savable_amount'];excess=max(0,data.monthly_payment-cap)
    capacity=cash['user_savings_capacity']
    mode='UNSPECIFIED' if capacity is None else 'EXPLICIT_ZERO' if capacity==0 else 'EXPLICIT_LIMIT'
    message=(f'입력한 월 납입액이 현재 저축 투입 상한보다 {excess:,}원 큽니다. 납입액은 자동으로 줄이지 않았습니다.'
        if excess else '입력한 월 납입액은 현재 계산한 저축 투입 상한 이내입니다.')
    if cash['disposable_after_policy']<0:message+=' 현재 월 예산은 적자이며 저축 투입 상한은 0원입니다.'
    message+=' 현재 입력에 따른 상한 비교이며 실제 상품 가입이나 장기 납입 여력을 보장하지 않습니다.'
    return RecurringSavingsResponse(**result.to_dict(),
        assumptions=dict(deposit_timing='BEGINNING_OF_MONTH',contribution='FIXED_MONTHLY',rate_type='FIXED',interest='SIMPLE',tax='PRE_TAX',period='INTEGER_MONTHS'),
        rounding=dict(mode='ROUND_HALF_UP',unit='KRW',stage='TOTAL_INTEREST_ONCE',description='총이자를 계산한 뒤 마지막에 한 번만 원 단위로 반올림합니다. 0.5원은 올립니다.'),
        unsupported_conditions=list(UNSUPPORTED),cashflow=cash,
        budget_comparison=BudgetComparison(savable_amount_krw=cap,requested_monthly_payment_krw=data.monthly_payment,
            exceeds_budget_cap=excess>0,excess_krw=excess,has_deficit=cash['disposable_after_policy']<0,
            savings_capacity_mode=mode,user_savings_capacity_krw=capacity,message=message),
        disclaimer='가상 정액적금의 계산 예시입니다. 실제 은행 상품·추천이 아니며 세후 실수령액이나 금융수익을 보장하지 않습니다. 정책 지원금 반영은 0원입니다.')

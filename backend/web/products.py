"""공식 스냅샷 목록/비교. 사용자 입력의 외부 전송·저장·순위 없음."""
from datetime import datetime,timedelta,timezone
from typing import Annotated
from fastapi import APIRouter,HTTPException
from pydantic import Field,model_validator
from backend.finance import products
from . import service
from .schemas import Money,SimulationInput
from .savings import BudgetComparison

router=APIRouter(prefix='/api/financial-products',tags=['financial-products'])
DISCLAIMER='공식 과거 스냅샷의 조건 비교이며 현재 금리·가입 자격·수익을 보장하지 않습니다. 우대금리는 자동 적용하지 않습니다. 정책 지원금 반영은 0원입니다.'

def today():return datetime.now(timezone(timedelta(hours=9))).date()

class ProductComparisonInput(products.StrictModel):
    profile:SimulationInput
    after_profile:SimulationInput|None=None
    monthly_payment:Money
    term_months:Annotated[int,Field(strict=True,ge=1,le=120)]
    product_ids:Annotated[list[products.Identifier],Field(min_length=1,max_length=10)]

    @model_validator(mode='after')
    def unique(self):
        if len(self.product_ids)!=len(set(self.product_ids)):raise ValueError('DUPLICATE_PRODUCT_ID')
        return self

def get_catalog():
    try:return products.load_catalog()
    except products.CatalogError:raise HTTPException(503,detail='공식 상품 스냅샷을 읽지 못했습니다. 데이터 확인이 필요합니다.') from None

def product_info(product,as_of):
    reasons=products.compatibility_reasons(product,as_of)
    return {**product.model_dump(mode='json'),
        'calculation_status':'SUPPORTED_ASSUMPTIONS' if not reasons else 'INFORMATION_ONLY',
        'calculation_reason_codes':reasons,'calculation_reasons':[products.REASONS[c] for c in reasons],
        'freshness':'STALE' if 'STALE_SNAPSHOT' in reasons else 'SOURCE_DATED',
        'user_eligibility':'NOT_EVALUATED'}

@router.get('')
def list_products():
    catalog=get_catalog();as_of=today()
    values=[product_info(p,as_of) for p in catalog.products]
    return dict(dataset_version=catalog.dataset_version,evaluated_on=as_of.isoformat(),
        review_after_days=products.REVIEW_AFTER_DAYS,review_policy='서비스 재검토 기준이며 은행의 금리 유효기간이 아닙니다.',
        sources=[s.model_dump(mode='json') for s in catalog.sources],products=values,
        information_count=len(values),compatible_count=sum(not p['calculation_reason_codes'] for p in values),
        disclaimer=DISCLAIMER)

def budget(profile,payment):
    cash=service.simulate(profile).cashflow
    cap=cash['savable_amount'];excess=max(0,payment-cap);capacity=cash['user_savings_capacity']
    return BudgetComparison(savable_amount_krw=cap,requested_monthly_payment_krw=payment,
        exceeds_budget_cap=excess>0,excess_krw=excess,has_deficit=cash['disposable_after_policy']<0,
        savings_capacity_mode='UNSPECIFIED' if capacity is None else 'EXPLICIT_ZERO' if capacity==0 else 'EXPLICIT_LIMIT',
        user_savings_capacity_krw=capacity,
        message=(f'현재 저축 투입 상한보다 {excess:,}원 큽니다. 입력 납입액은 유지합니다.' if excess else '현재 계산한 저축 투입 상한 이내입니다.')+
        (' 월 예산이 적자입니다.' if cash['disposable_after_policy']<0 else '')+' 현재 입력의 예산 비교이며 실제 가입이나 장기 납입 여력을 보장하지 않습니다.').model_dump(mode='json')

@router.post('/compare')
def compare_products(data:ProductComparisonInput):
    catalog=get_catalog();by_id={p.product_id:p for p in catalog.products}
    if any(p not in by_id for p in data.product_ids):raise HTTPException(422,detail='목록에 없는 상품 ID입니다. 목록을 새로 확인해 주세요.')
    as_of=today()
    results=[dict(product=product_info(by_id[pid],as_of),**products.evaluate_product(by_id[pid],data.monthly_payment,data.term_months,as_of)) for pid in data.product_ids]
    supported=sum(r['calculation_supported'] for r in results)
    return dict(dataset_version=catalog.dataset_version,evaluated_on=as_of.isoformat(),monthly_payment=data.monthly_payment,
        term_months=data.term_months,results=results,sources=[s.model_dump(mode='json') for s in catalog.sources],
        information_count=len(results),calculated_count=supported,ranking=None,
        direct_maturity_comparison_supported=supported>=2,
        comparison_note='같은 월 납입액·기간·기본금리 계산 방식이 검증된 결과끼리만 금액 비교가 가능합니다. 미계산 결과는 0원으로 대체하지 않으며 순위를 만들지 않습니다.',
        budget=budget(data.profile,data.monthly_payment),
        after_budget=budget(data.after_profile,data.monthly_payment) if data.after_profile is not None else None,
        assumptions=dict(method=products.recurring.METHOD,rate_basis='BASE_RATE_ONLY',policy_benefit_applied=0),disclaimer=DISCLAIMER)

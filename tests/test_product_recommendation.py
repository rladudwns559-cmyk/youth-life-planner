from copy import deepcopy
from datetime import date
from decimal import Decimal
import pytest
from backend.finance.discovery import Catalog,Product
from backend.finance.recommendation import select_rate,rank_products,compile_recommendations
DAY=date(2026,11,2)
def product(id='BASE',kind='SAVINGS',maximum=500000):
 return Product.model_validate(dict(product_id=id,institution='검증은행',product_name=id,kind=kind,schedule='MONTHLY' if kind=='SAVINGS' else 'LUMP_SUM',minimum=1000,maximum=maximum,maximum_kind='KNOWN',min_months=6,max_months=36,allowed_months=None,payment_note='한도',term_note='기간',eligibility_note='추가 확인',features=[],preferential_conditions=[],required_checks=['확인'],channels=['모바일'],early_exit_note='중도해지',reference_only=False,reference_reason=None,rates=[],sources=[source()]))
def source(mode='OFFICIAL_PAGE',reviewed='2026-11-02'):
 return dict(url='https://www.kakaobank.com/products/freerate',title='공식상품',reviewed_on=reviewed,basis_date='2026-11-02',mode=mode,locator='금리표')
def review(base='3.8',top='8',**kwargs):
 return dict(rates=[dict(min_months=12,max_months=12,base_rate_percent=base,max_total_rate_percent=top,evidence_locator='12개월 기본금리')],sources=[source()],**kwargs)
def catalog(ps):
 return Catalog.model_validate(dict(schema_version='product-discovery-v1',dataset_version='TEST',reviewed_on='2026-11-02',review_after_days=7,coverage_note='합성',products=[p.model_dump(mode='json') for p in ps]))
def test_uses_basic_not_highest_promotional_rate():
 ps=[product('A'),product('B')];c=catalog(ps);reviews={'A':review('3','15'),'B':review('4','4')}
 result=rank_products(c,reviews,'SAVINGS',300000,12,DAY)
 assert [r['product_id'] for r in result]==['B','A']
 assert all(r['eligibility']=='UNKNOWN' and r['calculation'] is None for r in result)
def test_full_budget_precedes_higher_rate_partial_and_unallocated_remains_explicit():
 c=catalog([product('FULL'),product('PART',maximum=100000)])
 r=rank_products(c,{'FULL':review('3','3'),'PART':review('10','10')},'SAVINGS',300000,12,DAY)
 assert r[0]['product_id']=='FULL'
 assert r[1]['allocation']==100000 and r[1]['unallocated']==200000
def test_deposit_never_uses_monthly_budget():
 c=catalog([product('D','DEPOSIT',maximum=10000000)])
 r=rank_products(c,{'D':review()},'DEPOSIT',None,12,DAY)
 assert r[0]['code']=='INPUT' and r[0]['allocation'] is None
@pytest.mark.parametrize('bad',[None,review(excluded_reason='회전 금리'),dict(rates=review()['rates'],sources=[source('OFFICIAL_INDEXED_PAGE')]),dict(rates=review()['rates'],sources=[source(reviewed='2026-10-20')]),dict(rates=[dict(review()['rates'][0],base_rate_percent='NaN')],sources=[source()]),dict(rates=[dict(review()['rates'][0],base_rate_percent='Infinity')],sources=[source()]),review('5','3')])
def test_unverified_stale_and_invalid_rates_are_not_rankable(bad):
 assert select_rate(product(),12,bad,DAY) is None
def test_period_conflicts_and_future_evidence_do_not_promote():
 p=product();r=review()
 assert select_rate(p,6,r,DAY) is None
 r['rates'].append(dict(r['rates'][0],base_rate_percent='4'))
 assert select_rate(p,12,r,DAY) is None
 assert select_rate(p,12,review(),date(2026,11,1)) is None
def test_zero_missing_and_order_compilation_preserve_inputs():
 c=catalog([product('A'),product('B')]);reviews={'A':review('3','4'),'B':review('4','8')};old=deepcopy(reviews);before=c.model_dump(mode='json')
 assert rank_products(c,reviews,'SAVINGS',0,12,DAY)[0]['code']=='BUDGET'
 compiled=compile_recommendations(c,reviews,DAY)
 assert compiled['order_pool'][compiled['order_calendar']['SAVINGS']['12']]==['B','A']
 assert compiled['actual_product_calculation_count']==0
 assert reviews==old and before==c.model_dump(mode='json')
def test_unknown_rate_id_rejected():
 with pytest.raises(ValueError,match='UNKNOWN_RATE_PRODUCT'):compile_recommendations(catalog([product()]),{'FAKE':review()},DAY)
@pytest.mark.parametrize('amount',[-1,True,1.5,'300000',10**12+1])
def test_invalid_amounts_rejected(amount):
 with pytest.raises(ValueError):rank_products(catalog([product()]),{},'SAVINGS',amount,12,DAY)


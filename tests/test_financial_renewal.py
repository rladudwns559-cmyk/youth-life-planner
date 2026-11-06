"""Synthetic recheck compiler contracts; these are not bank confirmations."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import pytest

from backend.finance.discovery import Catalog, decision, lookup
from backend.finance.renewal import compile_renewals

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample():
    raw = json.loads((ROOT/'data/financial-products/discovery-extended-20261103.json').read_text(encoding='utf-8'))
    product = next(p for p in raw['products'] if p['product_id']=='KAKAO-FREE-SAVINGS')
    catalog = Catalog.model_validate({**raw, 'products': [product]})
    new = deepcopy(product)
    for source in new['sources']:
        source.update(reviewed_on='2026-11-06', mode='OFFICIAL_PAGE')
    batch = {'checked_on':'2026-11-06','updates':[{'product':new, 'review':None,'sale_status':'CURRENT','evidence_note':'SYNTHETIC proof for compiler unit tests only','change_notes':[]}], 'holds':[]}
    return catalog, batch


def test_recheck_does_not_mutate_historical_inputs(sample):
    catalog,batch=sample
    original=deepcopy(batch);before=catalog.model_dump(mode='json')
    result=compile_renewals(catalog,{},[batch],date(2026,11,6))
    assert batch==original and catalog.model_dump(mode='json')==before
    record=result['records']['KAKAO-FREE-SAVINGS']
    assert record['valid_until']=='2026-11-13'
    assert result['actual_product_calculation_count']==result['policy_benefit_applied_krw']==0
    assert result['automatic_refresh'] is False


@pytest.mark.parametrize('amount',[0,999,1000,300000,3000000,3000001,None])
@pytest.mark.parametrize('months',[1,6,12,36,37,120])
def test_rechecked_table_matches_existing_python_engine_at_boundaries(sample,amount,months):
    catalog,batch=sample
    result=compile_renewals(catalog,{},[batch],date(2026,11,6))
    record=result['records']['KAKAO-FREE-SAVINGS'];compiled=record['compiled']
    product=Catalog.model_validate(compiled['catalog']).products[0]
    assert lookup(compiled,product,amount,months)==decision(product,amount,months,date(2026,11,6),catalog.review_after_days)
    assert product.eligibility=='UNKNOWN' and product.calculation is None


def test_missing_sale_page_does_not_renew_an_archived_pdf(sample):
    catalog,batch=sample
    for s in batch['updates'][0]['product']['sources']:s['mode']='OFFICIAL_DOCUMENT'
    with pytest.raises(ValueError,match='CURRENT_SALE_PAGE_REQUIRED'):
        compile_renewals(catalog,{},[batch],date(2026,11,6))


def test_unchanged_source_date_does_not_renew_by_successful_fetch_only(sample):
    catalog,batch=sample
    batch['updates'][0]['product']['sources'][0]['reviewed_on']='2026-11-03'
    with pytest.raises(ValueError,match='FRESH_DIRECT_SOURCE_REQUIRED'):
        compile_renewals(catalog,{},[batch],date(2026,11,6))


def test_closed_requires_official_evidence_and_failed_fetch_is_only_unconfirmed(sample):
    catalog,batch=sample
    hold={'product_id':'KAKAO-FREE-SAVINGS','sale_status':'DISCONTINUED','reason':'synthetic closure','sources':[]}
    batch.update(updates=[],holds=[hold])
    with pytest.raises(ValueError,match='OFFICIAL_DISCONTINUATION_EVIDENCE_REQUIRED'):
        compile_renewals(catalog,{},[batch],date(2026,11,6))
    hold['sale_status']='UNCONFIRMED';hold['reason']='Synthetic fetch failure is not closure'
    result=compile_renewals(catalog,{},[batch],date(2026,11,6));r=result['records']['KAKAO-FREE-SAVINGS']
    assert r['status']=='UNCONFIRMED' and r['product']['reference_only']
    assert r['product']['sources']==catalog.products[0].model_dump(mode='json')['sources']
    assert result['recommendations']['rate_by_product']=={}


def test_later_review_supersedes_previous_but_same_day_duplicates_fail(sample):
    catalog,batch=sample
    with pytest.raises(ValueError,match='DUPLICATE_SAME_DAY_RECHECK'):
        compile_renewals(catalog,{},[batch,batch],date(2026,11,6))
    later=deepcopy(batch);later['checked_on']='2026-11-07'
    for s in later['updates'][0]['product']['sources']:s['reviewed_on']='2026-11-07'
    result=compile_renewals(catalog,{},[later,batch],date(2026,11,7))
    assert result['records']['KAKAO-FREE-SAVINGS']['checked_on']=='2026-11-07'
    assert batch['checked_on']=='2026-11-06'


def test_future_recheck_is_rejected(sample):
    catalog,batch=sample
    with pytest.raises(ValueError,match='FUTURE_RECHECK'):
        compile_renewals(catalog,{},[batch],date(2026,11,5))


def test_every_published_renewal_table_matches_unchanged_engine():
    data=json.loads((ROOT/'frontend/src/public-data/financial-renewals.json').read_text(encoding='utf-8'))
    count=0
    for record in data['records'].values():
        if record['status']!='CURRENT':continue
        compiled=record['compiled'];product=Catalog.model_validate(compiled['catalog']).products[0]
        amounts={0,1000,300000,10000000,None}
        if product.minimum is not None:amounts.update([max(0,product.minimum-1),product.minimum])
        if product.maximum is not None:amounts.update([product.maximum,product.maximum+1])
        for months in [1,6,12,24,36,60,120]:
            for amount in amounts:
                assert lookup(compiled,product,amount,months)==decision(product,amount,months,date.fromisoformat(record['checked_on']),7)
                count+=1
    assert count>3000


@pytest.mark.parametrize('url',[
    'http://www.kakaobank.com/products/savings',
    'https://localhost/private','https://127.0.0.1/private',
    'https://www.kakaobank.com:8443/products/savings',
    'https://user:secret@www.kakaobank.com/products/savings',
])
def test_source_checker_rejects_unapproved_destinations(url):
    from tools.check_financial_sources import official_url
    with pytest.raises(ValueError,match='UNAPPROVED_OFFICIAL_URL'):official_url(url)


def test_certificate_failure_does_not_become_discontinuation_or_success(monkeypatch):
    import ssl
    from tools import check_financial_sources as tool
    class Failed:
        def open(self,*args,**kwargs):raise ssl.SSLError('synthetic verification failure')
    monkeypatch.setattr(tool,'build_opener',lambda *args:Failed())
    result=tool.inspect('https://www.kakaobank.com/products/savings')
    assert result['result']=='FETCH_FAILED_NOT_DISCONTINUED'
    assert 'sha256' not in result

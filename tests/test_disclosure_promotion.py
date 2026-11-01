from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import pytest
from pydantic import ValidationError
from backend.finance.discovery import ROOT,Catalog,Product,load_catalog,decision,search,compile_tables,lookup,validate_disclosure_links

DAY=date(2026,11,1)
@pytest.fixture(scope='module')
def catalog():return load_catalog()
IDS=['IM-TOGETHER-SAVINGS','BNK-BUSAN-CARBON-SAVINGS','BNK-BUSAN-PET-SAVINGS','BNK-BUSAN-ONLYONE-SAVINGS','BNK-BUSAN-BIG-SAVINGS','KBSB-KIND-EPLUS','KBSB-KIND-NURI','PEPPER-REGULAR','PEPPER-DIGITAL-REGULAR','PEPPER-2030','WELCOME-WALKING','WELCOME-HAJA','WELCOME-CHILDLOVE']

def named(catalog,pid):return next(p for p in catalog.products if p.product_id==pid)
@pytest.mark.parametrize('pid',IDS)
def test_each_promoted_product_has_real_minimum_term_and_cap_boundaries(catalog,pid):
    p=named(catalog,pid)
    assert p.disclosure_ids and p.sources and not p.reference_only and not p.comparison_hold_reason
    assert decision(p,p.minimum-1,p.min_months,DAY,7)=='BUDGET'
    assert decision(p,p.minimum,p.min_months,DAY,7)=='FIT'
    if p.maximum is not None:
        assert decision(p,p.maximum,p.min_months,DAY,7)=='FIT'
        assert decision(p,p.maximum+1,p.min_months,DAY,7)=='PARTIAL'
    else:assert p.maximum_kind=='UNLIMITED' and decision(p,10**12,p.min_months,DAY,7)=='FIT'
    assert decision(p,p.minimum,p.max_months+1,DAY,7)=='TERM'
    assert p.eligibility=='UNKNOWN' and p.calculation is None and not p.rates

def test_discrete_pet_period_and_parent_evidence_are_not_inferred(catalog):
    assert decision(named(catalog,'BNK-BUSAN-PET-SAVINGS'),10000,7,DAY,7)=='TERM'
    assert '만16세' in named(catalog,'WELCOME-CHILDLOVE').eligibility_note
    assert '합산' in named(catalog,'KBSB-KIND-EPLUS').eligibility_note
    # Neither satisfying a budget nor a product name establishes personal eligibility.
    assert all(r['eligibility']=='UNKNOWN' for r in search(catalog,300000,12,2000000,DAY)['rows'])

def test_exact_primary_to_disclosure_relationship_and_old_snapshot_preservation(catalog):
    previous=load_catalog(ROOT/'data/financial-products/discovery-expanded-20261031.json')
    assert len(catalog.products)==74 and len(previous.products)==61
    assert all(p==named(catalog,p.product_id) for p in previous.products)
    promoted=[p for p in catalog.products if p.disclosure_ids];assert len(promoted)==13
    assert sum(len(p.disclosure_ids) for p in promoted)==14
    assert len(named(catalog,'PEPPER-REGULAR').disclosure_ids)==2
    assert validate_disclosure_links(catalog)

def test_review_inventory_does_not_promote_held_or_missing_conditions(catalog):
    review=json.loads((ROOT/'data/financial-products/disclosure-verifications-20261101.json').read_text(encoding='utf-8'))
    linked={i for p in catalog.products for i in p.disclosure_ids}
    held={i for p in review['holds'] for i in p['disclosure_ids']}
    assert review['promoted_product_count']==13 and review['promoted_disclosure_count']==14
    assert len(review['holds'])==9 and not linked&held
    assert review['calculation_count']==0 and review['eligibility']=='UNKNOWN'

@pytest.mark.parametrize('ids',[['unknown'],['DISC-0000000000000000','DISC-0000000000000000'],['DISC-zzzzzzzzzzzzzzzz']])
def test_invalid_or_repeated_disclosure_ids_fail_closed(catalog,ids):
    raw=catalog.products[0].model_dump();raw['disclosure_ids']=ids
    with pytest.raises(ValidationError):Product.model_validate(raw)

def test_duplicate_ownership_and_unknown_source_ids_are_not_accepted(catalog):
    data=catalog.model_dump(mode='json');data['products'][0]['disclosure_ids']=data['products'][-1]['disclosure_ids']
    with pytest.raises(ValidationError):Catalog.model_validate(data)
    with pytest.raises(ValueError,match='UNKNOWN_DISCLOSURE_LINK'):validate_disclosure_links(catalog,set())

def test_promoted_public_results_match_python_without_refreshing_old_evidence(catalog):
    compiled=compile_tables(catalog,DAY)
    assert compiled['built_on']=='2026-11-01' and compiled['valid_until']=='2026-11-06'
    for pid in IDS:
        p=named(catalog,pid)
        for n in (0,p.minimum-1,p.minimum,300000,1000001):
            for m in (1,6,7,12,24,36,60):assert lookup(compiled,p,n,m)==decision(p,n,m,DAY,7)
    result=search(catalog,300000,12,2000000,DAY)
    newly=[r for r in result['rows'] if r['product_id'] in IDS]
    assert len(newly)==13 and all(r['code'] in ('FIT','PARTIAL') for r in newly)
    assert result['actual_product_calculation_count']==0 and result['policy_benefit_applied_krw']==0

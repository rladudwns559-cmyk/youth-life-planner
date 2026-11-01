import hashlib,json
from datetime import date
from pathlib import Path
import pytest
from backend.finance.discovery import Product,load_catalog,decision,compile_tables,lookup,ROOT
from tools.import_disclosure_directory import parse_disclosure,HEADERS

DAY=date(2026,11,1)
@pytest.fixture(scope='module')
def catalog():return load_catalog()
def product(catalog,pid):return next(p for p in catalog.products if p.product_id==pid)

@pytest.mark.parametrize('pid',['NH-ALLONE-E-SAVINGS','KN-WITHUS','KN-COME-DO','KB-TRAVEL'])
def test_payment_increment_is_not_silently_ignored(catalog,pid):
    p=product(catalog,pid)
    for n in (p.minimum,p.minimum+1,p.maximum,p.maximum+1):assert decision(p,n,p.min_months,DAY,7)=='MISSING'

@pytest.mark.parametrize('pid',['NH-CHAEUM','NH-SUCCESS-PARTNER','NH-HOPE-II','KB-HAPPINESS','HANA-SME-EMPLOYEE','SC-FIRST-HOUSEHOLD'])
def test_schedule_and_combined_contracts_do_not_become_positive_bounds(catalog,pid):
    p=product(catalog,pid);assert p.comparison_hold_reason
    assert decision(p,p.minimum,p.min_months,DAY,7)=='MISSING'

def test_deposit_partial_remains_lump_sum_and_never_interest(catalog):
    p=product(catalog,'IBK-FAMILY-DEPOSIT');assert decision(p,100000001,12,DAY,7)=='PARTIAL';assert p.calculation is None

def test_new_comparable_records_and_discrete_terms(catalog):
    cases=[('HANA-TODAY',200000,6,'FIT'),('HANA-TODAY',200001,6,'PARTIAL'),('NH-ALLONE-E-DEPOSIT',99999,12,'BUDGET'),('NH-ALLONE-E-DEPOSIT',100000,12,'FIT'),('NH-1934-COMPOUND',500000,12,'FIT'),('KN-PRIMARY',10000,13,'TERM'),('KB-ONE',500001,12,'PARTIAL'),('IBK-FAMILY-SAVING',10000,13,'TERM')]
    for pid,n,m,result in cases:assert decision(product(catalog,pid),n,m,DAY,7)==result

def test_public_encoding_deduplicates_only_identical_month_matrices(catalog):
    compiled=compile_tables(catalog,DAY);assert compiled['schema_version']=='product-discovery-public-v2'
    for t in compiled['tables'].values():
        assert len(t['months'])==120 and len(t['patterns'])<120
        assert len({json.dumps(p) for p in t['patterns']})==len(t['patterns'])
    for p in catalog.products:
        for m in range(1,121):
            for amount in (None,0,999,10000,10001,300000,500000,1000000,100000001):assert lookup(compiled,p,amount,m)==decision(p,amount,m,DAY,7)

def test_dated_disclosure_reference_data_never_invents_personal_conditions():
    data=json.loads((ROOT/'data/financial-products/disclosure-directory-20261023.json').read_text(encoding='utf-8'))
    assert data['source_level']=='BANK_REPUBLISHED_FSS_DISCLOSURE' and data['basis_date']=='2026-10-23'
    assert data['raw_rows']==416 and data['unique_products']==len(data['products'])==299 and data['institutions']==97
    assert len({(p['institution'],p['product_name']) for p in data['products']})==299
    assert sorted(n for p in data['products'] for n in p['row_numbers'])==list(range(1,417))
    assert all(p['monthly_limit'] is None and p['eligibility']=='UNKNOWN' and not p['current_sale_verified'] for p in data['products'])
    assert json.loads((ROOT/'frontend/src/public-data/disclosure-directory.json').read_text(encoding='utf-8'))==data

def table(rows,headers=HEADERS):return ('2026-10-23<table><tr>'+''.join('<th>'+v+'</th>' for v in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</table>').encode()
ROW=['1','시험은행','1금융권','시험적금','12개월','정액적립식','단리','2.00%','3.00%']
def test_importer_groups_variants_without_inventing_independent_products():
    row2=ROW.copy();row2[0]='2';row2[6]='복리'
    raw=table([ROW,row2]);d=parse_disclosure(raw,'2026-10-31')
    assert d['raw_rows']==2 and d['unique_products']==1 and len(d['products'][0]['options'])==2
    assert d['source_sha256']==hashlib.sha256(raw).hexdigest()

@pytest.mark.parametrize('index,value',[(0,'3'),(2,'모름'),(4,'6개월'),(5,'새방식'),(6,'알수없음'),(7,'NaN%'),(8,'-1%'),(7,'101%')])
def test_importer_rejects_drift_instead_of_guessing(index,value):
    row=ROW.copy();row[index]=value
    with pytest.raises(ValueError):parse_disclosure(table([row]),'2026-10-31')

def test_conflicting_same_variant_is_retained_without_averaging_or_max_choice():
    row2=ROW.copy();row2[0]='2';row2[7]='2.50%'
    d=parse_disclosure(table([ROW,row2]),'2026-10-31')
    assert {o['base_rate_percent'] for o in d['products'][0]['options']}=={'2.00','2.50'}

def test_importer_rejects_future_missing_date_and_changed_headers():
    with pytest.raises(ValueError):parse_disclosure(table([ROW]),'2026-10-01')
    with pytest.raises(ValueError):parse_disclosure(table([ROW]).replace(b'2026-10-23',b'2025-01-01'),'2026-10-31')
    with pytest.raises(ValueError):parse_disclosure(table([ROW],HEADERS[:-1]+['최고금리']),'2026-10-31')

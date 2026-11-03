"""Dated official product discovery. No policy eligibility or interest calculation.

The public page consumes tables compiled by this Python module. It never
reimplements these financial predicates or sends economic inputs elsewhere.
"""
import bisect,json
from datetime import date,timedelta
from pathlib import Path
from typing import Annotated,Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field,model_validator

ROOT=Path(__file__).resolve().parents[2]
CATALOG_PATH=ROOT/'data/financial-products/discovery-promoted-20261101.json'
MAX_AMOUNT=1_000_000_000_000
HOSTS={'www.nybank.co.kr','www.kusb.co.kr','www.kuemhwabank.co.kr','www.insungsavingsbank.co.kr','www.dhsavingsbank.co.kr','www.daemyungbank.co.kr','hisntm.com','hbsb.co.kr','www.ycbank.co.kr','www.smartbank.co.kr','www.samhosb.co.kr','www.ptbank.co.kr','www.moasb.co.kr','www.mkb.co.kr','www.dysbank.com','www.daehanbank.co.kr','www.bulimbank.co.kr','www.angukbank.co.kr','m.moasb.co.kr','www.suhyup-bank.com','www.oksavingsbank.com','www.daolsb.com','nsl.yegaramsb.co.kr','m.daolsb.com','ssmt.wooribank.com','spot.wooribank.com','www.woorisavingsbank.com','www.hanwhasbank.com','www.osb.co.kr','www.jt-bank.co.kr','kbthink.com','www.hanasavings.com','www.kakaobank.com','og.kakaobank.io','www.kbanknow.com','www.tossbank.com','api.tossbank.com','obank.kbstar.com','img2.kbstar.com','www.kebhana.com','banking.kebhana.com','m.kebhana.com','image.kebhana.com','mybank.ibk.co.kr','blog.ibk.co.kr','img.shinhan.com','www.kjbank.com','www.knbank.co.kr','m.knbank.co.kr','m.jbbank.co.kr','www.ibksb.co.kr','img.nonghyup.com','smartmarket.nonghyup.com','www.standardchartered.co.kr','m.kbsavings.com','www.pepperbank.kr','www.welcomebank.co.kr','www.busanbank.co.kr','www.imbank.co.kr'}

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)

class Source(Strict):
    url:str
    title:str
    reviewed_on:str
    basis_date:str|None
    mode:Literal['PREVIOUS_VERIFIED_SNAPSHOT','OFFICIAL_PAGE','OFFICIAL_INDEXED_PAGE','OFFICIAL_DOCUMENT']
    locator:str
    @model_validator(mode='after')
    def valid(self):
        p=urlsplit(self.url)
        if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):raise ValueError('OFFICIAL_SOURCE_REQUIRED')
        if not p.path or p.path=='/':raise ValueError('PRODUCT_SOURCE_REQUIRED')
        reviewed=date.fromisoformat(self.reviewed_on)
        if self.basis_date and date.fromisoformat(self.basis_date)>reviewed:raise ValueError('FUTURE_BASIS_DATE')
        return self

class Product(Strict):
    product_id:str
    institution:str
    product_name:str
    kind:Literal['SAVINGS','DEPOSIT']
    schedule:Literal['MONTHLY','LUMP_SUM','QUARTERLY','WEEKLY_STEP','DAILY','CUSTOM_DATE']
    minimum:Annotated[int,Field(ge=0)]|None
    maximum:Annotated[int,Field(ge=0)]|None
    maximum_kind:Literal['KNOWN','UNLIMITED','UNKNOWN']
    min_months:Annotated[int,Field(ge=1,le=120)]|None
    max_months:Annotated[int,Field(ge=1,le=120)]|None
    allowed_months:list[int]|None
    payment_note:str
    term_note:str
    eligibility_note:str
    features:list[str]
    preferential_conditions:list[str]
    required_checks:list[str]
    channels:list[str]
    early_exit_note:str
    reference_only:bool
    reference_reason:str|None
    rates:list[dict]
    sources:list[Source]
    disclosure_ids:list[str]=Field(default_factory=list)
    comparison_hold_reason:str|None=None
    amount_increment:Annotated[int,Field(ge=1)]|None=None
    calculation:None=None
    eligibility:Literal['UNKNOWN']='UNKNOWN'
    @model_validator(mode='after')
    def coherent(self):
        if len(set(self.disclosure_ids))!=len(self.disclosure_ids) or any(len(i)!=21 or not i.startswith('DISC-') or any(c not in '0123456789abcdef' for c in i[5:]) for i in self.disclosure_ids):raise ValueError('INVALID_DISCLOSURE_LINK')
        if self.comparison_hold_reason is not None and not self.comparison_hold_reason.strip():raise ValueError('EMPTY_HOLD_REASON')
        if not self.product_id or not self.sources:raise ValueError('MISSING_ID_OR_SOURCE')
        if self.maximum_kind=='KNOWN' and self.maximum is None:raise ValueError('MISSING_LIMIT')
        if self.maximum_kind!='KNOWN' and self.maximum is not None:raise ValueError('AMBIGUOUS_LIMIT')
        if self.minimum is not None and self.maximum is not None and self.minimum>self.maximum:raise ValueError('INVALID_LIMIT')
        if self.min_months and self.max_months and self.min_months>self.max_months:raise ValueError('INVALID_TERM')
        if self.allowed_months is not None and (not self.allowed_months or len(set(self.allowed_months))!=len(self.allowed_months) or any(type(m)is not int or not 1<=m<=120 or self.min_months and m<self.min_months or self.max_months and m>self.max_months for m in self.allowed_months)):raise ValueError('INVALID_ALLOWED_MONTHS')
        if self.kind=='DEPOSIT' and self.schedule!='LUMP_SUM':raise ValueError('WRONG_DEPOSIT_BASIS')
        if self.reference_only and not self.reference_reason:raise ValueError('MISSING_REFERENCE_REASON')
        return self

class Catalog(Strict):
    schema_version:Literal['product-discovery-v1']
    dataset_version:str
    reviewed_on:str
    review_after_days:Annotated[int,Field(ge=1,le=30)]
    coverage_note:str
    products:list[Product]
    @model_validator(mode='after')
    def coherent(self):
        reviewed=date.fromisoformat(self.reviewed_on)
        if not self.products or len({p.product_id for p in self.products})!=len(self.products):raise ValueError('EMPTY_OR_DUPLICATE_PRODUCT')
        linked=[i for p in self.products for i in p.disclosure_ids]
        if len(linked)!=len(set(linked)):raise ValueError('DUPLICATE_DISCLOSURE_OWNER')
        if any(date.fromisoformat(s.reviewed_on)>reviewed for p in self.products for s in p.sources):raise ValueError('FUTURE_SOURCE')
        return self

def pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('DUPLICATE_JSON_KEY')
        d[k]=v
    return d

def load_catalog(path=CATALOG_PATH):
    return Catalog.model_validate(json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs))

# Codes are a public presentation contract, not policy PASS/FAIL/UNKNOWN.
LABELS={'FIT':'금액·기간 비교 가능','PARTIAL':'일부 금액으로 비교 가능','TERM':'목표 기간과 다름','BUDGET':'납입 예산 부족','INPUT':'예치할 목돈 입력 필요','SCHEDULE':'납입 일정 추가 확인','REVIEW':'자료 추가 확인','STALE':'자료 재검토 시점','MISSING':'공식 조건 미확인'}

def decision(p:Product,amount:int|None,months:int,as_of:date,review_days:int):
    if type(months)is not int or not 1<=months<=120 or type(as_of)is not date:raise ValueError('INVALID_CONTEXT')
    if amount is not None and (type(amount)is not int or not 0<=amount<=MAX_AMOUNT):raise ValueError('INVALID_AMOUNT')
    if any(not 0<=(as_of-date.fromisoformat(s.reviewed_on)).days<=review_days for s in p.sources):return 'STALE'
    if p.reference_only:return 'REVIEW'
    if p.min_months is None or p.max_months is None:return 'MISSING'
    if not p.min_months<=months<=p.max_months or p.allowed_months is not None and months not in p.allowed_months:return 'TERM'
    if p.schedule not in ('MONTHLY','LUMP_SUM'):return 'SCHEDULE'
    if amount is None:return 'INPUT'
    if amount==0 or p.minimum is not None and amount<p.minimum:return 'BUDGET'
    if p.comparison_hold_reason or p.amount_increment is not None and p.amount_increment>1:return 'MISSING'
    if p.minimum is None or p.maximum_kind=='UNKNOWN':return 'MISSING'
    if p.maximum is not None and amount>p.maximum:return 'PARTIAL'
    return 'FIT'

def search(catalog,monthly_amount,months,lump_sum,as_of):
    # Reject invalid inputs even if no corresponding products are registered.
    for n in (monthly_amount,lump_sum):
        if n is not None and (type(n)is not int or not 0<=n<=MAX_AMOUNT):raise ValueError('INVALID_AMOUNT')
    if monthly_amount is None and lump_sum is None:raise ValueError('AMOUNT_REQUIRED')
    rows=[]
    for p in catalog.products:
        amount=lump_sum if p.kind=='DEPOSIT' else monthly_amount
        code=decision(p,amount,months,as_of,catalog.review_after_days)
        allocation=p.maximum if code=='PARTIAL' else amount if code=='FIT' else None
        rows.append(dict(product_id=p.product_id,code=code,label=LABELS[code],allocation=allocation,unallocated=None if allocation is None else amount-allocation,eligibility='UNKNOWN',calculation=None))
    return dict(rows=rows,actual_product_calculation_count=0,policy_benefit_applied_krw=0,ranked_by_yield=False)

def validate_disclosure_links(catalog,known_ids=None):
    linked={i for p in catalog.products for i in p.disclosure_ids}
    if linked and known_ids is None:
        source=json.loads((ROOT/'data/financial-products/disclosure-directory-20261023.json').read_text(encoding='utf-8'))
        known_ids={p['product_id'] for p in source['products']}
    if linked-set(known_ids or []):raise ValueError('UNKNOWN_DISCLOSURE_LINK')
    return True

def compile_tables(catalog,as_of):
    validate_disclosure_links(catalog)
    tables={};codebook=list(LABELS)
    for kind in ('SAVINGS','DEPOSIT'):
        products=[p for p in catalog.products if p.kind==kind]
        boundaries={0,1}
        for p in products:
            if p.minimum is not None:boundaries.add(p.minimum)
            if p.maximum is not None and p.maximum<MAX_AMOUNT:boundaries.add(p.maximum+1)
        bounds=sorted(boundaries)
        # None is the last row, distinct from zero. No inputs enter the build.
        # Many months have the same predicate outcomes. Store each exact matrix once.
        # This changes encoding only; all outcomes still come from decision().
        patterns=[];month_index={};seen={}
        for m in range(1,121):
            matrix=[[codebook.index(decision(p,a,m,as_of,catalog.review_after_days)) for p in products] for a in [*bounds,None]]
            key=json.dumps(matrix,separators=(',',':'))
            if key not in seen:seen[key]=len(patterns);patterns.append(matrix)
            month_index[str(m)]=seen[key]
        tables[kind]=dict(product_ids=[p.product_id for p in products],boundaries=bounds,months=month_index,patterns=patterns)
    valid_until=min(date.fromisoformat(s.reviewed_on)+timedelta(days=catalog.review_after_days) for p in catalog.products for s in p.sources)
    return dict(schema_version='product-discovery-public-v2',built_on=as_of.isoformat(),valid_until=valid_until.isoformat(),catalog=catalog.model_dump(mode='json'),tables=tables,codebook=codebook,labels=LABELS,actual_product_calculation_count=0,paid_service=False,automatic_refresh=False)

def lookup(compiled,product,amount,months):
    table=compiled['tables'][product.kind]
    i=len(table['boundaries']) if amount is None else bisect.bisect_right(table['boundaries'],amount)-1
    return compiled['codebook'][table['patterns'][table['months'][str(months)]][i][table['product_ids'].index(product.product_id)]]

"""공식 스냅샷 로딩과 M3.2 계산 호환성. 웹 요청 중 외부 통신 없음."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated,Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from . import recurring

CATALOG_PATH=Path(__file__).resolve().parents[2]/'data/financial-products/catalog-v1.json'
REVIEW_AFTER_DAYS=90  # 서비스 재검토 기준이며 은행이 정한 금리 유효기간이 아니다.
Text=Annotated[str,Field(strict=True,min_length=1,max_length=2000)]
Identifier=Annotated[str,Field(strict=True,pattern=r'^[A-Z0-9][A-Z0-9_-]{0,79}$')]
Nonnegative=Annotated[int,Field(strict=True,ge=0,le=1_000_000_000_000)]

class StrictModel(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)

def valid_date(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('INVALID_DATE')
    date.fromisoformat(value)
    return value

def official_url(value):
    url=urlsplit(value)
    if url.scheme!='https' or url.hostname not in {'www.data.go.kr','mybank.ibk.co.kr','kiup.ibk.co.kr','www.ibk.co.kr'} or url.username or url.password or url.port not in (None,443):
        raise ValueError('INVALID_OFFICIAL_URL')
    if not url.path or url.path=='/':raise ValueError('SOURCE_MUST_BE_SPECIFIC')
    return value

def decimal_rate(value):
    if not re.fullmatch(r'(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?',value) or Decimal(value)>100:
        raise ValueError('INVALID_RATE')
    return value

class Source(StrictModel):
    source_id:Identifier
    title:Text
    provider:Text
    official_url:Text
    document_id:Text
    source_date:Text
    verified_on:Text
    license_url:Text
    license_label:Literal['이용허락범위 제한 없음']
    reuse_status:Literal['UNRESTRICTED']
    raw_filename:Annotated[str,Field(pattern=r'^[a-z0-9_-]+\.xlsx$')]
    raw_sha256:Annotated[str,Field(pattern=r'^[0-9a-f]{64}$')]
    _urls=field_validator('official_url','license_url')(official_url)
    _dates=field_validator('source_date','verified_on')(valid_date)

class RateBand(StrictModel):
    min_months:Annotated[int,Field(strict=True,ge=1,le=120)]
    max_months:Annotated[int,Field(strict=True,ge=1,le=120)]
    base_rate_percent:Text|None
    max_total_rate_percent:Text|None
    evidence_locator:Text

    @field_validator('base_rate_percent','max_total_rate_percent')
    @classmethod
    def rates(cls,value):return decimal_rate(value) if value is not None else None

    @model_validator(mode='after')
    def consistency(self):
        if self.min_months>self.max_months:raise ValueError('INVALID_RATE_TERM')
        if self.base_rate_percent is not None and self.max_total_rate_percent is not None and Decimal(self.max_total_rate_percent)<Decimal(self.base_rate_percent):raise ValueError('MAX_BELOW_BASE')
        return self

class ProductSnapshot(StrictModel):
    product_id:Identifier
    snapshot_version:Annotated[str,Field(pattern=r'^\d+\.\d+\.\d+$')]
    product_name:Text
    institution:Text
    product_type:Literal['RECURRING_SAVINGS']
    source_id:Identifier
    evidence_locator:Text
    basis_date:Text
    collected_on:Text
    verified_on:Text
    official_material_status:Literal['CONFIRMED','UNCONFIRMED']
    key_fields_status:Literal['PARTIAL','VERIFIED','CONFLICT']
    subscription_status:Literal['UNCONFIRMED','OPEN_AS_OF_SOURCE','CLOSED_AS_OF_SOURCE']
    target:Text
    term_description:Text
    minimum_monthly_payment:Nonnegative|None
    maximum_monthly_payment:Nonnegative|None
    payment_step:Annotated[int,Field(strict=True,ge=1,le=1_000_000)]|None
    rate_options:tuple[RateBand,...]
    max_preferential_bonus_percentage_points:Text|None
    preferential_conditions:tuple[Text,...]
    accumulation_method:Literal['FIXED_MONTHLY','FLEXIBLE','UNKNOWN']
    rate_type:Literal['FIXED','VARIABLE','UNKNOWN']
    interest_method:Literal['SIMPLE','COMPOUND','UNKNOWN']
    deposit_timing:Literal['BEGINNING_OF_MONTH','ACTUAL_DATE','UNKNOWN']
    date_basis:Literal['INTEGER_MONTHS','ACTUAL_DAYS','UNKNOWN']
    rounding_method:Literal['TOTAL_INTEREST_KRW_HALF_UP','OTHER','UNKNOWN']
    calculation_evidence_locator:Text|None
    enrollment_method:Text|None
    product_detail_url:Text|None
    unknown_fields:tuple[Text,...]
    cross_check_notes:tuple[Text,...]
    _dates=field_validator('basis_date','collected_on','verified_on')(valid_date)

    @field_validator('max_preferential_bonus_percentage_points')
    @classmethod
    def bonus(cls,value):return decimal_rate(value) if value is not None else None

    @field_validator('product_detail_url')
    @classmethod
    def url(cls,value):return official_url(value) if value is not None else None

    @model_validator(mode='after')
    def consistency(self):
        if not self.rate_options:raise ValueError('RATE_OPTIONS_REQUIRED')
        if self.minimum_monthly_payment is not None and self.maximum_monthly_payment is not None and self.minimum_monthly_payment>self.maximum_monthly_payment:raise ValueError('INVALID_LIMITS')
        if not self.preferential_conditions and self.max_preferential_bonus_percentage_points not in (None,'0'):raise ValueError('PREFERENTIAL_CONDITIONS_REQUIRED')
        ordered=sorted(self.rate_options,key=lambda x:x.min_months)
        if any(a.max_months>=b.min_months for a,b in zip(ordered,ordered[1:])):raise ValueError('OVERLAPPING_RATES')
        if date.fromisoformat(self.basis_date)>date.fromisoformat(self.verified_on) or date.fromisoformat(self.collected_on)>date.fromisoformat(self.verified_on):raise ValueError('INVALID_CHRONOLOGY')
        return self

class Catalog(StrictModel):
    schema_version:Literal['m3.3']
    dataset_version:Identifier
    sources:tuple[Source,...]
    products:tuple[ProductSnapshot,...]

    @model_validator(mode='after')
    def references(self):
        source_ids=[s.source_id for s in self.sources];ids=[p.product_id for p in self.products]
        if not source_ids or not ids:raise ValueError('EMPTY_CATALOG')
        if len(source_ids)!=len(set(source_ids)) or len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_ID')
        sources={s.source_id:s for s in self.sources}
        for product in self.products:
            if product.source_id not in sources:raise ValueError('MISSING_SOURCE')
            if product.basis_date!=sources[product.source_id].source_date:raise ValueError('SOURCE_DATE_MISMATCH')
        return self

class CatalogError(ValueError):pass

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise CatalogError('DUPLICATE_JSON_KEY')
        result[key]=value
    return result

def load_catalog(path:Path=CATALOG_PATH)->Catalog:
    try:
        text=path.read_text(encoding='utf-8')
        # JSON strict parsing retains missing vs zero; dates/rates remain explicit strings.
        value=json.loads(text,object_pairs_hook=_pairs)
        catalog=Catalog.model_validate_json(json.dumps(value,ensure_ascii=False))
        for source in catalog.sources:
            raw=path.parent/'sources'/source.raw_filename
            if hashlib.sha256(raw.read_bytes()).hexdigest()!=source.raw_sha256:raise CatalogError('SOURCE_HASH_MISMATCH')
        return catalog
    except (OSError,ValueError,TypeError) as error:
        raise CatalogError('FINANCIAL_CATALOG_INVALID') from error

REASONS={
 'OFFICIAL_UNCONFIRMED':'공식 자료 확인이 완료되지 않았습니다.',
 'FIELDS_UNVERIFIED':'핵심 계산 조건이 모두 검증되지 않았습니다.',
 'SOURCE_CONFLICT':'출처 간 불일치가 해결되지 않았습니다.',
 'STALE_SNAPSHOT':'자료가 오래되어 재확인이 필요합니다. 현재 금리로 계산하지 않습니다.',
 'FUTURE_DATE':'자료 확인일이 평가일보다 미래입니다.',
 'SUBSCRIPTION_UNCONFIRMED':'현재 신규 가입 상태를 확인하지 못했습니다.',
 'SUBSCRIPTION_CLOSED':'자료에서 판매 종료 상태입니다.',
 'ACCUMULATION_UNSUPPORTED':'자유적립식 또는 적립방식 미확인으로 정액적금 계산과 맞지 않습니다.',
 'RATE_TYPE_UNVERIFIED':'고정금리 적용을 확인하지 못했습니다.',
 'INTEREST_UNSUPPORTED':'단리 계산임을 확인하지 못했거나 복리 상품입니다.',
 'TIMING_UNSUPPORTED':'매월 초 동일 금액 납입 조건과 대응하지 않습니다.',
 'DAY_BASIS_UNSUPPORTED':'정수 개월 기준과 대응하지 않거나 일수 기준이 미확인입니다.',
 'ROUNDING_UNVERIFIED':'총이자 원 단위 반올림 방식의 대응이 미확인입니다.',
 'CALCULATION_EVIDENCE_MISSING':'계산 가정에 대응하는 공식 근거 위치가 없습니다.',
 'LIMITS_UNKNOWN':'최소·최대 납입액 또는 납입 단위를 확인하지 못했습니다.',
 'TERM_MISMATCH':'입력한 기간에 대응하는 공식 금리 조건이 없습니다.',
 'BASE_RATE_UNKNOWN':'기본금리가 미확인입니다. 0%로 대체하지 않습니다.',
 'BELOW_MINIMUM':'공식 최소 월 납입액보다 작습니다.',
 'ABOVE_MAXIMUM':'공식 최대 월 납입액을 초과합니다.',
 'PAYMENT_STEP_MISMATCH':'공식 납입 단위와 맞지 않습니다.',
}

def compatibility_reasons(product:ProductSnapshot,as_of:date)->list[str]:
    reasons=[]
    if product.official_material_status!='CONFIRMED':reasons.append('OFFICIAL_UNCONFIRMED')
    if product.key_fields_status=='CONFLICT':reasons.append('SOURCE_CONFLICT')
    elif product.key_fields_status!='VERIFIED':reasons.append('FIELDS_UNVERIFIED')
    if (as_of-date.fromisoformat(product.basis_date)).days>REVIEW_AFTER_DAYS:reasons.append('STALE_SNAPSHOT')
    if date.fromisoformat(product.verified_on)>as_of:reasons.append('FUTURE_DATE')
    if product.subscription_status=='UNCONFIRMED':reasons.append('SUBSCRIPTION_UNCONFIRMED')
    elif product.subscription_status=='CLOSED_AS_OF_SOURCE':reasons.append('SUBSCRIPTION_CLOSED')
    for condition,code in (
      (product.accumulation_method=='FIXED_MONTHLY','ACCUMULATION_UNSUPPORTED'),
      (product.rate_type=='FIXED','RATE_TYPE_UNVERIFIED'),
      (product.interest_method=='SIMPLE','INTEREST_UNSUPPORTED'),
      (product.deposit_timing=='BEGINNING_OF_MONTH','TIMING_UNSUPPORTED'),
      (product.date_basis=='INTEGER_MONTHS','DAY_BASIS_UNSUPPORTED'),
      (product.rounding_method=='TOTAL_INTEREST_KRW_HALF_UP','ROUNDING_UNVERIFIED'),
      (product.calculation_evidence_locator is not None,'CALCULATION_EVIDENCE_MISSING'),
      (all(v is not None for v in (product.minimum_monthly_payment,product.maximum_monthly_payment,product.payment_step)),'LIMITS_UNKNOWN')):
        if not condition:reasons.append(code)
    return reasons

def evaluate_product(product:ProductSnapshot,payment:int,months:int,as_of:date):
    reasons=compatibility_reasons(product,as_of)
    band=next((b for b in product.rate_options if b.min_months<=months<=b.max_months),None)
    if band is None:reasons.append('TERM_MISMATCH')
    elif band.base_rate_percent is None:reasons.append('BASE_RATE_UNKNOWN')
    if product.minimum_monthly_payment is not None and payment<product.minimum_monthly_payment:reasons.append('BELOW_MINIMUM')
    if product.maximum_monthly_payment is not None and payment>product.maximum_monthly_payment:reasons.append('ABOVE_MAXIMUM')
    if product.payment_step is not None and payment%product.payment_step:reasons.append('PAYMENT_STEP_MISMATCH')
    calculation=None
    if not reasons:
        calculation=recurring.calculate_recurring_savings(recurring.RecurringSavingsInput(payment,months,Decimal(band.base_rate_percent))).to_dict()
    return dict(product_id=product.product_id,rate_basis='BASE_RATE_ONLY',preferential_conditions_met='UNCONFIRMED',
        selected_base_rate_percent=band.base_rate_percent if band else None,
        selected_max_total_rate_percent=band.max_total_rate_percent if band else None,
        calculation_supported=not reasons,reason_codes=reasons,reasons=[REASONS[c] for c in reasons],
        calculation=calculation,user_eligibility='NOT_EVALUATED')

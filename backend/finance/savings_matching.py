"""Official savings amount/term matching. No eligibility or interest calculation."""
import json
from datetime import date
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from .products import StrictModel, Identifier, Nonnegative, RateBand, valid_date

CATALOG_PATH = Path(__file__).resolve().parents[2] / 'data/financial-products/matching-20261030.json'
REVIEW_AFTER_DAYS = 7  # Service review window; never a bank rate guarantee.
Text = Annotated[str, Field(strict=True, min_length=1, max_length=2000)]
Month = Annotated[int, Field(strict=True, ge=1, le=120)]
DOMAINS = {'KAKAO': {'www.kakaobank.com', 'og.kakaobank.io'},
           'KBANK': {'www.kbanknow.com'},
           'TOSS': {'www.tossbank.com', 'api.tossbank.com'}}


class MatchSource(StrictModel):
    source_id: Identifier
    bank_id: Literal['KAKAO', 'KBANK', 'TOSS']
    official_url: Text
    document_url: Text | None = None
    document_name: Text
    document_sha256: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')] | None = None
    rate_basis_date: str | None
    verified_on: str
    evidence_locator: Text
    reuse_scope: Literal['FACTS_ONLY_WITH_ATTRIBUTION']
    _verified = field_validator('verified_on')(valid_date)

    @field_validator('rate_basis_date')
    @classmethod
    def rate_date(cls, value):
        return valid_date(value) if value is not None else None

    @model_validator(mode='after')
    def official(self):
        for value in [self.official_url, self.document_url]:
            if value is None:
                continue
            parsed = urlsplit(value)
            if (parsed.scheme != 'https' or parsed.hostname not in DOMAINS[self.bank_id]
                    or parsed.username or parsed.password or parsed.port not in (None, 443)
                    or parsed.path in ('', '/')):
                raise ValueError('OFFICIAL_PRODUCT_URL_REQUIRED')
        if self.rate_basis_date and self.rate_basis_date > self.verified_on:
            raise ValueError('FUTURE_RATE_BASIS')
        return self


class MatchProduct(StrictModel):
    product_id: Identifier
    bank_id: Literal['KAKAO', 'KBANK', 'TOSS']
    institution: Text
    product_name: Text
    source_id: Identifier
    minimum_monthly_payment: Nonnegative | None
    maximum_monthly_payment: Nonnegative | None
    payment_step: Annotated[int, Field(strict=True, ge=1)] | None
    min_months: Month | None
    max_months: Month | None
    allowed_months: tuple[Month, ...] | None = None
    rate_options: tuple[RateBand, ...]
    preferential_conditions: tuple[Text, ...]
    rate_note: Text
    eligibility_note: Text
    term_note: Text
    unknown_fields: tuple[Text, ...]
    publication_status: Literal['LISTED', 'WITHDRAWN', 'UNCONFIRMED']
    calculation_status: Literal['NOT_VERIFIED'] = 'NOT_VERIFIED'

    @model_validator(mode='after')
    def coherent(self):
        if (self.minimum_monthly_payment is not None and self.maximum_monthly_payment is not None
                and self.minimum_monthly_payment > self.maximum_monthly_payment):
            raise ValueError('INVALID_PAYMENT_LIMITS')
        if self.min_months is not None and self.max_months is not None and self.min_months > self.max_months:
            raise ValueError('INVALID_TERM')
        if self.allowed_months is not None:
            if not self.allowed_months or len(set(self.allowed_months)) != len(self.allowed_months):
                raise ValueError('INVALID_ALLOWED_MONTHS')
            if any((self.min_months is not None and m < self.min_months) or
                   (self.max_months is not None and m > self.max_months) for m in self.allowed_months):
                raise ValueError('TERM_OUTSIDE_RANGE')
        bands = sorted(self.rate_options, key=lambda b: b.min_months)
        if any(a.max_months >= b.min_months for a, b in zip(bands, bands[1:])):
            raise ValueError('OVERLAPPING_RATE_BANDS')
        return self


class MatchingCatalog(StrictModel):
    schema_version: Literal['savings-match-v1']
    dataset_version: Identifier
    sources: tuple[MatchSource, ...]
    products: tuple[MatchProduct, ...]

    @model_validator(mode='after')
    def references(self):
        sources = {s.source_id: s for s in self.sources}
        if not sources or not self.products or len(sources) != len(self.sources):
            raise ValueError('INVALID_SOURCES')
        if len({p.product_id for p in self.products}) != len(self.products):
            raise ValueError('DUPLICATE_PRODUCT')
        for product in self.products:
            if product.source_id not in sources or sources[product.source_id].bank_id != product.bank_id:
                raise ValueError('SOURCE_BANK_MISMATCH')
        return self


class MatchingCatalogError(ValueError):
    pass


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('DUPLICATE_JSON_KEY')
        value[key] = item
    return value


def load_matching_catalog(path: Path = CATALOG_PATH) -> MatchingCatalog:
    try:
        data = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique_pairs)
        return MatchingCatalog.model_validate_json(json.dumps(data, ensure_ascii=False))
    except (OSError, ValueError, TypeError) as error:
        raise MatchingCatalogError('MATCHING_CATALOG_INVALID') from error


REASONS = {
    'NO_SAVING_CAPACITY': '현재 저축 투입 상한이 0원입니다.',
    'SOURCE_REVIEW_REQUIRED': '공식 자료를 다시 확인해야 하는 시점입니다.',
    'FUTURE_VERIFICATION': '자료 확인일이 평가일보다 미래입니다.',
    'NOT_LISTED': '현재 공식 상품 목록 등재를 확인하지 못했습니다.',
    'LIMIT_UNKNOWN': '월 납입 최소·최대 금액을 확인하지 못했습니다.',
    'TERM_UNKNOWN': '가입 기간을 확인하지 못했습니다.',
    'BELOW_MINIMUM': '월 저축액이 최소 납입액보다 작습니다.',
    'ABOVE_MAXIMUM': '월 저축액 전체가 상품 납입한도를 초과합니다.',
    'PAYMENT_STEP_MISMATCH': '월 저축액이 확인된 납입 단위와 맞지 않습니다.',
    'TERM_MISMATCH': '선택한 개월 수는 확인된 가입 기간과 맞지 않습니다.',
}


def match_savings(catalog: MatchingCatalog, monthly_amount: int, term_months: int, as_of: date):
    """Pure, deterministic amount/term filter; input values are never silently capped."""
    if type(monthly_amount) is not int or not 0 <= monthly_amount <= 1_000_000_000_000:
        raise ValueError('INVALID_MATCH_AMOUNT')
    if type(term_months) is not int or not 1 <= term_months <= 120 or type(as_of) is not date:
        raise ValueError('INVALID_MATCH_CONTEXT')
    sources = {s.source_id: s for s in catalog.sources}
    matched, excluded, review = [], [], []
    for product in catalog.products:
        source = sources[product.source_id]
        codes = []
        age = (as_of - date.fromisoformat(source.verified_on)).days
        if age < 0: codes.append('FUTURE_VERIFICATION')
        elif age > REVIEW_AFTER_DAYS: codes.append('SOURCE_REVIEW_REQUIRED')
        if product.publication_status != 'LISTED': codes.append('NOT_LISTED')
        if monthly_amount == 0: codes.append('NO_SAVING_CAPACITY')
        if product.minimum_monthly_payment is None or product.maximum_monthly_payment is None:
            codes.append('LIMIT_UNKNOWN')
        else:
            if monthly_amount < product.minimum_monthly_payment: codes.append('BELOW_MINIMUM')
            if monthly_amount > product.maximum_monthly_payment: codes.append('ABOVE_MAXIMUM')
        if product.payment_step is not None and monthly_amount % product.payment_step:
            codes.append('PAYMENT_STEP_MISMATCH')
        if product.min_months is None or product.max_months is None:
            codes.append('TERM_UNKNOWN')
        elif not product.min_months <= term_months <= product.max_months or (
                product.allowed_months is not None and term_months not in product.allowed_months):
            codes.append('TERM_MISMATCH')
        band = next((b for b in product.rate_options if b.min_months <= term_months <= b.max_months), None)
        row = dict(product=product.model_dump(mode='json'), source=source.model_dump(mode='json'),
                   selected_base_rate_percent=band.base_rate_percent if band else None,
                   selected_max_rate_percent=band.max_total_rate_percent if band else None,
                   reason_codes=codes, reasons=[REASONS[c] for c in codes],
                   user_eligibility='NOT_EVALUATED', preferential_conditions_met='UNCONFIRMED',
                   calculation=None, match_basis='MONTHLY_AMOUNT_AND_TERM_ONLY')
        if not codes:
            matched.append(row)
        elif any(c in codes for c in ['SOURCE_REVIEW_REQUIRED', 'FUTURE_VERIFICATION', 'LIMIT_UNKNOWN', 'TERM_UNKNOWN', 'NOT_LISTED']):
            review.append(row)
        else:
            excluded.append(row)
    # Stable institution/name ordering, never an interest/yield/recommendation ranking.
    key = lambda r: (r['product']['institution'], r['product']['product_name'], r['product']['product_id'])
    return dict(monthly_amount=monthly_amount, term_months=term_months,
                matches=sorted(matched,key=key), excluded=sorted(excluded,key=key), review_required=sorted(review,key=key),
                matched_count=len(matched), excluded_count=len(excluded), review_count=len(review),
                total_count=len(catalog.products))

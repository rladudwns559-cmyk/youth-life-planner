"""Local matching endpoint. Economic inputs never leave this service."""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, HTTPException
from pydantic import Field
from backend.finance import savings_matching as matching
from .schemas import SimulationInput
from .service import simulate

router = APIRouter(prefix='/api/financial-products', tags=['financial-products'])


class MatchingInput(matching.StrictModel):
    profile: SimulationInput
    after_profile: SimulationInput | None = None
    term_months: Annotated[int, Field(strict=True, ge=1, le=120)]


def today():
    return datetime.now(timezone(timedelta(hours=9))).date()


@router.post('/match')
def match_products(data: MatchingInput):
    try:
        catalog = matching.load_matching_catalog()
    except matching.MatchingCatalogError:
        raise HTTPException(503, detail='공식 적금 자료를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.') from None
    as_of = today()
    baseline = simulate(data.profile)
    current = matching.match_savings(catalog, baseline.cashflow['savable_amount'], data.term_months, as_of)
    after = None
    changes = None
    if data.after_profile is not None:
        after_simulation = simulate(data.after_profile)
        after = matching.match_savings(catalog, after_simulation.cashflow['savable_amount'], data.term_months, as_of)
        before_ids = {r['product']['product_id'] for r in current['matches']}
        after_ids = {r['product']['product_id'] for r in after['matches']}
        changes = dict(added=sorted(after_ids-before_ids), removed=sorted(before_ids-after_ids),
                       retained=sorted(before_ids & after_ids))
    return dict(dataset_version=catalog.dataset_version, evaluated_on=as_of.isoformat(),
                review_after_days=matching.REVIEW_AFTER_DAYS, current=current, after=after, changes=changes,
                actual_product_calculation_count=0, ranking=None, external_transmission=False,
                disclaimer='공식 확인 자료 중 월 저축액과 기간이 맞는 상품입니다. 가입 자격·우대금리·향후 금리를 보장하지 않으며 실제 만기금액은 계산하지 않습니다. 실시간 조회가 아닌 확인일 기준 자료입니다.')

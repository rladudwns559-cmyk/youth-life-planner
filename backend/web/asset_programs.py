"""Public discovery and request-scoped recommendations. No raw user logging."""
from datetime import datetime,timedelta,timezone
from typing import Annotated
from fastapi import APIRouter,HTTPException
from pydantic import Field
from backend.opportunities.catalog import Strict,load_catalog,CatalogError
from backend.opportunities.matching import Supplement,discover
from .schemas import SimulationInput
from .service import simulate
from backend.asset_alerts.catalog_view import current_catalog,live_response

router=APIRouter(prefix='/api/asset-programs',tags=['official-asset-programs'])
def now():return datetime.now(timezone(timedelta(hours=9)))

class DiscoveryInput(Strict):
    profile:SimulationInput
    after_profile:SimulationInput|None=None
    supplement:Supplement=Supplement()
    goal_months:Annotated[int,Field(strict=True,ge=1,le=120)]|None=None

def catalog():
    try:return current_catalog(load_catalog())
    except CatalogError:raise HTTPException(503,detail='공식 지원사업 자료를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.') from None

@router.get('')
def list_programs():return live_response(discover(catalog(),now()))

@router.post('/recommendations')
def recommend_programs(data:DiscoveryInput):
    snapshot=catalog();as_of=now()
    def run(profile,extra):
        budget=simulate(profile).cashflow['savable_amount']
        return live_response(discover(snapshot,as_of,profile,extra,budget,data.goal_months))
    try:
        result=run(data.profile,data.supplement)
        extra=data.supplement
        if data.after_profile is not None and data.after_profile.region!=data.profile.region:
            extra=extra.model_copy(update={'province':None})
        result['after']=run(data.after_profile,extra) if data.after_profile is not None else None
        return result
    except ValueError:raise HTTPException(422,detail='추가 입력의 날짜와 범위를 확인해 주세요.') from None

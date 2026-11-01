"""Optional Python HTTP adapter; public static discovery does not require it."""
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from backend.finance.discovery import load_catalog,search

router=APIRouter(prefix='/api/product-discovery',tags=['product-discovery'])
class DiscoveryInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    monthly_amount:int|None=Field(default=None,ge=0,le=1_000_000_000_000)
    term_months:int=Field(ge=1,le=120)
    lump_sum:int|None=Field(default=None,ge=0,le=1_000_000_000_000)
    @model_validator(mode='after')
    def amount_required(self):
        if self.monthly_amount is None and self.lump_sum is None:raise ValueError('AMOUNT_REQUIRED')
        return self

@router.post('/search')
def discover(data:DiscoveryInput):
    try:
        catalog=load_catalog()
        result=search(catalog,data.monthly_amount,data.term_months,data.lump_sum,datetime.now(timezone(timedelta(hours=9))).date())
    except (ValueError,OSError):raise HTTPException(503,detail='공식 자료를 다시 확인해 주세요.') from None
    return dict(dataset_version=catalog.dataset_version,**result)

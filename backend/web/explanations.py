from typing import Literal
from fastapi import APIRouter,Depends
from backend.explanation.provider import get_provider
from backend.explanation.service import explain
from backend.explanation.contracts import ExplanationResponse
from .comparison_schemas import ComparisonInput

router=APIRouter()

class ExplanationRequest(ComparisonInput):
    mode:Literal['deterministic','ai_if_available']='ai_if_available'

@router.post('/api/synthetic/explain',response_model=ExplanationResponse)
async def explanation(data:ExplanationRequest,provider=Depends(get_provider)):
    # 클라이언트가 보낸 금액/정책 판정 결과는 받지 않는다. 기존 strict 프로필2개를 재실행.
    return await explain(data,provider=provider,mode=data.mode)

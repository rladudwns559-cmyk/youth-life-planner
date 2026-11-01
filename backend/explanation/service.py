import asyncio,json,re,unicodedata
from pydantic import ValidationError
from backend.web.comparison import DISCLAIMER,compare_scenarios
from backend.web.comparison_schemas import ComparisonInput
from .contracts import ExplanationDocument,ExplanationResponse
from .facts import build_facts,deterministic_document,render_document
from .provider import NoProvider,ProviderUnavailable,ProviderResponseTooLong,ProviderInvalidResponse,MAX_PROVIDER_BYTES

TIMEOUT_SECONDS=8

class OutputRejected(Exception):
    def __init__(self,code):self.code=code

def _no_duplicate(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('DUPLICATE_KEY')
        out[k]=v
    return out

def _canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def validate_output(raw,expected:ExplanationDocument) -> ExplanationDocument:
    if type(raw) is not str:raise OutputRejected('INVALID_JSON')
    if len(raw.encode('utf-8'))>MAX_PROVIDER_BYTES:raise OutputRejected('RESPONSE_TOO_LONG')
    try:
        obj=json.loads(raw,object_pairs_hook=_no_duplicate,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
        candidate=ExplanationDocument.model_validate(obj)
    except (ValueError,TypeError,ValidationError):raise OutputRejected('INVALID_JSON') from None
    b=expected.model_dump();a=candidate.model_dump()
    for field,code in [('changed_facts','NUMBER_MISMATCH'),('unknown_information','UNKNOWN_MISSING'),('next_actions','UNSUPPORTED_ACTION')]:
        if _canonical(a[field])!=_canonical(b[field]):raise OutputRejected(code)
    if len(a['policy_explanations'])!=len(b['policy_explanations']):raise OutputRejected('POLICY_STATE_MISMATCH')
    for x,y in zip(a['policy_explanations'],b['policy_explanations'],strict=True):
        x.pop('text');y.pop('text')
        if _canonical(x)!=_canonical(y):raise OutputRejected('POLICY_STATE_MISMATCH')
    for text in [candidate.summary]+[p.text for p in candidate.policy_explanations]:
        normalized=unicodedata.normalize('NFKC',text)
        if not re.search('[가-힣]',normalized) or re.search(r'[A-Za-z\d]|신청|수급|가입|승인|보장|확정|추천|기한|마감|지원금|충족|가능성|대상자|원|퍼센트|프로',normalized):
            raise OutputRejected('UNSUPPORTED_NARRATIVE')
        if '<' in normalized or '>' in normalized or 'http' in normalized:raise OutputRejected('UNSUPPORTED_NARRATIVE')
    # 모델의 핵심 사실을 반환하지 않는다. 대조 후에도 서버의 확정 값에 자연어 두 영역만 복사.
    return expected.model_copy(update={'summary':candidate.summary,'policy_explanations':[
        p.model_copy(update={'text':candidate.policy_explanations[i].text}) for i,p in enumerate(expected.policy_explanations)]})

async def explain(data:ComparisonInput,*,provider=None,mode='ai_if_available') -> ExplanationResponse:
    comparison=compare_scenarios(data)
    facts=build_facts(comparison)
    document=deterministic_document(comparison,facts)
    provider=provider if provider is not None else NoProvider()
    attempted=executed=success=validated=False
    reason=None;source='deterministic'
    if mode!='deterministic':
        source='deterministic_fallback'
        reason='PROVIDER_NOT_CONFIGURED'
        if provider.configured:
            attempted=True
            # Separate deep copies: a provider cannot mutate the canonical fallback or facts.
            payload={'facts':facts.model_dump(),'template':document.model_dump(),'schema':ExplanationDocument.model_json_schema()}
            try:
                raw=await asyncio.wait_for(provider.generate(payload),timeout=TIMEOUT_SECONDS)
                executed=bool(provider.real_model)
                document=validate_output(raw,document)
                validated=True;success=executed;reason=None
                source='llm' if success else 'validated_test_double'
            except (asyncio.TimeoutError,TimeoutError):reason='TIMEOUT'
            except ProviderResponseTooLong:reason='RESPONSE_TOO_LONG'
            except ProviderInvalidResponse:reason='INVALID_JSON'
            except (ProviderUnavailable,ConnectionError,OSError):reason='PROVIDER_UNAVAILABLE'
            except OutputRejected as exc:reason=exc.code
            except Exception:reason='GENERATION_FAILED' # 예외 메시지·입력·키·모델 원문을 로그/응답에 넣지 않음
    return ExplanationResponse(explanation_text=render_document(document,facts),document=document,facts=facts,
        explanation_source=source,related_policy_ids=[p.policy_id for p in facts.policy_facts],
        unknown_information=facts.unknown_information,fallback=source=='deterministic_fallback',fallback_reason=reason,
        ai_attempted=attempted,ai_executed=executed,ai_success=success,validation_passed=validated,
        provider_kind=provider.kind,disclaimer=DISCLAIMER)

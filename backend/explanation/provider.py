"""명시적으로 설정한 로컬 Ollama만 지원. 설치/다운로드/외부 API/키 탐색 없음."""
import asyncio,copy,json,os,re
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from .prompt import SYSTEM_PROMPT

MAX_PROVIDER_BYTES=32768

class ProviderUnavailable(Exception):pass
class ProviderResponseTooLong(Exception):pass
class ProviderInvalidResponse(Exception):pass

class NoProvider:
    kind='none'
    real_model=False
    configured=False

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ProviderUnavailable('REDIRECT_NOT_ALLOWED')

def _source_rules(payload):
    # 계약에 정의된 출처 배열만 변환한다. 다른 필드나 자연어를 보정하지 않는다.
    for section,key in [('facts','policy_facts'),('template','policy_explanations')]:
        for policy in payload.get(section,{}).get(key,[]):
            yield from policy.get('rules',[])

def _wire_payload(payload):
    wire=copy.deepcopy(payload)
    refs=sorted({ref for rule in _source_rules(wire) for ref in rule.get('source_refs',[])})
    aliases={ref:f'SOURCE-{i:03d}' for i,ref in enumerate(refs,1)}
    for rule in _source_rules(wire):
        if 'source_refs' in rule:rule['source_refs']=[aliases[ref] for ref in rule['source_refs']]
    return wire,{alias:ref for ref,alias in aliases.items()}

def _restore_sources(raw,reverse):
    if not reverse or len(raw.encode('utf-8'))>MAX_PROVIDER_BYTES:return raw
    def unique(pairs):
        obj={}
        for key,value in pairs:
            if key in obj:raise ValueError('DUPLICATE_KEY')
            obj[key]=value
        return obj
    def invalid(_):raise ValueError('NON_FINITE_JSON')
    try:obj=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
    except (ValueError,TypeError,RecursionError):return raw
    if type(obj) is not dict or type(obj.get('policy_explanations')) is not list:return raw
    for policy in obj['policy_explanations']:
        if type(policy) is not dict or type(policy.get('rules')) is not list:continue
        for rule in policy['rules']:
            if type(rule) is not dict or type(rule.get('source_refs')) is not list:continue
            rule['source_refs']=[reverse.get(ref,ref) if type(ref) is str else ref for ref in rule['source_refs']]
    # 미지 ID·순서·타입·다른 필드는 그대로 남겨 기존 validator가 거부하게 한다.
    return json.dumps(obj,ensure_ascii=False,allow_nan=False)

class OllamaLocalProvider:
    kind='ollama_local'
    real_model=True
    configured=True
    ENDPOINT='http://127.0.0.1:11434/api/generate'

    def __init__(self,model:str):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}',model) or 'cloud' in model.lower() or '://' in model:
            raise ValueError('LOCAL_MODEL_TAG_REQUIRED')
        self.model=model

    def _request(self,payload):
        wire,reverse=_wire_payload(payload)
        # 프록시 자동 사용과 리다이렉트를 막고 고정된 루프백 주소만 사용한다.
        opener=build_opener(ProxyHandler({}),_NoRedirect())
        body=json.dumps(dict(model=self.model,system=SYSTEM_PROMPT,prompt=json.dumps(wire,ensure_ascii=False),
            format=payload['schema'],stream=False,options={'temperature':0,'num_predict':4096}),ensure_ascii=False).encode('utf-8')
        request=Request(self.ENDPOINT,data=body,headers={'Content-Type':'application/json'},method='POST')
        with opener.open(request,timeout=6) as response:
            raw=response.read(MAX_PROVIDER_BYTES+1)
        if len(raw)>MAX_PROVIDER_BYTES:raise ProviderResponseTooLong()
        try:outer=json.loads(raw)
        except (ValueError,TypeError):raise ProviderInvalidResponse() from None
        if type(outer) is not dict or outer.get('done') is not True or type(outer.get('response')) is not str:raise ProviderInvalidResponse()
        return _restore_sources(outer['response'],reverse)

    async def generate(self,payload):
        return await asyncio.to_thread(self._request,payload)

def get_provider():
    # 외부 제공업체/ChatGPT 구독을 API 권한으로 간주하지 않는다. 기본값은 항상 미설정.
    if os.environ.get('AIX_EXPLANATION_PROVIDER')!='ollama_local':return NoProvider()
    model=os.environ.get('AIX_OLLAMA_MODEL','')
    contract=os.environ.get('AIX_EXPLANATION_CONTRACT','')
    if contract not in ('','narrative_v1','narrative_catalog_v2'):return NoProvider()
    try:
        if contract=='narrative_catalog_v2':
            from .catalog_provider import OllamaCatalogProvider
            return OllamaCatalogProvider(model)
        if contract=='narrative_v1':
            from .narrative_provider import OllamaNarrativeProvider
            return OllamaNarrativeProvider(model)
        return OllamaLocalProvider(model)
    except ValueError:return NoProvider()


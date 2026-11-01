"""고정 로컬 /api/chat → M3.8A 검사·조립. 실제 생성은 요청당 한 번뿐이다."""
import asyncio
import json
from urllib.request import Request, build_opener, ProxyHandler

from .contracts import ExplanationFacts, ExplanationDocument
from .narrative_contract import (
    NarrativeContractError, prepare_narrative, output_schema, parse_narrative, assemble_narrative,
)
from .narrative_prompt import NARRATIVE_SYSTEM_PROMPT_V1
from .provider import (
    OllamaLocalProvider, _NoRedirect, MAX_PROVIDER_BYTES,
    ProviderInvalidResponse, ProviderResponseTooLong,
)

MAX_REQUEST_BYTES = 8192
_METRICS = {'total_duration', 'load_duration', 'prompt_eval_count', 'prompt_eval_cached_count',
            'prompt_eval_duration', 'eval_count', 'eval_duration'}
_OUTER_FIELDS = {'model', 'created_at', 'message', 'done', 'done_reason', 'remote_host', 'remote_model'} | _METRICS


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('DUPLICATE_KEY')
        obj[key] = value
    return obj


def _invalid_constant(_):
    raise ValueError('NONFINITE_JSON')


class OllamaNarrativeProvider(OllamaLocalProvider):
    ENDPOINT = 'http://127.0.0.1:11434/api/chat'

    def _build_request(self, prepared):
        obj = dict(model=self.model, messages=[
            dict(role='system', content=NARRATIVE_SYSTEM_PROMPT_V1),
            dict(role='user', content=prepared.projection.model_input_json)],
            format=output_schema(prepared), stream=False, truncate=False, shift=False,
            options=dict(temperature=0, num_predict=256, num_ctx=16384))
        body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        if len(body) > MAX_REQUEST_BYTES:
            raise ProviderResponseTooLong()
        return body

    def _post(self, body):
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        request = Request(self.ENDPOINT, data=body, headers={'Content-Type': 'application/json'}, method='POST')
        with opener.open(request, timeout=6) as response:
            raw = response.read(MAX_PROVIDER_BYTES + 1)
        if len(raw) > MAX_PROVIDER_BYTES:
            raise ProviderResponseTooLong()
        return raw

    def _decode_envelope(self, raw):
        try:
            obj = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique, parse_constant=_invalid_constant)
        except (UnicodeError, ValueError, RecursionError):
            raise ProviderInvalidResponse() from None
        if (type(obj) is not dict or not set(obj) <= _OUTER_FIELDS or obj.get('model') != self.model
                or obj.get('done') is not True or obj.get('done_reason') != 'stop'):
            raise ProviderInvalidResponse()
        for name in ('remote_host', 'remote_model'):
            if name in obj and (type(obj[name]) is not str or obj[name] != ''):
                raise ProviderInvalidResponse()
        if 'created_at' in obj and type(obj['created_at']) is not str:
            raise ProviderInvalidResponse()
        for name in _METRICS & set(obj):
            if type(obj[name]) is not int or obj[name] < 0:
                raise ProviderInvalidResponse()
        message = obj.get('message')
        if (type(message) is not dict or not set(message) <= {'role', 'content', 'thinking', 'tool_calls', 'images'}
                or message.get('role') != 'assistant' or type(message.get('content')) is not str):
            raise ProviderInvalidResponse()
        if 'thinking' in message and (type(message['thinking']) is not str or message['thinking'] != ''):
            raise ProviderInvalidResponse()
        for name in ('tool_calls', 'images'):
            if name in message and (type(message[name]) is not list or message[name]):
                raise ProviderInvalidResponse()
        return message['content']

    async def generate(self, payload):
        if type(payload) is not dict or set(payload) != {'facts', 'template', 'schema'}:
            raise ProviderInvalidResponse()
        # payload는 기존 service가 서버에서 만든 값이다. legacy schema/template 전체를 모델에 보내지 않는다.
        facts = ExplanationFacts.model_validate(payload['facts'])
        expected = ExplanationDocument.model_validate(payload['template'])
        try:
            prepared = prepare_narrative(facts, expected)
            raw = await asyncio.to_thread(self._post, self._build_request(prepared))
            content = self._decode_envelope(raw)
            checked = parse_narrative(content, prepared)
            return assemble_narrative(prepared, checked).model_dump_json()
        except NarrativeContractError as exc:
            if exc.reason == 'RESPONSE_TOO_LONG':
                raise ProviderResponseTooLong() from None
            if exc.reason == 'INVALID_JSON':
                raise ProviderInvalidResponse() from None
            # 지연 import: 기존 service/provider 초기화의 순환 참조를 만들지 않는다.
            from .service import OutputRejected
            raise OutputRejected(exc.reason) from None

"""기존 로컬 전송 + M3.8D 후보 코어. 생성1회/전체 정형 대체 계약."""
import asyncio
import json

from .contracts import ExplanationFacts, ExplanationDocument
from .catalog_prompt import CATALOG_SYSTEM_PROMPT_V2
from .narrative_catalog import prepare_catalog, catalog_output_schema, parse_catalog, assemble_catalog
from .narrative_contract import NarrativeContractError
from .narrative_provider import OllamaNarrativeProvider, MAX_REQUEST_BYTES
from .provider import ProviderInvalidResponse, ProviderResponseTooLong


class OllamaCatalogProvider(OllamaNarrativeProvider):
    def _build_request(self, prepared):
        obj = dict(model=self.model, messages=[
            dict(role='system', content=CATALOG_SYSTEM_PROMPT_V2),
            dict(role='user', content=prepared.model_input_json)],
            format=catalog_output_schema(prepared), stream=False, truncate=False, shift=False,
            options=dict(temperature=0, num_predict=256, num_ctx=16384))
        body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        if len(body) > MAX_REQUEST_BYTES:
            raise ProviderResponseTooLong()
        return body

    async def generate(self, payload):
        if type(payload) is not dict or set(payload) != {'facts', 'template', 'schema'}:
            raise ProviderInvalidResponse()
        facts = ExplanationFacts.model_validate(payload['facts'])
        expected = ExplanationDocument.model_validate(payload['template'])
        try:
            # 요청별 불변 후보/원본은 이 호출에만 보관한다. 공유 상태/자동 재시도 없음.
            prepared = prepare_catalog(facts, expected)
            raw = await asyncio.to_thread(self._post, self._build_request(prepared))
            content = self._decode_envelope(raw)
            checked = parse_catalog(content, prepared)
            return assemble_catalog(prepared, checked).model_dump_json()
        except NarrativeContractError as exc:
            if exc.reason == 'RESPONSE_TOO_LONG':
                raise ProviderResponseTooLong() from None
            if exc.reason == 'INVALID_JSON':
                raise ProviderInvalidResponse() from None
            from .service import OutputRejected
            raise OutputRejected(exc.reason) from None

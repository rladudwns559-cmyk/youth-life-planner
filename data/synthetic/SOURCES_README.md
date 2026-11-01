# 합성 Source Registry fixture

`sources.json`은 **synthetic=True / test_only=True 용도의 테스트 자료**다. 실제 정책·기관·공고·공식 URL이 아니다. SYNTH-* ID, 명시적인 합성 제목·기관명, example.invalid URL만 사용한다.

현재 `source-registry-1.0` top-level 계약은 `schema_version`과 `sources`뿐이다. synthetic/test_only JSON 필드는 확정된 계약에 없으므로 새 필드를 추가하지 않았다. 이 파일의 용도는 이 설명과 각 source의 합성 metadata로 명시한다. 이 표시는 실제 데이터 수용 gate를 대신하지 않으며 loader가 공식 출처나 production 승인을 검증한다는 뜻도 아니다.

SYNTH-SOURCE-001은 locator 2개, SYNTH-SOURCE-002는 DRAFT locator 1개다. source_type enum은 문법 검증용이며 실제 공식 문서라는 주장이 아니다. 오래된 verified_at도 freshness 판정 없이 보존한다. 기존 합성 정책 JSON에는 연결하지 않는다.

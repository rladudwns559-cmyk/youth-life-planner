# M3.8F-R1 오프라인 증거

현재 자료의 최종본은 final_offline_diagnosis.json이다. offline_diagnosis.json은 첫 탐색 실행이다. 초기 native_log.source_sha256 필드는 줄바꿈을 정규화한 텍스트 해시였으므로 최종본에서 normalized_text_sha256으로 명칭을 바로잡았다. 실제 원본 파일 byte SHA256은 source_files와 native_log_excerpts.json의 source.sha256에 따로 있다. 원본 로그와 이전 실제 실행 결과를 수정하지 않았다.

environment.json은 읽기 전용 환경 조회다. native_log_excerpts.json은 기존 로그의 원래 줄번호/발췌이며 새로운 실행 로그가 아니다. source_inventory.json은 기존 자료의 hash/size/mtime 기준이다. final_offline_diagnosis의 후보16조합 검증은 합성이고 공식 모델 응답/평가 성과가 아니다.

공식 구현 근거(확인2026-10-26):

- [동일 버전 scheduler의 생략 shift 처리](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L159-L177)
- [동일 버전 runner 재로딩 비교](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L1358-L1364)
- [빈 Chat 요청의 로드 응답](https://github.com/ollama/ollama/blob/v0.40.11/server/routes.go#L3008-L3027)
- [공식 Chat metrics 안내](https://docs.ollama.com/api/chat)

MINIMAL_FIX_AND_RETEST_PLAN.md는 미구현·미실행 승인안이다. 모델을 실행하는 CLI는 이번에 추가하지 않았다. 신규 도구 tools/diagnose_t08.py는 파일을 읽고 기존 순수 코어로 측정할 뿐 서버를 시작하거나 POST하지 않는다. 기존 파일 또는 기존 출력 경로 덮어쓰기를 거부한다.

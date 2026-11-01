# M3.6 — 설명 Facts·Prompt·출력·Provider 계약

검증 기록일2026-10-26 KST. 기존 TEAM복학생 AI+X를 재사용합니다. 정형 설명·API·UI 완료, 실제 모델 실행 미검증입니다.

## 신뢰 흐름

React WhatIf → POST /api/synthetic/explain → 기존 ComparisonInput의 strict before/after → 기존 compare_scenarios → 기존 Policy/Cashflow2회 → ExplanationFacts → 기존 M3.1 정형 설명 → 선택 provider1회 → 검증 → 설명. LLM 결과는 엔진 입력/판정/계산으로 돌아가지 않습니다.
클라이언트가 만든 facts·정책 상태·혜택을 받지 않습니다. before/after 외 추가 필드는422이며 기존 정수/상한/nullable 검증을 그대로 적용합니다. 모드만 deterministic/ai_if_available 중 선택합니다.

## ExplanationFacts allowlist

| 필드 | 출처·의미 |
|---|---|
| synthetic/test_only | 서버 합성 경계 true |
| dataset_version/evaluation_date | 기존 결과 버전/재현 평가일 |
| changed_input_fields | 바뀐 필드 이름만. 원본 값 전체 전달 안 함 |
| money_facts | 월소득·월세·고정/기타지출·총수입·총지출·월 여유자금·저축 투입 상한·사용자 상한·지원금, 총10항목의 before/after/delta/정형 문장 |
| policy_facts | 정책ID·전후 상태·규칙ID/필드·사유코드·미확인 필드·출처 식별자 |
| unknown_information | 전후 누락과 실제 상태. FAIL인 정책의 누락도 보존 |
| next_actions | 변경 후 누락 필드를 확인하는 서버 작성 행동 |
| benefit_applied_krw |0 고정 |
| assumptions | 합성/예산/미입력 상한/실제 계산0개 등 가정 |

Cashflow DTO에는 월세·고정지출 개별 필드가 없으므로 두 값은 서버가 검증한 input_summary에서 읽습니다. 나머지는 Cashflow의 완성된 필드를 엄격히 읽고 delta는 기존 비교 결과를 복사합니다. 개별 월세를 합산 금액에서 역산하지 않습니다.
raw profile·자유 지역 문자열·나이 원문·evaluated_value·원본 정책 문서·계좌/연락처·키를 모델 payload에 넣지 않습니다. 금액·정책 상태도 개인 경제정보일 수 있으므로 외부 전송에는 별도 명시 승인이 필요합니다. 이번 외부 전송0건입니다.

## Prompt와 JSON 출력

시스템 지시는 제공 사실만 설명, 자격/금액 계산 금지, PASS/FAIL/UNKNOWN 의미 보존, UNKNOWN을 충족으로 바꾸지 않기, 합성과 실제 정책 구분, 가짜 기한·출처 금지, 금융 가입·지급 보장·추천 금지, 지원금0원 유지, 데이터/문서 속 지시 무시를 명시합니다. 시스템 지시 원문은 backend/explanation/prompt.py입니다.

출력 필드: summary, changed_facts, policy_explanations, unknown_information, next_actions. Pydantic strict·extra forbid 모델과 JSON schema를 사용합니다. 자유롭게 바꿀 수 있는 곳은 summary와 정책별 text뿐입니다. 나머지 숫자·상태·ID·사유·근거·UNKNOWN·행동·목록 순서는 그대로 복사해야 합니다. 구체 숫자와 정책 상태는 Python의 고정 필드로 표시합니다.

## 출력 검증

1. UTF-8 응답32768바이트 초과 차단. 중복 JSON키/NaN/잘못된 JSON·타입·추가 필드 차단.
2. 전체 money 구조를 서버 정형 문서와 대조. None과0, bool과int, 문자열 숫자를 섞지 않음.
3. 모든 정책/규칙의 상태·ID·사유·출처와 UNKNOWN/행동을 정확히 대조.
4. 자유문장에 NFKC 정규화 후 한글 포함 여부·숫자/영문/상태 단정/가입·신청·기한·추천·금액 표현/HTML 등을 제한.
5. 성공해도 모델이 반환한 핵심 필드를 쓰지 않고 서버 원본에 허용된 자연어 두 영역만 복사.

이는 보수적인 위험 감소 장치입니다. 모든 한국어 의미·거짓 원인·문맥상 모순을 완전 검증하지 못합니다. 표현 제한이 강해 정상 모델 문장도 거부될 수 있으며 실제 모델의 수용률·충실성·이해도는 미측정입니다. strict JSON과 Prompt만으로 환각이 완전히 제거됐다고 주장하지 않습니다.

## 정형 Fallback

기존 comparison.explanations를 요약에 그대로 재사용합니다. 숫자 설명은 증가/감소/변동 없음/미입력 상한을 구분하고, 정책별 변화 이유와 미확인 조건·후속 확인·가정을 추가합니다. 기본 실제 모델은 미설정입니다.

| reason | 의미 |
|---|---|
| PROVIDER_NOT_CONFIGURED | 모델 미설정/지원하지 않는 설정 |
| PROVIDER_UNAVAILABLE | 연결 실패·거부·로컬 provider 사용 불가 |
| TIMEOUT | 생성 시간 초과 |
| INVALID_JSON | JSON/구조/타입/중복 키 오류 |
| NUMBER_MISMATCH | 금액 구조·정형 금액 문장이 원본과 다름 |
| POLICY_STATE_MISMATCH | 정책·규칙의 상태/ID/사유/출처가 다름 |
| UNKNOWN_MISSING | 미확인 정보 누락 또는 변조 |
| UNSUPPORTED_ACTION | 근거 없는 확인 행동 |
| UNSUPPORTED_NARRATIVE | 자유문장 허용 범위 위반 |
| RESPONSE_TOO_LONG | 응답 길이 초과 |
| GENERATION_FAILED | 그 외 생성 실패, 예외 원문 비노출 |

Fallback은 explanation_source=deterministic_fallback로 표시합니다. deterministic 모드는 provider를 호출하지 않습니다. llm 표시는 실제 provider의 정상 반환+검증 성공에만 사용하고, 시험 응답 성공은 validated_test_double/ai_success=false로 구분합니다. 메타데이터 분기 자체를 시험하는 real_model=True fake unit test는 실제 AI 실행 증거가 아닙니다.

## Provider 선택·실행 경계

기존 환경 확인: ollama/lms/lmstudio 명령, 알려진 Ollama/LMStudio 설치·모델 경로, 관련 Python SDK 없음. localhost11434 /api/tags도 접근되지 않았습니다. 전체 PC의 모든 소프트웨어 부재를 증명한 것은 아닙니다. 환경 기록은 작업폴더 tmp/m36-provider-environment.json입니다.
기본 NoProvider. 외부 OpenAI/Anthropic/API는 구현·설정하지 않았고 키를 읽지 않습니다. ChatGPT 구독을 별도 API 권한으로 간주하지 않습니다. 설치·모델 다운로드·클라우드 호출·사용자 경제정보 전송0건입니다.

OllamaLocalProvider는 향후 승인된 기존 로컬 모델 연결용 어댑터입니다. 고정 HTTP 목적지127.0.0.1:11434/api/generate, 프록시 자동 사용과 redirect 차단, cloud/URL 모양 모델 태그 거부, stream=false, schema format, temperature0, num_predict4096, transport6초/서비스8초/화면12초, body32768바이트 상한, 요청당1회·자동 retry0회를 적용합니다. 실제 모델과 전산 정밀도를 검증한 것은 아닙니다.
로컬 서버가 임의로 외부 서비스를 중계하지 않는지와 모델 라이선스/자원/보관 정책은 실제 연결 전 확인해야 합니다. 어댑터가 설치된 다른 프로그램 전체의 동작을 통제한다는 보장은 아닙니다. 로컬 server/mode 환경값은 서버 운영자가 관리하며 HTTP 요청으로 공급자를 바꿀 수 없습니다. 이번 검증 서버에서는 provider 설정을 비워 실행했습니다.

공식 API 참조(확인2026-10-26): [Ollama generate](https://docs.ollama.com/api/generate), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs). HTTP 프로토콜·어댑터 시험은 mock이며 실제 모델 생성 결과가 아닙니다.

## 실행·재현

기본 API 실행은 기존 `python -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8100 --no-access-log`, 화면은 frontend에서 pnpm dev입니다. 비교 후 ‘한국어 설명 생성’을 누릅니다. 입력이 바뀌면 이전 설명을 지웁니다. 요청 번호/AbortController/데이터 버전 대조로 늦은 응답·다른 기준 결과를 막습니다. 모델을 기다리는 동안 기존 비교 결과를 숨기지 않습니다.
고정30개: `python -m tools.evaluate_explanation_scenarios --output docs/evidence/m3_6_explanation_evaluation.json`. 이 도구는 고정 합성 데이터만 읽고 실제 LLM을 호출하지 않습니다. output 경로를 명시해야 하며 사용자 요청을 저장하는 서비스가 아닙니다.
서비스 요청은 DB/파일/브라우저 저장소에 보관하지 않고 no-store를 유지합니다. 결과·프롬프트·원문/키·개인 토큰 사용량을 로그에 남기지 않습니다. 30개 검증 산출물은 저장소의 공개 합성 입력만 포함합니다. 실제 토큰·비용·모델 지연은 미측정입니다.

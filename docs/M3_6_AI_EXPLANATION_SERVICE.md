# M3.6 — AI Explanation Service MVP 결과

검증 기록일:2026-10-26 KST. 최종 판단: **`M3_DETERMINISTIC_EXPLANATION_COMPLETE_LLM_PENDING`**.
정형 설명·안전한 출력 계약·로컬 provider 어댑터·FastAPI/React·회귀·실제 HTTP/브라우저를 구현·검증했습니다. **실제 LLM 실행0건**, 실제 AI30개 응답 평가 미완료이며 AI 전체 완료로 표시하지 않습니다.

## 1. 기존 기능 재사용 구조

기존 FastAPI/React, `/api/synthetic/simulate`, `/api/synthetic/compare`, ComparisonInput/Response·정책 reason DTO, 기존 Python 정형 설명, Policy/Cashflow/What-if를 조사했습니다. M3.1/M3.2/M3.3 보고·v1.2 예선 제안서·ARCHITECTURE·OBSIDIAN_WORKFLOW도 확인했습니다.
새 설명 API는 기존 프로필2개를 검증해 compare_scenarios를 재실행합니다. 기존 service.simulate→Policy/Cashflow가2회 호출되고 확정한 값만 설명에 사용합니다. 판정·예산·적금 공식을 새로 계산하지 않습니다.

## 2. 생성·수정 파일

기존 변경5개: backend/web/app.py(라우터 추가), frontend/src/WhatIf.tsx(설명 영역), frontend/src/styles.css(설명 스타일), docs/ARCHITECTURE.md(현재 경로 추가), docs/M3_5_IBK_INQUIRY_DRAFT.md(사용자 발송 보고 후속 상태).
신규18개:

- `backend/explanation/__init__.py`
- `backend/explanation/contracts.py`
- `backend/explanation/facts.py`
- `backend/explanation/prompt.py`
- `backend/explanation/provider.py`
- `backend/explanation/service.py`
- `backend/web/explanations.py`
- `data/synthetic/explanation-scenarios-v1.json`
- `docs/M3_6_AI_EXPLANATION_CONTRACT.md`
- `docs/M3_6_AI_EXPLANATION_SERVICE.md`
- `docs/evidence/m3_6_explanation_evaluation.json`
- `frontend/src/ExplanationPanel.test.tsx`
- `frontend/src/ExplanationPanel.tsx`
- `frontend/src/explanation-api.ts`
- `frontend/src/testing/explanation-fixture.json`
- `frontend/tests/explanation-live-http.mts`
- `tests/test_explanation_service.py`
- `tools/evaluate_explanation_scenarios.py`

기존278개 중 나머지273개는 SHA256/크기/mtime 불변입니다. 기존 Backend/Frontend 테스트·golden·fixture·의존성/잠금파일은 수정하지 않았습니다. 새 frontend fixture는 실제 Python의 합성 fallback 응답으로 만든 컴포넌트 시험용이며 제품에서 import하지 않습니다.

## 3. ExplanationFacts 구조

합성 여부·버전/평가일·바뀐 필드명·금액10항목의 전후/차이·정책/규칙 상태/사유/근거·전후 UNKNOWN·다음 확인·지원금0원·가정을 담습니다. 원본 지역 문자열/나이/evaluated_value/프로필 전체/연락처/계좌/정책 원문은 제외합니다. 구조·필드 출처는 M3_6_AI_EXPLANATION_CONTRACT.md에 명세했습니다.
월세·고정지출은 Cashflow DTO 개별 키가 없어 검증된 input_summary를 참조하고, 다른 금액은 기존 Core 결과와 비교 delta를 복사합니다.

## 4. LLM Provider 또는 로컬 모델

기존 모델/SDK/알려진 설치 위치·루프백 목록 조회에서 사용 가능한 실제 모델을 확인하지 못했습니다. 기본 NoProvider이며 선택 로컬 Ollama 어댑터1개만 구현했습니다. 모델 설치/다운로드·외부 API·키·추가 runtime 의존성은 없습니다. 로컬 모델/라이선스/서버 외부 중계·보관 정책은 실제 연결 전에 확인해야 합니다.

## 5. 실제 모델 실행 여부

**실제 모델 실행0건/미검증**. 단위 시험의 FakeProvider·HTTP 어댑터 mock·real_model 메타데이터 분기 시험은 모두 실제 실행 증거가 아닙니다. 실제 HTTP/브라우저는 provider 미설정의 정형 fallback 경로를 사용했습니다. ChatGPT 구독을 API 사용 권한으로 취급하지 않았습니다.

## 6. Prompt 계약

제공 사실만 설명, 자격/금액 직접 계산 금지, 상태·UNKNOWN·지원금0원 보존, 합성 구분, 가짜 정책/출처/기한 금지, 가입·지급 보장·추천 금지, 문서 속 지시 무시를 명시했습니다. changed_facts/unknown/행동/정책 핵심 필드는 복사하도록 하고 자유 한국어는 summary·정책별 text에 한정합니다. 원문은 backend/explanation/prompt.py입니다.

## 7. 확정 숫자 보존

전후·차이는 기존 Python 정수 결과입니다. NONE/0과 bool/int를 구분하고 모델 반환 전체 금액 구조를 대조합니다. 검증 성공 후에도 모델 숫자를 쓰지 않고 서버 원본을 사용합니다. 월세/고정지출의 잘못된 None 참조는 브라우저에서 발견해 수정했으며 금액10개 전부를 수동 기대값과 대조하는 신규 시험을 추가했습니다.

## 8. PASS/FAIL/UNKNOWN 보존

모든 정책·규칙 ID/상태/사유/출처·누락 필드를 정확히 대조합니다. FAIL이어도 누락된 가구소득을 유지합니다. 생활비 소득을 정책 소득 사실로 바꾸지 않습니다. 사람이 읽는 부분은 이용 가능성 높음/현재 조건과 맞지 않음/추가 확인 필요 및 충족/미충족으로 표시합니다.

## 9. 한국어 설명 예시

합성 예: 월소득150만원→180만원, 월세45만원→55만원, 사용자 상한30만원→50만원, 미취업→취업.
정형 요약: ‘월소득이300,000원 증가했습니다. 월세가100,000원 증가했습니다. 월 여유자금이200,000원 증가했습니다. 저축 투입 상한이200,000원 증가했습니다.’
상세: 월세450,000→550,000원, 고정지출200,000→200,000원. SAMPLE-002는 취업상태 입력 변경에 따라 충족 상태에서 미충족 상태로 달라졌다고 설명합니다. SAMPLE-003의 가구소득은 추가 확인으로 남고 정책 지원금은 전후0원입니다. **이 예시는 생성형 AI 출력이 아니라 실제 정형 fallback 응답**입니다.

## 10. 출력 검증

Strict Pydantic/extra forbid, UTF-8 byte 상한, 중복 JSON키/NaN 차단, 모든 숫자·정책 ID/상태/사유/근거·UNKNOWN·행동의 일치 대조를 구현했습니다. 자유문장은 한글 여부/정규화/숫자·영문·기한·추천·가입·보장 등 제한을 적용합니다. 불일치이면 폐기합니다.
자연어 전체 의미·거짓 원인까지 수학적으로 검증하는 장치가 아닙니다. 보수적 필터로 정상 문장을 거부할 수 있으며 실제 모델 충실성·수용률·이해도는 아직 미측정입니다.

## 11. Fallback 동작

기존 M3.1 explanations를 그대로 재사용합니다. 미설정·연결 불가·timeout·JSON 오류·금액 불일치·정책 불일치·UNKNOWN 누락·길이 초과·지원하지 않는 행동/표현·생성 실패를 구분하고 `deterministic_fallback`으로 반환합니다. 기존 계산 결과는 유지합니다. deterministic 명시 모드에서는 모델을 호출하지 않습니다. 요청당 provider1회/자동 재시도0회입니다.

## 12. FastAPI endpoint

`POST /api/synthetic/explain`. 입력: strict `before`, `after`, 선택 `mode=ai_if_available|deterministic`. 사용자가 만든 결과/facts/지원금/provider 주소는 허용하지 않습니다.
응답: explanation_text/document/facts, explanation_source/fallback_reason, 관련 정책ID/UNKNOWN, fallback/ai_attempted/ai_executed/ai_success/validation_passed, provider_kind/external_transmission=false, synthetic/test_only 경고입니다. 기존 no-store/개인 입력 원문 없는422 처리와 simulate/compare를 유지했습니다.

## 13. React 설명 화면

What-if 결과 아래 ‘이 결과를 쉽게 이해하기’와 ‘한국어 설명 생성’을 추가했습니다. 수동 요청/로딩/한국어 요약/금액·정책별 이유/추가 확인/정형 대체 표시/오류·재시도가 있습니다. 비교 결과는 계속 표시됩니다. 현재 또는 After 수정/리셋/새 비교 시 이전 설명을 폐기하고 AbortController·요청 번호·데이터 버전으로 늦은 성공/실패·다른 기준 응답을 차단합니다. HTML로 실행하지 않고 텍스트로 렌더링합니다.

## 14. 실제 HTTP 검증

기존 실제 프로젝트의 FastAPI127.0.0.1:8100/Vite5173을 실행했습니다. frontend/tests/explanation-live-http.mts가 실제 requestExplanation/fetch로 예시 전후 금액10항목 중 월세/고정지출/여유자금, 정책 전이, UNKNOWN, 적자, 상한0, 변조422, no-store, provider 미설정 fallback을 확인했습니다. 기존 products/savings/comparison/live-http도 모두 통과했습니다. mock 응답이 없지만 실제 LLM 실행 시험도 아닙니다.

## 15. 실제 브라우저 검증

현재 상황 계산→After 네 변수 변경→실제 비교→설명 생성→정형 대체 표시와 금액/정책/UNKNOWN→명시 재생성→입력 수정 시 비교·설명 모두 제거를 확인했습니다. 오류를 고친 뒤 실제 서버를 재시작하고 같은 경로를 재검증했습니다.
390×844에서 clientWidth/scrollWidth가 모두375(스크롤바 포함 viewport390)이고 설명 글자16px, 수평 넘침 없음입니다. 데스크톱1280에서 client/scrollWidth1265입니다. 임시 viewport를 복구했습니다. 실물 휴대폰·모바일 Safari 시험은 미실행입니다. 상태/스크린샷은 작업폴더 output/m3.6에 있습니다. Obsidian GUI와 별도입니다.

## 16. 고정30개 시나리오 결과

정형 평가30개, 실제 LLM 평가0개, 오류 주입용 test double9개. 반환된 상태·금액·UNKNOWN 보존 불일치0건, 기대 fallback 검출을 확인했습니다. 이 수치를 ‘실제 AI30응답 검증 완료’ 또는 사용자 이해도 향상으로 발표하지 않습니다.
각 사례의 Python 확정 결과/정형 설명/시험용 출력/검출·fallback을 `docs/evidence/m3_6_explanation_evaluation.json`에 기록했습니다. actual_ai_output은 전부null입니다.

| 사례 | 범위 | 기대 설명 대체 사유 | 실제 모델 |
|---|---|---|---|
| EX01 | PASS 유지·변화 없음 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX02 | PASS에서 FAIL | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX03 | FAIL에서 PASS | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX04 | UNKNOWN 유지 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX05 | 새 UNKNOWN | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX06 | UNKNOWN 해소 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX07 | 소득 증가 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX08 | 소득 감소 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX09 | 월세 증가 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX10 | 월세 감소 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX11 | 저축 상한 증가 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX12 | 음수 Cashflow | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX13 | 나이 누락 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX14 | 지역 누락 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX15 | 재학 누락·비사용 조건 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX16 | 상한 미입력에서 0 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX17 | 상한 0에서 미입력 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX18 | 경계 나이 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX19 | FAIL이어도 가구소득 누락 보존 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX20 | 수입 지출 0 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX21 | 모델 미설정 | PROVIDER_NOT_CONFIGURED | 실제 AI 미실행 |
| EX22 | 연결 불가 | PROVIDER_UNAVAILABLE | 실제 AI 미실행 |
| EX23 | 시간 초과 | TIMEOUT | 실제 AI 미실행 |
| EX24 | 잘못된 JSON | INVALID_JSON | 실제 AI 미실행 |
| EX25 | AI 금액 조작 | NUMBER_MISMATCH | 실제 AI 미실행 |
| EX26 | AI 정책 상태 조작 | POLICY_STATE_MISMATCH | 실제 AI 미실행 |
| EX27 | AI UNKNOWN 누락 | UNKNOWN_MISSING | 실제 AI 미실행 |
| EX28 | 없는 신청기한 | UNSUPPORTED_NARRATIVE | 실제 AI 미실행 |
| EX29 | 근거 없는 추천 | UNSUPPORTED_NARRATIVE | 실제 AI 미실행 |
| EX30 | 출력 길이 초과 | RESPONSE_TOO_LONG | 실제 AI 미실행 |

## 17. 신규 Backend 테스트

**79개**. 고정30·Facts allowlist/원본 지역 지시문 배제·금액10항목 정확성·실제 기존 함수2회 호출·입력 불변·기존 정형 재사용·모든 오류 분기·실제 async timeout·provider1회·payload 변조 방어·JSON 중복키/NaN·숫자/기한/추천/HTML 차단·정책 ID/사유/근거·mock/실제 metadata 구분·미설정/모델 태그/redirect/고정 루프백·API strict입력/변조/기존경로/no-store를 검증했습니다. 실제 모델 충실성 시험은 아닙니다.

## 18. 신규 Frontend 테스트

**18개**. 자동 호출 없음·정확한 POST·대체 표시·모든 주요 금액·정책/UNKNOWN/다음 확인·로딩 시 기존 비교 유지·수동 재요청·네트워크/422/500/잘못된 응답·시간 초과·지연된 성공/실패·수정/해제 시 취소·AI/mock 표시·텍스트 렌더·데이터 버전 차이·What-if 연결을 검증했습니다. jsdom을 실제390px 레이아웃 시험으로 주장하지 않습니다.

## 19. 전체 pytest·회귀

최종 실제 ROOT: **11,679 passed /1 skipped /1 warning(66.61초)** = 기존11,600+신규79. Frontend **115 passed** = 기존97+신규18. TypeScript 검사/Vite build 성공. 실행 로그는 WORK/tmp/m36-pytest-after.txt, m36-frontend.txt, m36-build.txt, m36-http.txt입니다.
기존 skip은 실제 NTFS symlink 생성 권한 부족으로 유지, warning은 Starlette/httpx deprecation입니다. 기존 시험 기대값 변경·삭제·추가 skip 없음. 최초 기준선 실패와 수정·재실행 이력은 아래 별도 기록합니다.

## 20. GV/BV·Coverage freeze

GV01~GV15/BV01~BV16 및 기존 모든 Backend/Frontend 테스트·fixture와 Policy/Cashflow·Coverage·Acceptance/Benefit·Historical6·CrossValidator·Same-call·RawBytes 코어를 변경하지 않았습니다. 기존278개 중 승인된5개 외273개 SHA256/크기/mtime 불변을 최종 감사로 확인했습니다. m36-preservation-audit.json에 경로별 변경 범위를 기록합니다.

## 21. 실제 release6개 무변경

| 실제 파일 | 기준과 동일한 SHA256 |
|---|---|
| `data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| `data/releases/ansan-youth-2026-10-20-001/README.md` | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| `data/releases/ansan-youth-2026-10-20-001/sources.json` | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| `data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |
| `data/releases/ansan-youth-2026-10-20-002/README.md` | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| `data/releases/ansan-youth-2026-10-20-002/sources.json` | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |

## 22. 실제 상품 계산0개 유지

공식 상품 정보3개/실제 만기 계산0개/미승인 실제 지원금 반영0원 유지입니다. M3.2의 정수개월·ROUND_HALF_UP과 M3.3의 계산 보류 플래그를 바꾸지 않았습니다. 실제 정책 DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED, M2.77 SYNTHETIC_ONLY 유지입니다.

## 23. 개인정보·비용 경계

로그인·DB·입력 결과 영구 저장·외부 AI 전송·키 삽입/로그·모델 설치/다운로드가 없습니다. 요청당 기본 provider최대1회, 자동 재시도 없음, 명시 버튼에서만 호출, timeout·byte/token 생성 상한이 있습니다. 예외·프롬프트·개인 경제정보를 로그/파일에 넣지 않습니다. 고정 합성 검증 산출물과 실제 사용자 요청 저장을 구분합니다. 실제 토큰 사용량/모델 비용·지연은 미측정이며0원 유료 청구가 발생했다고 별도 검증한 것은 아닙니다. 사용한 외부 유료 API 자체가 없습니다.

## 24. Obsidian 기록

기존 Vault의 M3.6 AI 설명 서비스, 아키텍처, Prompt/출력 계약, Provider/Fallback, 고정30개, 실제 AI 실행0/미확인 항목과 대시보드/상태/테스트/다음 작업을 기록했습니다. 기존 M3.5 노트와 대시보드의 IBK 상태는 사용자 발송 완료 보고로 갱신했습니다. 링크/Properties/Bookmarks/Base/Canvas 참조를 파일로 검사하며 GUI 미확인 유지, 커뮤니티 플러그인/Sync/Publish/설정은 변경하지 않습니다. 최종 파일 검사: Markdown67개, Wikilink478개(제목11/블록1), source_paths228개, 외부 로컬 링크33개, 깨진 링크0개입니다. 기존13개 노트 갱신/신규5개, 앱설정8개 불변, 북마크13개/4그룹·Base1·Canvas1·템플릿5개 참조 유지. 실제 GUI는 미확인입니다.

## 25. IBK 문의 회신 대기 상태

**이메일 발송 완료 / 공식 회신 대기**, evidence=사용자 M3.6 지시문의 발송 완료 보고. 에이전트가 완료 화면을 확인한 것은 아닙니다. 실제 발송일/접수번호/회신일은미확인(null)이며 답변 원문0건입니다. 회신/계산 정답을 생성하거나 중복 문의를 보내지 않았습니다. 기존 미전송은 M3.5-FU 당시 이력으로 구분했습니다.

## 26. 최종 판단

**`M3_DETERMINISTIC_EXPLANATION_COMPLETE_LLM_PENDING`**. 실제 엔진 결과 기반 정형 설명·검증·API/React·고정30·회귀를 완료했습니다. 사용 가능한 승인된 모델을 확인하지 못해 실제 LLM 생성/충실성/이해도는 미검증입니다. `M3_AI_EXPLANATION_SERVICE_COMPLETE`를 선택하지 않습니다.

## 27. 다음 최소 개발 작업

**모델1개의 실행 환경·라이선스·전송/보관 조건과 비용을 확인하고 사용자 승인을 받은 뒤, 동일 Facts와 고정 시나리오로 실제 모델 생성·검증·fallback을 평가하기**를 제안합니다. 승인 없이 외부 전송·대형 다운로드를 시작하지 않습니다. 정책/금융 계산 계약 확장은 별개입니다.

## 최초 실패·수정·재실행 이력

1. 코드 수정 전 전체 검사에서 기존 bootstrap 테스트1개가 음수 timeout으로 실패(11,599통과/1실패/1skip/1warning)했습니다. 실행 시간·대기시간 이상이 포함된 환경성 실패로 의심했지만 단정하지 않았습니다. 기존 테스트/기대값 변경 없이 해당5개를 따로 재실행해 통과했고 최종 전체11,679개도 통과했습니다.
2. 제한된 실행에서 Windows asyncio 루프를 쓰는 검증 프로세스가 대기해 이번 M3.6 프로세스만 확인·중단했습니다. 로컬 통신이 허용된 실행 환경에서 재실행해 정상 종료했습니다. 외부 연결·보안 설정 변경은 없었습니다.
3. 신규 첫 시험75통과/1실패는 URL 모양 모델 태그가 거부되지 않은 것이었습니다. 새 provider검증에 URL 모양 거부를 추가했습니다. 새 시험의 빈 regex match로 생긴 경고도 시험에서 제거했고 기존 warning1개만 유지했습니다.
4. 브라우저에서 월세/고정지출을 ‘별도 상한 없음’으로 표시하는 새 Facts 오류를 발견했습니다. 기존 Cashflow의 합계 DTO에 없는 개별 키를 .get으로 읽은 문제였습니다. 두 값은 서버의 검증된 input_summary에서 읽고 나머지는 필수 Core키로 읽도록 고쳤습니다. 기존 예산 결과/금융 엔진은 정확했으며 변경하지 않았습니다. 금액10개 전체의 수동 기대값·화면/실제HTTP 검증을 추가하고 고정30·fixture·전체 회귀를 재실행했습니다.
5. 한국어 상태 문장의 조사를 ‘충족 상태에서 미충족 상태로’ 형태로 다듬고 최종 fixture/평가 기록·전체 pytest를 재확인했습니다. 잘못된 작업 디렉터리에서 fixture생성 경로1회 실패는 절대 경로 재실행으로 해결했습니다.
6. pnpm은 기존 잠금파일·오프라인 캐시만 사용해 추가167개 의존성을 검증 복사본에 연결했고 다운로드0개였습니다. 실제 의존성/잠금파일 변경 없음. 브라우저의 임시390px 폭은 최종에 복구했습니다.

## 화면 증거

![정형 대체 설명](<USER_HOME>/Documents/ChatGPT/AI+X채팅/output/m3.6/explanation-desktop.png)
![390px 수정 후 금액 설명](<USER_HOME>/Documents/ChatGPT/AI+X채팅/output/m3.6/explanation-policy-mobile-390.png)

스크린샷은 합성 값으로 실행한 실제 HTTP 화면이며 생성형 모델의 실행 결과가 아닙니다. 수정 전 오류 화면은 output/m3.6/explanation-before-fix-mobile-390.png에 별도 보존했습니다.

## 최종 감사 기록

원본 코드 보존: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m36-preservation-audit.json`. Vault 파일 검사: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m36-vault-audit.json`. 실제 브라우저: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\m3.6\browser-verification.json`. 모두 실제 모델 평가와 구분합니다. 로컬 API8100/React5173은 사용자 확인용 실행 상태로 남겼습니다.

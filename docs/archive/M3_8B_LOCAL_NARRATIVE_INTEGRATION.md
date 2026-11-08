# M3.8B — 경량 로컬 LLM 연결 및 실제 고정30 검증

확인일: **2026-10-26 KST**. **M3_LIGHTWEIGHT_LOCAL_LLM_INTEGRATED_QUALITY_REVISION_REQUIRED**.

연결·실행·실패 대체는 구현/검증했다. 고정30의 검증기 통과는25/30, 정형 대체5/30이고 **채택된 문장에도 의미 오류가 남아 서비스 기본 활성화/한국어 품질 검증 완료로 승격하지 않는다.** 기존 기본 설정과 현재 실행 API는 NoProvider 정형 설명이다. 아래 실패 이력을 숨기거나 검증기를 완화하지 않았다.

## 1. 승인 범위와 실제 변경

M3.8A 코어를 기존 로컬 Qwen 모델의 `/api/chat`에 연결했다. 신규 `narrative_provider.py`, `narrative_prompt.py`, 통신68시험, 실제 고정30 실행도구를 추가했다. 기존 provider.py는 **서버 설정 분기만** 추가했고 legacy 제공자는 그대로다. service.py/validate_output/narrative_contract.py/Facts/DTO/API/React/엔진·기존 테스트는 변경하지 않았다.

## 2. 모델·런타임·공식 설치 자산 재사용

Ollama **0.40.11**, `qwen3:4b-instruct-2507-q4_K_M` (GGUF4.0B/Q4_K_M), manifest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. 기존 M3.7 공식 자산 metadata와 설치 결과를 재사용해 기존 ZIP·config·모든 layer SHA256을 확인했다. 신규 설치/다운로드0. 외부 AI0. 하드웨어: Windows11 Home64 build26300, Ryzen7 260 8C/16T, RAM 약15.31GiB, RTX5050 Laptop8151MiB. 현재 모델 내용/해시는 증거 JSON에 있다. 설치 당시 이력은 이번 설치 실적으로 중복 계산하지 않는다.

## 3. 입력 경계

Python에서 만든 Facts와 정형 문서를 서버에 남기고 M3.8A 최소 투영만 모델에 보낸다. 바뀐 입력 항목·증감 방향·정책 상태/변경검사·누락정보·상한 미입력/영만 포함한다. 원본 금액/프로필/정책 ID/정형 문장/reason/source 경로는 보내지 않는다. 고정30 context749~959UTF8bytes. 서버의 p01~p03 순서와 요청별 prepared 객체로 원본 문서에 묶는다. 슬롯0~3 범위는 기존 계약 그대로다.

## 4. 출력·조립 경계

모델은 `summary`, `policy_texts`만 반환한다. inner JSON4KiB, summary60/정책40 Unicode code points, duplicate key/nonfinite/잘못된 UTF8/추가 필드/누락·추가 slot/제어문자/기존 금지 표현을 그대로 검사한다. 통과한 문장만 서버 원본문서 summary/text에 넣고 **기존 validator**를 다시 호출한다. 금액·상태·UNKNOWN·근거·next_actions는 서버 값이다. 불완전한 JSON을 고치거나 다시 생성하지 않는다.

## 5. 실제 통신 및 envelope

고정 `http://127.0.0.1:11434/api/chat`에 system1/user1, stream=false, format=슬롯별 JSON schema, temperature0, num_predict256, num_ctx16384, truncate=false, shift=false. history/tools/images/think 요청 없음. 모델명 일치·done=true·done_reason=stop·assistant/content, 선택적 빈 thinking/tool_calls/images만 허용한다. remote_host/model 비어있지 않음, length/미완료/알 수 없는 envelope 필드·음수/잘못된 metrics는 거부한다. ProxyHandler 비활성/redirect 거부이며 브라우저가 모델에 직접 접속하지 않는다.

## 6. 시간·크기 제한과 실패 대체

**기존6초 전송/8초 서비스/12초 UI 유지**, 요청8KiB/외부응답32KiB/문장4KiB/최대256토큰. 요청당 실제 생성1회, 자동 재시도/repair0. 타임아웃/연결실패/잘못된 응답/코어 검사 실패는 기존 전체 정형 문서로 대체한다. UI12초 경계는 기존 코드/프런트시험으로 보존했고 실제 UI에서는 6초 서버 TIMEOUT 대체를 확인했다. socket timeout과 전체 서비스 deadline은 서로 다르며 항상6초 wall-clock 이내를 보장한다고 쓰지 않는다.

## 7. opt-in 설정과 호환성

`AIX_EXPLANATION_PROVIDER=ollama_local`, `AIX_OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M`, **`AIX_EXPLANATION_CONTRACT=narrative_v1`**일 때만 새 경로다. contract 미설정은 기존 legacy 경로, provider 미설정은 NoProvider, 알 수 없는 contract는 NoProvider다. 모델/endpoint를 사용자 요청 JSON으로 받지 않는다. 이번 시험의 env는 프로세스 단위였으며 영구 설정하지 않았다. 현재 API는 정형 설정으로 복귀했고 이번에 시작한 모델 server/runner를 종료했다.

## 8. 실행 계수와 cold/warm 구분

**실제 생성 요청36회 = 별도 cold1 + 고정30 + 실제 HTTP2 + 화면3**. 고정30 batch는1회뿐이며 prompt 수정/재평가 batch0. metadata GET은 생성이 아니다. 이전 M3.7 실행과도 분리한다. cold1은6039.83ms TIMEOUT/정형 대체이고 최종 모델 원문은 수집하지 못했다. 이어진30은 전부 완료 응답을 수집했다. 이후 유휴 후 UI 첫 요청에서도 reload TIMEOUT이 발생했다. warm만 따로 좋은 결과로 전체 실적을 바꾸지 않았다.

## 9. 고정30 실제 결과

- 실제30요청/완료 모델 원문30개, 구조·표현 검증 통과25개, 전체 정형 대체5개.
- 거부: EX11(승인), EX13(불확정의 확정), EX15(충족), EX16(승인/숫자), EX17(승인). `UNSUPPORTED_NARRATIVE` / 코어 `FORBIDDEN_NARRATIVE`.
- 30개 전부 Python 확정값·정책 상태·UNKNOWN·rules/source·next_actions 불변. 이 사실은 **모델의 의미 정확도**가 아니다.
- 원문은 별도 [합성 증거 JSON](evidence/m3_8b_actual_evaluation.json)에 보관했다. 실제 사용자 데이터를 기록하는 제품 로그는 추가하지 않았다.
- EX21~30의 원래 fault label은 metadata만 남겼다. 실제 평가에서는 fake 오류를 주입하지 않았다. 이10개는 같은 입력이 반복되므로 실제 공격/오류 방어 성공10건으로 주장하지 않는다.

| 사례 | 지연ms | 최종 경로 | Codex 정성 검토 |
|---|---:|---|---|
| EX01 | 1253.92 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX02 | 1482.20 | 채택 | FACT_CONTRADICTION |
| EX03 | 1287.88 | 채택 | FACT_CONTRADICTION |
| EX04 | 1259.81 | 채택 | UNSUPPORTED_CAUSALITY |
| EX05 | 1230.94 | 채택 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED |
| EX06 | 1287.59 | 채택 | FACT_CONTRADICTION |
| EX07 | 1627.56 | 채택 | FACT_CONTRADICTION |
| EX08 | 1565.48 | 채택 | IRRELEVANT_POLICY_EXPLANATION |
| EX09 | 1281.45 | 채택 | FACT_CONTRADICTION |
| EX10 | 1358.98 | 채택 | FACT_CONTRADICTION |
| EX11 | 1203.30 | 정형 대체 | REJECTED_BEFORE_DISPLAY |
| EX12 | 1413.51 | 채택 | UNSUPPORTED_CAUSALITY |
| EX13 | 1446.70 | 정형 대체 | REJECTED_BEFORE_DISPLAY |
| EX14 | 1245.93 | 채택 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED |
| EX15 | 1307.60 | 정형 대체 | REJECTED_BEFORE_DISPLAY |
| EX16 | 1226.85 | 정형 대체 | REJECTED_BEFORE_DISPLAY |
| EX17 | 1267.12 | 정형 대체 | REJECTED_BEFORE_DISPLAY |
| EX18 | 1327.08 | 채택 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED |
| EX19 | 1605.17 | 채택 | FACT_CONTRADICTION |
| EX20 | 1230.72 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX21 | 1224.32 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX22 | 1146.51 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX23 | 1156.98 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX24 | 1188.06 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX25 | 1210.99 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX26 | 1253.04 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX27 | 1254.53 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX28 | 1217.84 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX29 | 1280.46 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |
| EX30 | 1211.88 | 채택 | AMBIGUOUS_SCOPE_LOW_UTILITY |

## 10. 지연·토큰·cache

고정30 전체(정형 대체5개 포함) 평균**1301.81ms**, 중앙값**1257.17ms**, p95 nearest-rank(29번째/30)**1605.17ms**. 채택25개 평균1304.11ms. cold TIMEOUT은 이 warm 평균에서 제외하되 별도 공개했다. 동일/반복 투영과 prompt cache 영향이 있으며 독립30개 신규 상황의 성능/일반적인 cold 성능으로 일반화하지 않는다. 회차별 prompt/eval count·cached count·완료이유·duration은 원문 envelope 그대로 저장했다.

## 11. 한국어 의미 검토와 미충족 관문

Codex가30개 원문을 Python 입력/결과와 대조했다. **사람/사용자 의미 검토0, 정확도 인증없음**. 검증기 통과25개 중 최소7개(EX02/03/06/07/09/10/19)에 입력·인과 설명의 명확한 모순을 기록했고,3개에 추가 인과/정책 관련성 우려를 기록했다. 다른 문장에도 불확실성 범위·유용성 문제가 있어 나머지를 정확도 통과로 단정하지 않는다. 특히 EX10은 월세 감소를 소득 증가로, EX07은 생활비 소득을 정책 통과 원인으로, EX02/03은 비사용 조건을 입력 불변으로 설명했다. 기존 validator의 금지어 검사는 이런 모든 의미를 판별하지 못한다.

| 사례 | 검토 분류 | 근거/한계 |
|---|---|---|
| EX01 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX02 | FACT_CONTRADICTION | 취업 입력은 미취업→취업인데 p01은 취업상태가 변하지 않았다고 설명한다. 해당 정책에 조건이 없는 것과 입력 불변을 혼동했다. |
| EX03 | FACT_CONTRADICTION | 취업 입력은 취업→미취업인데 p01은 취업상태가 변하지 않았다고 설명한다. |
| EX04 | UNSUPPORTED_CAUSALITY | 취업상태가 같기 때문에 소득 변화가 없다고 설명한다. 입력에 없는 인과관계다. |
| EX05 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED | Codex 검토에서 추가 확정 오류를 기록하지 않았다. 사람 검토/사용자 이해도/의미 정확성 인증이 아니다. |
| EX06 | FACT_CONTRADICTION | 취업 입력은 미입력→미취업인데 요약과 p01에서 취업상태가 유지됐다고 한다. UNKNOWN 해소를 입력 불변으로 설명한다. |
| EX07 | FACT_CONTRADICTION | 생활비 소득 증가로 p01/p02가 통과했다고 설명하지만 이 정책들은 생활비 소득을 자격 규칙으로 사용하지 않는다. 가구소득은 UNKNOWN이다. |
| EX08 | IRRELEVANT_POLICY_EXPLANATION | 소득 감소와 정책 통과를 함께 반복한다. 정책별 변경 조건 설명으로서 부정확하거나 오해할 여지가 있다. |
| EX09 | FACT_CONTRADICTION | 월세·총지출이 증가했는데 p02가 소득과 지출 모두 변화 없다고 설명한다. |
| EX10 | FACT_CONTRADICTION | 월세 감소를 소득·수입 증가라고 설명한다. Python 생활비 소득은 불변이다. |
| EX11 | REJECTED_BEFORE_DISPLAY | 금지 표현 승인. 전체 정형 대체. 의미 정확도 통과로 세지 않는다. |
| EX12 | UNSUPPORTED_CAUSALITY | 소득 감소로 소비 지출이 유지됐다고 설명한다. 입력된 지출 불변의 인과관계를 만들었다. |
| EX13 | REJECTED_BEFORE_DISPLAY | 금지 표현 불확정에 포함된 확정. 전체 정형 대체. 의미 정확도 통과로 세지 않는다. |
| EX14 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED | Codex 검토에서 추가 확정 오류를 기록하지 않았다. 사람 검토/사용자 이해도/의미 정확성 인증이 아니다. |
| EX15 | REJECTED_BEFORE_DISPLAY | 금지 표현 충족. 전체 정형 대체. 의미 정확도 통과로 세지 않는다. |
| EX16 | REJECTED_BEFORE_DISPLAY | 금지 표현 승인 및 숫자. 전체 정형 대체. 의미 정확도 통과로 세지 않는다. |
| EX17 | REJECTED_BEFORE_DISPLAY | 금지 표현 승인. 전체 정형 대체. 의미 정확도 통과로 세지 않는다. |
| EX18 | NO_ADDITIONAL_FLAG_NOT_CERTIFIED | Codex 검토에서 추가 확정 오류를 기록하지 않았다. 사람 검토/사용자 이해도/의미 정확성 인증이 아니다. |
| EX19 | FACT_CONTRADICTION | 지역 입력은 안산시→서울시인데 p02는 거주 지역 변화가 없었다고 설명한다. 비사용 조건과 입력 불변 혼동이다. |
| EX20 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX21 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX22 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX23 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX24 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX25 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX26 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX27 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX28 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX29 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |
| EX30 | AMBIGUOUS_SCOPE_LOW_UTILITY | 일부 정책은 PASS인데 전체 정책 상태가 불명인 듯한 요약. 정책별 UNKNOWN 범위가 불명확하고 예산 설명이 거의 없다. EX21~30은 반복된 같은 입력이며 새로운 오류 내성 성과가 아니다. |

설계의 warm27/30은 초기 **제안 목표**였으며25/30으로 미달했다. 더 중요한 필수 관문인 “채택 문장의 중대한 의미 모순0”도 미충족이다. 프롬프트를 사후 조정하거나 검증기를 느슨하게 만들어 지표를 맞추지 않았다.

## 12. 실제 API

실제 FastAPI `/api/synthetic/explain`에 합성 EX02/EX11을 각각1회 보냈다. EX02는1711.27ms/llm, EX11은1286.02ms/UNSUPPORTED_NARRATIVE 정형 대체. 둘 다HTTP200, Cache-Control:no-store, 원본 필드 불변을 assert했다. 이는 HTTP 연동 검증이며 EX02의 문장 의미를 인증하지 않는다. 이후 정형 기본값으로 복귀하고 기존 products/savings/comparison/explanation/main 실제 HTTP5경로를 재검증했다.

## 13. 실제390px 화면

390×844에서 첫UI TIMEOUT→정형, 별도 수동 두 번째 요청 표현 거부→정형, 취업 변경 세 번째 요청 검사 통과→생성형 표시를 확인했다. 로딩·disabled 버튼·UNKNOWN/추가질문·원본 숫자·입력 변경 시 이전 결과 제거를 확인했다. 검사 통과 화면에도 p01의 잘못된 취업 불변 문장이 있어 기본 활성화 승인의 근거가 아니다. 시험 후 viewport reset·페이지 reload/정형 API 복귀. 스크린샷은 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\m3.8b`의 browser-timeout/rejected/accepted/unknown-390.png에 있다. UI 원시HTTP body는 별도 수집하지 않았으며 화면 관측과 구분한다.

## 14. 자원 측정

warm 시점 GPU 전체 사용4978MiB/8151MiB, GPU사용률0% 유휴 관측. llama-server working set819650560bytes(약781.7MiB), 해당 프로세스 peak869564416bytes(약829.3MiB). server/runner는 별도다. 단일 시점·프로세스 수치이며 전체36실행 통합peak/모델 단독GPU 사용량이 아니다. 서버실행 설정/현재 model ps와 자원 원문을 증거에 포함했다. 모델을 새로 받거나 드라이버/보안/시작프로그램을 변경하지 않았다.

## 15. 신규 시험

신규 통신모의 **68 passed(1.49초)**. 고정30 service 연결, 최소 payload/privacy, 불완전/원격/다른모델/envelope/중복/nonfinite/byte/token/timeout/offline/거부, factory/legacy, 기존validator 호출, 동시 요청 격리를 검증했다. 모의시험68을 실제모델68회로 표시하지 않는다. 실제 fixed30는 별도다.

## 16. 회귀와 최초 실패 이력

최초 전체:1 failed/11939 passed/1 skipped/1 warning(81.78초). 기존 NTFS handle equality가234→231 **감소**로 실패했다. 코드·기대값 수정없이 단독 실제NTFS16passed/1skipped(2.22초), 전체 재실행**11940passed/1skipped/1warning(79.30초)**. 최초 실패를 삭제하지 않았고 정확한 외부 handle 감소 원인은 확정하지 못했다. 누수 확정이나 보안 결함 수정 완료로 쓰지 않는다.

Frontend115passed(5files/10.39초), TypeScript/Vite빌드 성공(Vite1.67초), 기존 실제HTTP5경로 통과. 새 production변경 이후 추가 소스 변경0. skip은 실제NTFS symlink권한 부족, warning은 기존Starlette/httpx. M2.77의증거보류를승격하지않는다. 도구실행에서 `python` 별칭이 Store바로가기로 미실행된 빌드는 기존.venv절대경로로 실행해 성공했으며 신규 설치0.

## 17. 알려진 메타데이터 한계

기존 service는 Provider가정상반환한뒤에만ai_executed=true로설정한다. 따라서 실제모델응답이후거부된경우도API에는false로표시될수있다. 이번 실제요청계수/원문이실행근거이며이flag로실제실행수를계산하지않는다. 기존DTO/검증기유지범위를넘겨고치지않았고후속검토과제로남긴다.

## 18. 보존 범위

Policy/Cashflow/금융/Coverage/Acceptance/Historical, 기존M3.2반올림, M3.8A코어·기존검증기·테스트/golden/fingerprint와실제release6개를보존한다. GV01~GV15/BV01~BV16기대값변경0이고전체회귀로재확인했다. 저장소baseline309개중기존변경은provider.py설정분기와ARCHITECTURE문서2개만허용한다. 6개release SHA256은다음과같으며게시후감사로재확인한다.

| 파일 | SHA256 |
|---|---|
| `data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025` |
| `data/releases/ansan-youth-2026-10-20-001/README.md` | `4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f` |
| `data/releases/ansan-youth-2026-10-20-001/sources.json` | `a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b` |
| `data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json` | `d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92` |
| `data/releases/ansan-youth-2026-10-20-002/README.md` | `8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99` |
| `data/releases/ansan-youth-2026-10-20-002/sources.json` | `711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620` |

## 19. 개인정보·외부 활동

모든실제생성/기록은공개합성30개또는같은합성UI값이다. 제품제공자에prompt/응답원문로깅추가0. 저장소증거는합성결과뿐이며민감계좌/비밀키없음. 원격AI/외부전송/새IBK문의/계좌로그인0. IBK는사용자발송보고/공식회신대기유지.

## 20. Obsidian

기존워크플로에따라새M3.8B마일스톤/대시보드/현재개발/회귀/설명계약·미해결항목에실행실적과품질보류를기록한다. Wikilink/heading/block/source_paths/local파일/Bookmarks/Base/Canvas/템플릿검사결과는게시후본절에추가한다. 앱설정·플러그인불변, GUI확인미완료·최신완료Bookmark M3.1구버전상태유지.

## 21. 현재 제품 상태

실제상품만기계산0, 검증되지않은실제지원금반영0원, 실제정책DRAFT/CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED, M2.77SYNTHETIC_ONLY, Coveragefreeze유지. 기본설명은NoProvider정형이다. 실험제공자는명시적서버opt-in으로만사용한다. 연결코드의완료와모델문장운영승인을구분한다.

## 22. 최종 판단과 다음 최소 작업

**M3_LIGHTWEIGHT_LOCAL_LLM_INTEGRATED_QUALITY_REVISION_REQUIRED**. 실제연결·고정30검증·기존제한내전체대체·회귀는완료했지만자연어품질관문은통과하지못했다. `M3_LOCAL_LLM_EXPLANATION_VERIFIED`로선언하지않는다.

다음최소작업제안하나: **M3.8C — 의미오류방지설명계약보완설계**. 생활비와정책소득/입력변화와정책비사용조건의혼동을막도록모델자유서술범위를더좁히거나서버확정설명단위선택방식을검토한다. 기존검증기·엔진을바꾸거나새모델설치/대규모구현은아직하지않는다. 사람의한국어검토와기존정형대비효용평가도남는다.

## 23. 재현

기존모델server를동일local-runtime/modelstore로실행하고위server환경을시험프로세스에만설정한다. 새고정30명령은 `python -B -m tools.evaluate_local_narrative --phase fixed30 --output <별도 합성 결과 파일>`이다. cold실행은별도 `--phase cold`로기록한다. 기존증거파일을덮어쓰거나실제사용자입력으로로그를만들지않는다. root의.venv실행기/기존node도구를사용하며설치명령은필요없다.


## 24. 게시 후 보존·문서 검사

저장소 기존309개 중 **307개 불변**, 변경기존2개(provider 설정분기/Architecture), 신규6개(Provider/Prompt/68시험/실제평가도구/보고/증거)만 확인했다. 기존코어/validator/API/화면/엔진/테스트/golden·Coveragefreeze·실제release6SHA256 불변이다. 보존감사와 Obsidian 감사 결과를 합성증거 JSON에 포함했다.

Obsidian은 **기존13노트 갱신/신규1노트**, Markdown71/Wikilink595(heading15/block1)/source_paths328/로컬파일59, 깨진링크0이다. Bookmarks13·4그룹/Base1/Canvas1/템플릿5/앱설정은 보존했다. GUI 미확인과 최신완료Bookmark M3.1 구버전 상태를 남겼다. 새 마일스톤은 partial로 표기하고 연결완료/문장품질보류를 구분했다.

시험용 모델server/runner는 경로와 소유를 확인해 종료했다. 초기 종료보호검사는 OS conhost를 모델 경로로 인식하지 않아 중단됐고, 모델 runner/server의 정확한 PID/실행파일을 확인한 뒤 두 프로세스만 종료했다. 사용자앱/보안설정은 변경하지 않았다. 기본API NoProvider 복귀 후 기존실제HTTP5경로가 통과했다. 제품 소스는 최종전체회귀 이후 추가수정하지 않았다.

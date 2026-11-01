# M3.0 — 기존 AI+X 코어 기반 첫 웹서비스 완료 보고

검증일: 2026-10-24 (한국 시간). 합성 시연 범위의 완료이며 실제 정책 서비스 승인이 아니다.

## 1. 기존 구조와 재사용 API

기존 `backend/policy_engine`, `backend/cashflow`, `data/synthetic`, `tests`, `docs`, `tools`를 조사했다. 기존 FastAPI/React 구현은 없었다. 새 저장소나 대체 엔진은 만들지 않았다.

- `load_policy_set(path)`로 기존 합성 fixture 로딩.
- `UserProfile`, `EvaluationContext`와 `evaluate_policies(profile, policies, context)` 재사용.
- `PolicyEvaluation.to_dict()`의 상태·조건 결과·reason·missing·evidence·context·version 보존.
- `CashflowInput`, `calculate_cashflow`, `CashflowResult.to_dict()` 재사용.
- CLI와 같은 합성 평가일 2026-10-20, 데이터 synthetic-v1 사용.

## 2. 생성·수정 파일

새 파일 22개:

```text
backend/web/
  __init__.py
  app.py                    HTTP 경로, 오류/캐시 응답
  schemas.py                웹 경계 입력 검증과 응답 형태
  service.py                기존 코어 연결, 혜택 0원 고정
frontend/
  index.html
  package.json
  pnpm-lock.yaml
  pnpm-workspace.yaml
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api.ts
    form.ts
    styles.css
    test-setup.ts
    App.test.tsx
  tests/live-http.mts
tests/test_synthetic_web.py
requirements-web.txt
requirements-web-dev.txt
docs/M3_0_SYNTHETIC_WEB.md
```

수정 3개: `README.md`(현재 기능/실행 안내/전국 청년 지향), `.gitignore`(웹 산출물), `docs/ARCHITECTURE.md`(M3.0 절 추가). 기존 코어·기존 테스트·정책/합성 fixture는 수정하지 않았다.

## 3. 합성 정책 3개 연결

기존 `data/synthetic/policies.json`을 읽는다. SAMPLE-001은 나이·안산시 일치, SAMPLE-002는 미취업, SAMPLE-003은 안산시·정책 기준 가구소득 조건이다. 정책 이름도 fixture를 사용한다. UI에서 합성 정책임을 상단과 각 결과에 표시하고 실제 공고와 구분한다.

## 4. 입력 스키마와 명시한 구현 가정

| 필드 | 웹 계약 |
|---|---|
| age | 만 나이 정수 0~120 또는 null, 생년월일 수집 안 함 |
| region | 문자열 80자 이내 또는 null, 앞뒤 공백 제거, 빈칸은 null |
| student_status | true / false / null |
| employment_status | employed / unemployed / null |
| monthly_income | 월 생활비 소득, 필수 정수 원 |
| monthly_rent | 월세, 필수 정수 원 |
| monthly_fixed_expenses | 월세를 제외한 고정지출, 필수 정수 원 |
| other_monthly_expenses | 기타지출, 필수 정수 원 |
| user_savings_capacity | 정수 원 또는 null, 미지정은 null, 0과 구분 |

금액은 각 항목 0~1,000,000,000,000원이다. 나이/금액 상한은 **웹 입력 검증 범위**이며 정책 자격 기준이 아니다. JavaScript에서 합계를 정수로 정확히 표시하기 위한 제한이다. 숫자의 문자열·소수·bool 변환은 허용하지 않는다. 재학/취업은 독립적이며 학생을 취업 상태로 입력하지 않는다.

명시한 구현 선택: 기존 엔진의 age 입력을 사용한다. 합성 평가일은 CLI와 같게 고정한다. 지역은 기존 규칙과 정확히 비교하며 임의 행정구역 정규화는 하지 않는다. 입력 부족은 추측하지 않는다. `policy_facts=()`를 유지해 생활비 소득을 가구소득으로 만들지 않는다. HTTP에서 추가 필드를 거부하므로 가구소득/지원금/정책 사실의 우회 주입도 422로 거부된다.

입력 모델의 HTTP 연결은 [FastAPI 공식 Request Body 문서](https://fastapi.tiangolo.com/tutorial/body/)를 확인했다. 프론트 실행 환경은 [Vite 공식 가이드](https://vite.dev/guide/)를 기준으로 확인했다.

## 5. FastAPI 경로

- `GET /api/health`: status=ok, synthetic=true, test_only=true. 프로세스 생존 확인용.
- `POST /api/synthetic/simulate`: 입력 검증 → 서비스 함수 → 두 기존 코어 → 구조화된 결과.
- 200: synthetic/test_only, input_summary, dataset_version, evaluation_date, policies, cashflow.
- 422: 입력 오류, field path/type만 반환하고 잘못된 입력 원문은 오류에 복사하지 않는다.
- 모든 응답 `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.

라우터는 계산식을 포함하지 않는다. 합성 정책의 불변 데이터만 메모리에 캐시하며 사용자 입력/결과는 캐시하지 않는다.

## 6. React 화면

React/TypeScript/Vite로 기본 정보와 금액 입력, 계산 버튼, 정책 3상태/조건별 이유/누락 정보/원본 근거, 월 예산/수입·지출 상세를 구현했다. 입력은 화면 메모리에서만 관리한다. 입력 수정 시 이전 결과를 지운다. 처리 중 중복 제출 방지, 로딩, 10초 요청 중단, 입력 오류, 서버 연결 실패와 재시도를 제공한다.

데스크톱은 입력/결과 2열, 좁은 화면은 1열이다. 키보드 포커스, 상태 텍스트와 색 구분, 적자 음수 표시, 입력 16px, safe-area를 적용했다. 외부 폰트/이미지/분석 서비스는 사용하지 않는다.

## 7. 실제 HTTP 연결

최종 기존 저장소에서 127.0.0.1:8100 FastAPI와 127.0.0.1:5173 Vite를 실행했다. Vite는 `/api`를 루프백 API로 전달한다. `frontend/tests/live-http.mts`는 실제 화면의 `api.ts`를 import하고 실제 fetch로 전/후 시나리오와 422를 검증했다. fetch mock이 없는 검증이다. 브라우저 계산도 같은 경로로 실행했다.

## 8. 제안서 4쪽 시나리오 재현

공통: 만24세, 안산시, 재학 중. 고정지출 200,000원, 기타지출 350,000원. 각 입력을 독립 실행했다.

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| 취업 | 미취업 | 취업 |
| 월소득 | 1,500,000 | 1,800,000 |
| 월세 | 450,000 | 550,000 |
| 총지출 | 1,000,000 | 1,100,000 |
| 월 여유자금 | **500,000** | **700,000** |
| 사용자 저축 상한 | 300,000 | 500,000 |
| 저축 투입 상한 | **300,000** | **500,000** |
| 지원금 반영 | 0 | 0 |

## 9. PASS / FAIL / UNKNOWN

| 실행 입력 | SAMPLE-001 | SAMPLE-002 | SAMPLE-003 |
|---|---|---|---|
| 기존 기본 fixture: 취업 | PASS | FAIL | UNKNOWN |
| 제안서 변경 전: 미취업 | PASS | PASS | UNKNOWN |
| 제안서 변경 후: 취업 | PASS | FAIL | UNKNOWN |
| 나이/지역/취업 모두 미입력 | UNKNOWN | UNKNOWN | UNKNOWN |

생활비 소득을 높여도 가구소득 사실은 생성되지 않는다. SAMPLE-003의 가구소득 조건은 계속 UNKNOWN이다. 모든 원본 reason code와 누락 경로를 보존한다.

## 10. Cashflow 결과

기존 Core의 essential=월세+고정지출, total expenses=essential+기타지출을 그대로 사용한다. 월세 중복 차감이 없다. 개인 소득만 입력하며 합성 PASS를 수입으로 바꾸지 않는다.

기존 Core에서 저축 상한 null은 max(0, 여유자금), 상한 값이 있으면 max(0, min(여유자금, 상한))이다. null과 0을 모두 테스트했다. 소득 100,000원/총지출 1,000,000원인 경우 여유자금 **-900,000원**, 저축 투입 상한 0원을 HTTP/브라우저에서 확인했다.

## 11. 개인정보 저장 여부

로그인·DB·localStorage·sessionStorage·쿠키·파일 저장·외부 LLM/분석 전송을 도입하지 않았다. 입력은 화면 메모리와 요청/응답 처리 중에만 사용한다. 현재 화면 결과에는 사용자가 제출한 값이 표시되므로 화면 공유 시 보일 수 있다. 서버 실행은 access log를 끄며 입력 원문 로깅은 없다. 시연은 가상의 입력을 사용했다. 공개 URL 배포는 하지 않았다.

## 12. 신규 Backend 테스트

`tests/test_synthetic_web.py`: **42 passed**.

기존 fixture/CLI 출력 전체와 비교, 코어 실제 호출 확인, 전/후 시나리오, 나이 경계/지역, UNKNOWN/가구소득 분리, Cashflow 결과 동일성, 월세 중복 차감, 적자, 상한 null/0, 지원금 0, 우회 필드/타입/금액 오류, 잘못된 JSON, 요청 간 독립성, health/no-store를 검증했다.

## 13. 신규 Frontend 테스트

`frontend/src/App.test.tsx`: **16 passed** (Vitest/Testing Library). 입력 오류/상한 null·0, 제출 전 미전송, 요청 payload/독립 필드, 3상태/누락 정보/금액 렌더링, 입력 수정 시 결과 폐기, 음수 표시, 서버 오류, 실제 fetch 실패 형태와 재시도, 중복 제출 방지를 검증했다. 이 컴포넌트 테스트의 fetch는 mock이다. 실제 HTTP 증거는 7절 및 14절과 구분한다.

`pnpm build`: TypeScript 검사 및 Vite 프로덕션 빌드 성공, 최종 CSS 경고 없음. lockfile을 사용해 최종 기존 저장소에서 설치/실행했다. 검증 환경 Python3.12.14, Node24.19.0, pnpm11.25.0, React19.3.1, Vite7.3.7, Vitest3.2.7, FastAPI0.162.0, Pydantic2.14.1, Uvicorn0.54.0이다.

## 14. 브라우저 실행 검증

실제 localhost 브라우저에서 기본 fixture, 제안서 전/후, 잘못된 금액, 누락 정보 UNKNOWN, 적자, 수입·지출 상세/원본 근거 펼침을 확인했다. 직접 시작한 API를 잠시 중단해 연결 오류가 표시되는 것을 확인한 다음 API를 재시작하고 ‘다시 시도’로 정상 복구했다. 결과를 fake 응답으로 바꾸지 않았다.

390×844 브라우저 viewport에서 content width=390, viewport width=390으로 가로 넘침이 없고 모든 입력 글자가16px임을 확인했다. 실물 휴대폰/모바일 Safari/가상 키보드 검증은 **미실행**이다. 임시 viewport는 원래대로 복구했다.

스크린샷/브라우저 최종 상태는 작업 채팅 폴더의 `output/m3.0/`에 저장했다. 최종 화면은 변경 후 결과를 표시한다.

## 15. 전체 pytest

- 변경 전: **11,317 passed, 1 skipped** (62.55초).
- 기존 저장소 변경 후: **11,359 passed, 1 skipped, 1 warning** (74.67초).
- 경고1건: 설치된 Starlette TestClient의 httpx 사용에 대한 deprecation warning. 테스트 실패는 없으며 경고를 숨기지 않았다.
- OS/NTFS 테스트의 샌드박스 제한을 피하기 위해 실행 도구의 허용된 외부 실행을 사용했다. UAC 관리자 권한/Developer Mode/보안 설정은 변경하지 않았다.

## 16. 기존 11,317개 회귀

기존 테스트 파일은 bytes/크기/수정시각 모두 불변이다. 기존 테스트를 제거하거나 기대값을 바꾸지 않았다. 전체 통과 수는 신규42개만 증가했다. 기존 정책 및 Cashflow 코어도 불변이다.

## 17. skipped 1건 유지

`tests/test_historical_raw_bytes_preparation_ntfs.py:202`의 실제 파일 symlink 생성 권한 부족 시험이 기존과 동일하게 skipped다. 웹서비스 검증을 이유로 M2.77을 COMPLETE로 선언하지 않는다. M2.77은 **HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY** 유지다.

## 18. Coverage freeze

기존 파일216개 중 README/.gitignore/ARCHITECTURE를 제외한 **213개**의 SHA256/크기/수정시각이 일치했다. Coverage 코어, Historical6 loader, CrossValidator, Same-call Orchestrator, RawBytesPreparation, Acceptance와 golden을 변경하지 않았다. GV01~GV15/BV01~BV16이 포함된 기존 테스트도 전체 회귀에서 통과했다.

## 19. 실제 release 6개 무변경

두 release 디렉터리의 정책 JSON/README/sources.json 총6개 모두 SHA256, 크기, 수정시각 불변을 확인했다. 두 release를 서로 다른 실제 정책2개로 세지 않는다. 상세 digest는 보존 감사 JSON에 기록했다.

## 20. 실제 정책 상태

실제 안산 정책 **DRAFT / CONDITION_SLICE**, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**를 유지한다. API는 해당 데이터를 로드하지 않는다. 실제 정책 지원금은 0원이고 미확인 조건을 PASS로 바꾸지 않았다. 제품 대상은 모든 청년이며 초기 검증 지역이 안산이다.

## 21. 이번에 구현하지 않은 기능

금융상품 필터/비교, 예·적금 이자/만기 계산, 통합 What-if/Before-After UI, 생성형 AI 설명, 실제 정책 서비스 판정, 실제 혜택 Cashflow Bridge, 로그인/DB, 계좌 연결, 공개 배포는 없다. 제안서 전/후 입력은 같은 경로에서 독립 실행했다.

## 22. 최종 판단

**M3_SYNTHETIC_VERTICAL_SLICE_COMPLETE**

React→실제 HTTP→기존 Policy/Cashflow→화면 표시를 확인했고 기존 회귀와 동결 범위를 유지했다. 합성 웹 연결 범위의 판단이며 실제 정책 적격성/지원금 반영/Windows symlink 보안 검증의 완료 판단을 대신하지 않는다.

### 최초 실패·수정·재실행 이력

1. pnpm 초기 설치: 샌드박스 파일 연결 권한 EPERM → 보안 설정 변경 없이 허용된 외부 실행으로 재시도.
2. esbuild 설치 스크립트 기본 차단 → 해당 패키지만 allowBuilds=true로 명시. `--allow-build` 인자는 미지원이라 실행 실패했으며 프로젝트 설정 방식으로 수정해 설치 성공.
3. jest-dom 범위가 deprecated6.10.0을 선택 → 6.9.1로 고정하고 lockfile 재생성/동일 설치 확인.
4. 샌드박스 안 TestClient 실행 응답 지연 → 허용된 외부 실행에서 동일한42개 테스트 전부 통과. production 코어 수정 없음.
5. API8000번은 사용 중 → 기존 프로세스는 건드리지 않고8100번으로 연결 설정 통일.
6. 최초 빌드 CSS media 공백 누락 경고 → 구문 수정, 최종 빌드 경고 없음.
7. 브라우저 누락 정보 설명이 나이/취업에도 생활비 대체 금지 문구를 붙임 → 가구소득 누락에만 붙이도록 표시 문구 최소 수정,16개 화면 테스트/빌드 재통과.
8. 브라우저 상세 열기에서 locator가 native summary를 button으로 찾지 못함 → 최신 접근성 상태에서 해당 summary를 눌러 실제 상세 표시 확인. 제품 결함이 아니며 코드 변경 없음.
9. 서버 연결 실패 시험은 의도적으로 서버를 중단해 실행한 예상 오류다. 재시작/재시도 성공.

## 23. 다음 최소 작업

**M3.1: 합성 데이터만 사용하는 Before/After 비교**. 현재 입력을 기준 시나리오로 유지하고 수정 시나리오를 같은 API로 독립 평가해 정책 상태/불확실성과 여유자금·저축 투입 상한 변화만 비교한다. 비교 값은 기존 결과에서 계산하며 정책 엔진/현금흐름 코어를 복제하지 않는다. 실제 정책/지원금 승격은 계속 분리한다. 이번에는 구현하지 않았다.

## 현재 PC 실행 안내 보충

일반 환경에서는 README의 pnpm 명령을 사용한다. 현재 PC에서 pnpm이 PATH에 없다면 frontend 폴더에서 다음 실제 실행 파일을 사용할 수 있다.

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd' dev
```

검증 후 로컬 API/화면 서버를 실행 상태로 남겼다. 종료 후 다시 실행하려면 저장소 README의 두 터미널 명령을 사용한다.

# M3.2 — 합성 적금 만기 계산 및 Obsidian 기록

검증 기간: 2026-10-24~2026-10-25 KST.
최종 판단: **M3_SYNTHETIC_SAVINGS_CALCULATOR_COMPLETE**.
코드/API/실제 계산/React 검증 완료. Obsidian 파일 기록·링크 검사 완료; Obsidian 앱 GUI 검증은 미완료.

## 목표와 구현 경계

TEAM복학생 AI+X 기존 프로젝트에 가상 정액적금1개의 실제 계산 경로를 추가한다.
전국 청년 대상이며 안산은 첫 정책 검증 지역이다. 학기 공동 기획/기존 자산과 개인 추가 개발을 구분한다.
실제 상품 추천이나 실수령액 보장이 아니다. 지원금은 항상0원이다.

## 계산 계약

입력 P=매월 납입 원화 정수, n=정수 개월, a=연 기본금리 퍼센트 십진 문자열.
매월 초 같은 금액을 납입하고 고정금리·단리·세전으로 계산한다.

```text
r = Decimal(a) / 100
principal = P * n
interest = P * r * n * (n+1) / 24
rounded_interest = interest.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
maturity = principal + rounded_interest
```

이는 P*(r/12)*n(n+1)/2와 같은 식이다. 월 이율을 먼저 잘라내거나 납입 건별로 반올림하지 않는다.
총이자를 계산한 뒤 마지막에 한 번만 원 단위 반올림한다. 비음수0.5원은1원이다.
함수 내부 별도 Decimal Context(prec=50, ROUND_HALF_UP)로 호출자 전역 정밀도/trap에 영향받지 않는다.
반올림 전 이자 문자열은50자리 정밀도 중간값이며 무한소수의 무한 정밀도를 주장하지 않는다.
정확한 십진 입력·정수 결과 계약이다. 중간 계산/결과에 float를 쓰지 않는다.
[Python Decimal 공식 문서](https://docs.python.org/3/library/decimal.html).

시뮬레이션 입력 한도: P0~1조 원, n1~120개월, a0~100%·소수4자리까지.
실제 상품 가입조건이 아니다. 이 범위 최대 만기725,000,000,000,000원은 JS 안전 정수 이내다.
0납입은 합성 계산상 허용한다. 실제 상품의 최소 납입액으로 해석하지 않는다.

필수 사례: P200,000원/n12/a3% → 원금2,400,000원 + 세전이자39,000원 = 세전만기2,439,000원.
경계: P60/n1/a9.9999%→0.499995원→0원,10%→0.5원→1원,10.0001%→0.500005원→1원.
P1/n3/a100%의 총이자0.5원→1원으로 건별 반올림과 구분한다.

## 파일과 실행 흐름

- backend/finance/recurring.py: frozen 입력/결과, 유효성 검사, 순수 Decimal 함수.
- backend/web/savings.py: strict 요청/응답, 기존 월 예산 adapter 재실행, 상한 비교.
- backend/web/app.py: 기존 경로 유지, 새 적금 POST만 추가.
- frontend/src/savings-api.ts: 실제 HTTP, validation/server 구분.
- frontend/src/SavingsPanel.tsx: 입력/로딩/결과/경고/오류/이전 응답 차단.
- frontend/src/App.tsx 및 styles.css: 기존 결과 아래04단계, 좁은 화면 대응.
- tests/test_recurring_savings.py 및 frontend/src/SavingsPanel.test.tsx: 신규 테스트.
- frontend/src/testing/savings-fixture.json: 실제 Python 결과로 생성한 테스트 전용 fixture. 제품 화면 숫자가 아니다.
- frontend/tests/savings-live-http.mts: 실제 fetch/API 검증. mock 없음.

## API

POST /api/synthetic/savings/recurring

```json
{
  "profile": {"age":24,"region":"안산시","student_status":true,"employment_status":"unemployed","monthly_income":1500000,"monthly_rent":450000,"monthly_fixed_expenses":200000,"other_monthly_expenses":350000,"user_savings_capacity":300000},
  "monthly_payment":200000,
  "term_months":12,
  "annual_base_rate_percent":"3"
}
```

금리를 JSON number로 받지 않는다. 계산 방식 생략 시 MONTHLY_BEGINNING_FIXED_SIMPLE_PRETAX.
다른 방식은422 및 errors[].type=UNSUPPORTED_ASSUMPTION. 미지원 필드도422(extra_forbidden).
오류는 기존 개인정보 비반환 handler를 재사용하고 입력 원문을 되돌려주지 않는다.
응답: synthetic/test_only, 납입/기간/금리, 원금/세전이자/만기, 계산방식/가정/반올림,
미지원 목록, 기존 cashflow, budget_comparison, disclaimer.
입력된 예산의 savable_amount를 서버에서 재계산한다. 클라이언트가 계산한 상한은 받지 않는다.
저축 상한 미지정/명시0/양수 제한을 각각 UNSPECIFIED/EXPLICIT_ZERO/EXPLICIT_LIMIT로 구분한다.
예산 적자를 유지하고 상한만0원으로 제한한다. 납입액 초과는 경고이며 원금을 자동 축소하지 않는다.
상한 비교에 PASS/FAIL/UNKNOWN을 쓰지 않으며, 현재 상한 이내라도 장기 납입 여력을 보장하지 않는다.

## React

현재 상황 계산 후04단계에서 월 납입/개월/금리를 입력한다. 기본 예시도 제출 전에는 계산하지 않는다.
서버 반환 금액을 표시하며 브라우저에 이자 공식을 복제하지 않는다.
빈 입력/형식 오류/서버 오류/연결 실패/10초 초과를 구분한다. 요청 중 중복 제출 차단,
입력 수정/현재 상황 변경/언마운트 시 취소하여 이전 결과를 제거한다.
가정·지원하지 않는 조건·세전·가상 상품·반올림을 화면에 표시한다.

## 지원하지 않는 범위

복리, 실제 일수, 중도해지, 우대금리 자동 충족, 세후 실수령액, 변동금리, 자유적립식,
정부 기여금, 재가입/장기 전망. 실제 은행 상품 수집/추천, 예금,3개 비교, What-if 상품 결과 비교도 미구현이다.
공개 배포/외부 LLM/실물 휴대폰 사용성 시험은 이번 완료 주장에 포함하지 않는다.

## 검증 상태

| 구분 | 실제 결과 |
|---|---|
| 변경 전 전체 기준선 | 11,407 passed / 1 skipped / 1 warning (66.14초) |
| 신규Backend | 83 passed / 기존 warning1 |
| 변경 후 전체 pytest | **11,490 passed / 1 skipped / 1 warning (70.08초)** |
| Frontend | **70 passed = 기존40 + 신규30** (8.04초) |
| 타입 검사·배포 빌드 | tsc -b && vite build 성공 |
| 실제 HTTP | 새 적금 및 기존 simulate/compare 모두 통과. fetch mock 없음 |
| 실제 브라우저 | 필수2,439,000원, 상한 초과, 빈 입력 차단 확인 |
| 390×844px | 납입액40만원 유지/10만원 초과 경고, 문서 clientWidth375=scrollWidth375; 가로 넘침 없음 |
| 보존 감사 | 기존248개 중244개 SHA256/크기/mtime 불변; 허용된 기존4개 수정 + 신규10개 |

skip1은 기존 실제 NTFS 파일 symlink 생성 권한 부족, warning1은 기존 Starlette/httpx TestClient deprecation이다.
별도 Windows 권한 환경을 확보하거나 보안 설정을 바꾸지 않았다. M2.77 판정을 승격하지 않는다.
Frontend는 실제 Python 결과로 만든 fixture를 사용하는 단위 시험과 mock 없는 실제 HTTP/브라우저 검증을 구분한다.
실물 휴대폰의 키보드/터치/사용성은 미검증이다. 브라우저 검증 크기를 원래대로 복원했다.

재현 명령(저장소 루트; 프런트엔드 명령은 frontend에서):

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -ra -p no:cacheprovider
pnpm test
pnpm build
node --experimental-strip-types tests/savings-live-http.mts
node --experimental-strip-types tests/live-http.mts
node --experimental-strip-types tests/comparison-live-http.mts
```

실행 때 pytest basetemp/TEMP/TMP는 작업 폴더 tmp로 지정했다. 현재 PC의 pnpm은
`<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd`를 사용했다.
API 실행: `.venv\Scripts\python.exe -B -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8100 --no-access-log`.
React 실행: frontend에서 `pnpm dev`, 로컬주소 http://127.0.0.1:5173/.

로그/증거의 실제 위치(작업 채팅 폴더; 임시 보관이므로 장기 증거는 별도 보존 필요):

- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-pytest-before.txt`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-pytest-new.txt`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-pytest-after.txt`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-preservation-audit.json`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-vault-audit.json`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-savings-desktop.png`
- `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m32-savings-mobile.png`

## 최초 실패·수정·재실행

신규Backend 최초73 passed/10 failed: 새 테스트가 기본 FastAPI detail 배열을 가정했으나
기존 개인정보 보호 오류 계약은 detail 문자열 + errors 배열이었다. 신규 테스트 접근만 errors로 수정했다.
기존 handler/기대값을 바꾸지 않았고 신규83 passed로 재실행했다.
실제 HTTP strip-types 실행을 위해 신규 TS 오류 클래스의 parameter property를 명시 멤버로 수정했다.
기존 이전 버전의 서버가 포트를 점유해 신규 실행이 실패했다. 실행 프로세스/프로젝트 경로와
OpenAPI 경로를 확인하고 같은 프로젝트의 API 서버만 갱신한 뒤 실제 HTTP3경로를 통과했다.
기존 Vite는 새 소스를 반영하므로 재시작하지 않았다. 신규 기능/테스트 이외 기존 기대값은 수정하지 않았다.
최종 Frontend는 잘못된 JSON 응답을 서버 오류로 분류하는 케이스까지 추가해70개 통과했다.

## 보호 및 기록

Policy/Cashflow/Coverage/Acceptance/Benefit/Historical6/CrossValidator/Same-call/RawBytes 변경 없음.
실제 release6, GV01~GV15/BV01~BV16 및 기존 테스트·fixture를 기준선과 SHA256/크기/mtime 대조하여 불변을 확인했다.
실제 정책 DRAFT / CONDITION_SLICE, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED,
M2.77 HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY 유지. 검증되지 않은 지원금0원.
Obsidian 기록은 실제 `<USER_HOME>\Documents\Obsidian\AI+X-Project`에 반영했다.
기존 노트17개 필요한 절만 갱신, 신규2개(M3.2 마일스톤·합성 적금 만기 계산)를 추가했다.
M3.1은 과거 제안을 소급 삭제하지 않고 이후 승인/완료 링크를 덧붙였다.
대시보드/현재 상태/테스트/미구현/로드맵/할 일/금융/Cashflow/코드 바로가기를 연결했다.
Markdown53개, Wikilink299개, source_paths120개, 외부 로컬 링크9개, 깨진 링크0개.
기존 Bases1/Canvas1/템플릿5/북마크13개4그룹과 앱 설정8개는 변경하지 않았다.
Bases의 필터상 신규 type=milestone, project=AI+X, status=completed인 M3.2 노트가 포함된다.
실제 표 렌더링·대시보드·Bookmarks 클릭은 앱에서 보지 않았으므로 검증 완료로 주장하지 않는다.
적금2개 노트에 북마크 후보를 표시했다. 커뮤니티 플러그인/Sync/Publish/외부 업로드는 추가하지 않았다.
Obsidian 앱 GUI 검증은 별도 미완료 상태를 유지한다.

## 다음 최소 작업

M3.3 — 실제 공식 금융상품 스냅샷3개 이상 검증 및 비교를 우선 검토한다.
실제 상품 수집/공시 이용 조건이 차단되면 확인 가능한 최소 범위만 진행한다. 이번에는 착수하지 않는다.

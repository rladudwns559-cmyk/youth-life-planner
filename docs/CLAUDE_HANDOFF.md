# Claude 인계서 — 청년 경제생활 의사결정 시뮬레이터

작성 기준: **2026-11-07 KST**. 이 문서는 현재 제품 기획·구현 현황·개발 시작 방법을 한 번에 전달하기 위한 인계서다. 아래 수치는 기준일의 기록이며 미래 시점의 실시간 현황이 아니다.

## 1. 이 문서를 받은 Claude에게

당신은 기존 AI+X 프로젝트를 이어받는 시니어 소프트웨어 엔지니어·데이터 엔지니어·AI 서비스 아키텍트다. **새 프로젝트를 만들지 말고 기존 코드를 먼저 읽고 실행한 뒤 작은 단위로 개선하라.** 사용자와는 한국어로 대화한다.

- 소스: https://github.com/rladudwns559-cmyk/youth-life-planner
- 운영 화면: https://youth-life-planner.rladudwns559.chatgpt.site/
- 현재 코드 기준 커밋: `d82e4fd720af31c3e4afb832dba24f4255edd415`
- 위 커밋 이후 이 인계서 같은 문서 변경이 추가될 수 있다. 최신 main과 실제 차이를 확인하고 다른 사람의 변경을 보존한다.
- 저장소는 공개되어 있다. GitHub를 읽을 수 없는 대화 환경이라면 접근했다고 주장하지 말고 저장소 ZIP 첨부 또는 저장소를 열 수 있는 개발 환경이 필요하다고 알린다. 링크 하나가 모든 파일을 자동으로 읽어 주는 것은 아니다.

현재 사용자 요청 → 이 인계서의 최신 상태 → 최신 검증 문서·실제 코드 → 과거 마일스톤 문서 순서로 현재 작업의 맥락을 확인한다. 불일치를 발견하면 숨기거나 임의 통합하지 말고 근거를 제시한다. 과거 문서에 남은 초기 계획을 최신 구현 상태로 오해하지 않는다.

원 기획서 `TEAM복학생_최종프로젝트_기획서_v1.0.pdf`는 정책 판단·계산·AI 역할 분리의 출발점이다. PDF 자체는 이 인계서에 첨부하지 않았다. 읽지 않았다면 읽었다고 하지 않는다. 이후 사용자가 명시적으로 전국 청년 대상, 공식 상품·지역 사업 확대, 추천 중심 탐색으로 범위를 발전시켰다. 과거 `PROJECT_PLAN.md`의 안산 한정 MVP를 현재 제품에 다시 강제하지 않는다.

## 2. 최종 제품 기획

**한 문장:** 청년이 자신의 조건으로 정부·지자체 지원사업과 예·적금을 탐색하고, 추천 근거·불확실성·생활비와 저축 계획의 변화를 확인하는 웹서비스.

### 대상과 문제

- 대상은 전국 청년이다. 안산은 초기 검증 지역이지 최종 서비스 대상의 한계가 아니다.
- 학생·취업 준비생·근로 청년 등 다양한 상태를 다룬다. 청년 나이는 사업별로 다르므로 일괄 19~34세로 확정하지 않는다.
- 흩어진 공고, 서로 다른 가입 조건, 최고금리 중심 안내 때문에 자신에게 맞는 지원과 금융상품을 비교하기 어렵다는 문제를 해결한다.
- 단순 목록보다 ‘왜 먼저 검토할 만한지, 어떤 조건을 확인해야 하는지’를 분명히 보여준다.

### 핵심 사용자 흐름

1. 지역·나이·취업 상태·월세 거주 여부 등 조건을 입력한다.
2. 지역과 조건에 맞으며 모집 근거가 있는 사업을 우선 제시한다.
3. 소득·재산·가구 구성 등 미확인 조건은 추가 확인으로 남긴다.
4. 월 저축 가능 금액·목돈·목표 기간에 맞는 예·적금을 추천하고 비교한다.
5. 로컬 계산 기능에서는 소득·월세·고정지출로 월 예산을 계산하고 What-if 전후를 비교한다.
6. 공식 출처·확인일·조건·추천 이유를 함께 제공한다. AI는 기존 결과를 설명한다.

현재 공개 사이트에서 5번의 Python 기능과 로컬 모델을 상시 제공하는 것은 아니다. 아래 구현 구분을 따른다.

### 입력과 개인정보

- 정책/생활 계획 개념: `age`, `region`, `monthly_income`, `student_status`, `employment_status`, `monthly_rent`, `other_fixed_expenses`, `monthly_saving_capacity`, `saving_goal`, `saving_period`.
- 추가 확인 개념: 가구원 수·공식 가구 소득·자산·주거 형태 등. 위 이름은 기획 개념이며 실제 API 필드·enum은 기존 스키마를 확인한다.
- 생활비 계산 소득과 공식 정책 소득 기준은 별개다. 학생 여부와 취업 여부도 별개다.
- 예금은 이미 보유한 목돈, 적금은 월 납입금 기준을 사용한다. 빈 입력/null과 0원을 같게 처리하지 않는다.
- 기본적으로 로그인 없이 이용하며 개인 소득·지출을 영구 저장하거나 외부 AI에 보내지 않는다. 관심·체크리스트는 브라우저에 사업 ID 등을 저장하며 개인 금융 프로필과 구분한다.

### 범위 밖

대출·주식·투자·보험 추천, 실제 상품 가입·정책 자동 신청, 계좌 연결, 복잡한 인증을 추가하지 않는다. 유료 서버·API·구독·모델 다운로드를 임의로 신청하지 않는다. ‘모든 상품·전국 모든 사업을 빠짐없이 제공한다’고 광고하지 않는다.

## 3. 현재 구현과 미완료를 구분한 상태표

| 영역 | 확인된 상태 | 제한 |
| --- | --- | --- |
| 공개 사이트 | React 정적 사이트, 기존 Sites v25 배포 | 상시 Python/LLM 서버 아님 |
| 지역 탐색 | 지역 선택지 268개, 지원사업·모집 안내 416건 | 고유 정책 수·전국 전수 수와 다름 |
| 모집 현황 | 2026-11-03 당시 공식 접수 확인 257건 | 오늘도 접수 중이라고 일괄 주장 금지 |
| 조건 탐색 | 지역·나이·취업·월세 조건, 검색·분야·모집 필터 | 미확인 조건 UNKNOWN 유지 |
| 사업 활용 | 관심 저장, 최대 3개 비교, 준비 체크리스트·일정 기능 | 신청·선정·수급 보장 아님 |
| 금융 목록 | 46개 금융회사, 상품·가입유형 상세 326개 | 채널/유형 포함, 고유 상품 326개 또는 전체 상품 아님 |
| 금융 재검증 | 11/6 현재 안내 재확인 108개, 기본금리 근거 57개 | 57개 모두가 누구에게나 추천되는 것은 아님 |
| 금융 미확인 | 보류 63개, 이번 내용 재확인 미완료 155개 | 접속 실패를 판매 종료로 단정하지 않음 |
| 자료 기한 | 갱신 상품 2026-11-13까지, 미갱신 과거 자료는 기존 11/6까지 | 만료 상품 추천 차단, 날짜만 바꿔 연장 금지 |
| 로컬 정책/예산 | 합성 정책 3개 판정, Cashflow, What-if | 공개 사이트 상시 API로 제공되지 않음 |
| 적금 계산 | M3.2 합성 적금 계산 구현 | 실제 상품 만기 계산 연결 0개 |
| AI 설명 | 로컬 Provider·정확 후보 검사·검증·Fallback 구현 | 기본값 NoProvider 정형 설명, 공개 상시 LLM 아님 |
| 실제 지원금 | 검증되지 않은 실제 정책 지원금 Cashflow 반영 0원 | 정책 목록을 지원금 확정으로 연결 금지 |
| 실제 정책 엔진 | 안산 실제 정책 DRAFT / CONDITION_SLICE | 전체 자격 판정 승인 아님 |
| 거주 이력 | OFFICIAL_INQUIRY_REQUIRED | 공식 답변 없이 거주기간 로직 구현 금지 |
| 사용자 평가 | A/B 과제 8개 준비, 실제 응답 확보 기록 0건 | 이해도 개선·AI 우위 미검증 |
| 자동 갱신/알림 | 로컬 모니터·WebPush 코드와 과거 기기 확인 기록 존재 | 공개 사이트 PC-off 상시 갱신·방문자 푸시·이메일 없음 |

추천 순서는 **전액 납입 가능한 후보(FIT) → 일부 납입 후보(PARTIAL)**를 구분하고 같은 상품 종류·기간에서 검증된 기본 연이율을 비교한다. 우대 최고금리 충족을 가정하거나 예금과 적금의 이율만으로 섞어 순위를 만들지 않는다. 실제 만기 이자·세후 수익 순위라고 표시하지 않는다.

지역 사업이 없으면 해당 사용자가 검토할 수 있는 광역·전국 사업이 무관한 다른 시군구 사업보다 먼저 오도록 한다. 다만 지역이 맞아도 공식 소득 등 미확인은 남긴다.

## 4. 반드시 유지할 엔진 계약

1. 정책 조건별 `PASS / FAIL / UNKNOWN`. 표시 상태는 ‘이용 가능성 높음 / 추가 확인 필요 / 현재 조건과 맞지 않음’. 법적 신청·수급 확정 표현을 쓰지 않는다. 집계 우선순위·연산은 기존 구현과 테스트를 따른다.
2. 정책 비교·월 예산·금융 필터·수학 계산·What-if 차이는 Python 책임이다. LLM이 직접 자격·금액·금리를 만들지 않는다.
3. AI는 허용된 설명 후보를 선택하고 정확 일치 검사와 기존 Output Validator를 거친다. 실패하면 **전체 정형 설명**으로 대체한다.
4. 기존 제한: Provider 6초, 서비스 8초, 화면 12초, 응답 최대 32KiB. 품질·속도 개선을 이유로 완화하지 않는다.
5. M3.2 합성 계산은 정수 개월·반올림 계약이다. IBK 공식 규칙의 실제 일수/365·원 미만 절사와 다르다. 날짜·납입일·만기일·독립 은행 기대금액이 함께 있는 사례 미확보 상태다. IBK 이메일에서는 답변 제공이 어렵다는 사용자 회신이 있었다. 가상 계산을 은행 정답으로 포장하지 않는다.
6. Coverage Core freeze, Acceptance/Historical 계약, 실제 release 6개, GV01~GV15·BV01~BV16 및 관련 golden/fingerprint를 보호한다. UI·목록 작업 때문에 기반 프레임워크를 다시 설계하지 않는다.
7. M2.77은 `HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY`. 실제 Windows NTFS 파일 symlink 거부 필수 시험이 권한 문제로 미완료다. mock·skip을 실제 보안 검증 완료로 바꾸거나 Developer Mode·관리자 권한·보안 설정을 자동 변경하지 않는다.
8. 참가자·응답·분석 결과를 생성하지 않는다. 처음 5명 목표였지만 사용자는 이후 P01~P03 3명 계획과 직접 사용 점검을 논의했다. 실제 평가 완료 또는 사람 40명의 응답처럼 주장하지 않는다.

## 5. 구조와 실제 수정 위치

```text
frontend/
  src/                 React 화면·조건 입력·결과 표시
    public-data/       Python 검증 후 공개하는 날짜별 스냅샷
    test-fixtures/     과거 기준 재현용 동결 데이터
backend/
  policy_engine/       정책 모델·로더·조건 평가·전용 판정 연결
  cashflow/            월 예산 계산
  finance/             금융 필터·추천·검증·갱신 자료 조합
  explanation/         정형 설명·로컬 Provider·후보/출력 검사
  opportunities/       지원사업 자료·조건 탐색
  asset_alerts/        로컬 모니터·알림 구현
  web/                 FastAPI 스키마·서비스·라우터
data/
  financial-products/ 공식 상품 구조화 근거·재검증 배치
  releases/            보호 대상 실제 release
tests/                 Python 계산·계약·골든 검증
tools/                 공개 데이터 생성·공식 출처 점검
docs/                  기획·설계·마일스톤·검증·출처 기록
```

| 작업 | 우선 읽을 파일 |
| --- | --- |
| 진입·라우팅·첫 화면 | `frontend/src/App.tsx`, `PortalShell.tsx`, `portal-routing.ts` |
| 지원사업·정렬·조건 결과 | `RegionalPrograms.tsx`, `SupportPlanner.tsx`, `FinderDialog.tsx`, `support-order.ts` |
| 예·적금·추천·비교 | `ProductExplorer.tsx`, `RecommendationShelf.tsx`, `ProductComparisonPanel.tsx` |
| 기한·입력·오류 처리 | `financial-snapshots.ts`, `DataFreshness.tsx`, `GroupedInput.tsx`, `ConditionPrompt.tsx`, `ErrorBoundary.tsx` |
| 디자인 | `styles.css`, `portal.css`, `launch-design.css`와 각 화면 CSS |
| 금융 결정/추천/갱신 | `backend/finance/discovery.py`, `recommendation.py`, `renewal.py` |
| API | `backend/web/app.py` 및 이 파일이 불러오는 라우터·스키마 |
| 갱신 도구 | `tools/build_financial_renewals.py`, `tools/check_financial_sources.py` |

표에서 경로를 생략한 화면 파일은 `frontend/src/` 아래다. 로컬 API에는 `GET /api/health`, `POST /api/synthetic/simulate`, `/api/synthetic/compare`, `/api/synthetic/savings/recurring`이 있다. 요청 JSON은 기존 스키마를 확인하며 임의로 새 API 형식을 만들지 않는다.

대표 공개 데이터는 `frontend/src/public-data/`의 `current-support-web.json`, `nationwide-districts.json`, `product-expanded.json`, `product-recommendations.json`, `financial-renewals.json`, `financial-sales-ended.json`, `release-summary.json`이다. 과거 원본을 오늘 자료처럼 덮어쓰지 않는다.

## 6. 개발 환경과 실행

기존 기준은 Python 3.12, Node.js 22.12 이상, `frontend/package.json`의 pnpm 11.25.0이다. 잠금 파일을 사용하고 인수인계만을 위해 라이브러리를 업그레이드하지 않는다.

### 공개 화면만 실행 — 권장 첫 단계

Windows PowerShell에서:

```powershell
git clone https://github.com/rladudwns559-cmyk/youth-life-planner.git
cd youth-life-planner
git switch -c claude/next-iteration
cd frontend
corepack pnpm install --frozen-lockfile
$env:VITE_PUBLIC_BACKEND_PENDING='true'
corepack pnpm dev
```

http://127.0.0.1:5173/ 을 연다. `corepack`이 없으면 지정 버전 pnpm을 준비해 `pnpm` 명령을 사용한다. 관리자 권한의 전역 변경을 필수 절차로 만들지 않는다. 이미 받은 저장소는 미커밋 변경을 먼저 확인하고 보관한 뒤 최신 내용을 가져온다. `reset --hard`나 강제 push를 사용하지 않는다.

환경변수는 Vite 실행 전에 설정한다. 지속 설정은 로컬 `frontend/.env.local`에 적을 수 있으나 커밋하지 않는다. 공개 화면 실행에 Python·DB·모델·은행 계정은 필요 없다.

### 로컬 Python 기능도 실행

저장소 루트의 별도 터미널:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8100 --no-access-log
```

프런트엔드 터미널에서 `VITE_PUBLIC_BACKEND_PENDING`을 `false`로 설정하고 개발 서버를 다시 실행한다. `/api`는 Vite가 8100으로 전달한다. 기본 NoProvider를 사용하며 LLM 재설치·다운로드·실행은 필요 없다. DB 연결도 기본 실행의 필수가 아니다.

### 검증 명령

```powershell
# 저장소 루트, 개발 의존성 설치 후
.\.venv\Scripts\python.exe -X utf8 -m pytest -q -p no:cacheprovider
# frontend 폴더
corepack pnpm test --maxWorkers=1
corepack pnpm build
```

기준일의 **이전 실제 실행 기록**: Backend **12,875 passed / 1 skipped / 1 warning**, Frontend **414 passed / 36 files**, TypeScript·Vite build 성공. skip은 실제 NTFS symlink 증거 미완료이며 기존 경고와 Vite 대형 청크 경고가 남아 있다. 새 환경에서 위 결과를 재실행한 것처럼 보고하지 않는다.

화면 확인 경로는 `/#/`, `/#/programs`, `/#/programs/list`, `/#/savings`, `/#/guide`다. `/#/budget`은 공개 모드에서 상품 찾기로 이동하며 로컬 API 기능과 구분한다. 모바일 크기 점검은 실제 휴대폰 검증과 구분한다.

## 7. 공식 자료 갱신·추천 운영 원칙

필독: [최신 금융 재검증](FINANCIAL_RECHECK_20261106.md), [반복 점검 절차](FINANCIAL_RECHECK_WORKFLOW.md).

- HTTP 200·HTML 해시·URL 연결 성공은 현재 판매·가입 조건·금리 검증과 다르다. 기존 점검 354개 URL 중 347개 접속 성공은 347개 상품 승인 수가 아니다.
- 공식 은행/지자체 자료의 기준일·확인일·모집기간·대상·납입한도·금리 조건·URL·문서 근거를 남긴다. 다른 회사 약관을 같은 상품 근거로 쓰지 않는다.
- 기본금리와 우대 최고금리를 분리한다. 자동 우대 충족 가정 금지. 조건이 모호한 상품은 비교 참고/보류로 남긴다.
- 접속 실패는 확인 불가이며 판매 종료 증거가 아니다. 종료는 공식 종료 근거가 있을 때 반영한다.
- 기존 7일 검토 기한을 유지한다. 실제 내용을 확인하지 않고 날짜만 갱신하지 않는다. 최신 근거가 보류·만료이면 과거의 높은 금리를 복원하지 않는다.
- 갱신 입력은 `data/financial-products/renewals/20261106/` 등 날짜별로 보존하고 기존 Python 경로로 공개 자료를 생성한다. 정확한 명령·스키마는 반복 점검 문서를 따른다.
- 현재 페퍼 정기예금 12~17개월은 기본 3.80%/조건부최고 3.95%로 정정됐다. 우대 포함 3.95%를 기본으로 되돌리지 않는다. 부림 제한 고객용 4.10% 공시 존재는 일반 추천 허용과 다르다. 이 예들은 과거 정정 기록이며 미래 금리는 다시 확인한다.
- 지원사업 추가 시 공식 신청 페이지의 실제 접수 여부와 대상 지역·나이·취업·주거 조건을 확인한다. 지원 규모·모집 차수·가입유형 중복을 고유 정책 수로 부풀리지 않는다.
- 대표 조건·경계 입력에서 추천 ID·기본금리·FIT/PARTIAL·지역 우선순위·UNKNOWN·만료 차단을 검증한다. 화면 양쪽의 추천 순서도 같아야 한다.

## 8. 공개 배포·협업·로컬 기록

GitHub와 Sites는 별도다. **GitHub push만으로 공개 사이트가 자동 갱신되지 않는다.** 현재 화면 v25의 Sites 소스 커밋은 `dcb490cce41b85e6894f06e2954ee60211e8a111`이며 GitHub 커밋과 저장소가 다르다. [배포 기록](PUBLICATION.md)을 확인한다.

Claude 환경에는 기존 Sites 계정·도구·인증이 전달되지 않는다. 배포 접근이 없다면 실행·테스트·빌드와 변경 내역까지 준비하고 접근 한계를 정확히 알린다. 토큰을 코드/문서/채팅에 붙여 넣도록 요구하지 않는다. 기존 공개 URL을 임의의 새 사이트로 대체하지 않는다.

친구가 디자인을 수정할 예정이므로 브랜치/PR로 협업한다. 작업 전 원격 변경을 확인하고 무관한 디자인·기능을 덮어쓰지 않는다. 공개 저장소 읽기 권한과 직접 push 권한은 별개다.

기존 Codex에는 매일 09:00 KST 금융자료 점검 작업이 등록됐다는 기록이 있다. 이는 PC·Codex 실행이 필요한 로컬 작업이며 GitHub나 Claude로 이전되지 않는다. 이 문서 작성 때문에 중지하거나 이전한 것은 아니다. Claude와 동시에 같은 원본을 수정하지 않도록 사용자가 실행 주체를 정해야 한다.

기존 PC의 경로(다른 환경에 있다고 가정하지 말 것):

- 개발 원본: `C:/Users/김영준/Documents/ChatGPT/ai+x`
- 공개 Git 복사본: `C:/Users/김영준/Documents/ChatGPT/AI+X채팅/github/youth-life-planner`
- Sites 작업 복사본: `C:/Users/김영준/Documents/ChatGPT/AI+X채팅/deploy/young-life`
- Obsidian: `C:/Users/김영준/Documents/Obsidian/AI+X-Project`

같은 PC에서 Obsidian을 갱신할 때는 [기존 Workflow](OBSIDIAN_WORKFLOW.md)를 따른다. 클라우드 Claude가 Vault를 갱신할 수 없다면 작성할 기록을 전달하고 갱신했다고 주장하지 않는다. 기존 GUI·북마크 확인 미완료 상태는 별도로 유지한다. 모델 바이너리·비밀정보·실제 응답·은행 계정은 GitHub에 추가하지 않는다.

## 9. 다음 개발 우선순위와 완료조건

### P0 — 인수인계 검증과 만료 자료 정리

기존 실행 경로·검증 기준을 확인한다. 다음으로 만료/보류 자료 중 공식 근거 확보가 가능한 **10~20개 정도의 작은 묶음**을 골라 재확인한다. 불확실한 자료를 억지 추천하지 않는다.

완료조건: 변경 전후 근거·확인일·기한·추천 포함/제외 이유가 기록되고, 미확인/만료 차단과 기존 금액·정책 상태가 보존되며, 관련 시험과 필요한 회귀·빌드를 실제 실행한다. 실패를 숨기지 않는다.

### P1 — 추천이 이해되는 화면과 지역 추천 정확성

추천 근거·확인일·우대 조건·추가 확인을 읽기 쉽게 한다. 지역 공고가 없는 경우 광역·전국 사업 우선, 입력 미완성 안내, 목록/조건 창 추천 일치, 비교·관심 기능을 점검한다. 친구 디자인과 변경 범위를 조정한다.

완료조건: 대표 지역/입력과 경계 조건에서 순서·필터·빈 결과·모바일·키보드 사용을 확인하고 사업 수나 수익을 과장하지 않는다. 전체 UI를 다시 쓰는 것이 목적은 아니다.

### P2 — 근거 확보 후 확장

공식 날짜별 독립 기대금액을 확보한 뒤 실제 상품 계산의 최소 설계를 별도 검토한다. 실제 사람 평가가 필요하면 동의한 사람의 응답만 분석한다. PC-off 운영/알림은 별도 무료 운영 가능성·보안·서버 실행 구조를 검토하며 현재 제공 기능으로 표시하지 않는다.

위 우선순위는 인계 제안이다. 사용자가 새 작업을 지정하면 그 작업을 우선한다. 논리 모순·보안 위험·범위 초과가 발견되면 영향과 최소 수정안을 먼저 설명한다.

## 10. 먼저 읽을 문서

1. 이 인계서와 [README](../README.md)
2. [최신 금융 재검증](FINANCIAL_RECHECK_20261106.md) · [반복 점검](FINANCIAL_RECHECK_WORKFLOW.md)
3. [디자인 인계](FRONTEND_DESIGN_HANDOFF.md) · [제품 품질 점검](PRODUCT_QUALITY_REVIEW_20261106.md)
4. [데이터 모델](DATA_MODEL.md) · [정책 Rule 계약](POLICY_RULE_SPEC.md) · [Coverage freeze](ELIGIBILITY_COVERAGE_CORE_FREEZE.md)
5. [실제 상품 계산 보류 근거](M3_5_OFFICIAL_DATED_SAVINGS_VERIFICATION.md) · [실제 모델 R2 진단](M3_8F_R2_MATCHED_PRELOAD_RETEST.md)
6. [Obsidian 기록 방식](OBSIDIAN_WORKFLOW.md) · [공개/배포 방식](PUBLICATION.md)

과거 설계·마일스톤 수백 개를 모두 재설계하느라 첫 작업을 미루지 말고 변경 대상과 직접 연결된 계약부터 읽는다.

## 11. 사용자용 — Claude에 그대로 보낼 시작 지시문

> 기존 AI+X ‘청년 경제생활 의사결정 시뮬레이터’를 이어서 개발해 줘. 새로 만들지 말고 첨부한 인계서를 먼저 읽어 줘.
>
> 코드 저장소: https://github.com/rladudwns559-cmyk/youth-life-planner
>
> 인계서: https://github.com/rladudwns559-cmyk/youth-life-planner/blob/main/docs/CLAUDE_HANDOFF.md
>
> 운영 화면: https://youth-life-planner.rladudwns559.chatgpt.site/
>
> 먼저 저장소 접근·현재 커밋·기존 변경을 확인하고, 공개 프런트엔드를 실행해 현재 상태를 파악해 줘. 기획과 실제 구현의 차이, 실행 결과, 우선 보완할 문제를 한국어로 간단히 보고한 뒤 기존 구조 안에서 공식 금융자료 재확인과 추천 정확성 개선을 작은 단위로 이어가 줘. 근거가 확보된 자료만 반영하고 관련 시험·회귀·빌드를 실제 확인해 줘.
>
> Python 계산값·정책 상태·UNKNOWN·검증기·시간 제한·전체 정형 Fallback과 기존 freeze/golden/release를 유지해 줘. 실제 은행상품 만기 계산 0개, 미승인 실제 지원금 반영 0원, 공개 상시 API/알림 미제공 상태를 임의로 해제하지 마. 친구의 디자인 변경을 보존하고 유료 서비스·모델 설치·외부 문의·새 배포 계정 생성은 임의로 진행하지 마. 배포 접근이 없으면 빌드와 인계까지 준비하고 미배포라고 정확히 보고해 줘. 저장소를 읽거나 실행할 수 없는 환경이면 그 한계를 먼저 말하고 실행했다고 주장하지 마.

인계서와 코드만으로 시작할 수 있도록 작성했지만, 새 환경의 저장소 접근·의존성 설치·배포 권한은 실제로 확인해야 한다. 이 문서 전달 자체가 계정 인증이나 로컬 파일·자동화의 이전은 아니다.

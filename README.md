# 청년 경제생활 의사결정 시뮬레이터

청년이 자신의 조건에 맞는 정부·지자체 지원사업과 예·적금 상품을 살펴보고, 생활비와 저축 계획의 변화를 비교하는 웹서비스입니다.

초기 검증 지역은 안산이며 서비스 대상은 전국 청년입니다.

## 처음 오셨다면 (2026-11-07 기준)

**이 저장소의 `main`이 가장 최신입니다.** 최신 화면은 아래 "팀원 빠른 실행"으로 직접 실행해서 확인하세요. 이전에 올렸던 chatgpt.site 사이트는 2026-11-06 버전에서 멈춰 있고 더 이상 갱신하지 않습니다. 발표용 화면은 Claude 페이지로 올려 두었으며, 비공개라서 소유자가 Share로 공유해야 볼 수 있습니다([올리는 방법](docs/CLAUDE_ARTIFACT_PUBLISH.md)).

읽는 순서:

1. [팀 업데이트 2026-11-07](docs/TEAM_UPDATE_20261107.md) — 무엇이 바뀌었고 어떻게 실행하는지
2. [디자인 작업 안내](docs/FRONTEND_DESIGN_HANDOFF.md) — 화면만 수정할 때 (Python·LLM 설치 불필요)
3. [프로젝트 전체 인계서](docs/CLAUDE_HANDOFF.md) — 기획, 구현 현황, 지켜야 할 계약
4. [금융자료 재확인 기록](docs/FINANCIAL_RECHECK_20261107.md)과 [주간 재확인 계획](docs/WEEKLY_RECHECK_PLAN_202611.md) — 추천 자료의 기한(11/13)
5. [문서 안내](docs/README.md) — 나머지 문서와 `docs/archive`(과거 작업 기록)

## 현재 구현

- 268개 지역 선택지, 지역·나이·취업·월세 조건별 지원사업 탐색
- 지원사업·모집 안내 416건, 2026-11-03 당시 공식 접수 확인 257건
- 지원사업 목록 검색, 분야·모집 필터, 관심 저장, 최대 3개 사업 비교
- 공식 자료를 확인한 46개 금융회사 예·적금 상품/가입유형 상세 326개, 금액·기간 비교 및 기본금리 우선 추천
- 숫자 입력 천 단위 쉼표, 빈 조건 입력 안내
- 로컬 FastAPI 합성 정책 3개 판정, 생활비 계산, What-if, 합성 적금 계산
- Python 결과 기반 설명·검증·정형 Fallback. 기본값은 외부 모델 없는 정형 설명

공개 사이트는 준비된 데이터를 쓰는 프런트엔드입니다. Python API와 로컬 LLM이 상시 운영되는 배포가 아니며, 자동 정보 갱신·상시 푸시는 현재 공개 서비스에서 제공하지 않습니다.

추천 카드의 순서는 전액 납입 가능성→같은 상품 종류·기간의 검증된 기본금리입니다. 우대 최고금리나 실제 만기금액 순위로 표시하지 않습니다. 2026-11-07 기준 공식 자료로 123개 상품·가입유형을 재확인했고 72개에서 기본금리 근거를 확보했습니다. 입력 조건과 보류 사유에 따라 추천 후보 수는 달라지며, 납입 상한이 공시에 없는 상품은 금리를 확인했어도 추천 후보에서 제외됩니다. 재확인 상품은 확인일 + 7일(11월13일~14일)까지, 미갱신 과거 자료는 기존 11월6일 기한을 적용합니다. 만료·판매 미확인·종료 상품은 추천하지 않습니다. [최신 금융 재검증 기록](docs/FINANCIAL_RECHECK_20261107.md) · [반복 점검 절차](docs/FINANCIAL_RECHECK_WORKFLOW.md).

## 데이터와 계산

정책 조건은 PASS / FAIL / UNKNOWN으로 판단합니다. 신청·수급을 확정하지 않습니다. 생활비 소득과 정책의 공식 소득 기준은 다릅니다. 소득·재산·과거 근로·세대 구성 등 미확인 조건은 추가 확인입니다.

실제 지원금 Cashflow 반영은 0원, 실제 은행상품 만기 계산 연결은 0개입니다. 합성 적금 계산을 실제 상품 계산으로 취급하지 않습니다. 실제 안산 정책은 DRAFT / CONDITION_SLICE, 거주기간은 OFFICIAL_INQUIRY_REQUIRED입니다.

모집 현황은 자료 확인일 기준 스냅샷입니다. 전국 모든 사업·상품을 망라하지 않으며 변경·예산·정원·자격은 공식 신청처에서 확인해야 합니다.

## 팀원 빠른 실행

Python 3.12, Node.js 22.12 이상, pnpm 11.25.0 기준입니다.

~~~powershell
git clone https://github.com/rladudwns559-cmyk/youth-life-planner.git
cd youth-life-planner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8100 --no-access-log
~~~

별도 터미널에서:

~~~powershell
cd youth-life-planner/frontend
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm dev
~~~

브라우저 http://127.0.0.1:5173 · API http://127.0.0.1:8100/api/health

API 없이 공개 화면만 실행하려면 frontend 터미널에서:

~~~powershell
$env:VITE_PUBLIC_BACKEND_PENDING='true'
corepack pnpm dev
~~~

개인 소득·월세·계좌정보나 실제 사용자 응답은 저장소에 올리지 마세요. 키·비밀번호는 로컬 .env 등으로 관리합니다.

## 검증

2026-11-07 Backend 12,877 passed / 1 skipped / 1 warning, Frontend 414 passed 및 TypeScript/Vite build 성공을 확인했습니다(자세한 범위는 [팀 업데이트](docs/TEAM_UPDATE_20261107.md)). 프런트엔드 `ProductExplorer` 시험은 PC 부하가 클 때 5초 제한을 넘겨 간헐적으로 실패할 수 있으며, 다른 작업 없이 다시 돌리면 통과합니다.

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
corepack pnpm test --maxWorkers=1
corepack pnpm build
~~~

실제 HTTP 통합 검증은 API를 실행한 뒤 frontend에서 pnpm test:http로 실행합니다. 로컬 모델 다운로드·실행은 기본 테스트에 필요하지 않습니다.

## 구조와 협업

- frontend/: React·TypeScript, 공개 데이터, UI 테스트
- backend/: Policy·Cashflow·Coverage·Acceptance·Historical 및 API
- data/: 공식 출처를 기록한 스냅샷과 합성 정책
- tests/: Python 계약·경계·회귀 테스트와 합성 fixture
- tools/: 데이터 준비·설명 검증 도구
- docs/: 현재 기준 문서(위 읽는 순서)와 설계 명세. 과거 마일스톤·운영 기록은 `docs/archive/`

기획은 docs/archive/PROJECT_PLAN.md와 docs/ARCHITECTURE.md를 참고하세요. `docs/archive/`는 당시 이력이며 현재 현황은 이 README와 최신 문서가 기준입니다. 실험 폴더의 private는 합성 과제 정답·배정용 이름이며 실제 참가자 응답을 포함하지 않습니다.

기능별 브랜치와 Pull Request로 검토하는 방식을 권장합니다. 누구나 읽을 수 있으며 팀원의 직접 push 권한 초대는 소유자가 별도로 설정할 수 있습니다.

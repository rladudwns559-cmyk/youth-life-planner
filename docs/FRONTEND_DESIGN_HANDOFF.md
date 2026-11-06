# 프런트엔드 디자인 작업 안내

2026-11-06 갱신. 현재 공개 화면을 로컬에서 실행하고 디자인을 수정하기 위한 안내입니다. 최근 변경은 [제품 품질 검토](PRODUCT_QUALITY_REVIEW_20261106.md)를 참고하세요.

2026-11-07 금융자료 재확인: [공식 금융 재검증](FINANCIAL_RECHECK_20261106.md). 날짜별 조회는 `financial-snapshots.ts`, 새 자료는 `public-data/financial-renewals.json`입니다. 기존11월3일 JSON은 역사 자료로 보존합니다. 갱신 기한을 CSS/문구 수정으로 늘리지 않습니다. 최신 전체 UI 검증은414 passed입니다.

- 저장소: https://github.com/rladudwns559-cmyk/youth-life-planner
- 공개 사이트: https://youth-life-planner.rladudwns559.chatgpt.site/
- 구성: React + TypeScript + Vite, 일반 CSS
- 화면만 수정할 때 Python·DB·로컬 LLM·은행 계정·유료 서비스는 필요하지 않습니다.

## 1. 화면만 실행하기

Node.js와 `frontend/package.json`에 지정된 pnpm 환경을 준비합니다. 기존 프로젝트 기준은 Node.js 22.12 이상, pnpm 11.25.0입니다. 아래는 **Windows PowerShell**용입니다. `corepack`이 없는 환경에서는 지정 버전 pnpm을 준비한 뒤 `corepack pnpm` 대신 `pnpm`을 사용합니다.

```powershell
git clone https://github.com/rladudwns559-cmyk/youth-life-planner.git
cd youth-life-planner
git switch -c design/frontend-refresh
cd frontend
corepack pnpm install --frozen-lockfile
$env:VITE_PUBLIC_BACKEND_PENDING='true'
corepack pnpm dev
```

브라우저에서 http://127.0.0.1:5173/ 을 엽니다. 환경변수는 공개 사이트와 같은 프런트엔드 모드를 켭니다. 터미널을 새로 열면 개발 서버 실행 전에 다시 설정합니다. 지속 적용하려면 로컬 `frontend/.env.local`에 `VITE_PUBLIC_BACKEND_PENDING=true`를 적어도 됩니다. `.env.local`은 커밋하지 않습니다.

이미 받은 저장소라면 작업 내용을 커밋하거나 보관한 다음 `main`에서 `git pull --ff-only`로 최신 내용을 받고 디자인 브랜치를 만듭니다. 다른 사람의 변경을 덮어쓰는 강제 push는 사용하지 않습니다.

## 2. 먼저 볼 화면

| 주소 | 화면 | 확인할 점 |
| --- | --- | --- |
| `/#/` | 첫 화면 | 메뉴, 서비스 카드, 주요 버튼, 모바일 배치 |
| `/#/programs` | 청년지원사업 진입 | 조건 찾기와 전체 목록으로 들어가는 흐름 |
| `/#/programs/list` | 지원사업 목록 | 검색, 분야·모집 필터, 비교·관심 저장 |
| `/#/savings` | 예·적금 찾기 | 금액·기간 입력, 추천 카드, 상세·비교 |
| `/#/guide` | 이용 안내 | 기능 범위와 자료 확인일·미완료 기능 설명 |

공개 모드에는 상시 Python 서버와 로컬 모델 연결이 없습니다. 생활비 계산·What-if 등 로컬 API 기능도 수정해야 하면 [README](../README.md)의 별도 백엔드 실행 절차를 사용합니다. 공개 모드에서 `/#/budget`은 상품 찾기로 이동합니다.

## 3. 화면별 수정 파일

경로는 저장소 루트 기준입니다. 먼저 화면 컴포넌트와 대응 CSS를 함께 살펴보세요.

| 작업 | 주요 파일 |
| --- | --- |
| 화면 조합·페이지 연결 | `frontend/src/App.tsx` |
| 상단 메뉴·첫 화면·푸터·페이지 제목 | `frontend/src/PortalShell.tsx`, `frontend/src/portal.css` |
| 브랜드·공통 안내 | `frontend/src/ServiceShell.tsx` |
| 전역 글꼴·색상·입력·버튼 | `frontend/src/styles.css` |
| 현재 디자인의 추가 스타일 | `frontend/src/launch-design.css` |
| 지원사업 페이지·목록 | `frontend/src/RegionalPrograms.tsx`, `frontend/src/regional-programs.css` |
| 조건 선택·체크리스트·사업 비교 | `frontend/src/SupportPlanner.tsx` |
| 조건 검색 결과 창 | `frontend/src/FinderDialog.tsx`, `frontend/src/finder-dialog.css` |
| 지역 결과 건수 안내 | `frontend/src/LocalNotice.tsx` |
| 예·적금 검색·목록 | `frontend/src/ProductExplorer.tsx`, `frontend/src/product-explorer.css` |
| 금융 추천 카드 | `frontend/src/RecommendationShelf.tsx` |
| 금융상품 비교 패널 | `frontend/src/ProductComparisonPanel.tsx` |
| 숫자 입력과 천 단위 쉼표 | `frontend/src/GroupedInput.tsx` |
| 해시 경로·페이지 전환 효과 | `frontend/src/portal-routing.ts` |
| 자료 확인일·기한 안내 | `frontend/src/DataFreshness.tsx`, `frontend/src/data-freshness.css` |
| 화면 오류 복구 | `frontend/src/ErrorBoundary.tsx` |

`main.tsx`가 전역 `styles.css`를 불러오고, `App.tsx`와 각 화면이 추가 CSS를 불러옵니다. 같은 요소에 여러 스타일이 적용될 수 있으므로 개발자 도구에서 실제 적용 규칙을 확인합니다.

## 4. 디자인 변경 중 유지할 동작

- 입력, 검색, 필터, 추천 순서, 비교 선택, 관심 저장, 상세·닫기 버튼이 계속 동작해야 합니다.
- 금리·금액·모집일·공식 출처·추천 근거·추가 확인 표시는 실제 데이터와 대응해야 합니다.
- UNKNOWN을 충족 또는 신청 확정으로 바꾸지 않습니다. 설명을 줄여도 불확실성과 공식 확인 안내는 유지합니다.
- 원금·세전이자·우대 최고금리·기본금리를 혼동하는 문구를 사용하지 않습니다. 실제 금융상품 만기 계산 연결은 현재 0개입니다.
- `frontend/src/public-data/`의 JSON은 준비된 자료입니다. 카드 디자인을 위해 공식 수치나 상태를 직접 바꾸지 않습니다.
- 디자인 작업에서 `backend/`, 원본 `data/`, golden fixture, release 파일, 정책·계산·검증 계약을 함께 수정하지 않습니다. 별도 기능 변경이 필요하면 PR에서 구분해 설명합니다.

자료는 확인일 기준 스냅샷입니다. 11월 3일 확인한 접수 건수를 오늘도 접수 중인 수로 표시하지 않습니다. 금융 추천 스냅샷의 현재 유효기간은 2026-11-06이며 디자인 작업이 이를 연장하지 않습니다.

## 5. 수정 후 확인 순서

1. 데스크톱과 약 390px 모바일 폭에서 첫 화면·지원사업·상품 찾기를 확인합니다. 가로 잘림, 겹친 버튼, 긴 사업명도 살펴봅니다.
2. 조건을 비워 찾기를 눌렀을 때 입력 안내가 나오는지, 입력 후 결과 창과 지역별 건수가 읽히는지 확인합니다.
3. 지원사업 검색·필터·비교·관심 저장과 상품 금액·기간 입력·추천·비교를 확인합니다. 공식 링크도 열어 봅니다.
4. 숫자 입력의 쉼표와 커서, 키보드 Tab 이동·포커스 표시, 결과 창 닫기, 뒤로 이동을 확인합니다.
5. 페이지 전환 효과와 결과 창을 확인하고, 동작 줄이기 설정에서도 사용할 수 있는지 살펴봅니다.
6. `frontend` 폴더에서 아래 검증을 실행합니다.

```powershell
corepack pnpm test --maxWorkers=1
corepack pnpm build
```

`build`에는 TypeScript 검사가 포함됩니다. 기존 기대값을 무조건 바꾸지 말고 실패가 접근성·문구·실제 기능 중 무엇 때문인지 확인합니다. 2026-11-06 실제 프런트엔드 전체 회귀는 406 passed였습니다.

## 6. 변경 공유

직접 push 권한이 있다면 작업 브랜치를 push하고 `main`을 대상으로 Pull Request를 만듭니다. 권한이 없다면 GitHub에서 Fork한 저장소에 작업하고 원본으로 Pull Request를 보내면 됩니다.

PR에는 바꾼 화면, 데스크톱·모바일 전후 화면, 실행한 테스트 결과를 적어 주세요. 설치 파일·`node_modules/`·`.env.local`·개인정보는 포함하지 않습니다.

**이 저장소에 push하거나 PR을 병합해도 현재 Sites 웹사이트가 자동 배포되지는 않습니다.** 디자인을 검토·검증한 뒤 별도로 공개 사이트에 반영해야 합니다.

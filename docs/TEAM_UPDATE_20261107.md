# 팀 업데이트 2026-11-07 — 무엇이 바뀌었고 어떻게 실행하나

이 저장소의 `main`은 아래 변경까지 반영돼 있습니다. **공개 사이트(Sites)는 이 변경이 배포되기 전까지 이전 버전(v25)입니다.** GitHub에 push해도 공개 사이트는 자동으로 바뀌지 않습니다.

## 실행 (공개 화면만, Windows PowerShell)

```powershell
git pull --ff-only
cd frontend
corepack pnpm install --frozen-lockfile
$env:VITE_PUBLIC_BACKEND_PENDING='true'
corepack pnpm dev
```

http://127.0.0.1:5173/#/savings 에서 확인합니다. 자세한 안내는 [FRONTEND_DESIGN_HANDOFF.md](FRONTEND_DESIGN_HANDOFF.md).

## 바뀐 것

| 영역 | 내용 | 파일 |
| --- | --- | --- |
| 금융 자료 | 저축은행 15개(민국·동양·스마트) 공식 재확인. 재확인 108→123개, 기본금리 근거 57→72개 | `data/financial-products/renewals/20261107/`, `frontend/src/public-data/financial-renewals.json`, [기록](FINANCIAL_RECHECK_20261107.md) |
| 홈 | 주요 버튼을 바로가기 카드 위로 이동 | `PortalShell.tsx`, `polish.css` |
| 상품 찾기 | 자료 확인 안내를 숫자 칩으로 정리, 모바일에서 입력칸이 첫 화면 안으로 | `DataFreshness.tsx`, `polish.css` |
| 추천 카드 | 금리 확인일 12px로 확대, 같은 불릿 3줄을 1줄로(일부 금액 상품은 3줄 유지), "추가 확인" 칩, 글자 중간 줄바꿈 방지 | `RecommendationShelf.tsx`, `polish.css` |
| 운영 | 주간 재확인 일정과 추천 대상 체크리스트 도구 | [WEEKLY_RECHECK_PLAN_202611.md](WEEKLY_RECHECK_PLAN_202611.md), `tools/list_recommendable_products.py` |
| 사용자 점검 | 3명 사용성 점검 키트(응답 없음, 준비 자료) | `docs/experiments/public_site_usability_20261107/` |

## 디자인 담당에게

- 이번 디자인 변경은 **새 파일 `frontend/src/polish.css`** 에 모았고 `App.tsx`에서 `launch-design.css` 다음에 불러옵니다. 기존 CSS 파일은 수정하지 않았습니다. 이 파일의 규칙을 지우거나 덮어쓰면 위 변경을 되돌릴 수 있습니다.
- 시험 2개의 기대값을 새 화면 순서에 맞게 고쳤습니다(홈 주요 버튼이 마지막 자식이 아니라 바로가기 카드보다 앞에 있다는 검사). 링크 대상과 동작 검증은 그대로입니다.
- 금리·확인일·"추가 확인" 표시는 신뢰 장치이므로 줄이지 말고, 읽기 쉽게만 바꿔 주세요.

## 꼭 알아 둘 점

- **재확인 기한**: 추천 화면에 실제로 나오는 상품 50개의 기한이 **2026-11-13**입니다. 그 전에 다시 확인하고 배포하지 않으면 11/14부터 추천이 비어 보입니다. 일정은 [주간 계획](WEEKLY_RECHECK_PLAN_202611.md)을 따릅니다.
- 이번에 재확인한 15개 상품은 납입 상한이 공시에 없어 `MISSING` 판정이므로 추천에는 나오지 않습니다.
- 로컬 Codex의 매일 09:00 점검과 이 계획이 같은 `financial-renewals.json`을 수정할 수 있으니, 한 회차는 한 사람(또는 한 도구)만 수행하세요.
- 실제 은행 상품 만기 계산 0개, 검증되지 않은 지원금 0원, 사용자 평가 응답 0건이라는 한계는 그대로입니다.

## 검증 (2026-11-07, 개발 PC)

Backend 12,877 passed / 1 skipped / 1 warning · Frontend 414 passed / 36 files · `tsc -b` 및 공개 모드 `vite build` 성공. 프런트엔드 `ProductExplorer` 시험은 PC 부하가 클 때 5초 제한을 넘겨 간헐적으로 실패한 적이 있습니다(다른 작업 없이 다시 돌리면 통과). 제한 시간은 바꾸지 않았습니다.

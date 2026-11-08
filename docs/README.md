# 문서 안내

처음이라면 저장소 [README](../README.md)의 "읽는 순서"를 먼저 보세요. 이 폴더는 두 종류로 나뉩니다.

## 지금 기준으로 읽는 문서

| 문서 | 내용 |
| --- | --- |
| [TEAM_UPDATE_20261107.md](TEAM_UPDATE_20261107.md) | 최근 변경, 실행 방법, 알아 둘 점 |
| [FRONTEND_DESIGN_HANDOFF.md](FRONTEND_DESIGN_HANDOFF.md) | 화면 수정 방법과 지킬 동작 |
| [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) | 전체 기획, 구현 현황, 유지할 계약 (작성 2026-11-07 기준) |
| [FINANCIAL_RECHECK_20261107.md](FINANCIAL_RECHECK_20261107.md) · [20261106](FINANCIAL_RECHECK_20261106.md) | 공식 금융자료 재확인 기록 |
| [FINANCIAL_RECHECK_WORKFLOW.md](FINANCIAL_RECHECK_WORKFLOW.md) · [WEEKLY_RECHECK_PLAN_202611.md](WEEKLY_RECHECK_PLAN_202611.md) | 재확인 절차와 11월 주간 일정 |
| [CLAUDE_ARTIFACT_PUBLISH.md](CLAUDE_ARTIFACT_PUBLISH.md) | Claude 페이지로 올리는 방법 |
| [PRODUCT_QUALITY_REVIEW_20261106.md](PRODUCT_QUALITY_REVIEW_20261106.md) | 제품 품질 점검 기록 |
| [ARCHITECTURE.md](ARCHITECTURE.md) · [DATA_MODEL.md](DATA_MODEL.md) · [POLICY_RULE_SPEC.md](POLICY_RULE_SPEC.md) · [ELIGIBILITY_COVERAGE_CORE_FREEZE.md](ELIGIBILITY_COVERAGE_CORE_FREEZE.md) | 구조, 데이터 모델, 정책 규칙, 동결된 판정 계약 |

## 그대로 두어야 하는 명세

`BENEFIT_ACCEPTANCE_*_SPEC.md`와 `HISTORICAL_*_SPEC.md` 11개는 자동 시험이 내용을 직접 읽습니다. 옮기거나 이름을 바꾸면 시험이 실패합니다. `evidence/`와 `experiments/` 폴더도 시험과 동결 기록이 쓰므로 옮기지 않습니다.

## 과거 기록

[archive/](archive/)에는 마일스톤별 설계·검증 문서와 이전 운영 기록(Codex 시기의 배포·Obsidian 절차 포함) 약 90개가 있습니다. 당시 이력일 뿐 현재 상태의 기준이 아닙니다. 지우지 않은 이유는 판단 근거와 실패 이력을 남기기 위해서입니다. 파일 이름으로 찾으면 됩니다. 예를 들어 `M3_*`는 마일스톤, `REAL_POLICY_001_*`은 안산 정책 구현 기록, `PUBLICATION.md`는 2026-11-07까지의 공개 이력입니다.

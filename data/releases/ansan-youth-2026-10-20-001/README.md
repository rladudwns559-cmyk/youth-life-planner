# 실제 공식자료 기반 주민등록 조건 slice — DRAFT

이 경로는 기존 설계의 releases 배치를 따른다. 디렉터리 이름은 **운영 발행·승인 상태를 나타내지 않는다**.
M1.15에서 수동 확인한 실제 정책 데이터이며 `synthetic=false / test_only=false`다.
사용자 사실과 실제 신청자 정보는 저장하지 않는다.

- `sources.json`: 공식 게시물·첨부 원문 메타데이터와 짧은 의미 locator 3개.
- `policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json`: 정규화된 PolicyEnvelope 1개. root는 주민등록 leaf 하나다.
- 검증 상태: `DRAFT`, 범위: `CONDITION_SLICE`. **서비스 추천·신청·수급 승인 자료가 아니다.**
- 미구현: 연령/생년월일, 등록분류/국적/귀화일, 경기도 연속·합산 거주기간, 신청창, 자동·소급신청, 지원금 계산.
- 원본 HWP는 복제하지 않았다. 원문 URL 및 재확인한 SHA256을 sources.json에 남겼다.
- 확인일은 2026-10-20이다. 정책 페이지의 미확인 게시일과 효력 시작/종료일은 null로 유지한다.
- Manifest/review JSON은 생성하지 않았다. 배포 artifact가 없는 상태에서 가상의 엔진 hash를 넣지 않는다.

주민등록 **조건 leaf**의 PASS/FAIL/UNKNOWN만 검증한다. root의 overall_status도 이 leaf 한 개의 집계다.
`SELF_REPORTED` 테스트 입력이 실제 행정자료로 인증되었다는 뜻은 아니다.

상세 근거·한계·재실행 방법은 `docs/REAL_POLICY_001_IMPLEMENTATION.md`를 참조한다.

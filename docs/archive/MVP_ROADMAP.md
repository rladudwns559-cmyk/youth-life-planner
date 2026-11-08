# MVP 로드맵

## 1. 기획 PDF에서 확정된 요구사항

8주차 범위·데이터·규칙 설계, 9주차 판정 엔진, 10주차 현금흐름/금융/API, 11주차 기본 UI, 12주차 금융 비교/What-if, 13주차 AI, 14주차 사용자 검증, 15주차 배포·발표가 기획서의 개발 흐름이다. 전체 정책 10~12개와 금융상품 10~20개는 최종 MVP 목표다.

## 2. 이번 M1에서 승인한 결정

| 작업 | 목적/내용 | 선행조건 | 완료조건 | 검증 |
|---|---|---|---|---|
| 폴더 확인 | 기존 파일·AGENTS·PDF 확인 | 없음 | 기존 작업 보존 | 파일 확인 |
| 문서 5종 | PDF/승인/미정 구분 | 요청 확인 | 모델·명세·범위 일치 | 문서 검토 |
| 불변 도메인 | 입력·규칙·결과·컨텍스트 | 명세 | 잘못된 타입 거부 | 생성자 테스트 |
| JSON 로더 | 합성 정책 3개 | 도메인 | 잘못된 규칙을 로딩 시 거부 | JSON 오류 테스트 |
| 판정 엔진 | 비교·논리 집계·사유 | 로더 | 동일 사용자 P/F/U | acceptance 테스트 |
| 경계·논리 검증 | 오판정 방지 | 엔진 | 모든 요구 테스트 통과 | pytest |
| 실행 안내 | 재현 가능한 인계 | 엔진/테스트 | README 명령 실행 확인 | 샘플/pytest 실제 실행 |

M1 전체가 P0이다. 이번 작업은 여기서 종료한다. 승인된 합성 정책/프로필은 저장소에 보관하지만 실제 사용자 자료를 수집·저장하지 않는다.

## 3. 향후 결정해야 할 사항

- 다음 최소 작업 제안: PDF 후보 중 실제 정책 1개의 공식 공고를 읽어 조건표와 수동 기대 사례만 작성해 M1 모델의 표현 가능성을 검토한다. 이번에는 수행하지 않는다.
- 후속 P0 후보: 실제 정책 검증과 확장, 금융 계산, What-if 핵심.
- 후속 P1 후보: API, UI, AI 설명, 데이터 최신성, 사용자 검증/배포.
- P2 후보: 필요할 때 DB 이전과 성능·UX 개선.
- 실제 정책 선정과 금융 계산 기준, 전후 시나리오 의미, 데이터 수명, API 및 운영 방식은 아직 승인되지 않았다.

## 2026-10-30 정부·지자체 자산형성사업 연결

사용자 후속 요청에 따라 전국 청년 대상의 정부·지자체 적금/자산형성사업 탐색과 기초 추천을 추가했다. 안산은 기존 실제 정책 전체 조건의 첫 검증 지역이다. 기존 원기획/과거 milestone 기록은 유지한다.

공식12출처·10사업 스냅샷과 GET /api/asset-programs, POST /api/asset-programs/recommendations, React 공개목록·입력 후 추천·추가정보·What-if를 연결했다. 기존 Policy/Cashflow를 재사용하며 소득인정액/건강보험료/기준일 주민등록/가구원/선발·유지조건은 UNKNOWN이다. 모두 DRAFT / CONDITION_SLICE이며 실제 지원금0원/실제 만기 계산0개를 유지한다.

신규 backend/opportunities는 catalog/matching/changes로 분리했다. 공개 변경 이벤트는 개인 입력 없이 생성하고 NOT_SENT를 유지한다. 자동 수집/구독/실제 알림 발송은 후속 범위다. 7일 freshness는 임시 운영 Assumption이다.

전체 Backend12,463 passed / 1 skipped / 1 warning, Frontend148 passed, TS/build·실제 API/브라우저 통과. 상세: [구현·근거·검증](OFFICIAL_ASSET_PROGRAM_DISCOVERY.md), [후속 알림 계약](ASSET_PROGRAM_NOTIFICATION_CONTRACT.md).

## 2026-10-30 공식 모집 자동 확인·관심 알림

사용자의 후속 요청으로 등록 공식 출처 자동 확인·관심 지역/사업 구독·사이트 알림함·브라우저 Web Push를 연결했다. 이메일은 사용자 결정으로 제외했다. 서버 실행 중6시간 확인이며 상시 운영/전국 완전 수집은 별도 단계다. 단순200·본문 동일 검증·일정 추출·푸시 서버 접수·기기 표시는 구분한다.

알림 전용 저장소는 관심 지역/사업·수신 설정·필요한 browser subscription/기기 식별자/알림 기록만 저장한다. 소득·월세·생년월일·계좌정보는 저장하지 않는다. 구독90일 만료·정기 삭제·즉시 구독 삭제를 지원한다. 원본 금융·정책 규칙은 자동 생성하지 않고 신규 공고 전체 자격 UNKNOWN을 유지한다.

실제 공식25주소 확인·일정3건 추출(모두마감), 새 API17사례, 전체 Backend12562/1skip/1warning·Frontend161·TS/build 통과. 브라우저 기기 표시는 사용자 직접 확인이며 자동 OS 검증과 구분한다. release6/GV/BV·기존 core 보존. 상세: [구현·검증](OFFICIAL_INTAKE_MONITORING_AND_ALERTS.md), [운영](ASSET_ALERTS_OPERATIONS.md).
## 2026-10-30 화면 분리·공개 정보 배포와 상시 서버 대기

새 원본 보고: `docs/PORTAL_REDESIGN_AND_DEPLOYMENT.md`, 배포 절차: `docs/CLOUD_DEPLOYMENT_RUNBOOK.md`.

https://youth-life-planner.rladudwns559.chatgpt.site 에 공식 정보 UI를 공개 배포했다. 홈 CTA 아래 내용 제거·메뉴별 화면·입체 디자인·220ms 전환 및 접근성/상태 보존을 적용했다. 공개본은10월30일 고정 사업10/은행4 정보이며 계산·개인알림은 Python 상시 서버 연결 대기다. 로컬 전체 기능은 유지한다.

전체 Backend12,586 passed/1skip/1warning, Frontend186 passed, TS/build·production-only venv·Windows production-mode HTTP 통과. Docker/Linux·유료 서버·PC-off 정기수집은 미검증. Render starter+1GB 월 기본$7.25 제안은 계정·비용 승인 전이며 신청하지 않았다. 독립 urllib 공개접속403은 미검증으로 기록하고 native 공개설정/실제 in-app 브라우저 성공과 구분한다. 실제 만기0/미승인 지원금0원, release6·핵심95해시·Coverage freeze 보존.
## 2026-10-31 유료 배포 보류·무료 상품 탐색 우선

현재 결정은 **유료 배포 보류**다. 상품 탐색 확대와 공개 기능 정리: 기존 공개 Site에서 은행8곳·20종의 무료 조건 비교를 제공한다. 실제 만기계산0·미승인 지원금0원, 정부10사업 유지. 자동 갱신/브라우저push/이메일은 공개본에서 제공하지 않는다. 유료 서버·계정·알림 요금제0건. source 검토일의 정적 비교표이며 전국 전수·실시간 자료가 아니다. 원본 `docs/FREE_PRODUCT_DISCOVERY_AND_CLEANUP.md`, 출처 `docs/PRODUCT_DISCOVERY_SOURCES.md`. 기존 Render 제안은 승인되지 않은 보류 자료다.
## 2026-11-01 상품 목록 확대와 증거 수준 분리

상품 목록 확대: 공식상세목록61개·13금융회사, 별도2026-10-23공시참고299항목·97회사. 서로겹치므로합산하지않음. 가입방법/납입방식/정렬/ID만관심저장/12·24·전체페이지, 미지원납입단위/복합조건보류. Backend12645/1skip/1warning·Frontend224·TS/build·공개v5검증. 유료0·자동갱신/알림보류·실제계산0·지원금0원·GUI미확인. [공개 상품 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/savings).
## 2026-11-01 공시 상품 공식 검증과 조건 비교 연결

공시 상품 공식 검증: 공시299개 중 공식 자료를 추가 확인한13상품을 승격해 상세74개·18금융회사로 확대했다. 공시14항목과 연결되며9후보는 보류했다. 월30만원·12개월·목돈200만원에서 전체 금액·기간FIT36/일부금액4,신규13개는10/3. 가입자격UNKNOWN·현재금리/판매 추가확인·실제만기계산0·미승인지원금0원. Backend12666/1skip/1warning·Frontend230·TS/build·공개v6 검증. [공개 상품 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/savings).
## 2026-11-01 지역별 청년 지원사업 탐색 확장

지역별 청년지원사업 탐색: 기존 자산형성10개에서 주거5·취업8·교육5·생활8·문화2를 포함한 고유사업38개로 확장.17개 광역지역의 확인 자료,시군구7곳 일부 자료이며 전수 수집은 아님. 지역 선택 시 전국+광역+시군구 검토 목록,안산전체13·주거2. 나이/가구소득/재산/거주기간/전체자격UNKNOWN,지원금0원. Backend12698/1skip/1warning·Frontend238·공개v7검증. [공개 지원사업 찾기](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs).

## 2026-11-01 개인 조건 기반 지원 추천

개인 조건 기반 지원 추천: 지역·현재나이·취업·월세 입력에 따라 후보 자동 비교. 지원41개(신규3),근거 연결20개/연령16·고용4·월세2 부분 비교,나머지UNKNOWN. 전체자격UNKNOWN·지원금0원. Backend12740/1skip/1warning·Frontend247,공개v8. [공개 화면](https://youth-life-planner.rladudwns559.chatgpt.site/#/programs).

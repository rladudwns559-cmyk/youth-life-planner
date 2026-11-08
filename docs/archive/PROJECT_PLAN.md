# 프로젝트 계획

## 1. 기획 PDF에서 확정된 요구사항

- 기준: `TEAM복학생_최종프로젝트_기획서_v1.0.pdf`, 2026-10-20, 17쪽.
- 확인한 원본: `<USER_HOME>/Desktop/Ai+x/TEAM복학생_최종프로젝트_기획서_v1.0.pdf`
- SHA256: `5B41EA5221D4322775BDBD6F116C2716CF752FBDD9574F945542D40C82F166AD`
- 제품 목표: 안산 청년의 정책 이용 가능성, 현금흐름, 예·적금, 조건 변화 결과를 공식 근거와 계산으로 설명한다.
- 주요 사용자: 안산 거주 20대 대학생, 취업준비생, 사회초년생.
- 정보 부족으로 신청 기회를 놓친다는 주장은 검증할 가설이다. 6주차 예시 p값과 7주차 제주 회귀계수를 판정 근거로 사용하지 않는다.
- 전체 MVP: 정책 10~12개 우선/최대 15개, 금융상품 10~20개, 정책 검색, 입력, 판정, 계산, What-if, 근거, AI 설명.
- Python이 판정·계산하고 AI는 구조화된 결과만 설명한다.
- 조건을 PASS/FAIL/UNKNOWN으로 구분하고 최종 자격은 운영기관이 판단한다.
- 로그인 없는 세션/요청 계산과 개인정보 최소화를 기본으로 한다.
- 정책·상품의 출처, 기준일, 검증일, 버전을 관리한다.
- 비범위: 전국화, 자동 신청, 계좌 연결, 대출·투자·보험 추천, AI/ML 자격 판정.

## 2. 이번 M1에서 승인한 결정

- 이번 산출물은 순수 Python 정책 판정 엔진, 합성 JSON 정책 3개, pytest, 문서이다.
- 제한된 ALL/ANY/NOT 및 eq/in/gte/lte를 사용한다.
- 잘못된 규칙은 데이터 오류이며 UNKNOWN으로 숨기지 않는다.
- 생활비용 monthly_income과 정책 소득 사실을 분리한다.
- 재학과 취업을 독립적으로 취급한다.
- 평가일을 EvaluationContext로 전달하고 같은 데이터/입력/컨텍스트에서 결과를 재현한다.
- 입력을 수정하지 않고 null/0/false를 구분한다.
- 향후 지출 필드 명칭은 other_monthly_expenses를 채택한다. 이번에 계산이나 해당 필드는 구현하지 않는다.
- M1 내부 설계 선택: 표준 라이브러리 frozen dataclass와 명시적 검증을 사용한다. 실행 의존성은 없고 pytest는 개발 의존성이다.
- 합성 가구소득 기준은 테스트 전용이며 실제 정책 기준이 아니다.

## 3. 향후 결정해야 할 사항

- 실제 정책 선정, 공식 원문별 소득·나이·거주 기준, 필드 확장.
- 예금 초기 원금 입력, 적금 계산·세금·반올림, 장기 전망 가정.
- What-if의 날짜·의존관계·전체/부분 재계산 방식.
- DB, 제공업체, 배포, AI 가드레일 및 로그·외부 제공업체 보관 정책.
- 데이터 노후화 임계값과 운영 책임.
- 팀의 실제 주당 투입시간. PDF 8~15주차 계획은 이를 확인해야 한다.

## M1 완료 기준

세 정책 로딩, 동일 사용자 PASS/FAIL/UNKNOWN, 조건별 사유와 누락 필드, 논리표·경계값·잘못된 데이터·불변성·재현성 테스트 통과, README 명령 재현.

M1은 실제 정책 자격이나 제품 효과를 검증한 결과가 아니다.

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

# 화면 분리·입체 디자인과 공개 배포

확인일: 2026-10-30 / Asia/Seoul. 사용자 요청: PC 없이 작동하는 공개 서비스와 메뉴별 화면, 부드러운 전환, 입체적 디자인. 사용자는 기존 서버 계정이 없다고 답했다.

**판단: PUBLIC_INFORMATION_SITE_DEPLOYED / PYTHON_CLOUD_DEPLOYMENT_PENDING_ACCOUNT_AND_COST_APPROVAL**

공개 주소: https://youth-life-planner.rladudwns559.chatgpt.site

## 완료 범위와 남은 범위

| 항목 | 실제 상태 |
|---|---|
| 홈·화면 분리·입체 디자인 | 구현·로컬/공개 브라우저 확인 |
| 홈 CTA 아래 내용 | 서비스 섹션·푸터 없이 끝남 |
| 메뉴·뒤로가기·입력 보존 | 별도 hash 화면; 방문한 화면은 메모리에 유지 |
| 공개 청년사업 정보 | 2026-10-30 고정 스냅샷 10개; 실시간 아님 |
| 공개 은행 정보 | 같은 날 확인한 4개 공식 상품; 개인 추천·실제 만기계산 아님 |
| 로컬 Python 계산·추천·알림 | 기존 기능 유지 |
| 공개 개인 계산·구독 | 상시 Python 미연결로 비활성화; 입력정보 수집하지 않음 |
| PC와 무관한 수집·푸시 | 미배포·운영 검증 전 |
| 이메일 | 사용자 결정대로 제외 |
| Linux Docker 빌드 | Docker 미설치로 미실행 |
| 유료 서비스 생성 | 0건; 계정·비용 승인 전 |

Sites는 정적 공개 UI에 사용했다. 기존 FastAPI와 Python 엔진을 그대로 실행하는 호스팅은 아니므로 정적 배포 성공을 계산/수집/알림 서버 성공으로 취급하지 않는다. 기존 엔진의 JavaScript 재작성은 하지 않았다.

## 디자인 검토

| Before | After | 이유 |
|---|---|---|
| 홈 아래에 입력·결과·여러 기능이 이어짐 | 홈 CTA에서 끝나고 메뉴로 각 화면 진입 | 사용자가 요청한 구조, 기능 집중 |
| 페이지 안 앵커 이동 | 홈/지원사업/생활비/적금/알림/안내 화면 분리 | 주소·브라우저 뒤로가기 지원 |
| 평면적인 서비스 카드 | 겹친 카드·동전·입체 그림자·눌림 효과 | 금융 서비스의 깊이 표현 |
| 전환 맥락 약함 | opacity/translate 220ms ease-out | 이동 인지; 키보드는 즉시, reduced-motion은 짧은 fade |
| 서버 유무가 불명확할 수 있음 | 공개 화면에 서버 연결 대기와 고정 기준일 표시 | 정적 정보와 실제 계산을 구분 |

animate 및 emil-design-eng 스킬 지침을 적용했다. CSS/SVG 기반 그래픽과 WAAPI를 사용해 새 이미지·애니메이션 라이브러리 다운로드를 추가하지 않았다. 사전 전환은 취소 가능하며 입력을 localStorage에 새로 보관하지 않는다. 모바일 실물 기기는 미검증이다.

## 실제 배포 식별

- Site: `appgprj_6ae4993139c08191975b01a22068da5c`
- version: `appgprj_6ae4993139c08191975b01a22068da5c~appgver_7bdf8508a7fc8191b6f4c018a614bdba` (2)
- commit: `f0667ce1ba61cc706b9f94527499da6adbbbdf0e`
- deployment: `appgdep_6ae4a48900ac819181ef7193bcfb1775`, native 결과 `succeeded`
- access: native Site 조회 `public`. 기존 별개 Site/저장소는 수정하지 않았다.
- 공개 bundle은 `VITE_PUBLIC_BACKEND_PENDING=true`; 서버용 bundle은 false.
- source helper로 정확한 소스를 push·패키징한 뒤 version 저장·배포했다. 단기 credential은 stdin/세션 메모리로만 전달했고 공개 소스·문서·로그에 넣지 않았다.

## 실제 검증

| 검증 | 결과 |
|---|---|
| Backend 전체 | 12,586 passed / 1 skipped / 1 warning, 137.14초 |
| 새 production hosting 시험 | 24 passed / 1 warning; 최종 테스트 격리 보완 뒤 재실행 2.06초 |
| Frontend 최종 전체 | 186 passed / 9 files, 19.15초 |
| TypeScript·최종 정상 build | 성공, build 3.53초 |
| 공개 build | 성공, 2.77초 |
| production-only 신규 venv | requirements-web 설치·앱 import 성공; dev 의존성 불필요 |
| 실제 Windows production-mode HTTP | PASS; 아래 상세 |
| 실제 Linux/컨테이너 | 미실행 |
| 공개 브라우저 | 홈/정부10/은행4/계산 비활성/알림 대기 실제 확인 |
| 독립 비인증 urllib 공개 접속 | HTTP403으로 미검증; 이유 미확정, 우회하지 않음 |

전체 Backend 12,586은 새 hosting24개를 포함한다. Frontend 기존161개 + 새 Portal25개다. 기존6개 통합 테스트는 메뉴 이동을 수행하게 변경했고 금액/판정 검증값은 유지했다. 전체 Backend 실행 후 추가 변경은 새 테스트3개의 getuid 격리뿐이며 해당24개를 재실행했다. 최신 공개 안내 문구 변경 뒤 Frontend 전체/TS/build를 재실행했다.

Windows clean venv의 임시 8102 서버에서 실제 HTML/JS/CSS/service worker와 API가 같은 origin에서 응답했다. 합성 예산 여유50만원·저축투입상한30만원·지원금0원·PASS/FAIL/UNKNOWN을 확인했다. 임시 inbox-only 구독의 TEST 생성·조회·읽음·삭제 후401, 다른 Origin403, private 파일/알 수 없는 API404, CSP/HSTS 등을 확인했다. 자동 수집은 시험 중 껐고 기기 push는 수행하지 않았다. 시험 서버는 finally에서 종료했고 기존5173/8100은 종료하지 않았다. 이는 Windows native 검증이지 Linux/Docker/HTTPS 외부 운영 시험이 아니다.

로컬 브라우저에서는 1280/390 크기, 가로 넘침 없음, 모바일 입체 그림과 제목 겹침 없음, 실제 예산 계산 후 적금 메뉴 이동과 뒤로가기의 값 보존을 확인했다. 320/768 및 실제 휴대폰을 이번에 검사했다고 주장하지 않는다. 공개 브라우저 접속 성공과 별도 네트워크·쿠키 없는 방문자 접속 성공은 구분한다. 배포 후 다른 기기/비로그인 브라우저 운영 점검이 남아 있다.

## 오류·수정·재실행

1. 초기 Frontend 13 fail/148 pass: 기존 시험이 홈에 곧바로 폼이 있다고 가정했다. 실제 메뉴 흐름으로6개 통합 시험을 갱신하고161개 통과, 새 Portal25개 포함 최종186개 통과.
2. 새 Portal 시험1 fail/24 pass: 기존 region label과 정확 문자열 매칭 충돌. 선택 항목을 포함한 label 매칭만 수정.
3. 관련 Backend10 fail/110 pass: 새 fixture가 생성한 환경변수의 정리 누락. monkeypatch에 원래 값을 등록하도록 고쳐120개 통과·전체12,586 통과. 제품 엔진 변경 없음.
4. 모바일 입체 그래픽과 제목 겹침: 음수 여백을 제거하고390 화면에서 다시 확인.
5. 기존 package.json 범위와 lockfile 해석 버전 불일치: 현재 설치·시험한 정확 버전으로 맞추고 pnpm11.25 offline lock 갱신. 다운로드/패키지 업그레이드0. 빌드 재현을 위해 고정했다.
6. production-only 환경에서 필요한 httpx를 requirements-web에 명시. 새 venv에서 검증.
7. 독립 HTTP 점검 스크립트가 입력 모델 필드명과 결과 필드명을 혼동해 KeyError2건. 기존 결과 계약 policy_benefit_applied/overall_status를 참조하게 고친 뒤 native PASS. production 코드는 바꾸지 않았다.
8. 별도 urllib 외부 조회는403. 이를 성공으로 덮어쓰거나 인증 우회하지 않았다. 원래 sandbox 네트워크 제한 WinError10013은 적법한 실행 승인 뒤 native 검증했다.
9. 신규 entrypoint 시험이 Linux root에서 실제 권한을 내리지 않도록 getuid mock을 추가하고24개 재검증. Linux runtime 자체는 미검증.

## 보존 감사

작업 전419파일 SHA256과 비교했다. Policy/Cashflow/Finance/설명 관련 보호 소스 및 freeze·release95개 불변, 실제 release6개 SHA256 불변. 기존 변경은 화면/메뉴 통합시험/호스팅 연결/운영 안내 flag/requirements·lock 범위다. 상세는 `preservation.json`.

GV01~GV15/BV01~BV16 기대값과 기존 golden 시험은 수정하지 않았고 전체 회귀가 통과했다. 해당 테스트 파일은419개 사전 해시 기준선에 포함되지 않았으므로 “전후 SHA 검증”이라고 표현하지 않는다. 현재 지문은 후속 비교용으로 별도 기록했다. Coverage freeze 유지. 실제 만기 계산0개·미승인 지원금0원·실제 정책 DRAFT/CONDITION_SLICE·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED·M2.77 SYNTHETIC_ONLY·기본 NoProvider 유지. 추가 LLM 실행0.

## 배포 준비와 운영 비용

`Dockerfile`, `.dockerignore`, `deploy/start.py`, `render.yaml`, same-origin static hosting을 준비했다. SQLite·VAPID는 영구 비공개 디스크에 보관하고1 worker/1 instance로 실행하는 구성이다. private state를 공개 static 경로에 넣지 않는다. root는 state 초기화 후 uid10001로 내려간다. Linux에서 해당 흐름을 실제 검증하는 것이 다음 배포 절차에 포함된다.

제안 비용: Render Starter 월$7 + 영구 디스크1GB 월$0.25 = **월 기본 $7.25**. 세금·환율·초과사용은 별도이며 상한 보장이 아니다. 요금제 신청/카드/계정 생성/유료 배포는 하지 않았다. [Render pricing](https://render.com/pricing), [영구 디스크](https://render.com/docs/disks). 무료 서비스는15분 무활동 후 중지·영구 디스크 미지원으로 현재 SQLite 알림 구성의 상시 운영에 맞지 않는다. [무료 서비스 제한](https://render.com/docs/free).

## 산출물·다음 최소 단계

별도 `CLOUD_DEPLOYMENT_RUNBOOK.md`에 배포·검증·중지/복구 절차를 정리했다. 안전한 backend source ZIP164파일(개인 DB/키/원본 문서/release 제외)과 Site archive, metadata, hashes, HTTP 증거, screenshot은 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\portal-deploy`에 있다.

다음은 계정/비용 승인 후 Render에 이 구성으로 단일 origin 전체 서비스를 연결하고 실제 컨테이너·재시작 후 상태·정기수집·기기 알림을 검증하는 작업 하나다. 승인 전에는 유료 자원을 만들지 않는다. Obsidian은 별도 최신 노트/대시보드로 동기화하고 앱 GUI는 미확인으로 유지한다.

실제 Obsidian 동기화 후80개 노트의 Wikilink795개 파일 대상과 Canvas/Bases 첨부를 확인했다. 깨진 파일 대상0개, 새 source_paths 존재, .obsidian 설정/Bookmarks SHA256 불변. 제목에 점이 들어간 M3.x 및 첨부 확장자를 일반 Markdown 확장자로 오인했던 검사기를 보완했다. 문서 본문이나 링크를 오탐에 맞춰 바꾸지 않았다. 앱 GUI·개별 제목/블록 anchor 렌더는 이번에 확인하지 않았다.

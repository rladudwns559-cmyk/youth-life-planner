# AI+X Python 상시 서버 배포 절차

2026-10-30. **준비 완료 / 계정·비용 승인 전 / cloud Python 미배포**. 공개 정보 UI는 https://youth-life-planner.rladudwns559.chatgpt.site . 현재 공개 계산·구독은 비활성이다.

## 제안 구성

Render Docker Web Service Starter1개 + 영구 디스크1GB + HTTPS. 같은 서비스가 React build와 FastAPI를 함께 제공한다. Python 판정/금액/UNKNOWN/검증기를 그대로 사용한다. 별도 JS 계산, Supabase 이전, 로그인 도입, 이메일은 이번에 추가하지 않았다.

최종 전체 기능 주소는 Render가 실제 부여한 HTTPS 주소를 사용한다. 기존 Sites 정보 공개 페이지는 상시 서버 연결 완료 뒤 실제 주소로 안내하도록 갱신한다. 연결되지 않은 Sites 페이지에서 localhost API를 호출하거나 개인 입력을 받지 않는다. 도메인 구매는 포함하지 않는다.

기본 비용은 Starter$7/월 +1GB 디스크$0.25/월, 합계$7.25/월. 세금·환율·추가 트래픽/워크스페이스 등은 별도. [공식 가격](https://render.com/pricing)·[디스크](https://render.com/docs/disks)·[무료 서비스 제한](https://render.com/docs/free). 비용 승인 뒤 실제 결제 화면을 재확인한다. 무료 인스턴스는15분 idle 중지/임시 파일 손실/영구 디스크 미지원으로 현재 알림 상태 보존 요구를 충족하지 않는다.

## 계정 연결 전 준비된 파일

- Dockerfile: node24/pnpm11.25 build → Python3.12 production-only.
- render.yaml: starter, Singapore,1instance,1GB `/var/data`, 자동배포 off, 종료유예180초.
- deploy/start.py: private state 초기화, umask077, Linux root이면 uid/gid10001로 전환, uvicorn1worker, access log off.
- backend/web/hosting.py: production에서만 static mount와 Origin·보안 헤더 설정.
- frontend: production build 기본은 계산 활성; 정보 공개 전용 배포만 VITE_PUBLIC_BACKEND_PENDING=true.
- sanitized ZIP: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\portal-deploy\python-cloud-deployment-source.zip`.

현재 ZIP에는 소스164개와 안내문이 있다. 실사용 구독 DB/VAPID키/토큰/개인 입력/실제 release6/다운로드 문서/로컬 모델은 포함하지 않는다. 로컬 구독·브라우저 권한은 새 origin으로 자동 이전되지 않으며 공개 서비스에서 다시 명시적으로 설정한다.

## 승인 후 순서

1. 사용자에게 월 기본 비용·별도 과금 가능성을 확인받는다. Render 로그인/가입·약관 동의·카드 입력은 사용자가 한다. 비밀번호나 API키를 채팅에 보내지 않는다.
2. 사용자 소유의 새 private Git 저장소를 연결한다. 관계없는 collaborator 저장소는 쓰지 않는다. 저장소에는 검토된 sanitized source만 올린다.
3. 가능한 Linux Docker 환경에서 `docker build -t youth-life-planner .`를 실행한다. 이 PC에는 Docker가 없어 아직 미실행이다. 실패하면 공개 기능을 켜기 전에 수정·검증한다.
4. Render Blueprint의 실제 자원/가격이 starter1개와disk1GB인지 확인하고 적용한다. region Singapore, root context `.`, Dockerfile `./Dockerfile`, health `/api/health`.
5. 환경변수는 아래 값. RENDER_EXTERNAL_URL은 Render가 주입하며 production_origin이 사용한다. 값을 임의 예측하지 않는다.

| 환경변수 | 값 |
|---|---|
| AIX_ENV | production |
| WEB_BUILD_DIR | /app/web |
| ASSET_ALERTS_STATE_DIR | /var/data/asset-alerts |
| ASSET_ALERTS_AUTO_REFRESH | 1 |
| PORT | Render 제공 값 |
| PUBLIC_BASE_URL | 생략 가능; Render 주입 실제 URL 사용 |
| ASSET_ALERTS_ORIGINS | 생략 시 실제 public origin 한 개로 설정 |
| ASSET_ALERTS_VAPID_SUBJECT | 생략 시 실제 HTTPS origin |
| EXPLANATION_PROVIDER | 기본 NoProvider 유지; 로컬 Ollama 미노출 |

공개 origin을 새 도메인으로 바꾸면 PUBLIC_BASE_URL/허용Origin/VAPID subject도 검토한다. wildcard CORS로 우회하지 않는다. secrets를 render.yaml/로그/Git/Vault에 저장하지 않는다.

## 공개 전 실제 확인

1. root/JS/CSS/service worker200, `/api/health` 정상, HTTPS 인증서 확인. 현재 health는 합성 서비스 정보이며 모든 외부 출처 성공을 보장하지 않는다.
2. 합성 입력으로 예산50만원/저축상한30만원/지원금0원·PASS/FAIL/UNKNOWN 보존 확인. What-if/적금 필터링/정형 설명과 제한을 확인한다.
3. 알림 상태의 hosting=cloud, worker_active, 마지막/다음 확인시각·출처별 성공/실패 확인. 첫baseline을 새 모집으로 보내지 않는지 점검한다.
4. 명시적으로 임시 관심 구독을 만들고 TEST inbox·브라우저권한·기기 표시·삭제를 확인한다. Push 서버 접수와 OS표시는 구분한다. 실제 모집 발송이 없으면 없는 것으로 기록한다.
5. 서비스 재시작 전후 임시 구독/알림/다음 주기 및 VAPID 공개키 동일성 확인. 개인키/원문구독은 출력하지 않는다. 영구 디스크가 실제 마운트되었는지 확인한다.
6.6시간 정기 주기1회가 실제 지나간 뒤 확인시각·실패 상태를 기록한다. 즉시 수동조회만으로 무인 정기운영 완료라고 하지 않는다. PC를 꺼도 서버가 독립 실행되는지 외부 기기로 확인한다.
7. 서로 다른 기기·비로그인 브라우저에서 공개 접속, 모바일화면, 정기수집과 구독을 확인한다. Sites 정보 UI는 in-app browser로 확인했으나 독립 urllib403 원인은 미확정이다.
8. 완료한 실제 URL로 정보 공개 Site의 안내를 갱신하고 source/version/deployment를 남긴다. 자동 수집은 등록25개공식주소 범위이며 전국 모든 공고/모든 PDF 자동판독은 아니다.

## 운영·중지·복구

단일instance/worker와 SQLite를 유지한다. 동시 서버 확대/복제·장기 백업 저장소는 별도 설계한다. private 디스크는 state DB와 VAPID키를 담으므로 전체 삭제/재생성/복사 공개를 하지 않는다. 서비스 코드 롤백과 디스크 복원을 같은 것으로 취급하지 않는다.

외부 출처 장애·HTML변경을 모집없음으로 처리하지 않는다. status의 실패와 최근성 기준을 확인한다. 수집만 일시 중지하려면 ASSET_ALERTS_AUTO_REFRESH=0 후 재시작한다. paid 인스턴스/디스크 비용을 끝내려면 실제 서비스·디스크의 삭제/과금 상태를 사용자가 확인해야 한다. 중요한 상태 삭제 전 별도 확인/복구 계획이 필요하다.

브라우저 알림은 수신 기기의 브라우저/OS/네트워크 설정에 따라 달라진다. 서버가 켜져 있어도 꺼진 사용자 기기에 즉시 화면표시된다고 보장하지 않는다. 이메일은 계속 제외한다.

## 현재 증거

Backend12,586/1skip/1warning, Frontend186, TS/build, clean production venv import, Windows production-mode 실제HTTP 통과. Linux Docker·유료 cloud·재시작 상태 보존·PC-off 정기수집·cloud 실제기기push는 아직 미실행. 자세한 원본 증거는 `PORTAL_REDESIGN_AND_DEPLOYMENT.md`와 `output/portal-deploy`.
## 2026-10-31 유료 배포 보류·무료 상품 탐색 우선

현재 결정은 **유료 배포 보류**다. 상품 탐색 확대와 공개 기능 정리: 기존 공개 Site에서 은행8곳·20종의 무료 조건 비교를 제공한다. 실제 만기계산0·미승인 지원금0원, 정부10사업 유지. 자동 갱신/브라우저push/이메일은 공개본에서 제공하지 않는다. 유료 서버·계정·알림 요금제0건. source 검토일의 정적 비교표이며 전국 전수·실시간 자료가 아니다. 원본 `docs/FREE_PRODUCT_DISCOVERY_AND_CLEANUP.md`, 출처 `docs/PRODUCT_DISCOVERY_SOURCES.md`. 기존 Render 제안은 승인되지 않은 보류 자료다.

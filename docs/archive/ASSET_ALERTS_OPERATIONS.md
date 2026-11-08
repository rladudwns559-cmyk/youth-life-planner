# 로컬 모집 알림 사용·운영

## 사용자

http://127.0.0.1:5173/#asset-alerts 를 Edge/Chrome에서 연다.
1. 관심 알림 설정 → 지역/사업 선택.
2. 사이트 알림함/브라우저 푸시를 선택하고 저장.
3. 브라우저 푸시를 선택했다면 사이트 알림 권한을 허용.
4. 테스트 알림 보내기. 실제 모집과 구분된 TEST이며1분당1회다.
5. 구독·기록 삭제로 설정과 알림을 지울 수 있다. 같은 기기의 비공개 식별자이므로 다른 브라우저에 자동 동기화되지는 않는다.

알림함은 다시 열어 확인할 수 있고, 브라우저 push는 페이지가 열려 있지 않아도 브라우저/OS 지원·네트워크·절전 정책에 따라 전달될 수 있다. 완전히 종료된 브라우저/꺼진 PC에서도 항상 전달된다고 보장하지 않는다. 이메일은 이번 범위에 없다.

## 개발 서버

기존 frontend Vite5173 / backend uvicorn8100을 유지한다. backend를 프로젝트 루트에서 실행하면 pytest 외 일반 실행은 자동 확인이 기본 켜진다.

```powershell
Set-Location 'C:Users김영준DocumentsChatGPTai+x'
$env:ASSET_ALERTS_AUTO_REFRESH='1'
& '..venvScriptspython.exe' -B -m uvicorn backend.web.app:app --host 127.0.0.1 --port 8100 --no-access-log
```

6시간 주기·다음 시각은 로컬 state DB에 유지한다. 서버/PC가 꺼지면 수집·전송도 중단된다. 재개 시 만료된 기존 공고를 새로 발송하지 않는다. 시작프로그램·Windows Task Scheduler·Codex heartbeat/cron은 등록하지 않았다. 이 기능은 제품 backend의 lifecycle worker다.

중지하려면 서버를 종료한다. 자동 확인만 끄려면 ASSET_ALERTS_AUTO_REFRESH=0으로 재시작한다. ASSET_ALERTS_STATE_DIR는 별도 비공개 로컬 경로를 명시할 때만 사용한다. 경로를 바꾸면 기존 익명 구독을 다른 저장소에서 찾을 수 없으므로 임의 변경하지 않는다.

## 공개 서버로 옮길 때

HTTPS·상시 실행·프로세스 감시·개인 저장소 접근 제한·명시 Origin 설정을 먼저 마련한다. ASSET_ALERTS_ORIGINS에 실제 frontend Origin을 명시하고 ASSET_ALERTS_VAPID_SUBJECT에 실제 운영자 연락 URI를 설정한다. VAPID 개인키를 보존·보호하고 코드·공개로그·Vault에 올리지 않는다. 임의 key 회전은 기존 브라우저 구독에 영향을 줄 수 있다. 다중 프로세스 운영은 별도 검증한다.

SQLite DB와 VAPID 개인키는 tmp/asset-alerts-runtime에 있다. .gitignore의 tmp/ 규칙으로 제외된다. 개인 구독·토큰·endpoint를 디버깅 명목으로 공개하지 않는다. 구독 삭제 후 개인별 전송 기록을 영구 보관하지 않는다.

## 점검

GET /api/asset-alerts/status의 worker_active·최근/다음 확인·출처별 실패를 확인한다. source_count는 접근한 주소 수이며, 실제 날짜 추출 수와 다르다. 동작 실패를 ‘모집 없음’으로 바꾸지 않는다. 연결 실패/변경 검토는 화면에 남긴다.

구독 없는 최초 확인은 baseline이며 과거 공고를 발송하지 않는다. 새 모집 여부는 명확한 공식 신청기간과 현재 시각으로만 판단한다. 알림은 자격·선정·수령을 확정하지 않는다.
## 2026-10-30 새 메뉴·공개 배포 상태

로컬 알림 진입 주소는 http://127.0.0.1:5173/#/alerts 이다. 과거 #asset-alerts도 호환한다. https://youth-life-planner.rladudwns559.chatgpt.site 공개본에는 현재 개인 구독을 받지 않는다. 클라우드 Python/영구 디스크/비용 승인 후 같은 origin 서비스에서 연결한다. 상세 `CLOUD_DEPLOYMENT_RUNBOOK.md`. 기존 구독·키를 자동 이전하지 않았다.
## 2026-10-31 유료 배포 보류·무료 상품 탐색 우선

현재 결정은 **유료 배포 보류**다. 상품 탐색 확대와 공개 기능 정리: 기존 공개 Site에서 은행8곳·20종의 무료 조건 비교를 제공한다. 실제 만기계산0·미승인 지원금0원, 정부10사업 유지. 자동 갱신/브라우저push/이메일은 공개본에서 제공하지 않는다. 유료 서버·계정·알림 요금제0건. source 검토일의 정적 비교표이며 전국 전수·실시간 자료가 아니다. 원본 `docs/FREE_PRODUCT_DISCOVERY_AND_CLEANUP.md`, 출처 `docs/PRODUCT_DISCOVERY_SOURCES.md`. 기존 Render 제안은 승인되지 않은 보류 자료다.

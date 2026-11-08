# M3.8F-R1 — T08 TIMEOUT 원인 분석 및 최소 보완

2026-10-26 KST. **M3_T08_LIVE_RETEST_APPROVAL_REQUIRED**.

실제 모델 추가 실행0회. 기존 두 실행의 사전 로드와 실제 요청 간 shift 설정 차이 및 runner 재시작을 확인했다. 첫 요청의 재로딩 중 취소는 확인됐지만, 두 번째 생성 지연의 전체 원인은 아직 **ROOT_CAUSE_UNCONFIRMED**다. 사전 로드 설정 일치만으로6초 내 정상 완료한다고 선언하지 않는다.

## 1. T08 원본 과제 구조

T08=FU01. 월소득1,500,000→1,800,000원, 월세450,000→550,000원, 미취업→취업. 저축 상한300,000원 유지. 기존 엔진은 여유자금500,000→700,000원, 저축 투입300,000→300,000원, SAMPLE-001 PASS→PASS, SAMPLE-002 PASS→FAIL, SAMPLE-003 UNKNOWN→UNKNOWN(가구소득 누락)을 반환한다. 지원금0원. 원본 입력/정답/실험용7개 정상 설명을 수정하지 않았다.

## 2. 기존 두 실행 결과

| 항목 | 첫 실행 | 추가 승인 후 둘째 실행 |
|---|---:|---:|
| 실제 설명 POST | 1회 | 1회 |
| 빈 사전 로드 | 5468.08ms / load 완료 | 6046.39ms / TIMEOUT |
| 설명 전송 wall time | 6021.00ms | 6034.54ms |
| 설명 서비스 wall time | 6065.73ms | 6064.52ms |
| 오류 | TimeoutError | TimeoutError |
| 완료 envelope/원문/공식 metrics | 없음 | 없음 |
| 최종 결과 | TIMEOUT / 전체 정형 대체 | TIMEOUT / 전체 정형 대체 |

첫·둘째 파일은 기존 원본 그대로다. 첫 실패/둘째 실패를 성공으로 교체하지 않았다. 둘째 사전 로드 실패 후에도 기존 연구 script가 설명을 계속 호출했다는 한계를 확인했다.

## 3. 모델 및 Provider 환경

기존 설치 Ollama0.40.11, `qwen3:4b-instruct-2507-q4_K_M`, Qwen3 4B Instruct2507, Q4_K_M. tag digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, weights SHA256 `85e4a5b7b8ef0e48af0e8658f5aaab9c2324c76c1641493f4d1e25fce54b18b9`는 기존 메타데이터/로그와 대조했다. 새 모델 실행·다운로드 없이 확인했다.

현재 읽기 전용 환경 조회: Win11Home64 10.0.26300, Ryzen7 260 8C/16T, RAM15.31GiB, RTX5050Laptop8151MiB/driver572.97, Python3.12.14. 확인 시 모델 프로세스0, GPU사용0MiB. 최초 sandbox CIM 접근 제한 뒤 읽기 전용 조회 권한으로 확인했으며 환경을 바꾸지 않았다. 과거 두 실행 당시 여유 RAM1.2~2.7GiB/VRAM약6.8GiB 기록은 있으나 OOM 증거·지속 사용량 표본은 없어서 메모리 압박을 원인으로 확정하지 않는다.

## 4. 입력·후보·출력 크기

복잡도 비교 기준은 **실제 요청 wire UTF8 byte 최대**다. tokenizer 순위/실제 계산 난이도 전체를 뜻하지 않는다.

| 측정 | T08 | 정상30 중 최대 EX06 |
|---|---:|---:|
| 변경 입력 수 | 3 | 1 |
| 요약군 | S3 | S4 |
| 정책 후보군 | P1/P2/P3 | P1/P6/P3 |
| wire | 2105bytes | 2201bytes |
| 후보 context | 561bytes | 609bytes |
| 시스템 Prompt | 360bytes /162문자 | 동일 |
| 두 message content 합 | 921bytes | 969bytes |
| format schema | 922bytes | 970bytes |
| 정책 슬롯 | p01/p02/p03 | 동일 |
| 필드별 후보 | 2×2×2×2=16조합 | 동일 |
| 허용 inner 최소~최대 | 269~286bytes | 291~312bytes |
| 원래 실제 응답 | 미확보 | 채택,1816.71ms |

T08 wire는96bytes 더 작다. 후보와 enum에 같은 문장이 반복되는 기존 표현은 양쪽 공통이다. 원본 복합3개 입력은 LLM으로 그대로 전달되지 않으며 서버가 S3 후보와3개 정책 슬롯으로 투영한다. 입력 byte 증가·슬롯 증가·후보 폭증·8KiB/4KiB 정적 한도 초과 근거는 없다. 단 byte 크기만으로 schema 문법/토큰 생성의 시간 비용이 같다고 증명하지는 못한다.

정상30의 공식 prompt_eval_count242~266/eval_count95~106. EX06은 prompt266/cached145, load7.60ms/prompt53.52ms/eval1653.82ms였다. T08 둘째 native에는 prompt250이 있으나 공식 완료 metrics가 없다. native slot 최종 n_tokens342를 공식 eval_count342 또는92라고 쓰지 않는다. 실제 토크나이저를 새로 실행하지 않았고 byte/문자를 토큰으로 환산하지 않았다.

269~286bytes는 기존 허용 후보16조합의 **합성 출력 상한**이다. 실제 모델 출력 길이·공식 세전금액·성공 응답이 아니다. 임의 envelope/metrics의 무제한 길이까지 예측하는 값도 아니다. 실제 전송의32KiB 한도는 기존 `_post`가32769bytes까지만 읽어 초과를 거부한다.

## 5. TIMEOUT 발생 지점

기존 RecordingProvider의 `_post` 구간에서 TimeoutError가 기록됐고 8초 서비스 전체 제한보다 먼저6초 전송 제한으로 전체 대체됐다. 기존 urllib `open(timeout=6)`과 비스트리밍 read 안에서 발생했다. connect/header/read 각각의 타이밍·예외 stack/정확한 구간은 저장하지 않아 **연결 지연인지 응답 대기인지 세분 확정 불가**다. loopback이라 지연0이라고 가정하지 않는다.

JSON 구조/후보 검사 단계까지 완료 원문이 오지 않아 structure/membership/공식 생성 토큰 수는 null이다. 이를 INVALID_JSON/후보 거부/출력256토큰 소진이라고 해석하지 않는다. 설명 서비스→TIMEOUT reason→원본 정형 document 전체 반환은 두 실행에서 확인됐으며 늦은 모델 내용을 기존 UI에 적용하지 않았다.

## 6. Cold/Warm 여부

첫 사전 로드는12:37:05.325 shift 활성 runner(port62254)를 시작했고12:37:09.668 load 완료였다. 실제 요청은shift=false여서12:37:12.256 비활성 runner(port62279)가 다시 시작됐다.12:37:15.799 모델 로딩 중 client closed/context cancelled 로그가 있다. **사전 로드 성공과 실제 요청의 동일 설정 warm은 다르다.**

둘째 사전 로드는12:40:58.001 shift 활성(port60854)로 시작했다가12:41:02.555 로드 중 취소됐다. 실제 요청용 shift 비활성(port60901)은12:41:14.090 시작,12:41:17.631 준비, 이후 새 prompt250/cached0→task 취소→slot342 로그가 있다. **둘째도 검증된 동일 설정 warm 재시도가 아니다.** 생성 진행 흔적은 있으나 native 줄에 시각/HTTP ID가 없어 첫 토큰 시점·정확한 생성 시간은 복원하지 않는다.

## 7. M3.8E 정상 사례와 차이

정상EX06은 이미 준비된 runner에서 load약7.6ms와cached145가 기록됐다. T08은 fresh runner/cached0 또는 로드 중 취소다. 동일 모델·같은 옵션과 정적 구조만으로 동일한 실행 준비 상태였다고 비교할 수 없다. 새로운 S3 요약군도 기존30에 없던 coverage 차이지만 이것만으로 지연 원인이라고 확정하지 않는다. 전체30의 입력·후보 크기와 실제 metrics는 별도 JSON에 보관했다.

## 8. 확정된 원인/결함 범위

**연구 실행 준비의 설정 불일치**: 사전 로드는 shift 생략, Provider는shift=false다. 로그에서 실행 인자 `--context-shift --keep 4` 유무가 번갈아 바뀌며 재시작한다. 동일 버전 [공식 기본값/재로딩 구현](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L159-L177), [needsReload](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L1358-L1364)이 이 동작을 뒷받침한다. 첫 요청에서 이 재로딩 중 취소가 발생한 사실을 확인했다.

또한 기존 script는 사전 로드 실패 후 모델 존재 조회가 끝나도 준비 완료를 강제하지 않고 설명으로 진행한다. 이는 warm 시험이라고 해석하는 것을 막는 gate 결함이다. **제품 후보/계산 엔진 결함이 확인된 것은 아니다.** 공식 같은 버전 source를 참고했으며 설치 binary의 모든 build 소스가 같다고 별도 증명한 것은 아니다.

## 9. 미확정 원인

둘째 요청의6초 전체 지연 중 scheduler/로드/커널 초기화/schema 문법 처리/실제 생성/소켓 대기 비중, 동일 설정 warm T08의 성공 여부, 메모리 압박의 영향, 첫 token 시각/공식 eval_count는 미확정이다. ROOT_CAUSE_UNCONFIRMED 범위를 유지하며 한 설정 차이가 두 실패의 유일 원인이라고 하지 않는다.

## 10. 최소 해결안 비교

| 대안 | 예상 효과·현재 증거 | 계약 영향·위험 | 필요 파일/검증 | 권장 |
|---|---|---|---|---|
| A Projection 중복 축약 | 약간의 입력 감소 가능. T08은 정상 최대보다 이미 작음 | 새 표현은 Prompt 계약 영향, 설명 의미/출처 변경 위험 | 후속 별도 설계/30개 투영·정확검사·실측 필요 | 지금 보류 |
| B 후보 전달 표현 축약 | context/schema 중복 감소 가능. 두 조건에 공통인 구조 | enum/후보 연결을 바꾸면 단순 압축이 아님. 후보 축소 금지 | 후보/Prompt/Provider 영향 먼저 명시·별도 승인 | 지금 보류 |
| C 설정 일치 사전 로드와 준비 gate | 확인된 불일치/불완전 warm 해석 해소 | 제품 계약 불변. 사전 로드6초 실패하면 계속 보류 가능 | 신규 연구 도구 제안1개, 동일 runner 확인 후 bounded 진단 | **우선 권장** |
| D 출력 제한/요청 설정 조정 | 현재는256토큰 소진이나길이 초과 증거 없음 | 토큰/stop/format 변경은 조기 절단·검증 실패 위험 | 기존 설정 그대로 측정 먼저. 변경은 별도안 | 지금 변경 안 함 |
| E T08 교체/프로토콜 개정 | 과제 확보 부담 감소 가능 | 복합 필수 coverage 상실·A/B 비교 가능성 변경 | 필요 시 새ID/version/정답/원본 보존, 사전 승인 | 근거 전 교체 안 함 |

구체적인 [최소 수정·재실행 승인안](../experiments/m3_8f_r1/MINIMAL_FIX_AND_RETEST_PLAN.md)을 작성했다. 새 Prompt·후보·Provider 설정을 제품에 적용하지 않았다.

## 11. 수정 파일

신규 `tools/diagnose_t08.py`, `tests/test_t08_diagnostics.py`, 이 보고서 및 `docs/experiments/m3_8f_r1/` 오프라인 증거/승인안만 추가한다. 기존 M3.8F 보고/프로토콜/실험 자료와 이전 두 실행 script/log는 모두 원본 보존한다. 기존 파일 변경0.

## 12. 새 실제 모델 실행 여부

**0회**. 사전 로드0, T08생성0, 다른 모델 생성0, 설치/다운로드0, 환경 변경0. 과거2회와 이번 오프라인 합성 시험을 혼합하지 않는다.

## 13. 추가 승인 필요 여부

**필요**. 사용자 지시문§6에 따라 설정 일치 사전 로드1회(빈 요청)+원인 조사 T08 1회·비교EX06 1회, 총 실제 설명 최대2회의 승인을 요청한다. 기존6/8/12초·32KiB·동일 모델/후보/검증기 유지, 자동 재시도0, 다운로드0이다. 과거 로그상GPU self약4.9GiB·host약0.4GiB+기타 메모리가 예상되며 요청 예산약18초+기동/정리 시간을 구분한다. 사전 로드 실패 시 설명0회로 중단한다. 최종 사람 평가용 확정 생성은 이번 제안 범위에 포함하지 않는다.

## 14. 신규 합성 테스트

**30passed,9.50초**. T08결정성/네트워크 차단/slot순서/후보schema매핑·16조합/중복·누락·교차·비정확 문장 거부/32KiB정확·초과/전송read TIMEOUT 전체대체·재시도0/기존8초 실제 deadline 후 늦은thread완료 무시/원본불변·동시요청·binding격리/로그 토큰·시각 미조작/원본 덮어쓰기 차단을 확인했다. 기존 시간 값을 줄여서 시험하지 않았다. 합성 late thread와 테스트용 envelope는 실제 모델 응답이 아니다.

## 15. 전체 회귀

기준12240passed/1skip/1warning+Frontend115. 신규 진단 코드가 있어 전체 Backend/Frontend·TypeScript/build를 실행한 최종 기록을 뒤에 추가한다. 기존skip은NTFS 파일symlink생성권한/DeveloperMode부재, warning은Starlette/httpx 사용 deprecation이다. 이 증거를 보안검증 완료로 승격하지 않는다.

## 16. 정책·금액·UNKNOWN 보존

T08 원본 Comparison/Facts/canonical hash와 기존 두 증거를 대조했다. 허용16조합 모두 금액·상태·rules/source·UNKNOWN·next_actions를 보존했다. 기존7개 정상 A/B와 고정정답은 변경하지 않았다. 실제 상품 만기 계산0개/미승인 실제지원금0원/실제안산DRAFT·CONDITION_SLICE/ResidenceHistory OFFICIAL_INQUIRY_REQUIRED/M2.77SYNTHETIC_ONLY/IBK공식회신대기 유지.

## 17. 기존 Fallback·시간 제한 유지

기존 Provider6초/서비스8초/React12초/응답32KiB/request8KiB/inner4KiB/num_predict256/num_ctx16384/정확일치/전체정형대체는 수정0. 늦은 응답을 이미 반환한 객체에 붙이지 않는 합성시험과 기존Frontend 회귀를 구분한다. 이번 실제 브라우저 재실행은0이다.

## 18. A/B 자료 상태

**7/8쌍**. T08 B=null, M3.8F의REVISION_REQUIRED/ready=false 유지. 이번은 오프라인 원인 조사 완료이며 평가 자료 준비 완료가 아니다. 정형 Fallback을 B로 넣지 않았다.

## 19. 실제 참가자·응답

각각0명/0건. 이해도·AI 추가 가치·정답률·오해·선호·시간은 미측정이다.

## 20. Obsidian 기록

기존 M3.8F 노트에 두 실행 차이/확인·미확정 원인/대안/승인 대기를 추가하고 대시보드·미해결 문제·테스트 기록을 필요한 범위에서 갱신한다. 앱 GUI 미확인·기존 북마크 구버전·앱설정 불변 유지. 최종 링크 검사 수치는 아래 추가한다.

## 21. 최종 판단

**M3_T08_LIVE_RETEST_APPROVAL_REQUIRED**. 설정 불일치/재로딩이라는 부분 원인은 확인했고 최소안은 준비됐지만, 둘째 요청의 전체 원인과 실제6초 내 성공은 미확정이다. FIX_READY/전체원인확정·EVALUATION_MATERIAL_READY로 과장하지 않는다.

## 22. 다음 최소 작업 하나

**사용자 승인 후, 설정 일치 사전 로드에서 T08·EX06을 각각1회만 진단 실행.** 원래 두 실패·원인 조사·향후 최종 확정 실행을 분리하고, gate 실패 시 추가 생성 없이 중단한다.

## 최종 회귀·보존 확인

- 신규30passed(9.50초), 전체 **12,270 passed / 1 skipped / 1 warning (90.07초)**. 최초 신규/회귀 실패0, 기존 테스트 기대값 수정0.
- Frontend **115passed(41.45초)**, TypeScript/Vite build 성공(Vite1.46초). 병렬 테스트 실행 시간이며 모델 속도 성과가 아니다.
- 기존 repository354파일 SHA256·크기·mtime 전체 불변. 기존7개 A/B·T08정답·기존두시도·고정30·원본실행script/log·금융/판정/검증/시간제한·GV/BV/golden·Coverage freeze·실제release6 모두 보존.
- 실제 모델/서버/API/UI 실행0, 사전 로드0, 환경 변경0. 모든 모델 process가 없는 읽기 전용 환경 확인 기록을 별도로 보존했다. 합성30시험을 TIMEOUT 해결이나 실제 AI 원문 확보라고 쓰지 않는다.
- 최종 측정본은 [final_offline_diagnosis.json](../experiments/m3_8f_r1/final_offline_diagnosis.json), [기존 native 로그 원래 줄번호 발췌](../experiments/m3_8f_r1/native_log_excerpts.json), [실행 환경](../experiments/m3_8f_r1/environment.json), [원본 hash 목록](../experiments/m3_8f_r1/source_inventory.json), [시험 로그](experiments/m3_8f_r1/pytest_full.txt), [최소 승인안](../experiments/m3_8f_r1/MINIMAL_FIX_AND_RETEST_PLAN.md)이다.
- 초기 탐색 JSON의 source_sha256은 줄바꿈 정규화 텍스트 해시였으므로 최종본에서 normalized_text_sha256으로 명칭을 고쳤다. 실제 원본 byte SHA256은 source_files에 별도 기록했다. 기존 실제 실행 증거를 변경한 것은 아니다. 최초 sandbox CIM 권한 제한은 읽기 전용 재조회로 해결했다.

최종 판단 **M3_T08_LIVE_RETEST_APPROVAL_REQUIRED**. 부분 원인 확인과 전체6초 지연 원인 미확정을 구분한다. 사전 로드1회+T08/EX06 각1회 진단 제안은 아직 승인/구현/실행하지 않았다. 최종 평가용 생성·실험자료 승격은 별도다.

## Obsidian 최종 검사

기존 M3.8F 노트·대시보드·현재 상태·할 일·미해결 문제·테스트2개·바로가기 총8개 노트를 필요한 범위에서 갱신했다. 신규 마일스톤 노트나 보관함 구조를 늘리지 않았다. 실제 추가 모델0·실험자료7/8·사람0명·전체원인미확정·재실행승인대기를 명시했다.

75Markdown /717Wikilink(제목23·블록1)/source_paths467/로컬링크94/깨진링크0. Bases1/Canvas1/템플릿5/북마크13·4그룹·앱설정불변. Obsidian GUI는UNVERIFIED, 최신북마크M3.1인 기존문제는 그대로다. 기존 본문·사용자메모는 보존하고 후속절을 추가했다.

승인 경계: 사용자 M3.8F-R1§6에 따라 추가 실제 실행은 승인 전0회다. 구체적인 제안은 빈 사전로드1회와 진단 설명최대2회(T08/EX06각1회), 다운로드/설치0, 기존6/8/12초·32KiB 유지다. 새 연구용 실행 도구와 준비gate 구현도 승인 후 별도로 진행한다. 이 보고의 오프라인30합성시험과 원본로그분석을 실제 TIMEOUT해결로 선언하지 않는다.

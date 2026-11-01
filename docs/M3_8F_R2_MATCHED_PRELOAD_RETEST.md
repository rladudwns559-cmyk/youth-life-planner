# M3.8F-R2 — 동일 설정 사전 로드 후 T08·EX06 실제 진단

2026-10-26 KST. **M3_T08_EVALUATION_MATERIAL_READY**.

승인된 빈 사전 로드1회→T08 1회→EX06 1회를 순서대로 실행했다. 사전 로드는성공했고, 두 설명 요청 모두 모델 재로딩 없이 후보 정확 일치/기존 Output Validator를 통과했다. 기존6/8/12초·32KiB 제한을 유지했다. T08 실제 원문을 신규 자료판에 채택해 **A/B8/8쌍 준비/실제 참가자 대기**다. 사람 이해도·AI 추가 가치 검증은 아직0명/0응답으로 미실행이다.

## 1. 승인 범위와 실행 수

- 동일 Ollama0.40.11, Qwen3 4B Instruct2507 Q4_K_M. tag digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
- 기존 설치 archive/config/모든 model layer SHA256을 재확인했다. 재설치/다운로드/유료API/외부전송0.
- 빈 사전 로드 **1회**, 실제 설명 생성 **2회(T08→EX06 각1회)**. 자동 재시도/추가 생성0.
- 기존 T08 실패2건은 원본 그대로, 이번은 `R2_DIAGNOSTIC_T08`, `R2_DIAGNOSTIC_CONTROL_EX06`로 분리했다.
- 사용자 R2 후속 지시에서 “실제 원문+기존 검사 통과 시 A/B 추가”를 승인했으므로 별도3번째 생성 없이 해당 진단 원문을 자료에 넣었다. R1의 원인 조사 제안과 이번 추가 승인 범위를 구분한다.

## 2. 사전 로드 성공 여부와 실제 설정

기존 Provider `_build_request` 결과를 복사해 messages만 빈 배열로 바꿨다. model/format schema/stream=false/truncate=false/**shift=false**/temperature0/num_predict256/num_ctx16384는 그대로다. 기존 `_post`의 proxy차단·redirect거부·timeout6·read32769/32KiB 검사를 그대로 사용했다. 사전 로드에만 연구 도구의 외부8초 gate를 두었으며 실패 시 설명 호출0으로 끝난다.

사전 로드 전체 **5645.947ms**(기존 전송 관측5586.729ms + metadata/gate 등), envelope162bytes, done_reason=load/빈content다. native 실행은14:07:13.917 runner 시작(port64243)→14:07:17.464 준비, 시작 관측3.54초였다. 실제 인자 `-c16384 -np1`, context-shift 비활성, 모델명/digest/ready를 확인한 뒤에만 설명으로 진행했다.

이는 준비 시간과 설명 요청 시간을 분리한 실측이다. cold 요청 전체가1.76초에 끝났다는 뜻은 아니며 사전 준비5.65초를 숨기지 않는다. `/api/ps`에 이름만 있다는 이유로 warm이라고 판정하지 않았다.

## 3. 모델 재로딩 발생 여부

이번 native log의 runner 시작은 **총1회**다. T08 전후/EX06 전후 모두 추가 시작0, 같은port64243/shift=false/context16384/parallel1을 유지했다. 기존 두 실패에서의 true→false 재로딩과 다르다. 모델 준비 완료 뒤 첫 설명인 T08의 cached prompt는0이었다. 별도 생성형 warm-up을 호출하지 않았다.

## 4. T08·EX06 지연과 공식 metrics

단위ms. 서비스 wall time은 기존 `service.explain` 호출을 측정한 client_latency다. 모델 공식 nanosecond metrics를ms로 표시했으며 native 처리 시간과 구별한다.

| 측정 | T08 | EX06 |
|---|---:|---:|
| 서비스 전체 wall | **1755.48** | **1733.28** |
| 기존 `_post` wall | 1718.88 | 1707.04 |
| 공식 model total | 1689.6116 | 1689.7879 |
| 공식 load_duration | 12.4902 | 13.7647 |
| 공식 prompt_eval_duration | 187.6330 | 48.7120 |
| 공식 eval_duration | 1459.0210 | 1581.9840 |
| 공식 prompt_eval_count | 250 | 266 |
| 공식 prompt_eval_cached_count | 0 | 138 |
| 공식 eval_count | 97 | 106 |
| 완료 envelope | 685bytes | 709bytes |
| 후보 정확 일치 | 통과 | 통과 |
| 기존 Output Validator | 통과 | 통과 |
| Fallback/TIMEOUT | 없음/없음 | 없음/없음 |

공식 load_duration12~14ms는 이미 로딩된 runner를 사용하는 요청의 metric이며 cold weight 로드 시간으로 쓰지 않는다. native prompt timing의 EX06 처리128tokens는 공식 prompt266 중 cached138을 제외한 값과 대응한다. 과거 실패의 slot342를 생성 토큰이라고 추정하지 않고 이번 공식 eval_count97/106을 사용했다.

## 5. TIMEOUT 위치·취소 관측

두 요청 모두 TIMEOUT 없음. open→headers→read를 기록했다. T08은 open시작13.389ms→headers1718.631ms→read완료1718.888ms, EX06은14.979→1706.757→1707.077ms였다(각 transport 관측 시작 기준). connect/TLS 등 urllib 내부 단계를 별도로 계측한 것은 아니므로 이를 순수 네트워크 연결 시간이라고 하지 않는다.

두 요청 모두 done=true/done_reason=stop과 완성 원문을 받았고 기존 검사 뒤 반환했다. 이번 native log에 task cancel은 없으며 정상 release를 확인했다. 서비스8초/화면12초 제한에 도달하지 않았다. 이미 TIMEOUT된 과거 요청에 이번 문장을 늦게 붙이지 않았다. 기존 late-response/전체대체 계약은 변경0 및 전체 회귀로 보존했다.

## 6. 정책 상태·금액·UNKNOWN 보존

각 응답의 Facts, changed_facts, 정책ID/전후상태/rules/source, unknown_information, next_actions를 해당 Python canonical과 대조했다. 모델이 바꿀 수 있는 summary/policy text 외에는 동일하다.

T08: 월소득150→180만원, 월세45→55만원, 미취업→취업, 여유자금50→70만원, 저축 투입30→30만원. SAMPLE-001 PASS유지/SAMPLE-002 PASS→FAIL/SAMPLE-003 UNKNOWN유지(가구소득 미입력), 실제 지원금0원. 입력/고정정답을 바꾸지 않았다.

실제 선택 원문은 요약 “월 예산에서 여러 항목의 변화를 비교했어요.”, 정책별 “이 정책의 종합 판정은 그대로예요.” / “이 정책의 종합 판정이 바뀌었어요.” / “종합 판정은 그대로이며, 추가로 확인할 조건이 있어요.”다. 기존 현재 요청 후보에 정확히 속하며 UNKNOWN 조건을 지우지 않는다. 이를 새 추론이나 실제 수급 확정으로 해석하지 않는다.

## 7. T08과 EX06 비교 및 원인 판단

T08 서비스 wall은EX06보다22.20ms 길었다. T08은처음읽는250prompt/cache0, EX06은prompt266/cache138로 실행 순서·cache 조건이 다르다. T08 출력97tokens가EX06의106보다 적었고 입력 처리/생성 시간이 서로 상쇄됐다. 단2건으로 task 자체의 시간 차이·평균/p95/일반 성능을 추정하지 않는다.

설정 일치 사전 로드와 준비gate를 적용한 이번 실행에서는 재로딩과 T08 반복TIMEOUT이 발생하지 않았다. 이것은 R1에서 확인한 준비 설정 불일치에 대한 최소 보완이 **이번 조건에서 충분했다는 증거**다. 과거 둘째 실패의 전체 지연 원인을 소급 분해하거나 모든 기기/cold/부하에서 재발하지 않는다고 보장하지 않는다.

## 8. A/B 자료 준비 상태와 버전

현재 자료판: **m38f-study-v2-r2**, [프로토콜](experiments/m3_8f_r2/study_v2/PROTOCOL.md), [실험자 정답/원문/배정](experiments/m3_8f_r2/study_v2/private/study_key.json), [실제0명 결과표](experiments/m3_8f_r2/study_v2/results/initial_summary_real.md).

기존v1의7개 과제 전체 객체/A/B/질문/정답과20슬롯 배정이 동일하다. T08 입력·질문·정답·A를 보존하고 R2 실제 채택 B만 추가했다. 원본v1·기존 두 실패·기존30개 파일은 수정하지 않았다. 과제ID T08은같고 자극자료 보완이므로 자료판version을올렸으며 바뀐 이유를 기록했다.

20개 예정 참가자 세션(각A4/B4)과 합성SYN001 8과제 QA를 만들었다. 원본 빌더의 사람용 세션에ready표기가 없으면 화면gate와 맞지 않는 점을 확인해 신규 자료판에만ready=true/version을 명시했다. 원본 빌더/과거자료/제품React는 수정하지 않았다. 제목/질문/후보 문장을 재작성하지 않았다. 보조X/Y선호는 주 과제 후에만 보인다.

사람 평가 상태: **M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING**. 예정20슬롯과SYN QA는 실제 사람이 아니다. 참가자0명/응답0건, 정답률·완료율·평점·선호·유용성은미측정/null이다. 목표80%·4/5·모순0을 실적으로 올리지 않는다.

## 9. 신규 코드·테스트 및 UI QA

신규 연구용 `tools/run_t08_preload_diagnostic.py`, `tests/test_t08_preload_diagnostic.py`와 이 보고서/신규자료판만 추가했다. 제품 Provider/Prompt/후보/검증기/Fallback/API/React/계산·판정 엔진은 변경0이다. 전송 관측 wrapper는 이 연구 프로세스에만 잠시 붙이고 원래 함수/객체를복구하며 기존 `_post`를 그대로 호출한다.

최초 gate·관측 모의21passed(0.64초) 후 실제 증거/자료판 검증을 추가해 **신규45passed(1.14초)**. 사전 로드의설정전체일치·불일치/실패시생성0·기존6초/32769read관측·예산/순서/재로딩·T08원문/정답/기존7개/20슬롯눈가림/실제0명표를확인했다. 신규/전체회귀 최초 실패0, 기존 테스트 기대값 변경0.

실제 브라우저에서는 **SYN001/합성QA**로8과제→T08→마지막보조X/Y→JSON내보내기를확인했다. 모든답DK·평점/선호빈칸의 도구조작기록이며 사람성과가아니다. 실제 T08문장·Python표/정책/UNKNOWN이보이는 화면증거를보관했다. desktop 기본크기만확인했고 실물휴대폰/ObsidianGUI를완료라고하지않는다. 실제 모델은브라우저QA에서호출하지않았다.

## 10. 전체 회귀

**Backend12315passed/1skipped/1warning(92.64초)** = 기존12270+신규45. Frontend **115passed(9.78초)**, TypeScript·Vitebuild성공(Vite1.36초). 기존skip은실제NTFS파일symlink생성권한/DeveloperMode부재, warning은Starlette/httpx deprecation이다. 보안검증완료로승격하지않았다.

## 11. 서버 종료·기본 정형 복귀

실측wrapper의finally에서 본시험서버PID3116과 그 자식runner17644를 경로/PPID로확인해종료했다. 후속프로세스조회에서모델서버/runner없음을확인했다. QA서버도종료했다. 기존설정환경값AIX_EXPLANATION_PROVIDER/AIX_OLLAMA_MODEL/AIX_EXPLANATION_CONTRACT는미설정이고get_provider는**NoProvider/configured=false**다. API서버나기본제품설정을이번에AI로바꾸지않았다. 로컬설치파일은보존했고다운로드/새설치/계좌연결/외부문의0이다.

## 12. 보호 상태

원래371파일SHA256·크기·mtime, 원래T08실패2건/원본연구script·log, 원래7개AB/고정30, Coveragefreeze/GV01~15/BV01~16/golden/실제release6을 보존한다. 실제상품만기계산0/미검증지원금0원/실제안산DRAFT·CONDITION_SLICE/ResidenceHistory OFFICIAL_INQUIRY_REQUIRED/M2.77SYNTHETIC_ONLY/IBK공식회신대기유지.

## 13. 근거 위치

[실제2건+사전로드원문·metrics·trace](experiments/m3_8f_r2/actual_diagnostics.json), [T08 자료채택 원문과부모SHA](experiments/m3_8f_r2/t08_accepted_for_study.json), [종료기록](experiments/m3_8f_r2/cleanup.json), [설치동일성기록](experiments/m3_8f_r2/runtime.json), [native 준비/종료구간](experiments/m3_8f_r2/native_after_cleanup.json). 이전실패는원래M3.8F evidence와R1분석에남아있다. 저장된원문을다른모델/새합성설명으로대체하지않았다.

## 14. Obsidian 및 최종 판단

기존M3.8F노트/대시보드/현재상태/할일/미해결문제/테스트/바로가기에이번2건·설정일치·재로딩0·8/8자료판·실제0명/응답0건·다음수동평가를기록한다. 앱설정·기존본문이력·GUI미확인상태를보존하며 최종링크검사는아래추가한다.

**M3_T08_EVALUATION_MATERIAL_READY**는 T08실제원문과실험자료준비범위다. 전체사람평가나AI우수성을완료했다는뜻은아니다. 사람평가최종상태는 **M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING**이다.

다음최소작업하나: **실제자원참여자5명의동의를받아새자료판8과제평가**. 모집/연락/참여동의는담당자가직접진행하고가상응답으로대체하지않는다. 이번요청의추가모델실행예산은전부사용했으며자동실행을예약하지않았다.

## 최종 Obsidian·파일 검사

기존M3.8F노트·대시보드·현재상태·할일·미해결문제·테스트2개·바로가기 총8개노트를갱신했다. 원본실패/R1승인대기는당시이력으로보존했고 최신상태는실측2채택·자료8/8·사람평가대기로표시했다. 노트속성status는partial이며 실제사람평가완료로올리지않았다.

75Markdown /725Wikilink(제목32·블록1)/source_paths495/로컬링크102/깨진링크0. 앱설정·Bookmarks13/4그룹·Bases1·Canvas1·템플릿5는그대로다. ObsidianGUI UNVERIFIED/기존최신북마크M3.1문제는유지한다. 임시Vault갱신본의속성명에숫자가들어간1건은실제반영전에lowercase/underscore이름으로고쳐검사를통과했다. 제품신규/회귀최초실패0과이문서검사이력을구분한다.

기존371파일metadata·원래T08실패2건/7개AB·원본script/log·release6/GV/BV/freeze 불변을마지막으로확인했다. 신규코드는연구도구/시험뿐이며 기존Provider/Prompt/후보/검증기/시간제한을완화하지않았다. 실제상품계산0·미검증지원금0원과정책/거주기간/보안보류를그대로유지한다.

[T08실제문장자료화면](experiments/m3_8f_r2/t08-actual-stimulus.png)과 [검증원장](experiments/m3_8f_r2/verification.json)에이번실측과자료판/회귀/정리/사람0명상태를연결했다. 합성QA JSON은synthetic/SYN001/8행/모든DK/빈평점으로strict검사를통과했고원자료를사람응답으로집계하지않았다. 실제사용자모집·동의·설문실시는아직없다.

최종 판단: **M3_T08_EVALUATION_MATERIAL_READY**. A/B **8/8**이며 사람평가는 **M3_EXPLANATION_EVALUATION_READY_PARTICIPANTS_PENDING**. 다음최소작업은실제5명동의후8과제비교평가다.

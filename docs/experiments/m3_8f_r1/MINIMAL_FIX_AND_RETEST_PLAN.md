# T08 최소 보완 및 재검증 승인안

2026-10-26 KST / **미구현·미실행·사용자 승인 대기**.

## 목적과 근거

기존 시험의 사전 로드는 shift를 생략했고 실제 Provider는 shift=false였다. 기존 로그는 shift 활성 runner→비활성 runner 재시작을 두 차례 보여준다. [동일 버전 공식 scheduler](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L159-L177)는 Qwen3의 생략 값을 true로 해석하며 [재사용 검사](https://github.com/ollama/ollama/blob/v0.40.11/server/sched.go#L1358-L1364)는 이 설정 차이를 재로딩 조건으로 삼는다. 첫 실제 요청은 재로딩 중 취소됐다. 둘째 요청은 새 runner에서 생성 도중 취소됐으므로 동일 설정의 로드 완료 상태에서 실제6초 내 완료하는지 추가 근거가 필요하다.

## 최소 수정 범위

제품 Provider/Prompt/후보/정확 일치 검사/정형 대체/계산기/정책/React는 수정하지 않는다. 이전 실행 script와 결과도 그대로 보존한다. 승인되면 **새 연구용 실행 도구1개** `tools/run_t08_preload_diagnostic.py`와 관련 모의 테스트만 별도 단계에서 작성한다. 파일명은 제안이며 현재 존재하는 구현으로 보고하지 않는다.

사전 로드 요청은 기존 Provider의 실제 `_build_request(prepared)` 결과를 복사한 뒤 **messages만 빈 배열로 바꾼다**. model/options/shift=false/truncate=false/stream=false/format은 그대로라 후보/schema/실제 요청을 변경하지 않는다. [Ollama 공식 Chat 경로](https://github.com/ollama/ollama/blob/v0.40.11/server/routes.go#L3008-L3027)는 빈 messages를 로드 응답으로 처리하고 생성으로 진행하지 않는다. 비어 있는 사전 로드는 모델 설명으로 세지 않는다.

```text
기존: { model, messages:[], stream:false, options:{num_ctx:16384} }
제안: existing_provider_request 복사 → messages:[]
      나머지는 기존 model/format/stream:false/truncate:false/shift:false/
      options:{temperature:0,num_predict:256,num_ctx:16384} 유지
```

추가 변경은 사전 로드 실패 시 중단하는 gate다. 현재 script는 사전 로드 TIMEOUT 뒤 /api/ps에 모델이 없더라도 최대20번 조회 후 다음 설명으로 진행할 수 있다. 제안 도구는 load 응답 완료·모델명/digest·동일 설정 native runner 준비를 확인하지 못하면 설명을 **호출하지 않는다**. `/api/ps`의 단순 모델 존재만으로 warm이라고 선언하지 않는다.

이 수정은 사전 준비의 잘못된 warm 해석을 고치는 것이다. 제품 설명의6초·8초·12초를 늘리거나 모델 준비를 제품 요청 안에서 몰래 재시도하는 기능이 아니다. cold 첫 요청의 성공을 보장하지 않으며 커널/프롬프트 캐시가 준비된 warm 결과와도 구분한다.

## 요청하는 실제 실행 예산

**추가 설명 생성 최대2회**이며 자동 재시도는 없다.

1. 기존 동일 모델/환경의 설정 일치 빈 사전 로드 **1회**. 전송6초·응답32KiB 유지. 실패/불일치면 여기서 중단한다.
2. 동일 runner에서 **T08 원인 조사1회**. 이전 두 실패와 별도 phase/파일/요청번호. 기존 Provider·서비스·검증기를 그대로 호출한다.
3. 같은 환경에서 **EX06 비교용 조사1회**. 정상30 중 wire 최대 사례다. 기존 EX06 원문/30개 결과를 덮어쓰지 않는다. T08보다 뒤에 실행해서 T08을 먼저 캐시 예열하지 않는다.

실제 T08 입력/정답/후보는 현재 고정본이다. 각 조사 요청은 전송6초·서비스8초/32KiB·최대256토큰, 클라이언트 재시도0.6초는 기존 urllib의 소켓 timeout이며 전체wall time과 같다고 보장하지 않는다. 서비스 호출2회의8초 제한과 별도 빈 사전 로드를 구분해 기록한다. 기존 실패 관측으로 약18초의 요청 시간을 예상하지만 고정 실행시간 보장은 아니다. 사전 로드에는 연구 도구만의8초 외부 deadline도 제안하며 이는 제품의 기존 제한을 늘리는 변경이 아니다. 모델 hash 확인·서버 기동/메타데이터 조회·정리 시간은 별도 기록한다.5분짜리 무한 warm-up이나 여러 번 성공할 때까지 재생성하지 않는다.

자원: 기존 Ollama0.40.11 + Qwen3 4B Instruct2507 Q4_K_M만 사용. 다운로드/설치/유료API/외부 전송0. 과거 native 로그 기준 GPU self 약4,865MiB(모델2,375+KV2,304+compute186), host 약376MiB에 기타 런타임/동시 앱 사용량이 추가된다. 이는 예상치이고 새 실행의 실측은 아니다. 환경 변수·드라이버·보안·컨텍스트16,384·모델·병렬1을 바꾸지 않는다. 메모리 확보를 위해 사용자 앱을 임의 종료하지 않는다.

기존 서버가 있으면 소유권을 확인하고 다른 작업의 서버를 인수하지 않는다. 이번 단계가 시작한 서버/runner만 PID와 경로로 확인해 종료한다. 실제 입력은 합성 사용자만 사용하고 제품에 진단 로깅을 추가하지 않는다.

## 진단 기록과 중단 조건

- 요청 직전/직후 monotonic 시각, 모델 digest, phase, 자체 request ID, 사전 로드 결과, native runner PID/port/shift/context, 기존 서버 유무를 기록한다.
- 전송 wrapper는 기존 요청을 바꾸지 않고 `open 시작/응답 header 도착/read 종료/예외` 구간을 관측한다. 예외 원문 대신 타입/단계만 저장한다. 기존6초는 변경하지 않는다.
- 가능한 공식 metrics(prompt_eval_count/cached_count/eval_count/load/prompt/eval durations)와 완료 원문·정확 일치·전체 대체·Python 불변 검사를 보존한다. 없는 metrics는 null이다.
- 사전 로드 실패/설정 불일치/다른 서버 소유·동시 작업 불명확이면 실제 생성0회로 종료한다. 정상 T08을 얻기 위해 새 예산을 자동 추가하지 않는다.
- 조사에서 정상 원문을 얻어도 `cause_diagnostic` 증거로 보관한다. 실험자료 B 확정/버전 갱신은 검토 후 별도 확정 단계에서 결정한다. 이번 승인 요청에는 별도의 최종 평가용 생성 실행이 포함되지 않는다.
- T08 원본2회, 조사 실행, 향후 평가 확정 실행은 각자 구분한다. 늦은 응답을 이미 TIMEOUT된 사용자 결과에 반영하지 않는다.

## 판정

현재 **M3_T08_LIVE_RETEST_APPROVAL_REQUIRED**다. 동일 설정으로 runner 재시작이 없어졌는지와 T08/EX06 각각6초 내 완료 여부를 확인해야 한다. T08만 실패하면 후보 schema/출력 생성 부담 등 다음 원인을 새로 분석한다. 둘 다 실패해도 시간 제한/검증기 완화를 자동 제안·구현하지 않는다. 현재 A/B7/8, 사람0명/응답0건, 기존 M3.8F 시작 보류는 유지한다.

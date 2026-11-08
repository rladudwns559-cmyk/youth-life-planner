# M3.7 — 실제 로컬 LLM 연결·설명 검증 최종 보고

확인일: 2026-10-26. 최종 판단: **M3_LOCAL_LLM_QUALITY_REVISION_REQUIRED**.

사용자의 설치 승인을 받은 뒤 로컬 모델의 GPU 실행을 확인했다. 그러나 기존 서비스 계약으로 실행한 고정 30개는 모두 시간 초과로 정형 설명을 반환했다. 실제 생성형 설명 기능이 완료됐다는 의미는 아니다.

## 1. 기존 M3.6 재사용 구조

기존 ExplanationFacts, Prompt, Output Validator, 정형 fallback, FastAPI endpoint, React 화면, 고정 30개 시나리오와 테스트를 재사용했다. M3.6 보고서·계약, 최종 기획서 v1.2, Obsidian 규칙을 먼저 검토했다.
계산과 정책 판정은 기존 Python 엔진의 책임이다. 모델 출력은 엔진 입력으로 돌아가지 않는다. 전국 청년이 최종 대상이며 안산은 첫 검증 지역이라는 제품 방향도 유지했다.

## 2. 노트북 하드웨어 확인

| 항목 | 실제 조회 결과 |
|---|---|
| OS | Windows 11 Home, 64비트, 10.0.26300/build 26300 |
| CPU | AMD Ryzen 7 260 w/ Radeon 780M, 8코어/16논리 프로세서 |
| RAM | 설치 16GiB, OS 사용 가능 15.309GiB |
| NVIDIA GPU | RTX 5050 Laptop GPU, VRAM 8151MiB, 조회 당시 free 7822MiB |
| 드라이버 | NVIDIA 572.97, WMI 32.0.15.7297 |
| 저장공간 | C: NTFS, 조사 시 여유 약 347.64GiB |
| Python | 기존 .venv 3.12.14, PyTorch 미설치 |
| CUDA | nvidia-smi의 12.8 지원 표시, nvcc 없음. 승인 후 Ollama CUDA12 backend에서 실제 GPU 추론 확인 |

WMI의 NVIDIA AdapterRAM은 약 4GB로 표시됐으므로 VRAM은 nvidia-smi의 8151MiB를 기준으로 했다. 드라이버의 CUDA 표시는 toolkit 설치나 모든 backend 호환성 보장이 아니다. 원시 근거는 [환경·설치·보존 기록](evidence/m3_7_local_llm_preparation.json)에 있다.

## 3. 로컬 Provider 설치 상태

설치 전에는 PATH, 등록 프로그램, 알려진 Ollama/LM Studio/HuggingFace 캐시와 11434/1234 포트에서 사용 가능한 환경을 찾지 못했다. PC 전체 디스크를 검사한 것은 아니다.

| 후보 | 조사 결과 | 선택 |
|---|---|---|
| 기존 환경 | 확인 범위에서 없음 | 우선 조사 완료 |
| Ollama | Windows·JSON Schema 지원, 기존 adapter 있음, MIT | 한 개 설치 |
| LM Studio | 공식 로컬 서버 제공, 미설치. 앱의 상세 배포 조건은 이번에 확정하지 않음 | 설치하지 않음 |

[Ollama Windows](https://docs.ollama.com/windows), [JSON Schema 출력](https://docs.ollama.com/capabilities/structured-outputs), [LM Studio 공식 서버 문서](https://lmstudio.ai/docs/developer/core/server)를 확인했다. 추가 Provider는 연결하지 않았다.

## 4. 검토한 모델 후보

| 모델/양자화 | 다운로드 | 판단 |
|---|---:|---|
| Qwen3 4B Instruct 2507 / Q4_K_M | 약 2.50GB | 다국어·non-thinking 모델. 8GiB급 GPU에서 우선 시험할 후보로 선택 |
| Qwen2.5 7B Instruct / Q4_K_M | 약 4.7GB | 한국어/JSON 지원 후보지만 메모리 여유가 줄어 이번에는 제외 |
| Qwen2.5 3B Instruct / Q4_K_M | 약 1.9GB | Qwen Research License의 비상업 연구·평가 제한 때문에 우선 제외 |

다운로드 크기만으로 속도나 한국어 품질을 추정하지 않았다. [4B 공식 태그](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M), [7B 공식 태그](https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M), [3B 라이선스](https://ollama.com/library/qwen2.5:3b-instruct-q4_K_M/blobs/b5c0e5cf74cf)를 각각 확인했다.

## 5. 실제 선택 모델

**Ollama v0.40.11 + qwen3:4b-instruct-2507-q4_K_M** 한 개를 설치했다. 모델은 GGUF 4.0B, Q4_K_M이다.
전체 manifest digest는 `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`이다. 모델 config·weights·template·license·params 5개 파일의 크기와 SHA256을 고정 manifest와 대조했다. 다른 모델은 내려받지 않았다.

## 6. 라이선스·사용조건

모델의 [Apache 2.0](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/LICENSE)과 런타임의 [MIT](https://raw.githubusercontent.com/ollama/ollama/v0.40.11/LICENSE)를 확인했다. 공개 시연·상업 이용이 가능한 조건의 후보이며, 재배포할 때는 라이선스·저작권 고지와 해당하는 NOTICE, 변경 표시 의무를 검토해야 한다.
동봉된 llama.cpp 및 vendor 라이선스 파일을 보존하고 일부 고지를 확인했다. 모든 CUDA 라이브러리의 재배포 권한까지 확정한 것은 아니다. 이번에는 모델이나 런타임 바이너리를 재배포하지 않았다. 사용료가 있는 외부 AI API나 결제도 없었다. 전력·통신의 실제 원화 비용은 측정하지 않았다.

## 7. 사용자 승인

설치 전 정확한 버전, 용량, 위치, 12GiB 작업 예산, 로컬 전용 실행 조건을 제시했다. 사용자가 **“설치·다운로드·실제 30개 검증 승인”**이라고 답한 뒤 실행했다.
초기 INSTALL_APPROVAL_REQUIRED는 승인 전 이력이며 현재 대기 상태가 아니다. 추가 모델·드라이버·외부 AI·결제 승인을 받은 것으로 확대 해석하지 않았다. [승인안과 실행 이력](M3_7_LOCAL_LLM_INSTALL_PLAN.md)에 남겼다.

## 8. 설치·다운로드 결과

| 항목 | 실측 |
|---|---:|
| 공식 Ollama ZIP | 1,586,356,606 bytes |
| ZIP 해제본 | 2,231,045,135 bytes |
| 모델 config+layers | 2,497,293,803 bytes |
| 승인 위치 전체 점유 | 6,314,703,988 bytes, 약 5.88GiB |

12GiB 작업 예산 안에서 완료했다. ZIP SHA256은 `bda4a493ba8a7c24d57263cd843cd68cee84f44aed4299eeed532acad7eda12a`이다. 공식 릴리스와 일치했다.
위치는 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\local-runtime`이다. 관리자 권한, 설치 관리자, 시작프로그램, 영구 PATH/환경변수, 드라이버·보안 설정은 변경하지 않았다. Ollama가 사용자 폴더에 자체 키 두 파일을 자동 생성했으며 내용은 읽거나 전송하지 않았다.

## 9. 실행 API

기존 `http://127.0.0.1:11434/api/generate`를 사용했다. 고정 모델 ID, JSON Schema, stream=false, temperature=0, num_predict=4096, 응답 상한 32768bytes, 통신 6초/서비스 8초/화면 12초, 요청당 1회·자동 재시도 0회를 보존했다.
context 16384, 병렬 1, 적재 모델 1, cloud off, 요청 본문 logging off는 시험 프로세스에만 설정했다. 서버 버전과 loopback listening, cloud-disabled 로그를 확인했다. 임의 외부 endpoint·프록시·redirect를 허용하지 않았다.

## 10. ExplanationFacts

기존 금액 10개, Before/After/차이, 정책·규칙 ID/상태/사유, 근거, UNKNOWN, 다음 확인사항, 지원금 0원을 그대로 사용했다. Facts 모델과 생성 코드는 변경하지 않았다.
기존 source_refs에 내부 저장소 경로가 있어 **모델에 보낼 때만 익명 SOURCE-ID로 치환하고 응답의 알려진 ID를 원래 출처로 복원**하도록 adapter를 보완했다. 이름·연락처·계좌·키·전체 원본 프로필·불필요한 정책 원문은 추가하지 않았다.

## 11. Prompt 및 JSON 계약

기존 SYSTEM_PROMPT와 ExplanationDocument 계약을 보존했다. Facts와 template의 동일 출처에 같은 별칭을 사용하며, 원본은 deep copy로 보호한다.
별칭 복원이 중복키, NaN/Infinity, 잘못된 JSON, 과대 출력을 정상 문서로 보정하지 않게 했다. 미지 출처, 순서, 금액, 상태, 누락 필드와 자유문장의 오류는 기존 검증기가 거부한다. 정답에 맞추기 위한 응답 수정은 없다.

## 12. Output Validator

**기존 service.py의 검증 규칙과 SHA256을 보존했다.** 금액·상태·ID·사유·근거·UNKNOWN·확인행동을 대조하고, 핵심값은 검증 후에도 서버 원본을 렌더링한다.
이번에는 timeout과 자유영역 숫자 복사를 대체 경로로 처리했다. 자연어의 모든 거짓 인과나 의미 오류를 자동으로 검출한다고 주장하지 않는다. 기존의 엄격한 표현 제한이 사실적으로 맞는 문장도 거부할 수 있다는 한계도 남아 있다.

## 13. 실제 LLM 실행 횟수

**실제 생성 요청은 총 35건**이다.

| 실행 구분 | 요청 수 |
|---|---:|
| 고정 EX01~EX30 | 30 |
| 짧은 한국어 JSON 구동 시험 | 1 |
| 전체 Facts 진단 및 원인 분리 재실행 | 2 |
| 실제 FastAPI | 1 |
| 실제 React 브라우저 | 1 |

mock/test double은 이 수에 포함하지 않았다. 고정30의 완성 응답은 0건이다. 별도 진단 1건의 완성된 전체 문서와 짧은 인사 JSON 1건을 보존했으며, 앞선 전체 진단은 수신 한도 초과로 본문을 보존하지 못했다.
TIMEOUT 응답의 ai_executed=false는 완성된 모델 출력을 받지 못한 기존 metadata이다. 실제 호출 자체가 없었다는 뜻으로 해석하지 않는다.

## 14. 고정 30개 결과

**실제 요청 30/30, 수용 0/30, 거부된 완성 응답 0건, TIMEOUT에 따른 정형 대체 30/30**이다. EX21~30의 기존 fault 라벨은 이력으로만 보존하고 실제 평가에서 mock을 주입하지 않았다.
각 행에 Python 확정 결과, 모델/digest, 원문 null, 지연, TIMEOUT, 정형 결과를 저장했다. 모델의 구조·금액·상태·UNKNOWN·근거 없는 주장·의미는 완성 응답이 없어 평가할 수 없다. **30개의 완성된 생성 설명을 검증했다는 의미가 아니다.**

| 사례 | 요청 지연 ms | 결과 |
|---|---:|---|
| EX01 | 6071.74 | TIMEOUT → 정형 설명 |
| EX02 | 6064.43 | TIMEOUT → 정형 설명 |
| EX03 | 6042.23 | TIMEOUT → 정형 설명 |
| EX04 | 6029.48 | TIMEOUT → 정형 설명 |
| EX05 | 6034.95 | TIMEOUT → 정형 설명 |
| EX06 | 6059.83 | TIMEOUT → 정형 설명 |
| EX07 | 6062.52 | TIMEOUT → 정형 설명 |
| EX08 | 6054.09 | TIMEOUT → 정형 설명 |
| EX09 | 6036.49 | TIMEOUT → 정형 설명 |
| EX10 | 6042.24 | TIMEOUT → 정형 설명 |
| EX11 | 6021.88 | TIMEOUT → 정형 설명 |
| EX12 | 6034.62 | TIMEOUT → 정형 설명 |
| EX13 | 6062.04 | TIMEOUT → 정형 설명 |
| EX14 | 6054.41 | TIMEOUT → 정형 설명 |
| EX15 | 6029.13 | TIMEOUT → 정형 설명 |
| EX16 | 6040.62 | TIMEOUT → 정형 설명 |
| EX17 | 6053.90 | TIMEOUT → 정형 설명 |
| EX18 | 6048.13 | TIMEOUT → 정형 설명 |
| EX19 | 6054.29 | TIMEOUT → 정형 설명 |
| EX20 | 6033.67 | TIMEOUT → 정형 설명 |
| EX21 | 6028.56 | TIMEOUT → 정형 설명 |
| EX22 | 6035.55 | TIMEOUT → 정형 설명 |
| EX23 | 6037.00 | TIMEOUT → 정형 설명 |
| EX24 | 6050.16 | TIMEOUT → 정형 설명 |
| EX25 | 6057.12 | TIMEOUT → 정형 설명 |
| EX26 | 6038.82 | TIMEOUT → 정형 설명 |
| EX27 | 6032.98 | TIMEOUT → 정형 설명 |
| EX28 | 6043.66 | TIMEOUT → 정형 설명 |
| EX29 | 6044.87 | TIMEOUT → 정형 설명 |
| EX30 | 6028.07 | TIMEOUT → 정형 설명 |

[실제 30건 전체 기록](evidence/m3_7_actual_fixed30.json). 기존 고정 입력과 M3.6 결과는 변경하지 않았다.

## 15. 중대한 불일치와 의미 검토

최종 반환 결과의 Python 핵심값 모순은 **0건**이다. 고정30 모델 출력의 중대한 오류 수·정확도는 **평가 불가**다.
별도 완성 EX01 진단에서는 금액·정책·UNKNOWN·근거·확인행동이 일치했다. 다만 summary에 정확한 `0원`과 지원금 문장을 복사해 자유영역 계약을 위반했다. 금액을 지어낸 오류와 금지 영역에 정확한 금액을 복사한 오류를 구분한다.
Codex가 진단 1건을 정성 검토한 결과 한국어와 사실 관계는 맞지만 정형문장 복사로 추가 효용이 낮았다. **사람의 의미 평가 0건, 사용자 이해도 연구 없음**이며 이를 대신했다고 주장하지 않는다. [진단 원문과 검토](evidence/m3_7_real_diagnostic.json)에 범위를 명시했다.

## 16. Fallback 및 실패 원인

고정30과 별도 HTTP/React 각 1건은 모두 TIMEOUT 후 정형 설명으로 대체했다.
첫 전체 진단은 37,098.41ms 후 기존 32KiB 수신 한도를 넘었다. 원인 분리용 재실행만 별도의 60초/256KiB 한도로 수행했고, 34,478.34ms에 받은 문서는 UNSUPPORTED_NARRATIVE로 거부됐다. 이 진단을 운영 계약 통과로 집계하지 않았다.
기존 합성 transport-double 13개(정상 1/대체 12)와 실제 모델 통계를 혼합하지 않았다. 운영 timeout·응답 제한·validator는 변경하지 않았다.

## 17. 지연·성능·메모리

| 항목 | 실측 결과 |
|---|---|
| 고정30 평균 요청 지연 | 6044.25ms |
| 중앙값 | 6042.24ms |
| p95 | 6064.43ms, 최근접 순위 29/30 |
| 고정30 검증 통과율/대체율 | 0% / 100% |
| 모델 GPU 할당 | /api/ps size_vram=size=5,102,307,901bytes, context 16384 |
| NVIDIA 순간값 | 4982MiB 사용, 2841MiB free, GPU utilization 94~95% |
| RAM 순간값 | runner WorkingSet 6,618,263,552bytes, server 16,977,920bytes |
| 완성 EX01 별도 진단 | 34,478.34ms, prompt 5043/output 1932 tokens |
| 반환 문맥 | 6974 tokens, 로그의 truncated=0, context 16384 이내 |
| 응답 envelope | 39,949bytes. 부가 문맥 토큰도 기존 32KiB 수신 제한에 포함됨 |

평균·중앙값·p95는 **정형 대체 완료까지의 요청 지연**이며 모델의 정상 생성 완료 속도가 아니다. 짧은 cold 구동 5,565.55ms도 전체 설명 속도로 일반화하지 않는다.
PrivateCommit 14,859,046,912bytes는 물리 RAM 사용량과 다르며 WorkingSet/GPU와 합산하지 않았다. 고정30 정상 생성 지연 분포와 사람의 한국어 품질 평가는 미측정이다.

## 18. FastAPI 연결

기존 POST `/api/synthetic/explain`에 시험 프로세스 설정으로만 로컬 모델을 연결했다. 실제 HTTP 1건에서 ai_attempted=true/provider_kind=ollama_local → TIMEOUT → deterministic_fallback, no-store, UNKNOWN·지원금 0·Python 값을 확인했다. 소요 시간은 6,375.32ms이다.
품질 미달을 확인한 뒤 **기본 NoProvider로 복구**하고 기존 5개 실제 HTTP 경로를 다시 통과했다. 새 endpoint나 계산 엔진은 만들지 않았다.

## 19. React 연결

기존 화면 코드는 변경하지 않았다. 실제 모델 호출에서 버튼 비활성·로딩 후 “AI 응답 시간이 초과됐습니다” 안내와 정형 대체, 재생성 버튼, 기존 비교 결과 유지를 확인했다.
실제 모델의 검증 성공 설명은 0건으로 성공 화면 검증은 미완료다. 네트워크 오류·재요청·오래된 응답 차단은 기존 18개 설명 화면 테스트를 포함한 Frontend 115개 회귀로 확인했다. 미설정 상태에서 입력 변경 시 이전 설명 제거도 실제 화면으로 확인했다.

## 20. 실제 HTTP·브라우저

실제 모델 HTTP 1건과 브라우저 1건에서 시간 초과 대체를 확인했다. 390px 화면은 clientWidth=scrollWidth=375px, 설명 글자 16px로 가로 넘침이 없었다. 임시 viewport를 복구했다. 실물 휴대폰 및 실제 모델 성공 화면과 구분한다.
화면 증거: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\output\m3.7\actual-model-timeout-mobile-390.png`. 현재 API는 정형 설명 기본값이며 로컬 API8100/React5173은 유지했다.

## 21. 신규 테스트와 최초 실패 이력

신규 Backend 합성 시험 **54 passed(0.95초)**: 고정30의 출처 비공개/roundtrip, 잘못된 JSON 10개, 공유 매핑 1개, transport-double 13개이다. 기존 테스트나 기대값은 수정하지 않았다.
최초 실행은 긴 입력을 pytest 자동 이름으로 사용해 Windows 환경변수 길이 한도를 넘으면서 53 passed/2 errors였다. 새 테스트 ID만 짧게 지정해 54 passed로 해결했다. 환경값이 포함될 수 있는 최초 진단 원문은 보고서/Vault에 복제하지 않았다.
문서 준비 중 stage와 원본 비교가 1회 중단된 이력도 남겼다. 원본 동시 변경 여부를 guard로 확인하고 준비된 문서만 반영한 뒤 최종 감사를 다시 통과했다. 제품 실패와 문서 작업 오류를 구분한다.

## 22. 전체 회귀

| 구분 | 최종 결과 |
|---|---|
| Backend | **11,733 passed / 1 skipped / 1 warning, 70.46초** |
| Frontend | **115 passed, 10.11초** |
| TypeScript | tsc -b 성공 |
| Vite build | 성공, 1.73초 |
| 실제 HTTP | 기존 5개 경로 통과, 실제 모델 시간 초과 대체 별도 확인 |

Backend는 실제 모델 실행·기본값 복구 후 재실행했다. Frontend 코드는 불변이며 통과한 테스트·빌드와 실제 모델 연결 화면을 확인했다.
skip은 기존 NTFS 파일 symlink 생성 권한 증거 미확보, warning은 기존 Starlette/httpx deprecation이다. 기존 의미를 변경하지 않았다. 로그는 `<USER_HOME>\Documents\ChatGPT\AI+X채팅\tmp\m37-pytest-after.txt`, `m37-frontend.txt`, `m37-build.txt`, `m37-http.txt`에 있다.

## 23. 기존 정책·금융상품·동결 계약 보호

기준선 296개 중 기존 변경은 **backend/explanation/provider.py 1개**, 나머지 295개는 SHA256·크기·mtime 불변이다. 신규 파일은 테스트 1개·보고서 1개·승인안 1개·증거 JSON 3개, 총 6개다.
Facts/Prompt/validator/API/Frontend/기존 테스트, Policy/Cashflow/M3.2/M3.3/Coverage/Benefit/Acceptance/Historical6/Cross/Same-call/Raw Bytes 코어와 golden을 보존했다. 실제 release 6개 SHA256, GV01~GV15/BV01~BV16, Coverage freeze도 불변이다.
실제 정책은 DRAFT/CONDITION_SLICE, ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED, M2.77은 SYNTHETIC_ONLY다. 실제 상품 만기 계산 **0개**, 미승인 지원금 반영 **0원**을 유지한다.

## 24. 개인정보·외부 전송·종료 상태

고정 합성 입력만 실행했다. 실제 경제정보·계좌·연락처·키를 외부 AI로 보내거나 원문 로그로 저장하지 않았다. 모델에 보내는 내부 출처 경로도 익명 ID로 바꿨다.
다운로드는 공식 GitHub/Ollama registry, 추론은 loopback/cloud-off였다. 자체 프로세스의 연결 순간 검사에서 Established 대상은 loopback뿐이었다. 전 시간 패킷 감사나 모든 외부 통신 부재를 검증한 것은 아니다.
현재 **Ollama 서버 종료·포트11434 닫힘·기본 정형 설명 복구** 상태다. 승인된 실행 파일과 모델은 보존했다. 영구 설정이나 보안 설정을 변경하지 않았다.

## 25. Obsidian 기록

`M3.7 모델 선택·실행 검증` 노트와 홈/현재 상태/할 일, 마일스톤, 아키텍처·Prompt·Provider, 정책 검증, 테스트, 자료실을 갱신했다. 승인 전 준비와 승인 후 실제 실행을 구분했다.
최종 파일 검사: Markdown 68개, Wikilink 517개(제목12/블록1), source_paths270개, 로컬 파일 링크39개, **깨진 링크0개**다. Bookmarks13개/4그룹, Base1/Canvas1/템플릿5개와 앱 설정8개는 보존했다.
**Obsidian GUI의 Bookmarks/Bases/템플릿은 미확인**이다. 최신 완료 북마크가 M3.1을 가리키는 구버전 상태도 기록했으며 설정 파일을 덮어쓰지 않았다. 플러그인·Sync·Publish를 추가하지 않았다.

## 26. IBK 회신 상태

**이메일 발송 완료 / 공식 회신 대기(사용자 보고)**를 유지했다. 회신 원문·접수번호·날짜는 미확인이다. 중복 문의나 은행 답변 생성은 하지 않았다. 실제 상품 계산 0개를 해제하지 않았다.

## 27. 최종 판단

**M3_LOCAL_LLM_QUALITY_REVISION_REQUIRED**.
실제 GPU 구동·고정30 호출·실패 대체·API/모바일·회귀를 확인했지만 현재 서비스 계약에서 성공은 0/30이다. 시간·응답 envelope·자유영역 계약 문제가 남아 있다. 실제 30개 완성 응답과 사람의 의미 검토, 성공 UI 검증을 완료한 것으로 발표하지 않는다.
기존 계산·판정과 정형 설명을 보존했으며, 현재 모델의 실서비스 연결은 보류했다. 설치 승인 대기 상태는 이미 해소됐다.

## 28. 다음 최소 작업 하나

**M3.8 제안: 설명 문장만 반환하는 경량 LLM 입출력 계약 설계.**
Python의 금액·상태·UNKNOWN·근거 렌더링과 기존 최종 validator를 유지하면서 모델에 전체 핵심 JSON 재생성을 요구하는 비용, 문맥 토큰 부가 응답을 분리하는 최소 설계를 검토한다. timeout을 늘리거나 검증기를 약화해 성공률을 만들지 않는다. 새 계약이나 새 모델 구현은 이번에 추가하지 않았다.

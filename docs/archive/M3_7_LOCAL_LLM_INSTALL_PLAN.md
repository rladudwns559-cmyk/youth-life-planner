# M3.7 로컬 모델 설치·실행 승인안

작성/공식 메타데이터 확인: 2026-10-26. **아래는 승인 전 제안 이력이다. 이후 사용자가 설치·다운로드·실제30개 검증을 명시 승인했고 실행했다. 최종 결과는 아래 승인 후 실행 기록과 M3.7 보고서를 따른다.**
사용자 M3.7 §3/§13/§17: “모델 설치, 대용량 다운로드, 외부 서비스 연결 또는 유료 결제가 필요하면 먼저 사용자 승인을 받는다.”

## 1. 설치 대상과 다운로드 크기

| 대상 | 고정 버전/태그 | 공식 다운로드 크기 |
|---|---|---:|
| Ollama standalone Windows AMD64 ZIP | v0.40.11 | 1,586,356,606 bytes (약 1.59GB / 1.48GiB) |
| Qwen3 4B non-thinking Instruct | qwen3:4b-instruct-2507-q4_K_M | 2,497,293,803 bytes (약 2.50GB / 2.33GiB) |
| 합계 | 한 실행환경 + 한 모델 | 4,083,650,409 bytes (약 4.08GB / 3.80GiB) |

모델 수치는 registry manifest의 config+layers 합계이며 HTTPS/메타데이터 전송량은 별도다. ZIP 해제 뒤 정확한 크기는 아직 알 수 없다. **압축본·해제본·모델·임시 공간을 합쳐 12GiB를 작업 예산 상한으로 제안**하며 실측 점유량이 아니다. 초과가 필요하면 임의 확대하지 않는다. 현재 C: NTFS 여유 공간 347.64GiB.

- [고정 Ollama 공식 릴리스](https://github.com/ollama/ollama/releases/tag/v0.40.11) / [ZIP](https://github.com/ollama/ollama/releases/download/v0.40.11/ollama-windows-amd64.zip). 게시일 2026-10-24T00:30:13Z.
- ZIP SHA256: `sha256:bda4a493ba8a7c24d57263cd843cd68cee84f44aed4299eeed532acad7eda12a`. 승인 후 내려받은 파일의 SHA256이 다르면 실행하지 않는다.
- [공식 Ollama 모델 태그](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M), 카탈로그 ID `0edcdef34593`.
- weights SHA256: `sha256:85e4a5b7b8ef0e48af0e8658f5aaab9c2324c76c1641493f4d1e25fce54b18b9`. [registry manifest](https://registry.ollama.ai/v2/library/qwen3/manifests/4b-instruct-2507-q4_K_M)의 config 및 모든 layer digest도 대조한다. 태그가 바뀌어 다른 내용이면 중단한다.
- [원제작자 모델 카드](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507): 4.0B·비사고 모드. 한국어 실제 설명 품질은 미검증.

## 2. 설치 위치와 실행 범위

제안 위치(아직 생성하지 않음):

- 실행 파일: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\local-runtime\ollama-v0.40.11`
- 모델: `<USER_HOME>\Documents\ChatGPT\AI+X채팅\local-runtime\models`
- 다운로드 임시 파일: 같은 `local-runtime/downloads` 안. 모델을 저장소·Obsidian·공개 저장소로 복제하지 않는다.

공식 ZIP을 검증해 별도 폴더에 해제하고 수동 `ollama serve` 프로세스만 실행한다. 설치 관리자·관리자 권한·서비스 등록·시작프로그램 등록·PATH/영구 환경변수·방화벽/보안 설정·드라이버 변경을 하지 않는다. API는 **127.0.0.1:11434**만 허용한다. LM Studio·다른 모델·외부 AI API를 추가하지 않는다.

환경변수는 시험 프로세스에만 적용: `OLLAMA_HOST=127.0.0.1:11434`, `OLLAMA_MODELS=위 모델 폴더`, `OLLAMA_NO_CLOUD=1`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`.
초기 context는 `OLLAMA_CONTEXT_LENGTH=16384` 제안. 이는 지원 품질/메모리 보장이 아닌 시험 설정이다. 실제 tokenizer 수와 prompt_eval_count로 전체 Facts/출력이 잘리지 않았는지 검증한다. 상한 때문에 Facts를 몰래 생략하지 않는다.

기존 adapter는 API `/api/generate`, schema format, stream=false, temperature0, num_predict4096, 응답32768bytes, 통신6초/서비스8초/화면12초, 요청당1회·자동재시도0회를 유지한다. 최초 적재/생성에 이 시간이 부족할 수 있다. timeout을 숨기거나 한도를 자동으로 늘리지 않는다. cold/warm은 구분해 측정한다.

## 3. 리소스와 호환성의 근거·한계

RTX5050 Laptop GPU **8151MiB**, RAM **16GiB 설치/15.31GiB 사용 가능**, Ryzen7 260(8C/16T), Windows11 Home64비트. NVIDIA572.97은 [Windows 최소551.61](https://docs.ollama.com/windows)보다 높지만 이것만으로 해당 최신 Ollama backend의 GPU 가속을 확정하지 않는다. NVIDIA CUDA12.8 표시는 드라이버의 지원 표기이며 toolkit 설치·PyTorch CUDA 실행 증거가 아니다. nvcc/PyTorch는 확인되지 않았다. Ollama NVIDIA 라이브러리로 시험하며 별도 CUDA/PyTorch를 설치하지 않는다.
**Assumption:** 2.50GB Q4 모델은 8GiB급 GPU에서 우선 시험할 후보이다. KV cache/context/runtime/다른 앱 메모리를 포함한 실제 적합성·속도는 미측정이다. OOM/드라이버 호환 문제는 기록하고 중단하며 드라이버를 자동 교체하지 않는다. `ollama ps`와 nvidia-smi로 실제 GPU 사용과 메모리를 측정한다. AMD iGPU 활용은 이번 대상이 아니다.

## 4. 라이선스·비용·개인정보

- [Ollama MIT 라이선스](https://raw.githubusercontent.com/ollama/ollama/v0.40.11/LICENSE): 사용/수정/배포/판매 허용, 복제·재배포 시 저작권·허가문 보존. 배포 ZIP의 동봉 GPU 라이브러리 제3자 고지도 설치 후 확인하고 런타임 바이너리를 대회 제출물에 재배포하지 않는다.
- [모델 Apache2.0](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/blob/main/LICENSE): 공개 시연·상업 이용/배포 가능한 조건의 후보. 재배포 시 라이선스·저작권/관련고지·존재하는 NOTICE를 보존하고 변경을 표시해야 한다. 상표 사용권을 부여하는 것은 아니다. 이번 범위는 로컬 사용이며 모델 재배포는 하지 않는다.
- 유료 API·구독·결제 없음. 다운로드 데이터와 노트북 전력·메모리·GPU 점유 비용은 발생할 수 있다. 추론당 유료 서비스 비용은 없으며 실제 소비전력·원화 비용은 미측정이다.
- 인터넷은 공식 GitHub 릴리스 및 Ollama registry의 실행 파일·모델 다운로드에 사용한다. 다운로드 서비스에는 접속 IP/메타데이터가 노출될 수 있다. 경제 입력·원문 프로필은 보내지 않는다.
- [Ollama 공식 FAQ](https://docs.ollama.com/faq): 로컬 실행 시 프롬프트를 서비스로 보내지 않으며 `OLLAMA_NO_CLOUD=1`로 cloud/web search를 끈다. 실제 프로세스 설정·통신 범위는 승인 후 확인한다. 아직 모든 네트워크 패킷을 감사한 상태로 주장하지 않는다.
- Facts는 금액·정책/규칙 ID/상태/사유·UNKNOWN·최소 가정만 사용한다. 이름/연락처/계좌/키/원본 프로필/전체 정책 원문은 제외한다. 내부 출처 경로는 wire에서 SOURCE-ID로 대체한다. 사용자 원문 요청/응답을 로그·Vault에 저장하지 않는다. 고정 합성 시험 응답만 평가 기록 대상이다.

## 5. 승인 후 최소 실행 순서

1. 명시적 승인 확인 → 공식 ZIP/모델 한 개 다운로드 및 크기/SHA256/라이선스 확인.
2. loopback/local-only 프로세스 실행 → API 버전/모델 digest/양자화/GPU/메모리·입력 비절단 확인. 실제 모델 1건을 먼저 시험하고 별도 smoke 횟수로 기록.
3. 기존 고정30개 **모두**를 실제 모델로 순차 실행. EX21~30의 기존 test double 오류 이름은 별도 합성 부정 시험으로 보존하되, 실제 평가에서는 주입 provider로 대체하지 않는다. 실제 정상/거부/timeout/미실행을 각각 기록한다.
4. 각 원문 출력·서버 Facts·schema/숫자/상태/UNKNOWN·근거없는 주장·fallback·지연·사람의 한국어 의미 검토를 남긴다. 평균/중앙값/p95와 validator 통과율을 실제 측정한다. 응답이 없는 timeout을 정상 생성 표본으로 분모에 넣지 않는다.
5. 실제 API/React/390px·실패대체·오래된 응답 차단 및 전체 회귀를 확인한 뒤 판정한다. 목표 미달이면 연결을 보류한다. 모델 미실행/시험0건으로 VERIFIED를 선언하지 않는다.

승인 대상은 **이 실행환경 한 개 + 모델 한 개의 위 범위 설치·다운로드·합성 실행 검증**이다. 추가 모델/드라이버/외부 API/결제/대회 업로드/개인 데이터 저장은 포함하지 않는다.

## 6. 승인 후 실제 실행 기록

사용자 답변 **“설치·다운로드·실제 30개 검증 승인”**을 받은 뒤 동일 버전/태그를 설치했다. 공식ZIP SHA256 및 모델 config/layers5개 digest를 모두 확인했다. 실제 점유6,314,703,988bytes(약5.88GiB),12GiB예산 이내. 별도 모델/관리자/드라이버/보안/자동시작/영구환경 변경 없음. Ollama가 자동 생성한 사용자폴더 .ollama/id_ed25519 및 .pub는 존재 여부만 확인했고 내용은 읽거나 전송하지 않았다. CLI stdout은 버려 키 본문을 진단 로그에 복제하지 않았다.

실제고정30요청 모두 기존6초 TIMEOUT→정형대체. GPU실행은 성공했으나 전체JSON진단34.48초/39,949bytes 및 자유영역 숫자복사로 기존validator거부. 운영제한·검증기를 변경하지 않았다. 원인분리 진단 한 건만60초/256KiB의별도제한으로수행했으며운영통과로집계하지않았다. 실제API/390px도TIMEOUT대체확인. 현재 기본NoProvider복구·Ollama서버종료,설치파일/모델만보존. 최종판정 **M3_LOCAL_LLM_QUALITY_REVISION_REQUIRED**. 설치승인을다시요청할필요는없다. 후속최소제안은전체핵심JSON재생성대신설명문장만모델이반환하도록하는경량계약설계이며구현은이번에추가하지않았다.

# M2.76 — Historical Raw Bytes Preparation Contract

**현재 구현 기록 — M2.77:** 제한된 준비 함수·OS helper·합성/NTFS 시험을 추가했다. 현재 판단은 **HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY**다. 실제 NTFS16개는 통과했지만 파일 symlink 생성 권한 부족으로 필수 실제 사례1개를 실행하지 못해 전체 보안 완료를 보류한다. 정확한 구현·시험/실패 이력·남은 경계는 **26절**이다. 기존1~25절/부록의 미구현 표기는 M2.76 설계 당시 기록으로 보존한다.

작성일: **2026-10-24 / Asia/Seoul**. 새 설계 문서1개만 추가한다. 아래 preparation 함수·Windows 보안 처리는 **미구현**이며 이번에는 신규 실행 테스트0개다.

최종 판단: **READY_TO_IMPLEMENT_HISTORICAL_RAW_BYTES_PREPARATION**. 신뢰된 보관소를 대상으로 하는 제한된 Windows 구현의 준비 판단이다. 실제 파일 보안·발급 신뢰·production ZIP 실행·Content 전체·정책 사용 승인이 완료됐다는 뜻이 아니다.

## 1. 목적·범위·확인 근거

허용 보관소의 Review Artifact와 Historical6 원본을 안전한 handle에서 불변 bytes로 확보하고, 기존 M2.75 순수 Orchestrator에 정확한 A/전체 expected/raw7을 전달하는 **외부 I/O 준비 계약**을 확정한다. 새 도메인 모델·정책 검증 알고리즘·프레임워크·서명/권한 서버는 만들지 않는다.

| Source of Truth / 실제 파일 | 확인·적용 |
|---|---|
| HISTORICAL_SAME_CALL_ORCHESTRATION_CONTRACT.md 3~17·23절, historical_artifact_orchestration.py | 실제9입력·P0a~P8·B 진입점·원본 tuple 반환·오류/미완료 경계 |
| HISTORICAL_CROSS_ARTIFACT_VALIDATOR_CONTRACT.md 24절, historical_cross_artifact_validator.py | 기존8입력·None·정상 partial/MISSING/STALE·선택 정책과 전체 release 구분 |
| HISTORICAL_SIX_ARTIFACT_INTEGRATION_REPORT.md, test_historical_six_artifact_integration.py | 원본 저작 DAG·raw20/root·독립 SHA·합성 원본 크기 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md 4~5·30절, 실제 Review 모델/로더 | 내용 주소·기존 archive locator·외부21필드 원본·Entry 참조6 |
| BENEFIT_ACCEPTANCE_REVIEW_CONTENT_VALIDATION_SPEC.md 5~6·17~20절 |11입력 후보·같은 bytes/복원 원본·추가 Source/전체 envelopes/실행 책임 |
| RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md 8~13절, tools/artifacts/bootstrap.py | Windows 공유 제한 패턴·합성 verify-only 한계·backend import 전 실행 신뢰 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md 15~17절, ARCHITECTURE.md 63절 | 동결·실제 slice·공식 문의·same-call 구현과 외부 I/O 미구현 |
| benefit_acceptance.py / benefit_acceptance_review_artifact.py / manifest.py / errors.py | A21필드·R2필드·Entry15필드·ArtifactReference2필드·PolicyDataError |
| benefit_acceptance_review_artifact_loader.py / historical_*_loader.py | Review2필수입력·Historical6 각각3필수입력·기존 strict/직접 binding·오류 유지 |

실제 Orchestrator 모듈은 **historical_artifact_orchestration.py**다. historical_same_call_orchestrator.py라는 alias는 없다. 실제 ZIP bootstrap은 **tools/artifacts/bootstrap.py**이며 업무 엔진 운영 실행기가 아니다. 기존 문서/코드 이름을 바꾸지 않는다.

이 문서의 **A**는 원본 PolicyBenefitAcceptance, **R_pre/E_pre**는 경로 선택용으로 먼저 복원/선택한 원본, **R_final**은 M2.75가 재복원해 반환하는 원본이다. B/RB 등의 철회 원본은 이번 I/O 대상 A를 자동 대체하지 않는다.

## 2. 현재 준비 공백과 네 신뢰 계층

| 계층 | 책임 | 이번 범위 |
|---|---|---|
| A Expected Identity | 독립 발급/보존된 A·전체 expected 기록 및 기대 참조 SHA | 외부 신뢰 전제. 보안 발급/권한/이력 완전성 인증은 미완료 |
| B Raw Bytes Preparation | 허용 경로·실제 열린 파일/handle·bounded read·자원 정리·동일 bytes 보존 | **이번 설계 대상**, 실제 구현/경쟁 시험은 후속 |
| C Same-call Validation | Review·raw6 strict 복원/직접 binding·교차 관계 | 기존 M2.75 실제 호출 재사용, 수정하지 않음 |
| D Implementation Trust | 준비/검증 코드·Python/stdlib·실행 artifact/import 출처 대응 | 별도 production 선행 조건. 이번 설계/회귀로 완료 주장 없음 |

현재 C는 입력 bytes를 검사하지만 어느 파일에서 어떤 권한/handle로 읽었는지 관찰하지 못한다. B가 없으면 잘못된 경로·재열기·교체·과대한 파일·부분 원본을 호출자가 공급할 수 있다. B의 성공이 A/D의 진실성을 인증하지는 않는다.

## 3. 기존 Orchestrator의 정확한 입력·반환

실제 private 함수 `_orchestrate_historical_artifact_validation`은 다음9개 필수 keyword-only 입력과 기존 반환 타입을 가진다. default/optional/우회 옵션은 없다.

| 입력 순서 | 정확한 인자 | exact 타입 |
|---|---|---|
| 1 | expected_acceptance | PolicyBenefitAcceptance |
| 2 | expected_acceptances | tuple[PolicyBenefitAcceptance, ...] |
| 3 | review_artifact_raw_bytes | bytes |
| 4 | benefit_raw_bytes | bytes |
| 5 | coverage_raw_bytes | bytes |
| 6 | policy_envelope_raw_bytes | bytes |
| 7 | coverage_reviews_raw_bytes | bytes |
| 8 | dataset_manifest_raw_bytes | bytes |
| 9 | source_registry_raw_bytes | bytes |

반환은 exact `(R_final, (BenefitSnapshot, EligibilityCoverage, PolicyEnvelope, CoverageReviewContext, DatasetManifest, SourceRegistry))`다. 위 타입명을 담은 설명이며 실제 slot은 이번 호출의 로더 반환 원본이다. A/R/원본6 is·호출 순서·기존 오류를 유지한다. raw7을 직접 반환하는 함수는 아니므로 후속 Content를 위해 bytes를 보존하는 책임은 B에 둔다.

## 4. Review Artifact ref와 trusted locator

A.review_artifact_ref는 모델 차원에서는 비공백 문자열이다. strict Review 프로파일에서는 정확히 `acceptance-review:sha256:<소문자 hex64>`여야 한다. **ref에는 파일 경로가 없다.** R도 review_artifact_ref/entries의2필드이며 원본 위치 필드를 새로 만들지 않는다.

기존 BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC5절의 위치 규약을 재사용한다.

```text
trusted_root / acceptance-reviews / <H>.json
```

H는 독립 expected records의 content-addressed ref suffix다. 새 locator 인자/index/검색/최신 선택·Manifest.review_manifest 전용·SourceRegistry 전용은 필요 없다. trusted_root는 외부 신뢰된 명시 설정이며 ref/사용자/LLM/현재 디렉터리/환경변수에서 자동 추론하지 않는다.

후속 B는 먼저15절의 exact 입력을 검사하고 기존 Review 로더의 `_expected_ref(expected_acceptances)`를 재사용해 공통 ref·유일 ref/revision·문법을 확인한다. 이 함수는 실제 현재 구현에 존재한다. A는 expected tuple의 동일 객체여야 하며 부재/clone은 B 입력 오류다. 공통 ref의 H로만 위 상대경로를 구성한다. helper의 기존 오류는 그대로 전파하고 원본 A.ref를 다시 발급하지 않는다.

legacy opaque ref도 A 모델로는 유효할 수 있으나 이 파일 준비 프로파일에서는 기존 strict ref 오류로 중단한다. 자동 문자열 교정·현재 파일 hash로 ref 갱신·별도 locator fallback을 하지 않는다. 보관소가 없거나 고정 위치에 파일이 없으면 준비 실패이며 실제 저장소의 현재 release를 검색하지 않는다.

## 5. Historical6 참조와 파일 역할

**Stage1의 실제 Review strict 검증과 명시 E_pre 선택이 성공하기 전** 다음 참조에서 파일을 열지 않는다. untrusted JSON을 별도 파싱해 경로만 뽑지 않는다.

| 고정 순서 | E_pre 참조 | raw 역할 | M2.75 인자 |
|---|---|---|---|
| 1 | accepted_terms_ref | BenefitSnapshot | benefit_raw_bytes |
| 2 | coverage_snapshot_ref | EligibilityCoverage | coverage_raw_bytes |
| 3 | policy_envelope_ref | PolicyEnvelope | policy_envelope_raw_bytes |
| 4 | coverage_reviews_ref | CoverageReviewContext | coverage_reviews_raw_bytes |
| 5 | dataset_manifest_ref | DatasetManifest | dataset_manifest_raw_bytes |
| 6 | source_registry_ref | SourceRegistry | source_registry_raw_bytes |

ArtifactReference는 exact path/sha256의2필드다. 실제 constructor는 빈/주변 공백·역슬래시·colon·빈/점/상위 component·제어문자 등을 거부하지만 Windows 장치명/끝점·끝공백/실제 handle 대상까지 검증하지 않는다. Windows 파일 접근 프로파일은8~11절의 추가 거부 규칙을 적용한다. 도메인 constructor/허용값을 변경하는 작업이 아니다.

선택 A는 기존 selector가 요구하는 ACCEPTED여야 한다. REVOKED E의 None 참조는 과거 A의 파일로 보완하지 않는다. E_pre의 원래 ArtifactReference6개를 로컬 tuple로 보존하며 다른 Entry/ref/version을 자동 선택하지 않는다.

## 6. Two-stage Preparation과 전체 순서

| Phase | 동작 | 실패 후 중단 범위 |
|---|---|---|
| Q0 | exact3입력·지원 OS·기존 expected ref helper·A 원본 membership | 파일/Review/Orchestrator 호출 없음 |
| Q1 | trusted_root 문법·depth·길이 검사, drive에서 root까지 안전한 directory chain 확보 | 준비 실패, 확보 handle 전부 정리 |
| Q2 | root/volume·아래 directory/file handle 대상 검사, Review 위치를 같은 handle에서 bounded read | 실패 시 Review 로더/원본6/Orchestrator0회 |
| Q3 — Stage1 완료 | `load_acceptance_review_artifact_bytes(raw_bytes=review_raw, expected_acceptances=원본 전체 tuple)`1회 → 기존 `_selected_entry(R_pre, A)` 직접1회 → 참조6 경로를 전부 사전 검토 | 실패 시 Historical 파일6/Orchestrator0회 |
| Q4 — Stage2 |5절 순서대로 실제 원본6 handle을 열어 검사·bounded read, raw6 확보 | 첫 파일 실패 뒤 나머지 파일 열기/읽기·Orchestrator0회 |
| Q5 | 보존한 directory/file handle metadata를 같은 handle에서 재확인, 읽기 집합 고정 | 실패 시 Orchestrator0회 |
| Q6 | 기존 M2.75에 **동일 A/전체 tuple/Review raw/raw6** 전달, 정확히1회 호출 | 기존 최초 예외 그대로, 정상 결과 없음 |
| Q7 | 같은 handle 최종 상태 점검, 모든 handle 역순 정리 | 변경/정리 실패면 결과 폐기 |
| Q8 |15절의 완전한 `(same_call_result, raw7)` 반환 | 이 단계 이전 부분 반환 없음 |

모든 raw bytes/참조/handle/카운터는 한 준비 호출의 로컬 값이다. 전역 cache·예전 호출 결과·최신 자료 조회·실패 재시도·대체 경로 검색은 없다. 파일 열기는 직렬이다. Q3에서 일부 Entry가 맞아도 전체 Review 검증을 축소하지 않는다.

Review strict 로더는 **전체 정상 준비에서2회** 실행된다. Q3의1회는 경로 선택 전 검증이며, Q6의 M2.75 내부1회는 same-call 검증이다. M2.75 내부 호출 횟수는 여전히1회다. A/expected/raw를 동일 객체로 보존하고, R_pre를 M2.75에 주입하지 않는다. R_final은 새로 복원한 원본이며 `R_pre is R_final`을 요구하지 않는다. 선택 기준 ref/원본 A 및 raw bytes가 고정돼 있으므로 동일 Entry 의미를 재현한다.

참조6를 추출한 뒤 불필요한 R_pre/E_pre 참조를 해제할 수 있다. 원본 A/expected/raw 및 참조6는 그대로 보존한다. 파일 paths를 얻었다는 이유로 Q6의 Review 재검증을 생략하지 않는다.

## 7. Trusted Root·지원 환경·명시 전제

최초 구현 지원은 **Windows 10/11 x64의 신뢰된 로컬 고정 NTFS volume**으로 제한한다. 다른 OS·UNC/SMB/network·removable·ReFS/FAT·가상/사용자 재지정 namespace·cloud reparse 보관소는 명시 거부한다. support 실패 때 일반 open/Path.read_bytes로 내려가지 않는다.

trusted_root는 exact str의 명시 DOS drive 절대 디렉터리(`C:\...`)다. drive root 자체는 보관소로 허용하지 않는다. 뒷 separator/점 component/주변 공백·device/UNC/drive-relative 표기는 거부한다. 한글/공백을 포함한 정상 component는 허용하며 trim/NFC·casefold 정규화를 하지 않는다.16개 이하 root component와14절의 길이 예산을 적용한다.

**Assumption T1 — 보관소 권한:** root와 그 ancestor는 신뢰된 관리자가 배치·보존하며 비신뢰 사용자/서비스가 수정·reparse/rename·mount/drive 재지정을 수행할 수 없다. 보관소 발행자는 호출 중 자료를 덮어쓰지 않는다. 준비 process는 읽기 권한만 사용하고 backup/restore privilege를 활성화해 ACL을 우회하지 않는다. 이번 최소 함수가 ACL 상속/모든 principal/소유권 진실성을 자동 인증하지는 않는다. 운영 배치 검토에서 이 전제를 확인하지 못하면 이 프로파일의 운영 사용을 허용하지 않는다.

**Assumption T2 — 신뢰한 호스트:** 정상 Windows/NTFS/kernel/driver/Python 설치와 독립 expected 발급·원본 보관을 신뢰한다. 악의적인 관리자/동일 process 코드 변조·기존 writable mapping·직접 volume 변경·공격자가 제어하는 filesystem에 대한 보안 격리를 주장하지 않는다.

**Assumption T3 — 좁은 구현 승인:** 후속 합성 구현과 Windows 임시 NTFS 경쟁 시험으로 실제 OS 동작을 확인한다. 이번 문서의 공식 API 조사·기존 회귀는 새 파일 보안 처리의 실행 증거가 아니다. 일반 사용자 업로드/임의 경로를 열어 주는 기능으로 노출하지 않는다.

## 8. Windows 경로 문자열 검토

검증된 E.path도 **파일 I/O에 대한 허가 자체는 아니다.** slash 기준 상대 component를 먼저 전부 검사한다. 통과한 component만 내부 Win32 경로 separator로 조합하며 URL decode/환경 확장/glob·현재경로 보정은 없다.

| 입력/별칭 | 최초 Windows 프로파일 결정 |
|---|---|
| 빈 component·`.`·`..`, 선행 slash·역슬래시·절대/drive-relative | 거부. root와 join해 정규화로 지우지 않음 |
| UNC·device/NT namespace·외부 `\\?\`·`\\.\` | 거부. 내부 handle에서 얻는 volume GUID 표기와 구별 |
| colon/ADS, NUL/control/DEL, Windows 금지 문자 | 거부. 기본 unnamed stream만 읽음 |
| component 끝 공백/점 | 거부, 자동 제거 없음 |
| CON/PRN/AUX/NUL·COM/LPT1~9 및 위첨자1~3·장치 alias | 확장자가 붙은 예약 base도 거부. CONIN$/CONOUT$/CLOCK$도 최소 profile에서 거부 |
| 정상 Unicode component | scalar 문자열로 허용, unpaired surrogate 거부. NFC/NFD 변환 없음 |
| 대소문자 차이·8.3 alias | 최종 handle의 normalized long path와 선언 component가 **정확히 일치**해야 함. alias를 자동 승인하지 않음 |
| 중간 directory가 symlink/junction/reparse | directory handle에서 거부. 마지막 파일만 검사해 통과시키지 않음 |
| hard link | 파일 link count가1이 아니면 내용 읽기 전에 거부.10절 한계 유지 |

Windows 예약명·stream·namespace·끝점/공백·8.3 개념의 공식 근거는 [Microsoft 파일 이름 규약](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)이다. 위의 엄격한 profile/길이·alias 거부는 **이번 설계 선택**이며 기존 ArtifactReference 문법의 수정이 아니다. 기존에 구조적으로 유효한 ref가 이 profile에서 거부되면 원본을 조용히 rename/재발급하지 않고 외부 준비 차단으로 보고한다.

## 9. Same-handle reading과 M2.53 재사용 수준

M2.53 `_protected_zip`은 CreateFileW(GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING), local fixed drive 확인, msvcrt.open_osfhandle→binary stream, 소유권 이전/예외 정리 패턴을 사용한다. `_absolute`는 path.lstat/resolve 기반이며 `_verify`는 같은 stream SHA 재확인과 pathname stat 대조도 한다. **이 코드 전체를 Historical 파일 reader로 호출/복사하지 않는다.** 초기 reparse 검사와 경로 기반 재조회만으로 이번 root chain·실제 대상·hard link·크기 계약을 충족하지 못한다.

후속 구현은 개념을 재사용하되 다음 Win32 절차를 별도 작은 I/O helper로 적용한다. ctypes는 명시 argtypes/restype/use_last_error=True를 사용하고 성공한 handle만 소유한다. Win32 API의 존재를 실제 실행 검증 완료로 보고하지 않는다.

| 대상 | 열기/읽기 계약 |
|---|---|
| drive→root→필요 subdirectory | 각 component를 top-down 기존 directory로 연다. FILE_READ_ATTRIBUTES, FILE_SHARE_READ만, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS + FILE_FLAG_OPEN_REPARSE_POINT. 부모 handle을 유지하며 실제 속성/대상 확인 후 다음 component 진행 |
| 원본 파일7 | GENERIC_READ, FILE_SHARE_READ만(WRITE/DELETE 공유 제외), OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT + FILE_FLAG_BACKUP_SEMANTICS. directory handle을 얻더라도 종류를 검사해 내용 읽기 전 거부하며 privilege는 활성화하지 않음. 장치/pipe/reparse도 거부 |
| 읽기 | 동기 ReadFile, 같은 handle의 현재 position에서 끝까지. 다른 path/stream 재열기·text decode·BOM/개행 보정 없음 |
| 수명 | 열린 파일7 및 검증된 directory handle은 Q7까지 보존. 종료 시 역순 정리 후 반환 |

CreateFile의 공유 모드는 handle 수명 동안 적용되며 충돌하는 일반 write/delete open을 거부한다. OPEN_REPARSE_POINT는 해당 최종 component 처리용이고, 그 자체가 모든 ancestor를 검사하는 기능은 아니다. 속성/확장 속성 접근은 공유 제약의 예외이므로 **이 flag 조합만으로 모든 metadata 변경을 잠근다고 주장하지 않는다**. root chain 검사·T1·같은 handle 사후 검사와 함께 사용한다. [Microsoft CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)

동일 handle로 정상 범위 내 short read는 남은 길이를 이어 읽는다. 초기 길이 전에 EOF/실패가 나오면 부분 bytes를 성공으로 반환하지 않는다. [Microsoft ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile)

## 10. 열린 파일 identity·실제 대상·hard link

문자열을 검사한 path와 실제 읽을 대상의 연결은 **열린 handle metadata**로 확인한다. 별도 Path.exists/is_file/stat 결과를 열린 대상의 인증으로 사용하지 않는다.

| 검사 | 결정 |
|---|---|
| volume | drive fixed 확인과 별도로 열린 root/파일의 GetVolumeInformationByHandleW 결과가 NTFS인지 확인. 같은 volume serial/volume GUID여야 함. API 실패/불일치 시 거부 |
| 종류·속성 | GetFileType은 DISK, directory bit는 역할에 맞음, FILE_ATTRIBUTE_REPARSE_POINT 없음. 이들은 별개 검사 |
| 실제 경로 | GetFinalPathNameByHandleW(FILE_NAME_NORMALIZED + VOLUME_NAME_GUID)의 component 목록을 사용. root의 실제 volume/path component prefix와 **separator 경계/정확한 component**로 비교 |
| 예상 위치 | root의 실제 canonical path + 승인한 상대 component 목록과 실제 target 전체 목록이 정확히 같아야 함. 대소문자/short alias 차이를 casefold로 흡수하지 않음 |
| identity | GetFileInformationByHandle의 volume serial + file index high/low를 최초·읽기 후·Q5·Q7에서 대조. 지원 profile은 NTFS이며 API 실패/정보 부재면 거부 |
| 파일 상태 | 크기·creation time·last-write time·link count·directory/reparse 속성을 같은 handle에서 재비교. last-access time은 읽기로 달라질 수 있어 equality 조건에서 제외 |
| links/역할 alias | 원본 파일은 nNumberOfLinks==1 필수.7역할에서 같은 최종 path 또는 같은 volume/file ID 재사용도 이 I/O profile에서는 거부 |

GetFinalPathNameByHandleW가 제공하는 normalized/volume GUID path는 열린 대상 조회이며 untrusted 입력의 device namespace 허용과 다르다. 단순 prefix 문자열 비교를 하지 않는다. [Microsoft 최종 handle 경로](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)

최종 경로 질의 buffer는 최대4096 UTF-16 units로 제한한다. 필요한 길이가 이를 넘으면 LIMIT_EXCEEDED이며 무제한 재할당하지 않는다. GetFileType의 UNKNOWN은 last-error를 초기화한 뒤 실제 API 실패인지 미지원 종류인지 구분해 OSError 또는 FILE_REJECTED로 중단한다. [Microsoft GetFileType](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype)

volume serial/file index는 두 열린 대상의 equality에 사용할 수 있고, link count는 NTFS 다중 링크 정보를 준다. 파일을 닫은 뒤 ID가 영구 고유하거나 재사용되지 않는다는 증명은 아니다. [Microsoft handle 정보](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandle), [Microsoft 정보 구조체](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information)

GetFileInformationByHandleEx/FileIdInfo의128bit ID도 검토했으나 최초 NTFS 최소 구현은 위 기존64bit index 쌍으로 제한한다. 다른 filesystem의 동일 보장을 가정해 fallback하지 않는다. [Microsoft FileIdInfo](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info)

**identity는 기대 SHA가 아니다.** A/E에는 기대 file ID가 없으므로 최초로 열린 대상의 ID는 그 요청 안의 안정성 비교 기준일 뿐이다. 열기 전에 교체된 정상 단일 링크 파일은 그 자체로 원본 진실성을 증명하지 못하며 기존 SHA 검증이 내용 대응을 판별한다. hard link count1도 과거 다른 위치에서 이동한 이력·원본 발급 신뢰까지 증명하지 않는다.

## 11. TOCTOU·경로 변경·경쟁의 보호 범위

drive에서 trusted_root까지의 ancestor와 모든 필요한 child directory를 **한 component씩 검사하고 handle을 유지**한다. 필요한 ancestor metadata 확인은 허용하지만 archive 밖 파일 본문을 읽거나 디렉터리를 열거하지 않는다. 검증된 실제 volume GUID path를 기준으로 child를 조합해 drive-letter 재해석 혼합을 줄인다. alias/불일치면 즉시 중단한다.

이것은 CreateFileW의 pathname open이다. root handle을 기준으로 한 원자적 상대 open API/NtCreateFile 또는 VSS를 구현했다고 표현하지 않는다. 유지한 chain/share 제한·target metadata 확인·T1의 비신뢰 수정 금지 전제 아래 일반 배치 경쟁을 통제하는 **제한된 정책**이다. 모든 actor/metadata 권한/악성 mapping까지 차단하는 경로 보안 증명은 아니다.

| 시점/경쟁 | 처리·남는 한계 |
|---|---|
| root 초기 open 전 ancestor 교체/drive 재지정 | T1 배치 신뢰 전제. chain/실제 volume/path 검사로 발견한 차이는 거부하나 이전 상태를 알 수 없어 완전 탐지 주장 없음 |
| 검사한 directory rename/delete/일반 write open | share 제한을 유지, 실패/변경 감지 시 중단. directory subtree 전체에 재귀적 잠금을 건 것은 아님 |
| 파일 읽는 동안 일반 write/delete/rename | 충돌 handle은 OS open 실패 또는 경쟁 쓰기 측 거부. 성공한 handle의 ID/속성/길이 재검사 |
| 이미 존재한 writable mapping·특권 변경·같은 process 공격 | 공유 flag만으로 차단 보장 없음. T1/T2 밖이며 실제 보안 승격 금지 |
| 파일 읽은 뒤 내용 path 교체 | immutable bytes는 그대로. Q7까지 metadata 불일치가 보이면 결과 폐기; 닫은 뒤 파일 경로를 계속 고정한다고 주장 안 함 |
| 검사 도중 API 정보 조회 실패 | 다른 이름으로 재조회/검증 생략 없이 실패 |

Q2~Q7에서 ReadFile·metadata·최종 경로는 이미 소유한 handle로만 수행한다. Path.resolve() 뒤 prefix 검사·path 재열기·hash할 때와 parse할 때 다른 파일 읽기는 지원 경로가 아니다. 호출 뒤 같은 경로를 다시 읽어 반환 raw를 대체하지 않는다.

## 12. 독립 Expected SHA와 역할 분리

기대 사슬은 **외부 원본 expected ref의 H → Review raw strict 검증 → 선택 E_pre.ref6 → 원본6 raw → M2.75의 같은 ref/SHA·도메인/교차 검증**이다. Stage1을 통과한 R_pre만 파일 경로 선택에 사용한다. 같은 A/tuple/Review raw가 M2.75에 전달되므로 다른 revision으로 기대값이 바뀌지 않는다.

B는 별도의 SHA 검증 알고리즘을 만들지 않는다. Q3은 실제 기존 Review 로더가 root SHA를 검사하고, Q6의 실제 로더6가 E의 SHA를 검사한다. 읽기 metadata/ID 비교는 B, 파일 raw SHA/strict/domain은 기존 C다. Registry domain fp·mtime/파일 크기·같은 path·현재 release hash는 expected raw SHA를 대신하지 않는다.

원본6의 SHA 불일치는 모든 bytes를 준비한 뒤 Q6에서 드러날 수 있다. 이때 이미 읽은 나머지 files도 부분 성공으로 내보내지 않는다. 외부 발급자가 A/E를 관찰 파일로 새로 저작해 일치시키는 신뢰 위반은 B/C가 인증하지 못한다. 합성 저작 단계에서 matching H를 고정하는 부정 사례와 운영 소비 중 자동 채택을 구별한다.

## 13. Snapshot consistency

이 프로파일이 제공하는 것은 **선택한 독립 기대 refs에 대응하는 불변 bytes 집합과 기존 도메인/교차 일관성**이다. 일반 경쟁 open을 제한한7개 handle을 함께 보존하고 최종 상태도 확인하지만, 파일들이 같은 시점에 생성/획득됐다는 뜻은 아니다.

| 개념 | 보장/책임 |
|---|---|
| 개별 read 안정성 | 같은 handle/종류·ID·상태 검사·공유 제한·bounded EOF, T1/T2 전제 |
| raw 무결성 | 독립 기대 SHA 대 실제 bytes, 기존 로더 |
| revision 대응 | 동일 A/expected/root/선택 E·원본 is, Stage1+M2.75 |
| 객체 간 일관성 | 기존 M2.73 교차 validator, 정상 partial 상태도 보존 |
| filesystem 원자적 snapshot | **미제공**. VSS/transaction/fs snapshot을 생성하지 않음 |

순차 읽기 중 다른 아직 열지 않은 파일이 교체되면 기대 SHA 또는 후속 관계 오류로 차단할 수 있다. 기대 bytes와 완전히 같은 내용이면 동일 내용 주소에 부합할 수 있지만 그 파일의 이전 물리 이력까지 증명하지 않는다. 잠금만으로 domain fp나 공고 의미가 맞다고 판정하지 않는다.

## 14. 파일 크기·메모리·handle 예산

실제 파일 크기를 읽기 전용으로 확인했다. **운영의 역사7종 archive는 아직 없다.** 기존 합성 M2.71 저작 helper를 메모리에서 실행해 canonical raw 크기를 측정했으며 신규 실행 테스트/fixture 발행으로 세지 않는다.

| 측정 대상 | bytes |
|---|---|
| 합성 Review / Benefit / Coverage | 3202 / 736 / 730 |
| 합성 Envelope / Reviews / Manifest / Registry | 1137 / 3889 / 1140 / 2446 |
| 합성 raw7 합계 | 13280; 정상 revision1/2 모두 동일 크기 |
| 실제001 README / sources / policy JSON | 1563 / 3803 / 1981 |
| 실제002 README / sources / policy JSON | 5620 / 5944 / 2922 |

다음 값은 측정한 최대치가 아닌 **초기 구현을 위한 보수적 설계 한도**다. 공식 정책/금융 기준이 아니며 입력 인자·환경변수로 완화하지 않는다. 후속 구현 모듈의 고정 profile 상수로 두고 변경 시 설계/회귀/운영 자원 검토를 다시 승인한다.

| 한도 | 확정값 |
|---|---|
| 각 raw 파일 최대 | **4,194,304 bytes (4 MiB)**, 정확히 같은 값은 허용 |
| raw7 합계 최대 | **16,777,216 bytes (16 MiB)**, 정확히 같은 값은 허용 |
| ReadFile 최대 단위 | 65,536 bytes (64 KiB), 매번 남은 길이 이하 |
| 길이/깊이 | component255 UTF-16 code units 이하, root/각 상대경로1024 units 이하, root/각 상대경로16component 이하 |
| 열린 자원 | 파일7개, 서로 다른 directory 최대128개. 상한 초과 시 중단, 일반 open fallback 없음 |

파일을 연 즉시 같은 handle에서 길이 n을 얻어 0<n<=개별 cap 및 현재 합계+n<=전체 cap을 확인한다. 길이를 아는 만큼만 최대 n의 고정 bytearray에 읽고 짧은 정상 read는 이어 간다. 초기 n보다 이른 EOF는 변경/불완전 read 오류다. n을 채운 뒤 같은 handle에서1byte EOF probe를 해 성장/추가 데이터가 보이면 실패한다. 후속 metadata 크기도 초기 n과 같아야 한다. 빈 파일은 B의 FILE_REJECTED로 중단하며 성공 b""로 반환하지 않는다.

완성한 buffer만 exact bytes로 한 번 변환하고 mutable buffer를 버린다. 누적 보존 raw payload는16MiB 이하, 현재 buffer/bytes 전환의 추가 payload는 최대4MiB여서 **I/O payload 저장분은 최대20MiB + 작은 read 보조 buffer** 수준으로 설계한다. 이 값은 allocator/object overhead·UTF-8/JSON trees·domain 객체·기존 로더의 일시 복사·expected records를 포함한 **process RSS hard limit이 아니다**. 전체 decoder 메모리/CPU·동시 요청 수/worker 제한은 별도 실행 계층 책임이며 이번 함수가 Job Object/프로세스 메모리 상한을 설정하지 않는다. MemoryError 등은 삼키지 않고 handle 정리 후 실패한다.

과대한 파일은 allocation/read 전에 거부한다. 합계는 Review 포함 고정 순서로 증가시키며 같은 bytes를 재검증한다고 중복 합산하지 않는다. 모듈 전체 raw bytes를 join해 추가 복사하거나 각 파일 read 목록을 무제한 쌓지 않는다.

## 15. 최소 API 비교·최종 입력/출력

| 후보 | 이점 | 결정 |
|---|---|---|
| A: raw7만 반환 | I/O 책임만 작음 | caller가 C를 생략할 수 있음. 이번 정규 진입점으로 선택하지 않음 |
| B: raw7 확보 후 기존 C 호출 | 파일 준비→필수 검증 누락을 정상 호출 경로에서 막음 | **선택**. I/O 코드는 B, strict/도메인 계산은 기존 C에 유지 |

후속 private 진입점 이름은 `_prepare_and_validate_historical_artifacts`로 확정한다. 위치는 `backend/policy_engine/policy_data/historical_raw_bytes_preparation.py`다. 아래는 **설계 서명만**이며 이번에 파일/함수/공개 export를 만들지 않는다.

```python
def _prepare_and_validate_historical_artifacts(
    *,
    expected_acceptance: PolicyBenefitAcceptance,
    expected_acceptances: tuple[PolicyBenefitAcceptance, ...],
    trusted_root: str,
) -> tuple[
    tuple[
        AcceptanceReviewArtifact,
        tuple[
            BenefitSnapshot, EligibilityCoverage, PolicyEnvelope,
            CoverageReviewContext, DatasetManifest, SourceRegistry,
        ],
    ],
    tuple[bytes, bytes, bytes, bytes, bytes, bytes, bytes],
]: ...
```

정확히3개 필수 keyword-only이며 default/optional/nullable가 없다. root는 trusted caller의 명시 설정이다. A exact type → expected exact 비어 있지 않은 tuple/각 원소 exact type → root exact str 순서로 검사하고, 지원 OS 확인 → 기존 `_expected_ref` → A의 tuple 원본 membership 순서로 Q0를 닫는다. input 검사에는 preparation 신규 prefix를, helper 자체의 오류에는 기존 prefix를 사용한다. A를 원문 JSON에서 발급하거나 tuple을 축소하지 않는다.

새 모델 없이 **`(same_call_result, raw7)`**를 반환한다. 첫 원소는 Q6 M2.75의 **반환 tuple 자체 is**이며 그 안의 R_final/객체6도 원본이다. 둘째는 exact bytes7의 고정 tuple이고 순서는 Review → Benefit → Coverage → Envelope → Reviews → Manifest → Registry다. raw7의 각 slot은 C에 전달한 바로 그 bytes 객체다. handle/path·R_pre·보안 bool·승인 상태·영구 receipt를 반환하지 않는다.

raw7도 반환하는 이유는 후속 Content의 historical_artifact_bytes에서 **같은 bytes**를 재사용하기 위해서다. R/객체6만 반환하고 path를 다시 읽게 하지 않는다. caller는 자신의 A와 R_final의 선택 E_ref6를 raw7[1:]에 연결할 수 있다. Review raw7[0]의 내용 주소와 ArtifactReference path/sha를 혼동하지 않는다.

코드상 책임은 하나의 얇은 I/O 진입점과 작은 OS handle/read helper 수준으로 분리한다. helper에 도메인 판단/검증 완료 상태·새 service/Context/model을 넣지 않는다. test-only WinAPI spy는 가능하지만 runtime callback/reader 주입/skip·force·일반 open fallback 옵션은 API에 없다.

## 16. 기존 Orchestrator 연결·중복 검증·반환 원본

Q6 매핑은 정확히 다음과 같다. 기대 기록과 raw의 복사/변환 없이 전달한다.

| M2.75 인자 | preparation의 공급 값 |
|---|---|
| expected_acceptance | 입력 원본 A |
| expected_acceptances | 입력 전체 원본 tuple 자체 |
| review_artifact_raw_bytes | Q2 Review immutable bytes |
| benefit_raw_bytes | Q4 역할1 bytes |
| coverage_raw_bytes | Q4 역할2 bytes |
| policy_envelope_raw_bytes | Q4 역할3 bytes |
| coverage_reviews_raw_bytes | Q4 역할4 bytes |
| dataset_manifest_raw_bytes | Q4 역할5 bytes |
| source_registry_raw_bytes | Q4 역할6 bytes |

Q3의 R_pre만으로 성공 반환하지 않는다. Q6에서 기존 함수가 Review를 재복원하고 원본 A와 결합하는 계약을 유지한다. 두 Review 로더 호출은 같은 입력 bytes/expected를 사용하므로 중복 읽기/중복 파일 확보가 아니다. file bytes는 원본당1회 확보하고 동일 handle의 EOF/metadata 확인만 수행한다.

C는 여전히 순수9입력 함수다. B의 OS/path/size 오류 precedence는 C보다 앞서며 C 자체의 P0a~P8은 변경하지 않는다. 예를 들어 이미 읽은 Benefit의 SHA가 틀려도 아직 Q4 Registry가 없으면 Registry open 오류가 먼저다. raw7을 모두 확보한 뒤 여러 SHA가 틀리면 C의 기존 Benefit 우선이 유지된다. 파일 크기 초과·빈 파일은 SHA보다 B에서 먼저 거부할 수 있다.

## 17. Fail-Closed·정리·반환 수명

어느 단계든 첫 실패 후 다른 path 검색/재시도/최신 release·다른 revision/과거 cache/빈 bytes 대체·부분 raw 반환을 하지 않는다. 최초 오류 이후 후속 파일 **새 open/read**와 C/Content 호출은0회다. 이미 확보한 handle의 cleanup은 예외이며 반드시 시도한다.

파일은 소비/검증 중까지 유지하고 정상 반환 직전에 닫는다. 닫힌 뒤에도 반환 immutable bytes는 변하지 않는다. file path/handle이 이후에도 고정된다는 약속은 없으며, 이 요청의 bytes/복원 결과만 보존한다. 원본을 읽는 상위 코드가 반환 이후 다시 path를 열어 내용을 바꾸는 것은 지원 경로가 아니다.

모든 성공 handle은 소유권을 한 곳에 기록해 역순으로 정확히1회 CloseHandle한다. invalid handle은 닫지 않는다. 이번 reader는 ReadFile을 사용하므로 msvcrt fd 소유권 이전을 섞지 않는다. 기존 primary 예외가 있으면 cleanup 실패로 덮어쓰거나 mutate하지 않고 그 객체를 그대로 전파한다. 다른 handle close도 계속 시도한다. 정상 계산 뒤 첫 close가 실패하면 아직 결과를 외부에 반환하지 않았으므로 결과를 폐기하고 그 OS 오류로 실패한다. 다른 cleanup 오류 기록은 상위 신뢰된 실행 진단 책임이며 민감 path/raw를 공개 출력하지 않는다. 실패한 close까지 무조건 자원 해제가 성공했다고 주장하지 않는다. [Microsoft CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)

## 18. 오류 prefix·순서·OS/도메인 구분

새 preparation 구조/보안 오류는 기존 PolicyDataError를 사용한다. 새 exception class·정상 상태 Enum은 없다. 고정 prefix6개와 고정 role/field만 사용하며 형태는 `PREFIX: fixed.role.field: 계약을 확인하세요`다. 실제 path/ref/hash/raw·사용자 소득은 새 메시지에 넣지 않는다.

| 신규 prefix | 대상 |
|---|---|
| INVALID_HISTORICAL_RAW_PREPARATION_INPUT | exact3입력·expected membership 등 Q0 입력 계약 |
| HISTORICAL_RAW_PREPARATION_UNSUPPORTED_ENVIRONMENT | Windows/local fixed NTFS profile 밖·필수 API 미지원 |
| HISTORICAL_RAW_PREPARATION_PATH_REJECTED | root/상대경로·alias·실제 target containment 위반 |
| HISTORICAL_RAW_PREPARATION_FILE_REJECTED | 잘못된 종류/reparse·hard link/역할 중복·empty |
| HISTORICAL_RAW_PREPARATION_LIMIT_EXCEEDED | per-file/aggregate/depth/길이/directory handle 예산 |
| HISTORICAL_RAW_PREPARATION_FILE_CHANGED | 최초·후속 ID/길이/속성/EOF·상태 모순 |

WinAPI 자체가 실패한 경우는 **OSError(원래 winerror 보존)**다. file missing/access denied/sharing violation/read/query/close 실패를 정상 Policy UNKNOWN/STALE/MISSING이나 위 의미 오류로 몰래 바꾸지 않는다. WinAPI false/INVALID_HANDLE_VALUE의 last-error를 즉시 읽어 OS 예외를 구성하는 것은 새 reader의 책임이다. 성공 후 값이 policy에 맞지 않으면 위 고정 PolicyDataError다. API 오류 객체에 payload/path를 덧붙이지 않고 공개 UI에 원본 예외의 filename/내부 경로를 그대로 노출하지 않는다.

기존 `_expected_ref`, Review 로더·selector·M2.75·로더6·교차에서 발생한 PolicyDataError/예상 밖 오류 객체는 그대로 전파한다. 래핑/접두사 교체/정상 상태 변환은 없다. 새 I/O 우선순위는 **Q0→Q1→Q2→Q3→Q4 역할1~6→Q5→Q6 기존 내부 순서→Q7→Q8**이다. Q0 exact 타입은 API 순서, helper 뒤 membership 순서다. Q4 각 파일은 lexical precheck(Q3) 완료 후 open→종류/reparse→volume/path/ID→link/alias→길이 한도→read→post-check 순서다. Q5/Q7의 재검사는 Review부터 고정 역할 순서다.

중도 OS 실패는 그 지점의 첫 오류다. 실제 파일 syscall 스케줄/외부 경쟁이 달라질 수 있으므로 변화하는 filesystem에서 매번 동일한 오류를 약속하지 않는다. 같은 syscall 결과/고정 입력을 재현한 합성 spy에서는 동일 phase·첫 오류·후속0회가 결정적이어야 한다. 정상 함수들의 기존 내부 오류 순서는 변경하지 않는다.

## 19. Production ZIP·실행 신뢰 경계

현재 tools/artifacts/bootstrap.py는 **합성 source ZIP verify-only**다. 환경 flags·기대 ZIP H·원본 source inventory/runtime profile·import origin 등을 확인하지만 실제 운영 Manifest/전체 release/준비 실행/정책 계산 호출까지 연결하지 않는다. `_verify`의 expected SHA는 CLI 입력이고 해당 구현을 공식 운영 기대값 발급 신뢰로 승격하지 않는다.

후속 preparation 모듈과 Historical 로더/Orchestrator는 backend 코드다. production은 **이 모듈을 import하기 전에** 신뢰된 외부 launcher/Python/배치 bootstrap이 실제 코드 bundle/환경을 검증하고 import 경로·모듈 출처를 고정해야 한다. checkout backend를 먼저 import한 뒤 ZIP을 검사하는 흐름은 기존 import-before-trust 계약을 충족하지 않는다. 이번에 bootstrap/import/ZIP 코드를 변경하지 않는다.

준비 I/O 코드의 실행 신뢰, strict/도메인 검증 코드의 실행 신뢰, E.implementation_artifact_ref가 가리키는 역사 업무 구현 ZIP, 파일 접근에 쓰는 OS 권한은 별개다. 현재 검증 코드가 역사 bytes를 복원했다고 그 역사 ZIP을 실행한 것은 아니다. 공유 ZIP profile에서만 허용된 H 역할 대응을 모든 과거 Manifest/Acceptance의 전역 equality로 소급하지 않는다.

운영 D와 T1을 확인하지 못했다면 결과를 production 보안 검증 완료로 사용하지 않는다. 반면 trusted 임시 NTFS·합성 expected/raw로 좁은 B 구현을 검증하는 작업은 그 미완료와 구분해 진행할 수 있다. 악성 호스트/발급자/권한을 이 API로 인증하는 새 framework를 추가하지 않는다.

## 20. Content Validator 연결과 미완료

선택한 반환의 same_call_result는 기존 `(R_final, tuple6)`이고 raw7을 함께 보존하므로, 신뢰된 상위 Content caller가 **같은 A/R/객체6와 참조-원본 bytes 쌍**을 만들 수 있다. B는 Content를 호출하거나 그 성공 None을 생성하지 않는다.

추가로 필요한 것은 전체 Manifest의 다른 PolicyEnvelope 원본/호환 역사 환경, 공식 Source 원문 bytes/locator/claim 합집합·membership/의미, 실제 검토자/발급 권한·이력 완전성, 역사 implementation 실행 원본/현재 코드 신뢰, Source 사용일/freshness Gate, 필요한 FULL 근거다. 원본7 파일 준비가 그 전체를 제공하지 않는다.

현재 Content11입력 후보의 historical_artifact_bytes에는 선택 원본6의 `(E_final.ref, raw)`를 직접 연결할 수 있다. 그러나 공식 원문·다른 envelopes·ZIP·철회 대상 원본은 별도다. 선택 Envelope 하나를 historical_envelopes 전체라고 가장하지 않는다. REVOKED B의 target A를 Context/ref로 외부에서 준비하는 기존 책임도 그대로다. accepted_terms/claim·정책 자격·월 금액을 LLM이나 파일 이름으로 판정하지 않는다.

## 21. 후속 설계 검증 시나리오 — HBP01~HBP80

**수동80개이며 이번 신규 실행 테스트0개다.** 각 행은 입력·예상 결과/phase·담당·후속 합성 시험 가능성을 명시한다. **M**은 mock/spy로 단계·정리/반환 계약을 시험 가능, **W**는 Windows 임시 로컬 NTFS에서 실제 OS/process 시험 필요, **E**는 외부 신뢰/운영 절차이며 mock 성공으로 인증 불가다. 시험을 만들 때 M과 W를 구분하고 지원하지 않는 호스트의 결과를 OS 보호 성공으로 계상하지 않는다.

| ID | 입력/사례 | 예상 결과·실패 단계 | 담당 / 시험 |
|---|---|---|---|
| HBP01 | 정상 trusted root/expected/raw7 파일 | Q0~8 성공, 완전 반환 | B/C / M+W |
| HBP02 | A의 정상 내용 주소 | 고정 acceptance-reviews/H.json만 open | A/B / M+W |
| HBP03 | ref가 경로가 아닌 문자열 | 별도 임의 path로 해석하지 않음 | B / M |
| HBP04 | opaque/잘못된 expected ref | Q0 기존 helper 오류, 파일0회 | A/B / M |
| HBP05 | expected 공통 ref 다름/중복 revision | Q0 기존 helper 오류 | A/B / M |
| HBP06 | 같은 값의 A clone/tuple에 A 부재 | Q0 입력 오류, 파일0회 | B / M |
| HBP07 | list/빈 tuple/record subtype/root Path객체 | Q0 exact 타입 오류 | B / M |
| HBP08 | 여러 정상 Entry와 명시 옛 A | Q3 전체 복원 후 선택 A의6경로 | B/C / M+W |
| HBP09 | Review가 틀린 SHA 파일 | Q3 기존 Review bytes mismatch,6파일0회 | C / M+W |
| HBP10 | matching H이나 invalid strict JSON | Q3 기존 strict 오류,6파일0회 | C / M+W |
| HBP11 | 선택하지 않은 뒤 Entry 값 모순 | Q3 전체 binding 오류 | C / M+W |
| HBP12 | 선택 A가 REVOKED | Q3 기존 selector status 오류, None ref fallback 없음 | C / M+W |
| HBP13 | body 경로는 정상처럼 보이나 Review 검증 실패 | 그 경로 파일 open0회 | B/C / M+W |
| HBP14 | 정상 raw7 | Review 실제2회, M2.75 내부1회·로더6/교차1회 | B/C / M+W |
| HBP15 | R_pre를 기존 C에 주입 시도 | 그런 API/옵션 없음, 원본 raw 재검증 | B/C / M |
| HBP16 | 실제 반환 | same_call_result tuple 자체 is·R_final/객체6/raw7 is 보존 | B/C / M+W |
| HBP17 | root가 상대/drive-relative/drive root | Q1 path 거부 | B / M+W |
| HBP18 | ref에 상위/점/빈 component | 기존 구조 또는 Q3 lexical 거부 | B/C / M |
| HBP19 | 절대경로 주입 | Q1/Q3 path 거부, 내용 read0회 | B / M+W |
| HBP20 | UNC/SMB/root network | Q1~2 unsupported/path 거부 | B / M+W |
| HBP21 | device/NT/외부 extended namespace | Q1/Q3 path 거부 | B / M+W |
| HBP22 | ADS colon 경로 | 구조 또는 Q3 path 거부 | B/C / M+W |
| HBP23 | CON.txt/NUL/COM1/LPT장치명 | Q1/Q3 path 거부 | B / M+W |
| HBP24 | COM/LPT 위첨자 예약명 | Q1/Q3 path 거부 | B / M+W |
| HBP25 | 끝 공백/끝점/금지 문자/control | Q1/Q3 path 거부, trim 없음 | B / M+W |
| HBP26 | 정상 한글·공백·서로 다른 Unicode형 | 원문 scalar 보존, 실제 정확한 component만 허용 | B / M+W |
| HBP27 | 실제와 대소문자만 다른 component | Q2/Q4 final path 불일치 거부, casefold 우회 없음 | B / M+W |
| HBP28 |8.3 alias로 root/파일 지정 | normalized long path 불일치면 거부 | B / M+W |
| HBP29 | root/ancestor가 junction/symlink | Q1 directory handle reparse 거부 | B / M+W |
| HBP30 | nested child directory reparse | Q2/Q4 해당 directory에서 중단 | B / M+W |
| HBP31 | 마지막 파일 symlink/reparse | Q2/Q4 FILE_REJECTED, target 내용 read0회 | B / M+W |
| HBP32 | archive 경로지만 다른 실제 volume/path | Q2/Q4 target 거부, 단순 prefix 사용 없음 | B / M+W |
| HBP33 | root와 이름 접두사만 같은 sibling | containment component 불일치로 거부 | B / M+W |
| HBP34 | 파일 대신 directory/pipe/device | Q2/Q4 종류 거부, 본문 read0회 | B / M+W |
| HBP35 | 없는 Review 파일 | Q2 OSError, Review/원본6/C0회 | B / M+W |
| HBP36 | 없는 역할별 Historical 파일 | Q4 해당 OSError, 이후 파일/C0회 | B / M+W |
| HBP37 | hard link2개/루트 외 alias 있음 | Q2/Q4 link count 거부 | B / M+W |
| HBP38 | 두 역할이 같은 path/file ID | Q3/Q4 profile alias 거부 | B / M+W |
| HBP39 | 단일 링크 파일이 과거 밖에서 이동됨 | 위치/ID만으로 발급 신뢰 인증 못함 | A / E |
| HBP40 | 파일 open 전에 정상 단일파일 교체 | 실제 열린 대상 기준검사 후 SHA가 판별, 사전 교체 완전탐지 아님 | B/C / M+W+E |
| HBP41 | open 후 다른 process가 write open | 공유 충돌/거부 확인, 데이터 성공으로 완화 없음 | B / W |
| HBP42 | open 후 다른 process가 rename/delete | 공유 충돌/거부 또는 변경 감지, 결과 없음 | B / W |
| HBP43 | 중간 directory rename/reparse 경쟁 | 유지 handle·T1·검사 범위 시험, 모든 공격 차단 주장 없음 | B / W+E |
| HBP44 | 최초/후속 ID·길이·속성 불일치 | Q4/Q5/Q7 FILE_CHANGED | B / M+W |
| HBP45 | last-access만 변경됨 | 안정성 오류로 오인하지 않음 | B / M+W |
| HBP46 | query/final path API 실패 | 해당 OSError, 검사 생략/다른 방식 fallback 없음 | B / M+W |
| HBP47 | 정상 여러 short read | 같은 handle에서 남은 n까지 읽고 성공 | B / M+W |
| HBP48 | n 이전 EOF/부분 read 종료 | FILE_CHANGED, 부분 bytes 반환 없음 | B / M+W |
| HBP49 | ReadFile false/중간 I/O 예외 | OSError 원본·이후0회·cleanup | B / M+W |
| HBP50 | 정확히4MiB 개별 파일 | read 한도 통과, 의미 검증은 C | B/C / M+W |
| HBP51 |4MiB+1 또는 거대 sparse 파일 | Q2/Q4 allocation 전 LIMIT_EXCEEDED | B / M+W |
| HBP52 | 합계 정확히16MiB | I/O 한도 통과, domain 성공은 별도 | B/C / M+W |
| HBP53 | 합계16MiB+1 | 해당 Q4 파일에서 limit, 이후0회 | B / M+W |
| HBP54 |0byte 실제 파일 | B FILE_REJECTED, 성공 b"" 없음 | B / M+W |
| HBP55 | initial n 뒤 EOF probe에 추가 byte | FILE_CHANGED, 증가를 잘라 성공하지 않음 | B / M+W |
| HBP56 | component/depth/길이/handle예산 초과 | allocation/open 전 또는 해당 directory LIMIT_EXCEEDED | B / M+W |
| HBP57 | immutable bytes 전환 후 handle close | raw는 그대로, path 재열기 없음 | B / M+W |
| HBP58 | 파일5 open 중 예외 | 기존 handle 전부 역순 정리, file6/C0회 | B / M+W |
| HBP59 | C에서 PolicyDataError/RuntimeError | 같은 예외 객체, cleanup 후 부분 반환 없음 | B/C / M+W |
| HBP60 | primary 오류와 close 실패 동시 | primary 유지, 다른 close도 시도, 정상 결과 없음 | B / M |
| HBP61 | 계산 성공 뒤 close 실패 | Q7 OSError·결과 폐기, 나머지 close시도 | B / M |
| HBP62 | raw6 각 역할 SHA mismatch | Q6 기존 해당 로더 오류, C 후속0회 | C / M+W |
| HBP63 | 같은 policy의 다른 revision 파일 | Q6 SHA/직접 binding 오류, fallback 없음 | C / M+W |
| HBP64 | 다른 Entry의 ref/bytes 혼합 | 선택 E 기대값 유지, Q6 거부 | B/C / M+W |
| HBP65 |6로더 성공 후 교차 모순 | Q6 기존 교차 오류, 완전 반환 없음 | C / M+W |
| HBP66 | Benefit SHA 오류+Registry 파일 없음 | Q4 Registry OSError 먼저, C0회 | B / M+W |
| HBP67 | raw7 확보 뒤 여러 SHA 오류 | Q6 기존 C의 Benefit 우선순위 | C / M+W |
| HBP68 | 읽기 후 파일 path 재열기 시도 | 정상 경로 재열기 없음, OS spy로 확인 | B / M+W |
| HBP69 | 같은 A/raw로100회 별도 호출 | 매번 새 file handles/Review/C, cache 없음 | B/C / M+W |
| HBP70 | filename이 같고 domain fp만 맞음 | raw SHA 불일치는 C 거부 | C / M+W |
| HBP71 | 보관소 파일을 순차 확보 | 기대 refs/교차 일치만, 원자적 fs snapshot 주장 없음 | B/C / M+W+E |
| HBP72 | 파일 잠금은 성공하나 domain fp 모순 | Q6 오류, lock을 의미 승인으로 사용 안 함 | B/C / M+W |
| HBP73 | 기대 record/refs가 자기 발급됨 | 내부 equality로 발급 권한 신뢰 인증 불가 | A / E |
| HBP74 | byte 검증 성공·production ZIP 미검증 | 합성 성공 가능, production 실행 신뢰 미완료 | D / E |
| HBP75 | backend 먼저 import한 뒤 ZIP 확인 | 운영 import-before-trust 계약 미충족 | D / E |
| HBP76 | source 원문/locator/전체 envelopes 미준비 | B/C 가능해도 Content/Source/release 완료 아님 | 외부 Content / E |
| HBP77 | 반환 성공만으로 VERIFIED/USABLE 요구 | 그런 상태/필드 없음, 현재 사용 판단 제외 | C/후속 / M+E |
| HBP78 | 비Windows/NTFS 밖/필수 API 미지원 | Q0/Q2 unsupported, 일반 open fallback 없음 | B / M+W |
| HBP79 | 악성 admin/기존 writable mapping/불신 ACL | T1/T2 밖, 공유flag의 완전 보호 주장 없음 | A/B/D / E |
| HBP80 | 새 문서·기존 코드/테스트/release 동결 | 전후 파일 감사·전체 회귀만, 새 보안 구현 성공 아님 | 문서 감사 / 실행 회귀 |

실제 경쟁 시험은 준비 process와 경쟁 process의 준비/해제 barrier를 고정해야 한다. OS sharing 실패와 spy로 합성한 예외를 구분한다. hard link/junction 생성 권한이 없어 시험을 못 했으면 해당 OS 사례를 통과로 기록하지 않는다. 이는 후속 시험 설계이며 이번에 임시 junction/hard link·경쟁 파일·보안 테스트를 만들지 않았다.

## 22. 보존해야 할 기존 계약·Validation

**이번 추가는 docs/HISTORICAL_RAW_BYTES_PREPARATION_CONTRACT.md 한 개다.** 기존 문서·운영 코드·tests·fixture·기대값·public export·모델·설정·M2.53 bootstrap·실제 release 수정/삭제0개, 신규 실행 테스트0개다. API 후보/Win32 절차는 구현된 함수로 취급하지 않는다.

사전 전체 pytest: **11144 passed in 91.83s (0:01:31)**. 사후 전체: **11144 passed in 61.40s (0:01:01)**. 사전/사후 전체 각각 최초 실행 통과, failed/skipped/timeout/실패 수정 재실행0회. 기존11,144개 회귀는 새 preparation 보안 기능을 실행 검증한 것이 아니다.

보호 범위는 backend/tests/data/docs/tools 및 .gitignore/pyproject.toml/README.md/requirements-dev.txt의 일반 파일이며 venv·임시물·pycache·pytest cache는 제외한다. data/releases6개는 별도 전수 기록한다. 사전 기존 보호205개/실제 release6개의 SHA256·크기·mtime_ns 기준선을 확보했다. 사후 **기존 보호205개 전부 SHA256·크기·mtime_ns 동일**, 수정/삭제0개다. 이 문서1개만 추가해 보호 파일206개가 됐으며 파일 목록 차이도 이 새 문서 하나뿐이다. 실제 release6개 전부 SHA256·경로·크기·mtime_ns 동일.

GV01~GV15/BV01~BV16·Coverage freeze·Historical Loader6·교차 validator·M2.75·Review strict 로더·Source parser/fp·Manifest validator·Acceptance/Benefit/Cashflow·bootstrap을 보존했다. Generic core는 **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**, ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan은 **DRAFT / CONDITION_SLICE**다. 실제 정책 혜택 Cashflow 반영0원 원칙·실제 원본/Acceptance/철회/금액 미발급을 유지한다.

## 23. 미해결 사항·선택한 한계

| 항목 | 확정 / 남은 것 |
|---|---|
| Review locator | 기존 내용 주소 + trusted_root/acceptance-reviews/H.json 재사용. 새 index/입력 모델 불필요 |
| 원본6 경로/순서 | 실제 strict R_pre/원본 A의 ref6 → Windows profile → raw6. 해결 |
| handle/identity/읽기 | local fixed NTFS·chain/열린 대상·same-handle·제한/정리 절차 확정. 실제 W 시험은 아직 없음 |
| snapshot/기대값 | 내용 주소 및 기존 교차 일관성, fs 원자성/발급 신뢰 인증은 보장 밖 |
| 크기/자원 |4MiB/file·16MiB/raw7·bounded buffer/handle 예산 확정. process RSS/decoder CPU hard limit 별도 |
| API/반환 |3입력·기존 C 호출강제·(same_call_result, raw7)·기존 C 변경 없음 |
| 운영 archive/ACL admission | T1의 실제 보관소/권한·불변 발행 확인은 배치 책임, 미구현 |
| 실행 artifact | backend import 전 production D/정상 OS·Python 신뢰 별도 미완료 |
| Content/Source/release | 공식 원문·전체 envelopes·역사 환경·claim/locator/사용요건·현재 evaluator 미완료 |

이 초기 Windows profile은 기존 구조적으로 유효한 모든 ArtifactReference/환경을 지원하려는 범용 파일 sandbox가 아니다. 지원 밖 ref는 명시 거부하며 원본 모델을 수정하지 않는다. 신뢰된 보관소/호스트 전제를 충족하지 못하는 환경을 잠금 flag만으로 수용하지 않는다. 설계 미확정을 완료로 포장하는 대신 확정한 제한 profile의 구현과 실제 운영 적용 차단 요건을 구별한다.

## 24. 최종 판단

**READY_TO_IMPLEMENT_HISTORICAL_RAW_BYTES_PREPARATION**

내용 주소 locator·검증된 R에서 참조6 선택·허용 root/Windows 경로·same-handle/실제 대상·독립 기대 SHA·크기/자원·B 진입점/반환·최초 실패/cleanup·기존 C 연결을 확정했다. 기존 M2.75/도메인 모델을 변경하지 않고 제한된 trusted NTFS 환경에서 구현할 수 있다.

실제 운영 파일 보안/경쟁 보호가 검증됐다는 판단은 아니다. T1/T2/D를 만족하지 못하는 운영 적용은 여전히 차단한다. OS 실제 시험/원본 보관소/전체 Content 준비는 구현 완료 전에도 후속 증거가 필요하다. 임의 사용자 경로·불신 filesystem까지 지원하려면 별도 보안 계약 검토가 필요하며 이 승인을 확대하지 않는다.

## 25. 다음 최소 작업 하나

**별도 승인 후 이 제한된 Windows Raw Bytes Preparation 진입점과 필요한 작은 OS helper·합성/Windows NTFS 파일 시험만 구현한다.**3입력, Stage1 Review 검증과 Stage2 ref6 읽기, 안전한 chain/handle/identity·bounded read, 기존 M2.75 호출, `(same_call_result, raw7)` 반환과 cleanup/오류 전파를 확인한다.

HBP01~80을 M/W/E로 대응하고 실제 Windows sharing/reparse/hard link/rename 경쟁 시험의 성공/권한 부족/미지원과 mock 시험을 구분해 보고한다. 기존 bootstrap/Orchestrator/로더6·모델·fixture/기대값·실제 release는 수정하지 않는다. production launcher·전체 Content/Source Gate·release validator·Acceptance evaluator·Bridge/Cashflow/API/UI를 함께 구현하지 않는다.

## 부록 A. 실제 release6 보존 기준선

작업 전 개별 기준선이다. mtime_ns는 파일 시스템 epoch 기준 정수값이며 실제 운영 검증 결과를 새로 발급한 hash가 아니다.

| 실제 경로 | SHA256 | 크기(bytes) | mtime_ns |
|---|---|---|---|
| data/releases/ansan-youth-2026-10-20-001/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 | 1981 | 1792485283217142700 |
| data/releases/ansan-youth-2026-10-20-001/README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f | 1563 | 1792485455968002700 |
| data/releases/ansan-youth-2026-10-20-001/sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b | 3803 | 1792485282447400500 |
| data/releases/ansan-youth-2026-10-20-002/policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 | 2922 | 1792498860277470600 |
| data/releases/ansan-youth-2026-10-20-002/README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 | 5620 | 1792499011465653800 |
| data/releases/ansan-youth-2026-10-20-002/sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 | 5944 | 1792498860276460800 |

## 부록 B. 요청한 최종 보고30항목 대응

| 번호 | 항목 | 확정·검증 |
|---|---|---|
| 1 | 생성 문서 | HISTORICAL_RAW_BYTES_PREPARATION_CONTRACT.md 하나 |
| 2 | 준비 공백 |2절 A/B/C/D 구분, B 실제 파일 취득 경계 미구현 |
| 3 | Review ref/locator | 경로 없는 내용 주소, 기존 root/acceptance-reviews/H.json |
| 4 | ref6 |5절 선택 검증 Entry의 기존 ArtifactReference6 |
| 5 | Two-stage | Q3 먼저 Review strict/Entry, Q4 원본6, Q6 기존 C 재검증 |
| 6 | root | 신뢰된 명시 local NTFS root·ACL/발행/ancestor 신뢰 전제 |
| 7 | Windows 경로 | traversal/UNC/device/ADS/예약명/alias·reparse 거부 |
| 8 | same-handle | CreateFileW 제한 공유·기존 파일·동기 ReadFile·끝까지 유지 |
| 9 | file identity | 열린 volume/file index·실제 canonical path·종류/속성/link 검사 |
| 10 | TOCTOU | chain/share/handle 사후 검사, 비신뢰 권한/악성 host·원자 open 보장 제외 |
| 11 | 기대 SHA | 외부 expected ref→검증된 E.ref6, 관찰값 자동 채택 없음 |
| 12 | snapshot | 내용 주소/교차 일관성, filesystem 원자성 미제공 |
| 13 | 자원 | 각4MiB·합계16MiB·read64KiB·directory128+file7, process RSS와 구분 |
| 14 | API |15절 private3필수 keyword-only, (same_call_result, raw7) |
| 15 | 기존 C 연결 |9입력 원본 그대로1회, 전체 준비에서 Review strict2회 |
| 16 | 오류 | 신규 preparation6prefix·기존 도메인 예외/OSError 분리·Q0~Q8 |
| 17 | Fail-Closed | 첫 실패·이후 open/read/C0회, cleanup 별도, 부분 반환 없음 |
| 18 | ZIP | 합성 verify-only와 production import-before-trust 분리 |
| 19 | Content | 같은 raw 보존 가능하나 원문/locator/claim/전체 release/실행 미완료 |
| 20 | 수동 시나리오 | HBP01~HBP80 수동80개, 이번 신규 실행0개 |
| 21 | 코드 변경 | 없음. 새 설계 문서1개만 추가 |
| 22 | 전체 pytest | 사전11144 passed in91.83s / 사후 11144 passed in 61.40s (0:01:01) |
| 23 | 기존11144 | 기존11,144개 사전/사후 전부 통과, tests/fixture/기대값 변경 없음 |
| 24 | GV/BV | GV01~15/BV01~16 기존 literal·계산·회귀 보존 |
| 25 | release | 실제 release6개 전부 SHA256·경로·크기·mtime_ns 동일. |
| 26 | freeze | ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS |
| 27 | ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED |
| 28 | 실제 정책 | DRAFT / CONDITION_SLICE, 실제 승인/금액 발급 없음 |
| 29 | 판단 | READY_TO_IMPLEMENT_HISTORICAL_RAW_BYTES_PREPARATION |
| 30 | 다음 최소 작업 | 제한 Windows preparation+합성/실제 NTFS 시험 한 단계, 별도 승인 후 |

## 26. M2.77 — 제한 Windows Raw Bytes Preparation 구현·검증 기록

### 26.1 실제 파일·API·프롬프트 차이

신규 운영 파일은 `backend/policy_engine/policy_data/historical_raw_bytes_preparation.py`와 `historical_windows_file_io.py`다. 전자는15절의 private `_prepare_and_validate_historical_artifacts` 한 함수, 후자는 제한 Win32 binding·경로/handle/read 소유권 helper다. 신규 테스트는 `tests/test_historical_raw_bytes_preparation.py`, `tests/test_historical_raw_bytes_preparation_ntfs.py`다. 기존 문서 변경은 이 계약의 현재 상태/26절과 ARCHITECTURE64절뿐이다. 공개 export·도메인 모델·Historical 로더·새 검증 알고리즘·범용 Artifact framework는 없다.

실제3개 필수 keyword-only는 expected_acceptance: PolicyBenefitAcceptance, expected_acceptances: tuple[PolicyBenefitAcceptance, ...], trusted_root: str다. nullable/default/추가 option·reader callback·skip/force/fallback은 없다. annotation과 중첩 tuple 반환은15절 서명과 동일하다.

**지시문4절의 설명과 실제 기존 알고리즘의 차이:** 기존 strict Review 로더는 raw20 Acceptance projection을 포함하는 **전체 canonical Review raw bytes의 SHA256**을 expected ref suffix와 비교한다. raw20은 자기참조를 피하는 본문 schema이지 별도20key만 해시하는 알고리즘이 아니다. M2.76/실제 로더 우선 규칙에 따라 기존 함수만 호출했으며 preparation/helper는 hashlib/JSON parser를 추가하지 않았다. 기존 알고리즘/기대값·로더를 변경하지 않았다.

### 26.2 구현한 Q0~Q8

| 단계 | 실제 구현 |
|---|---|
| Q0 | A exact→전체 expected exact nonempty tuple/각 원본 exact→root exact str→지원 Windows→기존 `_expected_ref`→A 원본 membership. 파일 호출 이전에 중단 가능 |
| Q1 | root lexical/길이/깊이, drive fixed 확인, 실제 volume GUID root handle부터 ancestor를 하나씩 확보·유지. drive alias가 실제 volume root 밖을 가리키면 거부 |
| Q2 | 고정 acceptance-reviews/H.json, 같은 handle 종류/속성/volume/실제 canonical path/ID/link/크기 확인 뒤 bounded read |
| Q3 | 기존 Review strict 로더1회·기존 selector1회, E_pre.acceptance is A. 참조6 경로를 전부 사전 검토한 뒤 읽기 시작 |
| Q4 | Benefit→Coverage→Envelope→Reviews→Manifest→Registry를 각각 같은 handle에서 확보.7역할 path/file ID 중복 금지 |
| Q5 | 파일은 Review→원본6 순서, directory는 확보 순서로 같은 handle 재검사 |
| Q6 | 기존 M2.75를 정확히1회 호출. A/전체 tuple/raw7 객체 그대로 전달 |
| Q7 | 최종 handle 상태 재검사·역순 정리. primary 예외 보존, 정상 후 close 실패도 결과 폐기 |
| Q8 | M2.75 반환 tuple 자체와 exact bytes7 고정 tuple을 `(same_call_result, raw7)`로 반환 |

기존 M2.75/Review/로더6/교차 함수는 수정하지 않았다. Stage1 R_pre와 C의 R_final은 서로 다른 복원 객체이고 원본 A는 동일하다. 전체 정상 경로에서 Review strict 검증은2회이며, M2.75 내부 호출은1회다. Historical raw는 원본당 한 번 확보한 뒤 같은 bytes로 C에서 검증한다. 반환 뒤 path를 재열지 않고 raw7을 후속에 재사용할 수 있다.

### 26.3 Windows OS helper와 자원 수명

`_Win32`는 필요한 kernel32 함수에 ctypes argtypes/restype/use_last_error를 지정한다. 구조체는 DWORD4/FILETIME8/BY_HANDLE_FILE_INFORMATION52 bytes로 실제 환경에서 확인했다. directory는 FILE_READ_ATTRIBUTES, file은 GENERIC_READ, 공유는 READ만, OPEN_EXISTING, BACKUP_SEMANTICS+OPEN_REPARSE_POINT를 사용한다. backup/restore privilege를 활성화하지 않는다.

`_FileSession`은 한 호출의 handle 목록·directory cache·파일 상태·누적 bytes만 소유하는 OS 자원 helper다. 도메인/보안 인증 모델이 아니다. 전역 mutable cache나 filesystem/정책 service를 만들지 않았다. M2.53 bootstrap을 호출/복사하지 않고 제한 공유/소유권 원칙만 재사용했다.

GetFileType·GetFileInformationByHandle·GetVolumeInformationByHandleW·GetFinalPathNameByHandleW로 DISK/역할 종류·reparse·local NTFS/serial·정확한 volume GUID component·file index·link count를 확인한다. 초기 ID0은 식별 정보 미확보로 거부한다. casefold/단순 prefix/Path.resolve·pathname stat를 인증으로 사용하지 않는다. parent chain은 같은 실제 volume 경로로 전개하며 handle을 유지한다. 파일 정보는 읽기 후/Q5/Q7에 재비교하고 last-access는 제외한다.

ReadFile은 최대65,536bytes, 개별4,194,304bytes·합계16,777,216bytes 한도를 적용한다. fixed bytearray로 초기 길이까지만 읽고 정상 short read는 이어 읽는다. 이른 EOF/추가1byte/읽기 실패·사후 상태 변경을 중단 사유로 삼는다. empty 파일·path/depth/component/4096unit 최종 경로/directory128·file7 예산도 적용한다. raw 한도를 process RSS 보장으로 표현하지 않는다.

성공한 handle은 즉시 소유한다. 소유권 목록 append 자체가 MemoryError로 실패해도 방금 연 handle을 닫도록 보강했다. 이후 실패는 남은 handle을 역순으로 모두 정리 시도하고 기존 primary 예외 객체를 보존한다. 실제 CloseHandle 실패를 숨겨 정상 결과를 내보내지 않으며, 이미 primary가 있을 때 secondary cleanup 오류로 덮지 않는다. 실제 반복 시험에서는 file/directory handle 수 증가가 없었다.

### 26.4 합성 시험·첫 실패·수정·재실행 이력

**합성 OS 단위 시험과 실제 NTFS 시험을 별도 파일/로그로 구분**한다. fake Win32는 syscall 결과/읽기/오류를 명시 저작하며 OS 보호 성공을 증명하지 않는다. 합성 정상 경로에서도 기존 Review 로더·M2.75·로더6·교차는 실제 실행한다. M2.71 저작 helper/M2.73 부정 사례/M2.75 원본 저작 helper는 tests에서만 재사용한다.

| 실행 | 결과 | 원인/변경 |
|---|---|---|
| 합성 최초 | **147 passed, 2 failed in 2.90s** | 새 테스트 보관소 helper가 invalid JSON을 파싱하고 REVOKED의 None ref를 정상 파일처럼 접근. 운영 구현 실패가 아님 |
| helper 수정 후 | **149 passed in 2.19s** | 두 부정 사례는 Review 파일만 준비하도록 새 테스트 setup 수정. 기존 fixture/기대값 변경 없음 |
| 소유권/alias/재검사 보강 후 | **156 passed in 2.18s** | 새 handle 목록 할당 실패 정리, 역할 alias·handle 예산·Q5/Q7·RuntimeError 원본 시험 추가 |
| 합성 최종 | **157 passed in 1.97s** | 초기 file ID0 거부 사례까지 추가. 추가 실패 없음 |

정상 fixed OS 입력100회와 최초 호출을 합한101회에서 새 open/read/C·불변 expected·새 원본 반환/동일 값 재현을 확인했다. 이는 외부 파일을 읽는 B의 순수성을 뜻하지 않는다. 고정된 fake syscall 결과의 재현성과 기존 순수 C의 결정성을 구분한다.

### 26.5 실제 Windows/NTFS 시험·권한 제한

관찰 환경은 **CPython3.12.14 / win32 / AMD64 / 64bit**, Windows version major10/build26300/workstation이다. 임시 보관소 handle에서 filesystem=NTFS·실제 volume serial/file ID·link count1을 확인했다. 실제 release를 시험 대상으로 쓰거나 수정하지 않았다.

| 실행 | 결과 | 해석 |
|---|---|---|
| 정상 native 최초 | **1 passed in 1.07s** | 실제 raw7/handle→기존 C 전체 연결·구조체 layout 확인 |
| sandbox에서 시험 확장 | **8 passed, 4 failed, 1 skipped in 2.58s** | junction/hard link 생성3사례는 sandbox 접근 거부, directory rename 예상 code32와 관찰5의 새 시험 기대 차이1사례. file symlink는1314 권한 부족 |
| 추가 승인 후 제한 해제 시험 | **12 passed, 1 skipped in 1.94s** | 실제 junction/hard link 생성·거부 검증 통과. directory rename은 보호 중5/32 거부와 보호 해제 후 성공을 함께 확인하도록 새 시험 수정 |
| 실제 NTFS 최종 | **16 passed, 1 skipped in 2.25s** | 합계16MiB·case alias·empty·속성 변경 탐지4사례 추가. 새 실패 없음. symlink 권한 부족은 그대로 미실행 |

실제 통과 범위는 다음과 같다.

- 정상7파일/C/원본 is·실제 metadata와52byte 구조체, 기존 writer/delete handle과의 공유 충돌.
- ReadFile 진입 시점을 barrier로 자식 process를 실행해 일반 write open/file rename/delete는32로 거부됨을 확인. directory rename은5로 거부됐고 handle 해제 뒤 같은 directory rename과 일반 write open이 성공함도 확인했다. 반환 code 차이를 단순히 성공으로 완화하지 않았다.
- 새 임시 root/mid-path junction은 Windows mount-point reparse buffer/DeviceIoControl로 만들고 실제 거부를 확인했다. cleanup은 해당 임시 junction에만 os.rmdir를 호출하며 target tree를 재귀 삭제하지 않는다.
- 실제 hard link2개 상태 거부·link 제거 후 정상 복원, 64KiB 경계·4MiB 정확 경계/초과·16MiB 합계 경계/초과·empty·실제 case alias 거부.
- 일반 READ 공유 제약이 FILE_WRITE_ATTRIBUTES까지 모두 막지 않는다는 점을 실제로 확인했다. 읽기 중 메타데이터 handle의 SetFileTime은 가능했고, 사후 검사에서 FILE_CHANGED로 중단했다. 이 한계를 방어 성공으로 숨기지 않는다.
- 정상/도메인 실패 각20회 반복 전후 GetProcessHandleCount 동일, 실패 뒤 임시 원본 delete 가능. 실제 read/후속 검증에서 handle을 유지하고 정상 반환 전 해제했다.

**파일 symlink 실제 시험은 미실행이다.** CreateSymbolicLinkW(ALLOW_UNPRIVILEGED_CREATE)가 실제 WinError1314로 실패했다. 추가 승인으로 sandbox를 벗어나도 동일했다. Developer Mode/권한/시스템 설정을 변경하지 않았고, skip을 PASS로 계산하지 않는다. 해당 사례는 현재 합성 FILE_ATTRIBUTE_REPARSE_POINT 거부와 실제 directory junction 시험으로 일부만 대응되며, 실제 file symlink 거부 증거로 대체하지 않는다. [Microsoft symlink 생성 조건](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createsymboliclinkw)

자동 승인 검토가 한 번 시간초과해 큰 테스트 파일 반영 작업이 중단됐다. 파일 미반영을 확인한 후 분할 재시도했다. 이는 pytest timeout/운영 보안 실패로 합산하지 않는다. 위 sandbox 시험 실패와 별도 기록이다. 최초 실제 시험 실패를 숨기려고 기존 테스트/timeout/fixture·보안 계약을 완화하지 않았다.

### 26.6 HBP01~HBP80 실행 대응

아래는 문서80사례의 추적 표이며 신규 테스트174개와 다르다. **M**은 합성 OS/실제 도메인 검증, **W**는 실제 NTFS 통과, **S**는 권한 부족 skip, **E**는 외부 신뢰 책임/미관찰이다. 운영 Enum·보안 상태 모델을 추가한 것이 아니다.

| 수동 ID | 실행 대응 / 미완료 한계 |
|---|---|
| HBP01 | M/W 정상 전체 준비→C→완전 반환 |
| HBP02 | M/W 기존 내용 주소의 고정 Review locator |
| HBP03 | M 내용 주소를 임의 파일 경로로 사용하지 않음 |
| HBP04 | M opaque ref는 기존 helper 오류·파일0회 |
| HBP05 | 기존 helper 보존/기존 Review 회귀 및 M2.75 다중 ref/revision 계약. 새 helper로 알고리즘 재작성 없음 |
| HBP06 | M clone/membership 위반 Q0 오류 |
| HBP07 | M exact 입력/type·필수/우회 옵션 거부 |
| HBP08 | M 복수 Entry의 명시 old/new 선택·전체 expected 전달 |
| HBP09 | M Review SHA 오류 뒤 참조6 파일0회 |
| HBP10 | M matching H의 invalid JSON 뒤 참조6 파일0회 |
| HBP11 | 기존 Review/M2.75 뒤 Entry 모순 회귀 보존, B가 전체 tuple 그대로 전달 |
| HBP12 | M REVOKED Review 복원 뒤 selector status 오류 |
| HBP13 | M untrusted Review 실패 시 파일6 미접근 |
| HBP14 | M/W B의 Review1회+C의 내부 Review1회, C1회 실제 경로 |
| HBP15 | M R_pre 주입/skip/reader 옵션 없는3입력 API |
| HBP16 | M/W same_call_result 자체와 raw7/원본 is |
| HBP17 | M 상대/drive-relative/drive root 거부 |
| HBP18 | M traversal/점/빈 component 거부 |
| HBP19 | M 절대경로 주입 거부 |
| HBP20 | M UNC/remote drive profile 거부, 실제 SMB 서버 시험은 미수행 |
| HBP21 | M device/extended/NT namespace 입력 거부 |
| HBP22 | M ADS colon 거부 |
| HBP23 | M CON/NUL/COM/LPT 예약명 거부 |
| HBP24 | M 위첨자 예약명 거부 |
| HBP25 | M 끝점/공백/제어/금지 문자·surrogate 거부 |
| HBP26 | M 한글/공백/NFC·NFD 원문 component 보존, W 한글 경로의 임시 보관소 |
| HBP27 | M/W 실제와 다른 case alias 거부 |
| HBP28 | M normalized long path/short alias 불일치 거부, 실제8.3 alias 생성 시험은 미수행 |
| HBP29 | M/W root junction 거부 |
| HBP30 | M/W mid-path junction/reparse 거부 |
| HBP31 | M leaf reparse 거부, **S 실제 file symlink 생성1314로 미실행** |
| HBP32 | M 실제 final path/volume 선언 불일치 거부 |
| HBP33 | M root 접두사만 같은 sibling 거부 |
| HBP34 | M directory가 파일 역할인 경우 거부, native GetFileType/종류 검사는 W 정상·junction에서 확인. 실제 pipe/device 생성 시험 없음 |
| HBP35 | M Review 파일 없음 오류·후속0회 |
| HBP36 | M raw6 역할별 파일 없음·이후 open0회 |
| HBP37 | M/W 실제 hard link count2 거부 |
| HBP38 | M 같은 path/file ID 역할 alias 거부 |
| HBP39 | E 과거 파일 이동 이력/발급 신뢰는 handle 정보로 인증 불가 |
| HBP40 | M 실제 열린 target 기준 검사·SHA, 사전 교체 완전 탐지 주장 없음 |
| HBP41 | W 자식 process 일반 write open32 거부 |
| HBP42 | W 자식 process file rename/delete32 거부·해제 후 write 가능 |
| HBP43 | W directory rename5 거부·해제 후 동일 rename 가능. 악성 metadata/reparse 모든 경쟁 차단은 E |
| HBP44 | M ID/길이/mtime/속성·location 변화, Q5/Q7 검사; W SetFileTime 변화 탐지 |
| HBP45 | access time을 저장 equality에서 제외하는 구현/정상 반복 회귀. access time 강제 변경 시험은 미수행 |
| HBP46 | M metadata/location/query 예외 원본 전파·fallback 없음 |
| HBP47 | M short read17byte로 전체 원본 재현 |
| HBP48 | M 초기 n 이전 EOF 거부 |
| HBP49 | M read 예외 원본 전파·handle 정리 |
| HBP50 | M/W 정확히4MiB 읽기 경계 |
| HBP51 | M/W4MiB+1 거부, M huge size는 allocation 전 거부 |
| HBP52 | M/W 합계16MiB 경계 |
| HBP53 | M/W 합계16MiB+1 거부 |
| HBP54 | M/W empty 파일 거부 |
| HBP55 | M EOF probe의 추가 byte 감지 |
| HBP56 | M component/depth/path/handle예산 거부, 고정4096unit native buffer 구현 |
| HBP57 | M/W 같은 bytes 보존·정상 후 닫힘·재읽기 없음 |
| HBP58 | M 각 원본 누락/open/query/read 예외 후 역순 정리 |
| HBP59 | M/W C 도메인 오류·M RuntimeError 원본 보존 |
| HBP60 | M primary+close 오류 동시 첫 예외 유지·모든 close 시도 |
| HBP61 | M 계산 성공 뒤 close 실패 시 결과 폐기 |
| HBP62 | M raw6 각 SHA 오류, W 실제 Envelope/Registry 변조 거부 |
| HBP63 | M 다중 Entry의 명시 revision 선택 및 기존 로더 직접 binding 회귀, 다른 revision fallback 없음 |
| HBP64 | M 선택 E 참조 유지·기존 M2.75 revision/Entry raw 혼합 거부 회귀 |
| HBP65 | M 실제 로더6 성공 후 기존 교차 부정20사례 거부 |
| HBP66 | M Benefit SHA 오류보다 먼저 발생한 Registry open 오류 전파 |
| HBP67 | 기존 M2.75 다중 SHA 오류 우선순위 보존·C 재사용 |
| HBP68 | M/W 원본당 한 file open·ReadFile/metadata는 같은 handle |
| HBP69 | M 고정 OS 입력101호출, W 정상/실패 각20회·handle 수 불변 |
| HBP70 | M 같은 ref/경로 raw 변조 SHA 거부, fp를 raw SHA로 대체하지 않음 |
| HBP71 | E filesystem 원자적 snapshot 미제공, refs/C 일관성만 확인 |
| HBP72 | M 실제 lock/bytes 준비와 도메인 fp/교차 오류 분리 |
| HBP73 | E expected 발급/보존 권한 신뢰 미인증 |
| HBP74 | E production ZIP/profile/import 실행 검증 미구현 |
| HBP75 | E import-before-trust 운영 launcher 미구현, 기존 bootstrap 변경 없음 |
| HBP76 | E 공식 Source/locator/전체 envelopes/Content·release 미완료 |
| HBP77 | M 반환 API에 VERIFIED/USABLE 상태 없음, 실제 사용 판정 E |
| HBP78 | M unsupported OS/drive/filesystem은 명시 거부, 일반 open fallback 없음 |
| HBP79 | E T1/T2/ACL·관리자·기존 writable mapping 한계 유지 |
| HBP80 | 전후206개 보호/실제6 release·기존11144 회귀, 결과는26.8절 |

80개를 전부 실제 OS에서 통과했다고 주장하지 않는다. 기존 helper/로더가 이미 검증하는 내용은 기존 회귀 재사용으로 기록하며 새 실행 테스트 수에 중복 합산하지 않는다. 권한 부족 S와 외부 E는 통과 수에 포함하지 않는다.

### 26.7 보안 보장 범위·최종 판단·다음 최소 작업

**HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY**

구현과 합성157개·실제 NTFS16개는 통과했으나, 필수 실제 file symlink 사례1개가 생성 권한 부족으로 미실행이다. 따라서 전체 **HISTORICAL_RAW_BYTES_PREPARATION_COMPLETE**를 선언하지 않는다. SYNTHETIC_ONLY라는 판정이 실제 OS 시험을 하나도 하지 않았다는 뜻은 아니며, 실제 보안 경계의 미완료 항목을 보수적으로 남기는 사용자 지정 판단이다.

추가 구현이 필요한 미완성 parser/보안 fallback으로 이를 우회하지 않았다. 새 source/도메인 모델·현재 정책 혜택/자격 승인도 없다. T1 보관소 ACL/발행·정상 호스트·A 발급 신뢰·D production 실행 artifact는 별도다. 준비 코드의 import/실행 성공을 production ZIP 검증 완료로 쓰지 않는다. 실제 NTFS 공유 제한도 악성 관리자/모든 metadata 변경/원자적 filesystem snapshot까지 보장하지 않는다.

**다음 최소 작업 하나:** file symlink 생성을 허용한 별도 Windows NTFS 시험 환경에서 **현재의 실제 file symlink 거부 시험1건을 실행하고 결과를 닫는다.** 현재 사용자 시스템의 Developer Mode/권한 설정을 변경하지 않았고 변경 승인을 추정하지 않는다. 이 잔여 시험을 새 History 모델·일반 framework·Content/Source Gate·production launcher 구현으로 확대하지 않는다.

### 26.8 전체 회귀·파일 보존

사전 actual 전체: **11144 passed in 81.30s (0:01:21)**. 최종 신규 합성 **157 passed in1.97s**, 실제 NTFS **16 passed, 1 skipped in2.25s**로 신규173개 통과/174개 수집이다. 사후 actual 전체: **11317 passed, 1 skipped in 61.84s (0:01:01)**. 사전/사후 전체는 각각 최초 실행 성공이다. 사후 건너뜀1개는 신규 실제 file symlink 생성 WinError1314이며 PASS로 계산하지 않는다. 신규 실패·수정·재실행 이력은26.4~26.5절에 모두 기록했다. pytest timeout0회, 별도 자동 승인 검토 timeout1회다. 사후 자동 보고 단계에서 skip 설명에 숫자1314가 포함된다고 잘못 가정한 보조 스크립트 assertion1건을 수정했다. 기존 실행 로그와 정확한 skip 사례/설명·시험 코드의1314 분기를 대조해 마무리했으며 전체 pytest는 재실행하지 않았다.

기존 보호 파일206개 중 **204개 SHA256·크기·mtime_ns 동일**, 변경2개는 승인된 계약/Architecture 문서뿐이다. 신규 운영2/테스트2를 추가해 최종 보호 파일210개, 삭제0개다. 기존 운영 코드·테스트·fixture·기대값·export·설정은 모두 보존했다. 실제 release6개는 **6개 전부 SHA256·경로·크기·mtime_ns 동일**. 기존 tests/fixture/기대값·GV01~15/BV01~16·Coverage freeze·M2.75/Review/로더6/교차·Source parser/fp·Manifest validator·ZIP bootstrap·Acceptance/Benefit/Cashflow·public export·설정은 **기존11,144개 전부 + 신규173개 = 11,317개 통과. 신규 실제 file symlink1개만 건너뜀이며 기존 테스트의 건너뜀/실패0개, 기존 파일·fixture·기대값 보존**.

사전/사후 실제 release 경로·SHA256·크기·mtime_ns는 기존 부록A 값과 동일하다. Coverage core **ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS**, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**, 실제 Ansan **DRAFT / CONDITION_SLICE**·정책 혜택 반영0원 원칙을 유지한다. 실제 검토/Acceptance/철회·정책 금액·새 실제 정책 지문·운영 실행 ZIP을 만들지 않았다.

### 26.9 최종 보고31항목 대응

| 번호 | 항목 | 구현·검증 |
|---|---|---|
| 1 | 구현 요약 | 파일 준비→기존 C 강제→완전 반환, 순수 함수가 아닌 I/O 계층 |
| 2 | 변경 파일 | 신규 운영2/테스트2, 수정 문서2만 |
| 3 | API | private3필수 keyword-only·15절 exact annotation, export 없음 |
| 4 | locator | expected 공통 H→기존 acceptance-reviews/H.json |
| 5 | Stage1 | 실제 Review strict·전체 expected·기존 selector/원본 A |
| 6 | Stage2 | 검증된 E의 ref6·고정 순서 read |
| 7 | root | trusted local NTFS·drive/root chain·T1 외부 전제 |
| 8 | 경로 | 문자열과 실제 handle 경로/volume/alias·reparse 분리 |
| 9 | same-handle | 제한 공유 CreateFileW·동기 ReadFile·Q7까지 유지 |
| 10 | identity | 실제 volume/index/path·속성/길이/link 비교 |
| 11 | TOCTOU | chain/handle/사후 검사, 원자 snapshot·악성 host 보장 없음 |
| 12 | 크기 |4MiB/file·16MiB/raw7·64KiB read, RSS 상한 아님 |
| 13 | 기대 SHA | 기존 로더 재사용, 직접 hash/parser 없음. 지시문 차이는26.1절 |
| 14 | C 호출 | raw7 완료 뒤 기존9입력·정확히1회 |
| 15 | 반환 | 기존 tuple 자체 is + 동일 immutable raw7 |
| 16 | 오류 | 신규6prefix·Q0~Q8·기존 PolicyDataError/OSError 객체 유지 |
| 17 | Fail-Closed | 첫 오류 이후 새 파일/C 호출0회·부분 반환 없음 |
| 18 | cleanup | reverse close·primary 보존·할당 실패도 close, native handle count 불변 |
| 19 | 합성 | 최종157개 통과, 최초2개 helper 실패/수정 이력26.4절 |
| 20 | 실제 NTFS |16개 통과·file symlink1개 권한 부족 skip |
| 21 | 실패/재실행 | 합성 helper2건·native sandbox3건/code 기대1건·승인 timeout 분리 기록 |
| 22 | 전체 pytest | 사전11144 / 사후 11317 passed, 1 skipped in 61.84s (0:01:01) |
| 23 | 기존11144 | 기존11,144개 전부 + 신규173개 = 11,317개 통과. 신규 실제 file symlink1개만 건너뜀이며 기존 테스트의 건너뜀/실패0개, 기존 파일·fixture·기대값 보존 |
| 24 | GV/BV | 기존 값·파일·계산 회귀 보존 |
| 25 | releases | 6개 전부 SHA256·경로·크기·mtime_ns 동일 |
| 26 | freeze | 기존 core/API/상태/지문/Review/오류 동결 유지 |
| 27 | ResidenceHistory | OFFICIAL_INQUIRY_REQUIRED |
| 28 | 실제 정책 | DRAFT / CONDITION_SLICE 유지 |
| 29 | 남은 실행 신뢰 | file symlink W증거·T1/ACL·발급 신뢰·production D/Content/Source/release |
| 30 | 판단 | HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY |
| 31 | 다음 한 작업 | 권한 허용 Windows에서 기존 file symlink 실제 시험1건 완료 |


## 27. M2.77 보충 검증 — Windows NTFS File Symlink Rejection

검증일: **2026-10-24 / Asia/Seoul**. 새 milestone/기능이 아닌 필수 실제 file symlink 증거1건의 보충 확인이다. 기존 운영 코드·helper·Orchestrator·로더6·교차 검증·모든 테스트/fixture/기대값을 그대로 실행했다.

**최종 판단 유지: HISTORICAL_RAW_BYTES_PREPARATION_SYNTHETIC_ONLY.** 허용된 별도 Windows NTFS 환경의 접속 정보는 제공·확인되지 않았으며 사용자는 별도 환경을 알지 못한다고 답했다. 현재 로컬 PC에서 설정을 바꾸지 않고 재확인했지만 파일 symlink 생성이 권한 부족으로 실패해 실제 준비 함수의 symlink 거부 시험은 미실행이다. 별도 환경을 사용한 것으로 표시하지 않는다.

### 27.1 필수15항목 기록

| 번호 | 항목 | 이번 보충 검증 결과 |
|---|---|---|
| 1 | Windows/아키텍처 | version major10/minor0/build26300/workstation, AMD64·64bit, CPython3.12.14. 현재 실행 토큰 IsUserAnAdmin=False |
| 2 | NTFS | 환경 probe 및 실제 단독 시험 archive의 열린 directory handle에서 NTFS 확인. probe/추가 검사 handle 정리 완료 |
| 3 | symlink 생성 | 기존 test_actual_file_symlink_rejected가 CreateSymbolicLinkW 오류1314 전용 skip 분기로 중단. 생성 성공 아님 |
| 4 | 실제 링크 종류 | **생성된 링크 없음**. 의도한 종류는 file symlink이며 flags2, directory flag 없음. junction/hard link 통과를 대체 증거로 사용하지 않음 |
| 5 | 임시 대상 | 단독 시험 tmp_path/original-review.json 파일 존재 및 기존 합성 Review fixture와 bytes 일치 확인. 계획한 link는 임시 archive/acceptance-reviews 아래이며 생성 실패 뒤 존재하지 않음. 실제 release를 시험 입력으로 사용하지 않음 |
| 6 | 준비 함수 거부 | **미관찰/미실행**. symlink 생성 실패가 함수의 거부 성공을 뜻하지 않음 |
| 7 | 오류 타입/prefix | 생성 API last-error1314를 기존 시험이 pytest.skip으로 처리. 준비 함수 PolicyDataError/prefix는 발생·관찰되지 않음. 기대되는 HISTORICAL_RAW_PREPARATION_FILE_REJECTED를 실제 결과로 기록하지 않음 |
| 8 | 후속 호출 차단 | skip 위치가 run(inputs, root) 이전이므로 해당 사례의 Preparation/Orchestrator 호출0회. 이는 코드 경로상 미진입이며 symlink 거부 뒤 후속 차단을 실측한 증거가 아님. 우회·부분 반환 없음 |
| 9 | handle 정리 | 해당 symlink 경로에서 Preparation이 열었던 handle 자체가 없음. symlink 거부 후 정리는 미검증. 별도 기존 NTFS 정상/실패 정리·반복 handle count 시험은 통과했지만 대체하지 않음 |
| 10 | 실제 NTFS | 단독 symlink **1 skipped in 0.69s**. 기존 실제 NTFS 전체 **16 passed, 1 skipped in 2.17s**. 건너뜀은 동일 file symlink1개뿐 |
| 11 | 전체 회귀 | **11317 passed, 1 skipped in 66.89s (0:01:06)**. 기존11,144+신규173개 통과, 동일 신규 symlink1개만 skip |
| 12 | 실제 release6 | SHA256·경로·크기·mtime_ns 전부 보충 시험 전후 동일. 기존 부록A의6개 SHA도 유지 |
| 13 | GV/BV | GV01~GV15·BV01~BV16을 포함한 기존 테스트·fixture·기대값/운영 파일 보존, 전체 회귀 통과 |
| 14 | Coverage freeze | ELIGIBILITY_COVERAGE_CORE_FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS 유지. 정책/수용/금액 승인 효과 없음 |
| 15 | 최초/수정/재실행 | 보충 단독/NTFS/전체 각1회 실행, failed0·수정0·실패 수정 재실행0·pytest timeout0. 동일 symlink 사례가 세 실행에서 각각 skip되며 중복 PASS로 계산하지 않음. 기존 M2.77 최초 이력은26.4~26.5/26.8절에 보존 |

이번 실행은 현재 사용자 권한으로 수행했으며 IsUserAnAdmin=False를 관찰했다. Developer Mode/토큰 권한·보안 설정 변경, 관리자 권한 상승/UAC 실행을 하지 않았다. sandbox 밖의 현재 사용자 실행은 임시 junction/hard link 시험 생성 제약만 피하기 위한 것으로, 관리자 권한을 부여하거나 별도 PC 환경을 제공하지 않는다. mock으로 실제 symlink 시험을 대체하지 않았고, 미관찰 결과를 PASS/COMPLETE로 올리지 않았다.

보충 검증 전 보호 파일210개와 releases6개의 SHA256·크기·mtime_ns 기준선을 확보했다. 검증 후 문서 기록 전 **210개+6개 전부 동일**했다. 결과 기록은 기존 이 계약과 ARCHITECTURE 두 문서에만 덧붙인다. 기록 후 **208개 보호 파일+실제 release6개가 모두 동일**, 변경은 문서2개뿐이며 신규 프로젝트 파일/삭제/운영·테스트 변경0개다. 상세 전후 metadata·실행 로그 위치는 작업 기록 m277-supplement-baseline.json / m277-supplement-results.json / m277-supplement-final-audit.json에 둔다.

### 27.2 미완료 증거와 다음 개발 방향

필수 **실제 Windows NTFS file symlink 생성→기존 준비 함수 거부→후속 차단/정리** 증거1건은 그대로 미완료다. 허용된 별도 환경이 확보될 때 기존 시험을 실제 실행하고 관찰해야 한다. 보안 결함은 이번 skip으로 확인되거나 배제되지 않았으며 환경 문제를 이유로 production 코드를 수정하지 않았다.

사용자의 최신 방향에 따라 후속 개발은 **M3 — 합성 데이터만 사용하는 실제 사용자 기능**으로 전환한다. 첫 목표 범위는 **사용자 입력 → 기존 Policy Engine → 자격 판정·불확실성 표시 → 기존 Cashflow Core → 결과 API → 최소 React 화면**의 단일 실행 경로다. 이번 보충 작업에서는 M3 설계/기능/API/UI를 구현하지 않았다. 이 전환이 M2.77 COMPLETE나 production artifact 신뢰 승인을 뜻하지 않는다.

실제 안산 정책은 **DRAFT / CONDITION_SLICE**, ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**, 검증되지 않은 실제 정책 지원금은 **Cashflow 반영0원**을 유지한다. 기존 Coverage freeze/GV/BV·독립 기대값·공식 원문/Content/Source Gate·production 실행 신뢰의 경계도 그대로다.

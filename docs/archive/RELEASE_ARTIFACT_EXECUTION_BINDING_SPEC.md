# 엔진·Coverage Artifact 식별 및 실행 대응 계약 — M2.52

현재 구현 상태는 **26절 M2.53**을 따른다. 외부 bootstrap의 합성 verify-only만 구현했으며 production builder·Manifest loader·정책/수용 평가는 없다.1~25절은 승인된 설계와 당시 검증 기록이다.

작성일: **2026-10-22 / Asia/Seoul**. **문서 한 개 추가**. 최종 판단: **READY_TO_IMPLEMENT_ARTIFACT_EXECUTION_BINDING_VALIDATION**.

이번 판단은 아래의 **고정 코드 ZIP·새 격리 프로세스·실제 import 대응 검증**을 구현할 준비에 한정한다. 현재 그런 배포물/검증기/실행기가 있다는 뜻이 아니다. 실제 artifact·artifact hash·Manifest·승인·금액을 생성하지 않는다. 코드·테스트·기존 문서·실제 releases는 수정하지 않는다.

## 1. 현재 구현과 확인 근거

| 실제 확인 자료 | 확인한 사실/적용 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md |8개 내부 입력, A 자료 준비/C 같은 호출 결합, 전체 release와 선택 대상 분리, 두 실행 artifact의 대응 미정 |
| BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md / COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md |9필드 Result·12Reason·정상 implementation 변경, 같은 호출 원본, 검토/실행 artifact 구별 |
| POLICY_DATA_ENVELOPE_SPEC.md / 실제 manifest.py·validation.py | 실제 artifact bytes SHA와 객체 지문 분리, 전체 집합 검증, 실제 빌드/bytes 검증 미구현 |
| COVERAGE_REVIEW_CONTEXT_SPEC.md / 실제 두 Review·Context | implementation_fingerprint는 입력/evaluator 배포물 원본 bytes SHA256. 과거 Review 대 현재 baseline 차이는 정상 STALE |
| COVERAGE_FINGERPRINT_SPEC.md / 실제 coverage_fingerprint.py | Inventory/Tree/subtree canonical payload·GV01~GV15 동결, artifact는 JSON 변환 없이 원본 bytes 전체 해시 |
| COVERAGE_INTEGRATION_GATE_SPEC.md / 실제 integration·matching | 순수 Gate·현재 지문/Review 결합·독립 conflict·기존 호출/오류 순서 |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md / CORE_FREEZE | 공식 Coverage 평가1회,8필드 Result·all-None baseline, 실행물 진실성은 외부 책임 |
| DATA_MODEL.md / ARCHITECTURE.md | 현재 완료 코드와 미구현 Acceptance evaluator/adapter·Bridge·실제 full 자료 구별 |
| pyproject.toml | pytest 설정만 있음. build-system/project/package 빌드 설정 없음 |
| requirements-dev.txt | pytest==8.4.2 하나. runtime dependency lock은 아님 |
| README.md / tests/conftest.py·test_acceptance.py | checkout 루트에서 pytest/합성 CLI 실행. CLI 테스트도 현재 Python과 checkout으로 subprocess 실행 |
| backend 전체61개 .py의 AST import 조사 | 로컬 코드와 표준 라이브러리만 사용. 동적 import/프로세스·환경 주입 코드는 조사 범위에서 발견하지 못함 |

backend는 policy_engine56개 .py, cashflow4개 .py, backend/__init__.py의 **실제 전체61개 .py**를 기준으로 조사했다. 정확한 포함 집합은4절 규칙이며 현재 숫자를 패키징 allowlist로 쓰지 않는다.

현재 실행 진입점은 `backend.policy_engine.__main__.main`인 **checkout의 합성 예제**다. 실제 Coverage 진입점은 `policy_data/eligibility_coverage_evaluator.py`의 `evaluate_eligibility_coverage`이며 서비스 launcher는 없다. `__main__.py`는 자기 경로에서 data/synthetic를 찾으므로 코드 ZIP 배포의 서비스 진입점으로 재사용하지 않는다.

현재 ENGINE_VERSION은 **m1.0**이다. 호환 표식이며 빌드 identity가 아니다. Git 저장소·Docker·wheel·lockfile·CI/배포 script는 프로젝트 조사에서 확인되지 않았다. 있다고 가정해 commit/container digest로 대체하지 않는다.

사전 전체 pytest: **6962 passed in 16.29s**. backend/tests/data/docs165개, 루트 설정4개, 실제 release6개의 SHA256 기준선을 확보했다.

## 2. 이번에 답하는 여섯 질문

| 질문 | 확정 답변 |
|---|---|
| A 무엇을 검토했는가 |4절 포함 코드와 bootstrap·runtime profile을 담은 **하나의 실제 코드 ZIP 확인본**. Review는 그 ZIP 원본 bytes SHA를 기록 |
| B 무엇을 실행하는가 |명시 Manifest.engine_artifact_sha256와 같은 SHA의 확보 ZIP을 새 worker가 직접 import. checkout/다른 설치 package와 혼합하지 않음 |
| C 무엇을 hash하는가 |ZIP 파일의 첫 byte부터 마지막 byte까지 그대로 SHA256. 내부 파일명 목록이나 버전 문자열의 해시가 아님 |
| D 어디서 대응하는가 |외부 bootstrap이 파일/환경을 검증한 뒤, 새 프로세스의 모든 backend 모듈 loader/archive/entry 경로를 대조. 계산은 그 worker 안에서만 수행 |
| E 변경 시 무엇을 하는가 |현재 코드/환경/배포 선택 재검증, 과거 Review/Acceptance binding 대조 및 필요한 실제 재검토. 기존 기록은 덮어쓰지 않음 |
| F 무엇을 못 증명하는가 |악의적 호스트/검증기·검토 진실성/권한·역사 완전성·Python/표준 라이브러리 bytes의 인증·일반 원격 attestation |

## 3. 지문 의미와 저장 위치

| 값 | 정확한 대상 | 저장/사용 위치 |
|---|---|---|
| Inventory fp | 기존 coverage-inventory-1.0 canonical JSON/UTF-8 | Review·Coverage findings·Acceptance binding |
| Tree fp | 기존 coverage-policy-tree-1.0 canonical JSON/UTF-8 | 같은 위치의 policy_tree_fingerprint |
| Subtree fp | 기존 coverage-subtree-1.0 canonical JSON/UTF-8 | ImplementationBindingReview·finding |
| Benefit fp | 기존 benefit-snapshot-1.0 정의15key canonical JSON/UTF-8 | 기존 전용 helper·Acceptance binding |
| Registry fp | 기존 fingerprint_source_registry의 메모리 도메인 값 | Manifest reference·Context/Result·Benefit/Acceptance |
| 엔진 artifact SHA | 아래 코드 ZIP 원본 bytes 전체 | DatasetManifest.engine_artifact_sha256 |
| Coverage implementation SHA | 같은 코드 ZIP 원본 bytes 전체 | 현재 CoverageReviewContext.implementation_fingerprint, 검토 당시 ImplementationBindingReview.implementation_fingerprint, Result 및 Acceptance의 구현 binding |

마지막 두 역할의 SHA가 같은 것은 **이번 MVP에서 실제 같은 ZIP bytes를 선택하기 때문**이다. 두 필드의 기존 의미를 하나의 domain fingerprint로 바꾸지 않는다. review_artifact_ref는 사람이 작성한 검토 자료 참조이며 실행 ZIP identity가 아니다.

Manifest에는 엔진 artifact 경로 필드가 없다. 작업자가 명시 전달한 로컬 ZIP 경로를 외부 실행 기록에 보존하고 그 **관찰한 bytes**를 Manifest 기대 SHA와 대조한다. 경로 이름은 identity가 아니며 Manifest schema에 몰래 필드를 추가하지 않는다. Context에도 경로/환경 지문을 추가하지 않는다.

## 4. 두 역할의 범위와 실제 의존관계

| 역할/참조 필드 | 고정할 책임 | 포함 코드 | 제외 자료 | 생성/검증 책임 |
|---|---|---|---|---|
| 엔진 배포 / Manifest.engine_artifact_sha256 | 정책 입력/파싱/판정·근거/metadata·Coverage/Benefit/Acceptance·Cashflow 및 호출 결합 | 아래 backend 전체 .py + bootstrap + runtime profile | 정책/source/검토 데이터·테스트·UI·환경 설치물 | 자료 준비자가 bundle 생성, 별도 검토, bootstrap과 worker가 bytes/import 대조 |
| Coverage implementation / Context·Review의 implementation_fingerprint | 검토한 입력·Rule 평가·Resolver/Adapter·Coverage 구조/결합/지문/매칭/Result와 공통 helper를 실제 배포 코드에 결합 | **같은 bundle 전체**. 아래 책임의 코드가 빠지지 않는 보수적 superset | 같은 제외 목록 | 검토자가 실제 bundle을 고정, current baseline은 확인한 worker에서 공급 |

포함 규칙은 **backend 아래 모든 일반 .py 파일을 상대 경로 그대로**다. package __init__.py도 포함한다. 현재61개는 조사 시점 수치이며 이후 파일 추가를 누락시키는 고정 숫자 제한이 아니다. backend 안 새 실행 .py는 자동 포함 대상이면서 별도 변경 검토 대상이다. 명시 제외한 __pycache__ 등 개발 캐시를 먼저 제외하고, 그 밖의 비-.py 실행 파일/동적 코드/리소스 의존성이 추가되면 조용히 제외하지 않고 패키징을 거부해 범위 개정부터 한다. symlink/junction으로 외부 코드가 들어오는 입력도 거부한다.

| 현재 경로군 | 결과에 영향을 주는 책임/포함 근거 |
|---|---|
| policy_engine/models.py·errors.py·result_types.py·evaluation_inputs.py | Policy/UserProfile/FactBasis·타입/날짜·입출력 검증·상태/근거·공통 serializer |
| policy_engine/facts/·specialized_rules/ | 출생/주민등록 사실·지역·특수 Rule 검증 |
| evaluator.py·routing.py·birth_evaluator.py·resolvers/·adapters/ | atomic/group 집계·혼합 Rule dispatch·주민등록 resolution/adapter·출생일 판정 |
| loader.py·sources/·policy_data/loader.py·envelope.py·manifest.py·validation.py | strict JSON parsing·source/locator·현재 release/domain 지문·참조/버전 대응 |
| policy_data/condition_*·required_condition.py·coverage.py·eligibility_coverage.py | Inventory/Binding/Scope/조건 입력모델 |
| policy_data/rule_root_resolution.py·coverage_ownership.py·coverage_unmapped.py·coverage_structure.py·coverage_composition.py | root/소유/미매핑/구조 및 결합 제약 |
| policy_data/coverage_fingerprint.py·coverage_review*.py·implementation_review.py | payload 생성/직렬화·검토 모델·조회/독립 guarded matching |
| policy_data/coverage_integration*.py·eligibility_coverage_result.py·eligibility_coverage_evaluator.py | findings·공식 평가·factory·파생 FULL/SLICE |
| policy_data/benefit_*.py | Benefit 정의/지문, Acceptance21필드·Context/resolver·결과9필드 |
| cashflow/*.py 및 모든 __init__.py·__main__.py | 실제 배포가 소유하는 계산/공개 import 코드 전체. 합성 main은 동봉하지만 서비스 실행 target은 아님 |
| 향후 backend 아래 Acceptance evaluator/source gate/adapter·release 호출 코드 | 추가 시 같은 bundle에 포함. 현재 존재한다고 가정하지 않으며 변경 시 SHA가 바뀜 |

Coverage 코어만 분리하면 `models.py`의 Rule/serializer, evaluator/routing/Resolver·사실 검증, package __init__의 간접 import를 빠뜨릴 수 있다. 현재 작은 규모에서는 전체 backend를 포함해 누락 위험을 줄인다. Acceptance만 바뀌어도 Coverage 구현 SHA가 바뀌는 보수성은5·19절에서 비용으로 인정한다.

## 5. 공유와 분리 비교 — 공유 선택

| 대안 | 실행 대응·변경 영향 | MVP 판단 |
|---|---|---|
| A 하나의 고정 코드 ZIP을 두 역할에 공유 | 실제 import되는 backend 전체가 검토 artifact에 포함. 별도 교집합/파일 대응표 필요 없음. Acceptance/Cashflow/주석 변경도 implementation SHA를 바꿔 재검토 범위가 넓음 | **채택**.61개 .py·표준 라이브러리 구조에서 운영 가능 |
| B engine bundle과 입력/evaluator bundle 분리 | Coverage 변화가 없는 Acceptance 수정에서 Review 재검토를 줄일 수 있음. 정확한 transitive dependency closure·공통 파일 bytes equality·두 bundle 대응 검증이 필요 | 현재 미채택. 같은 version 이름만으로 대응 인정 불가 |

분리한다면 engine 안 실제 입력/evaluator 모듈이 implementation bundle의 전체 대응 entry와 byte 단위로 같고, 공통 helper/package import 경로 및 환경이 같다는 검사를 추가해야 한다. 그 검사가 없으면 두 역할이 충족되지 않는다. 이 설명은 분리 운영을 허용하는 두 번째 MVP 경로가 아니다. 미래에 필요하면 새 명시 규약으로 선택해야 한다.

새 공유 방식은 **새로 발행하는 bundle**에 적용한다. 과거의 서로 다른 artifact hash를 같게 덮어쓰거나, 기존 합성 tests의 두 literal이 달라도 오류로 바꾸지 않는다. 기존 순수 모델/validator에 전역 equality 규칙을 삽입하지 않는다.

## 6. 선택한 최소 패키징 방식

wheel은 현재 build metadata·설치/lock 절차가 없고, 단순 checkout 실행은 수정/경로 혼재를 허용한다. MVP는 **표준 ZIP source bundle + 명시 bootstrap 실행**으로 확정한다. Docker·서명 서버·CI는 선행하지 않는다.

후속 패키징 결과의 개념 배치는 다음과 같다. **이번에는 이 파일들을 만들지 않는다.**

```text
code-bundle.zip
  bootstrap.py            # 후속 작은 실행 검증기, 표준 라이브러리만 사용
  runtime.json            # 아래 고정 환경/형식 선언, 사용자/정책 자료 없음
  backend/__init__.py
  backend/policy_engine/**/*.py
  backend/cashflow/**/*.py
```

ZIP 엔트리는 slash 상대 경로·code point 오름차순, 중복/대소문자 충돌/경로 탈출/절대 경로/drive/역슬래시/비일반 파일을 거부한다. backend package들의 __init__.py가 있어야 한다. 파일은 **ZIP_STORED, .py 원본 bytes 그대로** 저장한다. .pyc/.pyo·native module(.pyd/.so)·추가 ZIP 실행 경로는 허용하지 않는다. 이를 검사하지 않은 임의 ZIP을 release bundle이라고 부르지 않는다.

Python은 ZIP의 .py package import를 지원하고 ZIP 내부 native module import는 지원하지 않는다. 이번 방식은 프로젝트가 현재 pure Python이라는 조사 결과를 사용한다. [Python ZIP import 공식 문서](https://docs.python.org/3.12/library/zipimport.html).

runtime.json은 패키징 metadata이며 새로운 domain Context/Result가 아니다. exact key는 `bundle_format`, `python_implementation`, `python_version`, `sys_platform`, `machine`, `runtime_dependencies`다. bundle_format은 `python-code-bundle-1.0`, Python version은 세 exact int의 배열, 현재 runtime_dependencies는 빈 배열이다. strict UTF-8 JSON·duplicate/unknown keys 거부, 자동 default 없음. version/플랫폼 값은 실제 검토·선택 환경에서 명시한다. 절대 경로·시각·자기 SHA·Manifest·Review·선택 Acceptance는 넣지 않는다.

metadata는 정렬 key/compact JSON/UTF-8로 생성하되, **최종 artifact SHA 대상은 ZIP 전체 bytes**다. runtime.json JSON 지문을 implementation SHA로 쓰지 않는다.

## 7. 제외 목록과 코드·데이터 분리

| 자료 | 고정하는 경계 | 코드 bundle 포함 여부/이유 |
|---|---|---|
| 정책 JSON/Envelope | Manifest 전체 reference·artifact SHA·Envelope domain fp | 제외. 데이터 수정이 코드 변경이 되지 않음 |
| Registry/source 원문 | Manifest Registry artifact/domain fp·source_versions/bindings·원문 보존 | 제외. 코드 SHA로 source 최신성/동일성을 대신할 수 없음 |
| Inventory/Binding/Coverage Review·Benefit·Acceptance 이력 | 각 기존 구조·지문·검토/불변 원본과 현재 준비 계약 | 데이터는 제외, 이를 읽고 검증하는 코드는 포함 |
| 사람이 작성한 검토 artifact | 별도 불변 검토 evidence·ref/bytes 보존 | 제외. 실행물 일치가 claim 검토를 인증하지 않음 |
| tests/·pytest 설정·requirements-dev.txt | 개발/회귀 증거 | 제외. pytest/테스트 결과는 runtime 코드나 승인 artifact가 아님 |
| docs/·README·.git·frontend/UI | 설계/보조 이력·UI 별도 배포 책임 | 제외. UI가 계산을 대신 수행하면 이 계약의 보장 밖이며 별도 결합 필요 |
| .venv·site-packages·Python 설치물 |8절 외부 환경 | 제외. ZIP SHA가 interpreter/stdlib bytes를 포함한다고 주장하지 않음 |
| __pycache__·.pytest_cache·tmp·로그·사용자 입력·환경 설정 | runtime 결과/개인 환경 | 제외. 결과 영향 설정이 필요해지면 숨겨서 환경 변수로 읽지 않고 별도 명시 입력 계약부터 함 |

backend 내부의 새 non-.py 리소스를 쓰는 코드가 생기면 이 제외표로 안전하다고 간주하지 않는다. 빌더가 발견해 중단하고 포함 경계를 검토해야 한다. 현재 결과 계산에 영향을 주는 로컬 .py helper는4절 전체 포함으로 빠지지 않는다. bootstrap/환경은 별도 신뢰 기반도 있으므로20절 한계를 따른다.

## 8. 의존성과 실행 환경 고정 수준

관찰한 개발 실행환경은 **CPython 3.12.14 / win32 / AMD64**다. 설치된 배포 패키지는 pip25.0.1, pytest8.4.2, pluggy1.7.0, packaging26.3, iniconfig2.3.1, colorama0.4.6, Pygments2.21.0이다. 이 목록은 개발 환경 관찰이며 bytes 인증/운영 dependency lock이 아니다. backend import 조사에서 runtime 외부 패키지 의존은 발견하지 못했다.

| 구분 | MVP 규약 | 보장/한계 |
|---|---|---|
| A ZIP 안 | 모든 backend 코드·bootstrap·runtime.json | 원본 ZIP SHA가 이 bytes를 함께 고정 |
| B 외부 Python | 팀이 지정한 정상 설치의 **명시 절대 Python 경로**, 정확한 implementation/version/플랫폼/아키텍처 및 base installation, 허용 stdlib 경로를 실행 기록에 보존 | runtime.json과 관찰값 대조. 버전 문자열로 Python/stdlib bytes까지 인증하지 않음 |
| B 실행 옵션 | 새 프로세스 `-I -S -B -X utf8`, optimize=0, 명시 runner/bundle/자료 경로 | checkout/user site/환경 기반 package 주입·bytecode 사용 혼재를 예방. 옵션/실제 flags 대조 |
| B 의존 package | 현재 runtime third-party **0개**, site-packages 경로를 import 경로에서 제외 | pytest/pip 존재를 runtime 허용으로 간주하지 않음. 새 third-party 필요 시 설치물/간접 의존 pin 규약을 개정 |
| B 설정 | 문서화한 명시 입력만 사용, 코드 선택/규칙/현재 날짜를 환경에서 자동 선택하지 않음 | 외부 release·사용일·프로필은 별도 입력. worker가 임의 환경 설정을 계산에 참조하면 미지원 |
| C 보장 밖 | 동일 버전의 변조 interpreter/stdlib/native DLL·OS·호스트·외부 도구 | 신뢰된 설치/운영 절차 전제. supply-chain/remote attestation 보장 없음 |

격리 옵션의 의미는 Python 공식 문서로 확인했다. -I는 사용자 site와 script/current 경로·PYTHON 환경 변수 영향을 제한하고, -S는 site 초기화를 끄며 -B는 .pyc 생성을 막는다. 이 옵션만으로 ZIP을 자동 선택하거나 모든 호스트 위험을 제거하지는 않는다. [Python 실행 옵션](https://docs.python.org/3.12/using/cmdline.html).

실제 로컬 `-I -S -B` 점검에서 checkout/site-packages가 sys.path에 없고 base Python의 표준 경로만 남는 것을 확인했다. **3.12의 -S에서는 venv sys.prefix가 base를 가리킬 수 있으므로 venv prefix equality를 검증 기준으로 쓰지 않는다.** sys.executable·sys.base_prefix·허용 표준 경로와 실제 flags를 확인한다. 이는 환경 조회이며 artifact/정책 결과를 생성한 테스트가 아니다.

runtime.json의 버전/플랫폼을 변경하면 ZIP도 바뀐다. 같은 version·profile을 유지한 재설치/호스트 변경은 자동 hash 차이가 없을 수 있다. 이 경우 기존 프로세스/환경 확인을 폐기하고 설치의 신뢰와 회귀·실행 대응을 다시 확인한다. byte 동일성을 기계적으로 인증했다고 표현하지 않는다.

첫 구현의 지원 환경은 **Windows의 정상 로컬 파일시스템**으로 제한한다. 이 프로젝트의 실제 환경과13절의 파일 공유 제한을 사용하기 위한 선택이다. 다른 플랫폼/네트워크 파일시스템으로 옮기면 동일 불변 보장을 다시 정의하기 전 검증된 실행으로 인정하지 않는다. worker는 isolated/ignore_environment/no_user_site/no_site/dont_write_bytecode/safe_path 활성화, optimize=0, utf8_mode=1을 확인한다. int 문자열 변환 한도 등 결과 영향 Python 설정은 승인한 기본값에서 바꾸지 않고, 특히 get_int_max_str_digits=4300을 확인한다. hash randomization은 유지하되 기존 결정성 계약상 결과/지문 순서가 hash seed에 의존해서는 안 된다.

## 9. 정확한 hash 계산·보존 규약

H는 **확보한 code-bundle.zip의 원본 bytes 전체에 대한 SHA256 lowercase hexdigest**다. exact64자리·접두사/공백/newline 없음. ZIP 헤더/entry 내용/metadata/central directory/comment 등도 원본에 포함한다. JSON 변환·newline/BOM 제거·파일명/mtime/size/Git commit hash 대체는 없다.

빌더는 backend 입력을 읽어 불변 source snapshot을 준비하고, 그 **읽은 bytes**로 ZIP을 완성한 뒤 ZIP bytes를 해시한다. 검토자도 같은 ZIP을 보존·검토한다. 경로를 다시 읽었는데 내용이 바뀌었다면 새 대상이다. 빌드 도중 checkout을 수정해 혼합 snapshot을 만들지 않도록 동결된 준비본을 사용한다.

H를 쓰는 곳은 새 Manifest.engine_artifact_sha256, 현재 worker로 구성한 CoverageReviewContext.implementation_fingerprint, 실제 그 bundle을 검토한 ImplementationBindingReview.implementation_fingerprint다. 과거 Review 값은 유지한다. Acceptance 발급 시 coverage_implementation_fingerprint는 그 검토 확인본을 기록하고, 현재 평가 시 정상 변경을 대조한다.

ZIP 내부에는 자기 SHA를 저장하지 않는다. Manifest와 검토 원본도 ZIP 밖이므로 자기참조가 없다. 코드 version 이름·Git 정보는 보조 이력으로만 남길 수 있다. 현재 Git이 없고, 있더라도 미커밋 .py·생성 실행 코드·패키징 metadata 차이는 실제 ZIP bytes가 잡아야 한다. Git이 환경 bytes를 인증하지 않는다.

이번 문서의 H/H1/H2는 **기호**다. 실제 또는 합성 hex64를 계산/발행하지 않았다. 실제 artifact가 없으면 H를 임의로 채우지 않는다.

## 10. 실행 진입과 bootstrap의 신뢰 경계

후속 launcher는 새로운 `bootstrap.py`다. 아직 없다. 표준 라이브러리만 쓰고 **검증 전에 backend를 import하지 않는다**. 계산/도메인 정규화 코드는 향후 backend 아래에 두어 ZIP에 포함한다. launcher가 밖에서 금액/사유/Review를 재작성하면 이 범위를 벗어난다.

개념 실행은 다음과 같다. 실제 명령/script를 이번에 만들거나 실행하지 않는다.

```text
<승인한 절대 python.exe> -I -S -B -X utf8 <배치한 bootstrap.py>
  --bundle <명시 절대 ZIP 경로>
  --manifest <명시 Manifest 원본 경로>
```

bootstrap.py 실행용 사본은 해당 ZIP의 bootstrap.py entry와 **정확히 같은 bytes**여야 한다. 배치 시 준비자가 ZIP을 검증하고 그 사본을 배치하며, 시작 때도 사본 대 entry를 대조한다. 검증기의 코드 역시 배포 검토 대상으로 ZIP에 포함하되, 최초 사본 실행의 신뢰는 승인한 Python/배치 절차에 있다. 자기 파일 대조가 이미 실행된 악성 검증기를 암호학적으로 인증하는 것은 아니다.

bootstrap은 우선 Manifest bytes를 한 번 확보해 strict JSON의 schema_version/engine_artifact_sha256 헤더를 읽을 수 있다. duplicate keys·비표준 수치·잘못된 형식은 거부한다. **이 헤더 읽기는 전체 Manifest loader/검증이 아니다.** backend import 후 같은 원본 bytes로 완전한 Manifest를 구성/검증하고 header H와 도메인 필드가 일치하는지 확인해야 한다. 현재 Manifest JSON loader와 full runtime orchestration은 미구현이다. header-only 성공으로 계산에 진입하지 않는다.

후속 최소 구현의 `--verify-only`는 코드/환경/import 대응만 확인하고 종료할 수 있다. 그 성공은 전체 release·검토·Coverage·Acceptance 성공이 아니다. 검증용 expected SHA를 합성 호출에 직접 지정하는 테스트가 있더라도 실제 운영 H는 명시 선택 Manifest에서 와야 한다. caller의 H 문자열·verified bool만으로 실행 대응을 인정하지 않는다.

## 11. 시작 시 검증·실행 대응 순서

이 순서는 **후속 구현 계약**이며 현재 제공되는 함수가 아니다. 기존 pure API 내부를 수정하지 않는다.

| 단계 | 관찰/검증 | 실패하면 |
|---|---|---|
| 1 새 프로세스·재료 | 명시 Python/옵션, 새 worker, Manifest/ZIP/배치 bootstrap 존재·형식, backend가 미리 import되지 않음 | startup 실패, 도메인 평가0회 |
| 2 기대값/bytes | 같은 Manifest 원본에서 H 확보,13절 공유 제한 handle을 먼저 확보한 같은 ZIP bytes SHA와 비교 | 잠금 실패 또는 current artifact 대응 실패, STALE/UNUSABLE로 낮추지 않음 |
| 3 bundle/profile |6절 entry/중복/경로/.pyc/native/metadata 구조 및 bootstrap 사본 equality, 실제 Python·flags·허용 설치/경로와8절 대조 | 코드 bundle 또는 환경 실패 |
| 4 import 경로 고정 | sys.path를 검증한 ZIP 하나와 허용된 base stdlib 경로로 제한. checkout·site-packages·다른 코드 ZIP·빈 현재 경로 제외 | 임의 package fallback 금지 |
| 5 모듈 준비 | ZIP entry에서 backend 모듈 목록을 만들고 package 포함 **전부 eager import**, 각 모듈 출처를12절로 대조 | 혼재/누락/중복/지원 밖 import 실패 |
| 6 사용 직전 고정 | import 준비 전후 같은 ZIP 원본 SHA 대조, 현재 module 집합/출처·호출 target 출처 확인. 변경/혼재면 worker 폐기 | 코드가 바뀐 채 옛 성공 재사용 금지 |
| 7 도메인 준비 | 같은 Manifest/자료 bytes로 현재 전체 객체 준비·전체 validator, worker H로 current Context 구성 | 기존 데이터 오류/준비 실패, 결과 없음 |
| 8 계산 | 같은 호출의 공식 Coverage1회 → 미래 Acceptance → 같은 Benefit candidate | 각각 기존 순수 API/오류·원본 계약 |

파일 경로를 hash한 뒤 checkout을 실행하는 방식은2~5단계를 통과하지 못한다. archive를 시작 후 다른 파일로 교체/append하거나 reload하는 운영은 금지한다. ZIP 공유 제한·불변 배치·새 프로세스·전부 eager import·시작 전후 대조는 일반적인 실수/배치 교체를 검출·예방하는 절차다. 악의적 호스트에 대한 원자적 attestation을 주장하지 않는다.

모든 backend 모듈 eager import가 향후 import 시 I/O/side effect를 유발한다면 패키징 검토에서 중단해야 한다. 현재 코드의 합성 __main__은 import 시 main을 실행하지 않는다. ZIP에서 제외한 data를 찾는 합성 CLI main을 서비스 target으로 호출하지 않는다.

## 12. import 출처와 실제 계산 코드 대응

문자열 경로의 단순 startswith나 같은 package 이름만으로 성공하지 않는다. 후속 verifier는 다음을 대조한다.

- 모든 `backend`/`backend.*` 모듈의 spec/loader가 같은 ZIP의 zipimport 경로를 가리키고, loader.archive의 정규화된 실제 경로가 선택 ZIP과 같다.
- 모듈별 __file__/spec.origin/get_filename 결과가 그 모듈의 정확한 ZIP entry에 대응한다. package는 예상 __init__.py와 package 검색 위치가 같아야 한다.
- archive entry에서 얻은 module 목록과 실제 로드한 backend 모듈 집합이 대응한다. 로드 실패/다른 설치 위치/다른 ZIP·미리 로드된 backend가 있으면 실패다.
- 계산에 호출하는 기존 public Coverage 함수와 향후 내부 Acceptance/adapter의 __module__·code.co_filename이 그 모듈 원본에 속하는지 확인한다. 경로 문자열 대조만으로 함수 monkeypatch를 보안상 탐지한다고 주장하지 않는다.
- 실행 중 sys.path/sys.meta_path/sys.modules 변경·importlib.reload·새 plugin·checkout 코드 exec를 허용하지 않는다. 외부에서 계산 함수를 callback으로 받아 실행하지 않는다.

전부 eager import한 뒤 worker는 그 모듈/함수 참조를 유지한다. 따라서 검토 ZIP A를 검사하고 B를 import하거나, checkout의 모델과 설치 package의 evaluator를 섞는 정상 경로가 없다. 이미 다른 backend를 로드한 REPL/notebook/web dev server를 정리해 재사용하지 않고 **새 worker로 시작**한다.

stdlib/builtin/native extension은8절의 허용 Python 설치에 의존한다. backend는 전부 ZIP 출처를 확인하지만, interpreter/stdlib의 bytes 전체를 이 ZIP이 고정하는 것은 아니다. 같은 이름의 호스트 모듈이 허용 설치 자체에 잘못 들어 있는 문제는 신뢰 환경 재확인 대상이다.

## 13. 검증 수명·변경 사이의 조건

| 단위 | 고정하는 것 | 재검증/무효화 |
|---|---|---|
| 배포 | 완성 ZIP bytes·Manifest 선택·bootstrap 사본·승인 Python 설치/profile | overwrite 없이 새 ZIP/새 release를 선택. 코드/설치/사본 바뀌면 기존 worker 종료 |
| worker 프로세스 | H·ZIP 경로·쓰기/삭제를 허용하지 않는 읽기 handle·허용 Python/flags/import 경로·eager import 원본 함수 | 한 worker는 코드 artifact 하나만 사용. handle 해제 전 평가 종료, hot reload/editable checkout/다른 version 재사용 금지 |
| 한 계산 호출 | 전체 Manifest/Envelope/Registry·현재 Coverage/ReviewContext/Benefit/AcceptanceContext/ref·명시 날짜 | 자료/날짜/Context 변경 시 M2.51 새 평가. 여러 요청의 Result 재사용 금지 |
| before/after 묶음 | 같은 코드 H/환경·같은 자료/사용 기준, 다른 사용자 시나리오 | 비교 중 latest code/data를 재조회하지 않음 |

Windows bootstrap은 **최초 해시 전에** 선택한 정상 로컬 ZIP을 `CreateFileW`의 GENERIC_READ·OPEN_EXISTING·FILE_SHARE_READ만으로 열고, worker 종료까지 handle을 유지한다. FILE_SHARE_WRITE/FILE_SHARE_DELETE는 허용하지 않는다. 기존 writer/delete handle과 충돌하면 시작 실패이며, 이후 일반 쓰기·삭제/rename 요청은 차단된다. 같은 파일의 read는 허용해 zipimport가 읽을 수 있어야 한다. ctypes 등 표준 라이브러리에서 호출하는 작은 외부 I/O 책임이며 pure Coverage 코드에 넣지 않는다. [Windows 파일 공유 규칙](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

검사·hash·zipimport는 이 handle이 고정한 파일과 같은 정규화된 절대 경로를 사용한다. 실행용 배치 경로와 그 부모는 symlink/junction/rename 없이 불변으로 유지한다. handle을 일찍 닫아 검증 성공만 재사용하거나 read-only 속성만으로 이 조건을 대신하지 않는다. 실패/정상 종료 모두 handle을 닫고, handle이 없는 상태에서는 평가하지 않는다. 최초 bootstrap 배치와 승인 Python 설치 자체는20절 신뢰 기반이다.

시작 때 ZIP 전체를 해시하고 modules를 준비하며 공유 제한을 유지하므로 매 요청마다 checkout의61개 파일을 다시 읽는 계약은 아니다. 코드 검증 수명은 **그 고정 worker의 수명과 handle 유지 기간**이다. 각 호출은 고정 module/경로/원본 참조를 사용하며 request마다 전체 데이터 선택·선택 대상 검사는 별도로 수행한다.

운영자가 파일/설치/sys.path를 변경했다면 결과와 관계없이 worker를 폐기하고 새 프로세스에서 재검증한다. 동일 이름 ZIP 덮어쓰기·환경 in-place upgrade·승인하지 않은 후속 lazy backend import는 지원하지 않는다. 호스트가 이 불변 조건을 몰래 깨뜨리는 행위를 항상 탐지한다고 주장하지 않는다. 일반 개발용 `python -m backend.policy_engine`/pytest·editable/hot reload는 **검증된 release 실행이 아니다**.

## 14. 준비 자료 없음·형식 오류·불일치·성공

시작 전에는 backend 예외를 import할 수 없으므로, bootstrap은 **비정상 종료 코드2 + 고정 진단 prefix/field**로 준비 실패를 표시하는 방향을 정한다. 새 domain 상태/Result/Reason/예외 hierarchy를 만들지 않는다. 아래 이름은 후속 bootstrap 진단 계약이고 현재 구현된 오류 API가 아니다.

| 상태 | 진단/처리 | 의미 |
|---|---|---|
| 파일/필수 증거 미제공 | ARTIFACT_NOT_AVAILABLE | 검사 불가. 임의 hash/정상 UNUSABLE 없음 |
| expected H·명시 인자/헤더 형식 오류 | INVALID_ARTIFACT_INPUT | 잘못된 자료. 자동 parsing/strip/default로 복구 안 함 |
| 공유 제한 확보 실패·이미 열린 writer/delete handle | ARTIFACT_LOCK_UNAVAILABLE | 고정 수명 보장 불가, 평가 전 차단 |
| 선언 H와 관찰 ZIP bytes 다름 | ARTIFACT_HASH_MISMATCH | 현재 배포/실행 대응 실패 |
| ZIP entry/profile/bootstrap 사본 구조/내용 문제 | INVALID_CODE_BUNDLE | 잘못된 패키징/배치 |
| Python/옵션/설치 경로/profile 다름 | ARTIFACT_ENVIRONMENT_MISMATCH | 선언 환경의 실행 아님 |
| backend 선로딩/다른 loader/archive·version 혼재 | ARTIFACT_IMPORT_MISMATCH | 검사 artifact와 실행 코드 대응 실패 |
| 시작 검사 후 변경 관찰 | ARTIFACT_CHANGED_DURING_STARTUP | worker 폐기. 이전 성공 재사용 불가 |
| 정한 범위 확인 성공 | verify-only는 종료0, 전체 경로는 다음 준비 단계로 진행 | runtime binding만 통과. source/review/전체 release/USABLE을 인증하지 않음 |

단계11절 순서, 같은 단계에서는 명시 입력/ZIP entry 오름차순/module 이름 순서를 사용해 첫 실패를 결정한다. 정책 원문/사용자 값·raw 경로/지문/이력 payload를 진단에 노출하지 않는다. OS/parse/import 예외도 startup에서 전체 실패하며 부분 계산을 반환하지 않는다.

backend import 후 기존 Manifest/Source/Policy/Coverage/Data Error가 발생하면 기존 예외 의미를 유지한다. 준비 실패를 Acceptance의12Reason, Coverage STALE/SLICE 또는 정상0원으로 강등하지 않는다. 코드 artifact만 검증되고 검토 artifact/실제 환경의 보장 범위가 제한됐으면 그 한계를 외부 감사에 남긴다.

## 15. 세 종류의 mismatch를 분리

| 경우 | 비교 원천 | 기대 처리 |
|---|---|---|
| A current Manifest 기대 H1, 실제 준비/실행 ZIP H2 | Manifest.engine_artifact_sha256 대 관찰 ZIP·worker | **현재 대응 검증 실패**. Coverage/Acceptance 실행 전 차단. 과거 Review stale로 설명하지 않음 |
| B current worker H2는 정상, 과거 Implementation Review는 H1 | 확인한 H2로 만든 current Context 대 선택 과거 Review | 기존 matcher의 IMPLEMENTATION_CHANGED → STALE, 최종 Coverage는 다른 gate와 함께 SLICE. 현재 artifact 준비 실패 아님 |
| C current worker H2는 정상, 과거 Acceptance는 H1 | 현재 Result.implementation_fingerprint 대 selected record.coverage_implementation_fingerprint | 기존 Acceptance의 COVERAGE_SNAPSHOT_CHANGED, 다른 guards/사유와 함께 정상 사용 불가 |

B에서 Inventory review는 implementation 축이 없으므로 코드 hash 차이만으로 Inventory review를 새로 STALE로 만들지 않는다. Implementation slot들이 STALE일 수 있으며 그 차이를 old records를 수정해 없애지 않는다. C는 새로운 적절한 Implementation Reviews로 current FULL이 되더라도 과거 Acceptance와의 변경을 따로 추적한다.

같은 rule_version의 다른 Tree·같은 i의 다른 Inventory·같은 dataset의 다른 Registry 등 기존 독립 conflict는 정상 구현 변경/만료/철회 때문에 면제되지 않는다. 현재 release를 새 artifact에 맞추려면 새 불변 Manifest/검토 확인본이 필요하며 실제001/002를 수정하지 않는다.

## 16. 전체 release와8개 내부 입력 연결

bootstrap의 코드 SHA 검증은 전체 dataset validation이 아니다. **검증된 worker 내부의 C orchestration**이 명시 전체 envelopes tuple과 registry를 받거나 같은 자료 bytes에서 준비하여 `validate_dataset_manifest(manifest, all_envelopes, registry)`를 한 번 호출한다. 현재 함수가 보장하는 전체 집합·버전·domain fp·ref·engine 호환 검사와 원래 오류 순서를 그대로 쓴다.

선택 Envelope는 이 tuple에서 얻은 **원본**이고 그 envelope.policy로 Coverage를 생성한다. Benefit은 별도 정의 원본이므로 현재 dataset/Registry/target·claim 근거를 같은 release와 대조한 뒤 그 원본을 유지한다. Manifest에는 Benefit 목록/지문 reference가 없으므로 Manifest 검증만으로 Benefit이 등록 구성원이라고 증명하지 않는다. M2.51의 Benefit provenance와 검토 artifact 결합 의무가 남는다.

전체 준비 뒤 B에 넘기는 입력은 여전히 **CoverageResult, Envelope, Benefit, AcceptanceContext, 명시 ref, Manifest, Registry, data_use_date**의8개다. B가 전체 envelopes를 보거나 실제 실행 ZIP을 다시 검사했다고 주장하지 않는다. 외부 precomputed Result/serialized status는 입력으로 받지 않는다.

worker 밖에서 checkout 모델로 만든 Python 객체를 pickle/callback으로 넘겨 혼합 실행하지 않는다. 장래 프로세스 경계가 필요하면 원본/명시 데이터 bytes만 전달하고 worker의 검증된 코드로 객체를 만든다. 현재 부족한 Manifest/Review/Inventory/Benefit loader·외부 검토 대응을 이 문서로 구현 완료했다고 보지 않는다. 그 준비가 없으면 verify-only 이상으로 진행하지 않는다.

## 17. Coverage·Acceptance 호출 연결과 I/O 위치

```text
명시 ZIP/Manifest 원본 + 승인 Python
 → bootstrap: ZIP bytes/profile/새 실행/모든 backend import 대응
 → 고정 worker H와 자료 bytes
 → C: 전체 release 집합 검증·검토/근거 준비
 → current CoverageReviewContext 구성 시 implementation_fingerprint=관찰·대응 확인한 H
 → evaluate_eligibility_coverage(current_coverage, original_envelope.policy, current_context) 1회
 → 기존 Result 원본 + M2.51 나머지7입력으로 미래 Acceptance evaluator
 → 같은 Benefit 원본으로 candidate
 → 별도 개인/월/유형·중복 Bridge → 명시 int → Cashflow
```

current Context의 H는 임의 caller 문자열이 아니라 이 worker의 확인한 실행 artifact에서 공급한다. 이미 제공된 current Context가 H와 다르면 준비 불일치로 거부하고 조용히 필드만 바꾸지 않는다. 새 current Context를 원본 기록 tuple로 구성하는 것은 가능하지만 역사 ImplementationBindingReview의 H는 그대로 보존한다.

CoverageReviewContext=None은 기존 정상 SLICE/all-None baseline 경로다. H를 안다는 이유로 가짜 Context/Review를 만들어 채우지 않는다. 코드/환경 검증 자체는 별도로 수행할 수 있지만 공식 Result의 None baseline 의미를 바꾸지 않는다.

파일/환경/프로세스/import 관찰은 **bootstrap/A/C 외부 준비**에만 있다. 순수 Coverage evaluator·matcher·fingerprint helper·Acceptance 내부 함수에 I/O·현재시각 조회를 추가하지 않는다. 기존 public Coverage API·factory·동결 코드/오류를 수정할 이유가 없다.

## 18. 검토 artifact와의 끝 경계

implementation artifact는 **실행 코드 ZIP**이고, Coverage Review의 review_artifact_ref와 Acceptance.review_artifact_ref는 **사람의 검토 evidence**다. ZIP SHA 일치로 accepted_terms·5claim 근거 대응·별도 검토자·정확한 역사 Snapshot을 검토했다고 하지 않는다.

M2.51 11절의 구조화된 검토 artifact 표현/loader·본문 대조 공백은 그대로다. 이 문서에서 새 BenefitDefinitionReview/Context/Result 모델을 추가하지 않는다. 코드 검증만 성공했지만 검토 원본이 미확보/다른 대상을 가리키는 경우 실제 Acceptance 경로는 계속 차단한다.

## 19. 변경 영향표

아래 E는 엔진 bundle SHA, I는 Coverage implementation SHA다. 공유하므로 E=I=H이지만 역할은 다르다. “재검토”는 실제 영향 확인 후 새 Review/Acceptance 발급 여부를 결정한다는 뜻이며 자동 승인/자동 revision 생성이 아니다. 모든 행에서 기존 실제 release/역사 기록은 **보존**한다.

| 변경 | E 영향 | I 영향 | current release 재검증 | Coverage Review 재검토 | Acceptance 재검토 | 기존 실제 release |
|---|---|---|---|---|---|---|
| Rule 평가 로직 | 새 H | 새 H | 새 bundle/Manifest·runtime·데이터 대응 | Implementation 필요, 기존 H는 STALE. 데이터 같은-version guards 별도 | 기존 구현 binding 변경, 재수용 검토 | 보존 |
| 입력모델 검증 | 새 H | 새 H | 동일 | 입력 의미/경계·Implementation 필요 | 새 H 대응 검토 | 보존 |
| serialization/fingerprint 코드 | 새 H | 새 H | 동일, payload 변경이면 기존 schema/GV/BV change-control 우선 | Implementation 및 payload/원본 대응 영향 검토 | 정의/출처/구현 guards 재검토 | 보존 |
| Coverage matching | 새 H | 새 H | 동일 | Implementation 필요. frozen 변경은 별도 승인 없이 금지 | 현재 Coverage/구현 binding 검토 | 보존 |
| Acceptance evaluator만 | 새 H | 새 H, 보수적 superset | 새 실행물·기존 데이터 전체 대응 | 구현 SHA 차이로 기존 Implementation STALE. 좁은 영향이어도 자동 면제 없음 | 변경 기능·새 H 재검토 | 보존 |
| Cashflow/주석/CLI 등 backend .py | 새 H | 새 H, 같은 보수성 | 새 artifact 식별 | 코드 내용/포장 영향 확인 뒤 새 구현 검토 기록 필요 | 구현 binding 차이 추적 | 보존 |
| 정책 데이터만 | 없음 | 없음 | 새 policy/Manifest domain/bytes·scope/reference 전체 | i/r/Tree 변경 축대로 재검토, 코드 같다고 MATCHED 보장 안 함 | Coverage snapshot 변경 축 검토 | 보존 |
| SourceRegistry만 | 없음 | 없음 | 새 Registry/source/Manifest·freshness/bindings | dataset/Registry guards와 source 의미 검토 | provenance 및 해당 정의 근거 변경 검토 | 보존 |
| 검토 artifact만 | 없음 | 없음 | 검토 파일 SHA/ref·원본 대응·새 선언 release 확인 | 정정은 새 ref. 검토 metadata 변경과 target 지문 변화 구분 | 해당 결정/본문 대조, 기존 revision overwrite 금지 | 보존 |
| third-party 의존 package 추가/변경 | 현재 방식은 미지원. profile/패키징 개정 시 새 H | 새 H 예정 | 외부/간접 의존 고정 범위 개정 후 환경 검증 | 실행 영향 검토 필요 | 준비 미완료를12Reason에 넣지 않음 | 보존 |
| Python version/플랫폼 변경 | runtime.json 변경→새 H | 새 H | 새 환경·runtime profile·회귀/실행 대응 | Implementation 재검토 | 구현 binding 변경 검토 | 보존 |
| 같은 profile의 Python 재설치/경로 변경 | ZIP H는 같을 수 있음 | 같을 수 있음 | worker 폐기·설치 신뢰/경로/회귀 재확인 | hash만으로 자동 STALE 아님. 외부 환경 적합성 다시 검토 | 이전 환경 승인 자동 승계 안 함. 새 hash/Reason 발명 없음 | 보존 |
| UI만 | 없음, backend 변경 없을 때 | 없음 | UI/요청 API 별도 검증. backend 데이터 선택 경계 유지 | 코드 SHA로 자동 재검토 안 함 | 정의·선택/데이터 안 바뀌면 자동 무효화 없음 | 보존 |
| 동일 내용 재패키징 | bytes 동일이면 동일 H, 다르면 새 H | 동일 규칙 | 실제 bytes 비교·새 Manifest 연결 | 새 H면 Implementation STALE/재검토, 논리 동치 면제 없음 | 새 H면 기존 구현 binding 변경 | 보존 |

UI/로그/설정이라고 이름 붙인 파일이 실제 판정 코드를 공급하거나 backend 환경/입력을 바꾼다면 “영향 없음” 행을 적용하지 않는다. 검사 범위 밖이라 안전하다고 하지 않고 해당 실행/입력 책임에서 검증한다.

## 20. 신뢰·위협 범위와 Assumptions

최소 목표는 실수로 다른 코드/오래된 ZIP·잘못된 환경·import 경로를 선택하거나, artifact/Manifest/Review를 잘못 연결하고 검증 후 다른 코드를 재사용하는 것을 검출·예방하는 것이다. 모델/토큰/서명 서버로 실제 실행을 인증하는 프로젝트로 확대하지 않는다.

**Assumption A1:** 팀이 지정한 정상 Python/stdlib 설치·호스트·bootstrap 배치 절차가 정직하다. ZIP 내 bootstrap 사본 대조와 SHA는 이 최초 신뢰 기반을 독립 인증하지 않는다.

**Assumption A2:** worker가 사는 동안 ZIP·Python 설치·import 경로/함수 원본은 불변이고 운영자는 update 시 worker를 교체한다. 악의적 동시 파일 교체/monkeypatch·검증기 우회·원격 실행 진실성은 보장하지 않는다.

**Assumption A3:** 현재 runtime dependency는 stdlib뿐이며 코드 선택 설정은 명시 입력이다. 이후 플러그인·외부 package·동적 리소스가 생기면 실패/규약 개정 대상이며 자동 포함했다고 하지 않는다.

SHA256은 변경 감지/동일 bytes 대조다. 서명·발급 권한·실제 검토의 충실성/권한·역사 기록 완전성·소득/개인 지급 사실을 증명하지 않는다. Python private factory/token도 API 오용 방지 장치다. 제외된 Python/stdlib/OS/native bytes·검토자/자료 준비 진실성은 별도 신뢰 범위다.

## 21. 재빌드·재현성 표현

빌더는 entry 정렬·slash 상대 경로, 고정 ZIP timestamp `(1980,1,1,0,0,0)`, ZIP_STORED, 빈 comment/extra, 고정 creator/일반 파일 권한 metadata를 사용하도록 정한다. 로컬 절대 경로/mtime/소유자/발행시각을 ZIP에 넣지 않는다. 원본 .py의 line ending/BOM/내용은 그대로이며 자동 의미 정규화하지 않는다. ZIP API의 metadata 설정 수단은 표준 라이브러리에 있다. [Python zipfile 문서](https://docs.python.org/3.12/library/zipfile.html).

그러나 **현재 builder도 재현 빌드 검증도 없다.** 이 문서는 다른 OS/도구/Python으로 다시 묶어도 항상 같은 bytes/hash라고 보장하지 않는다. 후속 고정 builder에서 같은 entry bytes/profile의 반복 결과가 같은지 합성 검증하고, 도구가 달라지면 실제 ZIP bytes를 비교한다.

재포장 bytes가 다르면 다른 H다. 단순 주석/metadata만 바뀌어도 그렇다. 같은 source/tree/Benefit domain fp는 원본 ZIP 동일성의 대체가 아니다. 과거 재현은 보존한 **그 ZIP**과 당시 환경·자료·검토 원본을 사용하며 현재 checkout에서 다시 만들면 같다고 가정하지 않는다.

## 22. 최소 수동 검증 시나리오와 후속 테스트

아래 AR 사례는 **문서상 기대**이며 신규 실행 테스트0개다. H1/H2는 실제 값을 발급하지 않는 기호다. 실제 artifact 생성/ZIP import 대응은 이번에 실행하지 않았다.

| ID | 입력·전제 | 확인 가능한 사실 | 기대 처리 | 담당 | 후속 실행 테스트 | 보장하지 않는 것 |
|---|---|---|---|---|---|---|
| AR01 | 합성 ZIP bytes와 기대 H가 같고 profile/import 대응 정상 | 정한 bytes/실행 위치 일치 | verify-only 성공, 실제 계산 승인 아님 | bootstrap/worker | 합성 subprocess 가능 | 실제 원문/검토 truth |
| AR02 | entry bytes 일부 수정, 기대 H 유지 | 관찰 SHA 다름 | HASH_MISMATCH·평가0회 | bootstrap | 가능 | 악의적 충돌 방지 인증 |
| AR03 | 같은 version 이름·다른 ZIP | label이 같아도 bytes 다름 | 동일 실패 | bootstrap | 가능 | version 이름 신뢰 |
| AR04 | 같은 파일명·같은 size·다른 내용 | 실제 SHA 차이 | 동일 실패, mtime/size로 통과 금지 | bootstrap | 가능 | metadata 기반 동일성 |
| AR05 | A 검사 뒤 B의 import 경로 | loader/archive/entry 불일치 | IMPORT_MISMATCH·worker 폐기 | worker | 합성 경로 주입 가능 | 악성 loader 변조 인증 |
| AR06 | checkout과 설치 package/여러 version 혼재 또는 backend 선로딩 | 허용 경로 밖/기존 module 발견 | 새 격리 worker 요구, fallback 금지 | bootstrap/worker | subprocess·선로딩 가능 | 이미 실행한 임의 세션 복구 |
| AR07 | 공통 helper만 변경 | 전체 backend 포함으로 새 H | current 기대값 그대로면 A실패, 새 H가 유효하면 B/C정상 변경 | 빌더/worker/Coverage/Acceptance | 합성 가능 | 영향 파일 누락 허용 |
| AR08 | 검사 후 ZIP 쓰기/교체·target 변경 | 유지 handle이 일반 쓰기/delete/rename 차단, 출처 변경은 실패 | 변경 차단 또는 CHANGED_DURING_STARTUP, handle 상실 시 평가 금지 | bootstrap/운영 | 합성 subprocess의 쓰기/rename 실패·종료 후 해제 확인 | 악성 호스트/부모 경로 변조의 원자적 탐지 |
| AR09 | 다른 Python version/설치 경로·옵션·site 경로 | 선언 환경/실제 flags·허용 위치 차이 | ENVIRONMENT_MISMATCH, 재검증 | bootstrap | flags/설정·가능한 환경으로 시험 | 같은 version의 interpreter bytes 인증 |
| AR10 | 두 역할에 실제 같은 ZIP 사용 | E=I=관찰 H | 이 규약의 정상 공유 경로 | 준비/worker | 가능 | 코드 검토 진실성 |
| AR11 | 두 ZIP과 파일/의존성 대응이 정확하다는 별도 자료 | 분리 설계의 필요 사실은 비교 가능 | **현재 공유 규약에서는 미지원**, 자동 허용 안 함 | 준비 | 미지원 거부 시험; 분리 성공 시험은 별도 규약 후 | version 이름만의 대응 |
| AR12 | current H2/Manifest/runtime 정상, 선택 과거 Implementation Review H1 | current 검증 성공+과거 차이 | 기존 IMPLEMENTATION_CHANGED/STALE, 정상 SLICE | 기존 Coverage | 기존 순수 matcher 회귀+후속 연결 | CURRENT mismatch를 stale로 낮추기 |
| AR13 | current H2 정상·필요 새 Coverage reviews로 FULL, 과거 Acceptance H1 | 구현 binding 변경 | COVERAGE_SNAPSHOT_CHANGED, 독립 guards 유지 | 미래 Acceptance | evaluator 구현 후 합성 | 실제 승인/재발급 |
| AR14 | 선택 Envelope만 정상, Manifest 전체 정책 누락 | 전체 집합 검사 불충족 | 기존 POLICY_REFERENCE_SET_MISMATCH, B진입0회 | C/기존 validator | 기존 회귀+후속 연결 | 선택 대상만으로 전체 통과 |
| AR15 | ZIP/필수 증거 없음, ref나 caller verified=True만 제공 | 검증 불가 | NOT_AVAILABLE, H조작/12Reason 변환 없음 | 준비/bootstrap | 가능 | 누락 증거를 성공으로 간주 |
| AR16 | 합성 fixture/literal SHA로 모델 테스트만 성공 | 로컬 표현/계산 계약만 확인 | 실제 runtime/import 증거와 분리 보고 | tests/검토 | 기존 회귀·후속 구분 | 실제 배포/검토 인증 |
| AR17 | current H·import 정상, Acceptance review artifact 내용 대응 미완료 | 실행 코드만 대응 | 실제 Acceptance 진입 계속 차단 | 준비/C | 경계/미호출 tests 가능 | claim별 검토 완료 |
| AR18 | ZIP에 중복/case충돌/탈출/.pyc/native entry·미신고 dependency | 허용 bundle 아님 | INVALID_CODE_BUNDLE, backend import0회 | bootstrap | 합성 ZIP으로 가능 | 임의 packaging 지원 |
| AR19 | profile 동일한 Python 재설치 또는 동일 source 재포장 | 같은 환경 bytes는 인증 못함 / ZIP bytes 비교 가능 | 설치 재적합성 확인 / 새 bytes면 새 H로 추적 | 운영/준비 | 절차 확인+합성 재포장 | 무조건 같은 hash/동일 interpreter |

후속 tests는 실제 helper/함수 출처·startup 오류 우선순위·실패 시 Coverage/Acceptance/candidate 호출0회·새 프로세스·경로 혼재·전부 eager import·고정 bootstrap 사본·같은 input bytes 유지·환경 제한을 검증해야 한다. 기존 순수 함수에 I/O를 넣어 테스트를 통과시키지 않는다. 실제 source/review 진실성은 합성 fixture가 증명하지 않는다.

## 23. 기존 계약 영향과 남은 의존사항

이번 선택은 기존 artifact bytes 의미를 구체화한다. Inventory/Tree/subtree/Benefit payload·GV01~GV15/BV01~BV16, Coverage API/순서/Review STALE·Result8필드, Acceptance21필드/Context4필드/Result9필드/12Reason을 바꿀 필요가 없다. 새 MVP bundle에서만 두 역할이 같은 bytes라는 **외부 생성/실행 규칙**을 적용한다. 기존 합성 literals/과거 기록에 equality를 소급 강제하지 않는다.

| 대상 | 현재 결론 |
|---|---|
| 패키징·두 역할·hash 대상 | 이 문서에서 확정. 추가 비교 문서 없이 공유 ZIP 방식 구현 가능 |
| runtime binding | 신뢰된 Python/배치·새 isolated worker·profile/entry/import 확인·불변 수명으로 확정. 악성 호스트 인증은 제외 |
| builder/bootstrap·검증 코드 | 아직 없음.24절 범위부터 구현 가능 |
| 전체 Manifest JSON 로딩·실제 release 발행/실행 | 미구현. verify-only를 full release로 승격하지 않음 |
| 검토 artifact 구조화/내용 대응 | M2.51 별도 의존사항 유지. 이번에 새 검토 모델 설계/구현 없음 |
| source 사용 gate·Acceptance evaluator·같은 호출 adapter·Bridge | 미구현. artifact 검증 구현 완료와 구분 |
| 실제 안산 full/거주기간 | DRAFT/CONDITION_SLICE·정책 반영0원 원칙, ResidenceHistory OFFICIAL_INQUIRY_REQUIRED 유지 |

실제 Python 배포물 bytes·실제 package hash·새 Manifest·검토자/승인 기록·혜택 금액은 확보/발행하지 않았다. 호스트 bytes 인증이나 third-party runtime 지원을 원한다면 추가 범위가 필요하지만 현재 stdlib MVP의 artifact 실행 대응 구현을 막는 미정 기본값으로 남기지는 않는다.

## 24. 최종 판단과 다음 최소 작업 한 개

**READY_TO_IMPLEMENT_ARTIFACT_EXECUTION_BINDING_VALIDATION**

현재 pure Python/stdlib 구성에서 **단일 source ZIP을 두 역할에 공유하고 새 격리 worker에서 bytes·환경·import 출처를 확인**하는 MVP 계약을 확정했다. 동결 의미를 변경하거나 wheel/Docker/서명/범용 배포 플랫폼을 선행할 필요가 없다. 이 판단은 실제 evaluator/서비스/실제 안산 release 준비 완료가 아니다.

다음 최소 작업 한 개는 **합성 ZIP만 대상으로 하는 bootstrap의 `verify-only` 실행 대응 검증을 구현하고 subprocess 테스트를 추가**하는 것이다.

| 구현 범위 | 완료조건 |
|---|---|
| 최소 합성 package 준비 | tests 내부 합성 backend/고정 metadata/launcher bytes 사용. 실제 backend 배포물·실제 SHA·Manifest 발행 없음. 범용 builder CLI는 제외 |
| 검증 | 실제 ZIP bytes 대 명시 합성 기대 SHA, entry/profile·bootstrap 사본·새 Python flags/경로·모든 합성 backend module import 대응·Windows 읽기 handle의 쓰기/삭제 공유 제한 확인 |
| 성공/실패 | verify-only 종료0/고정 startup 실패2, 실패 뒤 도메인 계산0회. 새 Context/Result/Reason 없음 |
| 보존/범위 | 기존6962개·GV/BV·동결 source/명세·실제6개 release 보존. Coverage/Acceptance evaluator/loader·full release 검증·Bridge 구현은 포함하지 않음 |

이 작은 구현은 실제 artifact와 import 경로를 확인하는 기능이어야 한다. H 문자열 비교 helper만 만들고 실행 대응 완료라고 보고하지 않는다. 합성 verifier의 성공으로 실제 환경/검토/정책을 승인하지 않는다. 이후 실제 builder/full release/검토 결합은 각각 필요한 범위로 진행한다.

## 25. 검증 기록

사전 전체 pytest: **6962 passed in 16.29s**. 문서 작성 후 전체 pytest: **6962 passed in 16.87s**. 신규 실행 테스트/fixture/기존 기대값 변경은 **0개**다. 이 회귀는 기존 구현의 보존 확인이며 아직 없는 builder/bootstrap/파일 공유 제한/ZIP import 대응 검증을 실행한 결과가 아니다.

backend/tests/data/docs의 사전165개 파일은 **SHA256 모두 동일**하며 이 문서1개만 추가해166개다. 기존 파일 수정/삭제0개다. 루트 README.md·pyproject.toml·requirements-dev.txt·.gitignore4개도 SHA256이 같다. Coverage frozen source/문서·GV01~GV15·Benefit/BV01~BV16·Acceptance/Context/Result·모든 기존 tests/fixture/기대값·Cashflow·ResidenceHistory를 보존했다.

실제 release6개 파일은 **SHA256·경로·크기·수정시각 모두 동일**하다. 실제 코드 배포 artifact·엔진/implementation SHA·새 Manifest·실제 정책 지문·승인/철회/평가 결과·혜택 금액을 생성하지 않았다. source 보존용 SHA256 대조는 새 실행 artifact 지문 발행과 구분한다.

문서25개 절의 연속 순서·표 열 수·코드 블록·한국어 표기·AR01~AR19의 유일/연속 수동 사례 ID를 확인했다. Python의 ZIP/격리 옵션 및 Windows 공유 제한의 의미는 공식 문서로 확인했고, 실제 로컬 Python 정보와 격리 옵션의 sys.path/flags만 읽어 확인했다. 새로운 artifact나 잠금/배포 실행 테스트를 수행했다고 보고하지 않는다.

## 26. M2.53 — IMPLEMENTED: 합성 ZIP bootstrap verify-only

### 구현 위치와 trusted entrypoint

외부 준비 계층의 `tools/artifacts/bootstrap.py` 한 파일을 추가했다. backend 도메인 package에 넣지 않았고 domain/helper/예외를 import하지 않는다. 처음 실행되는 것은 명시한 Python과 **외부의 trusted script**다. ZIP 안 bootstrap.py는 이 script 원본 bytes와 대조할 뿐 실행하지 않는다. ZIP backend 코드는 Windows 보호 handle·외부 기대 SHA·구조/profile·실제 환경 검증 이후에만 import한다.

M2.52 10절의 --manifest는 장래 전체 release 연결의 개념 예시다. 이번24절의 승인 범위인 **합성 기대 SHA 직접 지정 경로**만 구현했다. --manifest/header reader·실제 Manifest 생성/loader·전체 release 검증은 구현하지 않고 해당 CLI 옵션도 거부한다. 같은 역할의 다른 artifact를 받는 옵션·skip/verified/allow_stale 옵션도 없다.

실제 CLI는 다음과 같으며 nullable/default 없는 다섯 필수 옵션을 사용한다. 이는8절의 외부 기대 interpreter/base를 구체화한 것이며 runtime.json의6필드를 확장하지 않는다.

```text
<명시 python.exe> -I -S -B -X utf8 <workspace>/tools/artifacts/bootstrap.py
  --verify-only
  --bundle <절대 합성 ZIP 경로>
  --expected-sha256 <외부에서 미리 확보한 합성 ZIP SHA256>
  --python-executable <기대 Python 실행파일의 절대 경로>
  --python-base <기대 base Python 설치의 절대 경로>
```

경로/expected SHA를 관찰값으로 자동 갱신하지 않는다. expected SHA는 최초 완성한 합성 ZIP bytes에서 fixture가 독립적으로 확보하며, mismatch 사례는 bytes 변형 뒤에도 **그 최초 기대값을 유지**한다. 구조 오류 fixture는 그 잘못된 구조 자체의 bytes와 기대 SHA가 일치하도록 별도로 준비해 hash 실패와 구분한다. ZIP 안에는 기대 SHA가 없으며 관찰 SHA를 성공 조건에 자동 대입하지 않는다.

### 실제 실행 순서와 I/O 경계

| 단계 | 실제 검사 | 실패/수명 |
|---|---|---|
| 초기 | Windows·명시 flags/int 한도·backend 선로딩 부재·기대 SHA 문법·명시 절대 경로 | 플랫폼 미지원은 ENVIRONMENT_MISMATCH, backend가 있으면 IMPORT_MISMATCH. 지우거나 reload하지 않음 |
| 보호/bytes | 정상 로컬 고정 drive, reparse 경로 거부, CreateFileW(GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING) → 같은 handle로 ZIP bytes SHA 대조 | 보호 실패는 LOCK_UNAVAILABLE. hash mismatch 때 ZIP/backend 실행0회 |
| 구조/profile | 필수 bootstrap.py/runtime.json/backend/__init__.py·정렬/유일/case충돌/경로·일반 .py·source package inventory·ZIP_STORED·고정 timestamp·CRC/read·정확한 script 사본 | source 보정/추출/fallback 없음. metadata6필드 strict UTF-8/중복·unknown/잘못된 타입·의존 package 거부 |
| 환경 | profile의 명시 Python implementation/version/platform/machine 대 실제 값, 별도 기대 executable/base 및 허용 stdlib 경로 | 관찰값을 기대값으로 바꾸지 않음. profile은 package bytes이고 설치물 bytes 인증은 아님 |
| import | 선택 ZIP 하나+명시 base의 pythonXY.zip/DLLs/Lib/base 경로. 예상 backend 모듈 전부 eager import | pytest 프로세스의 기존 backend import를 사용하지 않음. 각 모듈/패키지·간접 import 출처 대조 |
| 완료 전 | 전체 inventory equality, module identity·sys.path/meta_path/hooks 무변경, 같은 보호 파일 bytes 재대조 및 file identity, 최종 flags/출처 | 일부 모듈 성공만으로 완료하지 않음. 같은 handle을 최종 성공 출력까지 유지 |
| 종료 | 모든 정상/실패 경로에서 file stream/보호 handle 정리 | 강제 종료도 Windows가 handle을 회수. 종료 후까지 검증 수명이 유지되지 않음 |

현재 Windows stdlib 경로는 **외부에서 지정한 base 설치와 선언 version**에서 얻는다. 실제 sys.path를 그대로 허용 목록으로 받아들이지 않는다. venv의 sys.prefix 대신 명시 executable과 sys.base_prefix를 대조한다. required flags는 isolated/ignore_environment/no_user_site/no_site/dont_write_bytecode/safe_path/utf8_mode/hash_randomization 활성, optimize=0, int_max_str_digits=4300이다. -I/-S/-B의 역할을 서로 대체하지 않는다.

모든 backend namespace의 exact ModuleType/spec.name/zipimporter·archive/prefix·__file__/origin/get_filename·package __path__/검색 위치·함수 co_filename 및 전체 module inventory를 대조한다. 문자열 startswith 하나로 archive를 인정하지 않는다. backendish는 backend namespace가 아니다. 모듈 출처 metadata나 함수의 Python 속성이 악성 코드로 위조되지 않는다는 신뢰 한계는 유지한다. 모든 함수를 호출하거나 실제 업무 entrypoint를 평가하지 않는다.

### 출력·오류·최소 구체화

기존1~25절은 종료 코드와 prefix를 정했으나 stdout의 세부 key 이름은 정하지 않았다. 이번 구현은 새 Result 모델 대신 **최종 stdout JSON 한 줄의5key**로 범위를 명시한다.

```json
{"checked_module_count":5,"checked_modules":["backend","backend.alpha","backend.nested","backend.nested.beta","backend.z_last"],"expected_module_count":5,"mode":"verify-only","scope":"synthetic-code-import-only"}
```

이는 기본 합성 fixture의 예시이며 실제 backend61개를 검사했다는 뜻이 아니다. module 수는 ZIP inventory에서 얻으며61을 하드코딩하지 않는다. synthetic scope는 이번 테스트/사용 범위 표기이고 임의 source의 실제/합성 진실성을 인증하는 분류기가 아니다. 성공은 종료0이고 같은 프로세스의 정해진 검증만 뜻한다. 영속 token·출력 SHA·승인 상태·USABLE은 없다.

실패는 stderr의 `기존 prefix: 고정 field`와 종료2다. 준비된 prefix는14절 그대로 사용하며 backend import 예외의 raw payload/traceback을 노출하지 않는다. imported module의 일반 stdout은 stderr로 보내 최종 stdout 결과와 구분한다. 합성 동기화 신호 TEST_ONLY_HANDLE_HELD는 테스트 모듈의 stderr이며 최종 성공이 아니다. ARTIFACT_CHANGED_DURING_STARTUP은 방어 분기이고 악성 호스트의 우회를 실제 재현해 검증한 것은 아니다.

### 합성 테스트와 AR 대응

신규 `tests/test_artifact_bootstrap.py`만 추가했다. 기본 합성 package는 **명시5개 모듈**, nested package·간접 import·호출하면 실패하는 미사용 업무 함수로 구성한다. ZIP은 tmp의 synthetic-test-only 디렉터리에만 만들며 실제 backend 코드를 패키징하지 않는다. ZIP inventory와 profile의 플랫폼 독립 검사는 보조 unit test이고, Windows 핵심은 실제 subprocess/실제 API를 사용한다. 비-Windows에서는 native 사례를 skip하고 worker 자체도 native 보장을 흉내 내어 성공하지 않는다.

| AR | 실제 검증 및 한계 |
|---|---|
| AR01/AR10 | 정확한 합성 SHA/profile·5모듈 전체/간접 import·단일 ZIP·반복 새 프로세스 성공. 실제 두 domain 필드/production 배포물 생성은 없음 |
| AR02~AR04/AR07 | 최초 SHA 고정 뒤 raw/helper bytes 변경, 같은 이름/크기·같은 profile의 다른 내용, hash가 구조 검사보다 먼저 실패. import marker가 없음 |
| AR05~AR06 | CWD/PYTHONPATH 가짜 backend 미사용, 외부 backend 선로딩 거부, 다른 경로/ZIP·같은 이름·공통 문자열 prefix archive 거부, package 경로/검색 위치·loader/origin·예상 밖 모듈 검사 |
| AR08 | 실제 import가 보호 중 멈추는 파이프 동기화. 다른 프로세스의 write/overwrite/delete/rename/replace 거부, 같은 대상의 종료 후 성공. timeout/오류/kill 뒤 해제 |
| AR09 | 잘못된 implementation/version/platform/machine·기대 interpreter/base·실제 옵션/경로 거부. 같은 version의 설치물 bytes/악성 호스트 인증은 안 함 |
| AR11 | 두 artifact 입력·우회 옵션을 지원하지 않음. 분리된 artifact의 대응 성공 검사는 현재 규약/이번 구현 범위가 아님 |
| AR12 | 이번 verify-only는 과거 Review를 읽거나 STALE로 만들지 않음. 기존 Coverage matcher/회귀 보존과 분리 |
| AR13 | Acceptance evaluator 미구현. 과거 승인 대 current 구현 지문 비교를 실행했다고 하지 않음 |
| AR14 | --manifest 및 전체 release 경로 미구현/거부. 기존 전체 validator 회귀는 보존하지만 이 CLI가 whole dataset을 확인하지 않음 |
| AR15 | 파일/기대값 누락·잘못된 hash 문법·보호 handle 확보 실패는 정상 성공/UNUSABLE로 바꾸지 않음 |
| AR16 | fixture/model 검사와 새 Windows worker의 bytes/import·native sharing 검사를 따로 보고. 합성 성공을 실제 실행 검토 증거로 승격하지 않음 |
| AR17 | 검토 artifact 입력/Acceptance/Bridge 실행 경로 자체가 없음. 코드 검증 성공을 검토 내용 대응 성공으로 해석하지 않음 |
| AR18 | 필수 entry/parent package·정렬·중복/case충돌·탈출/drive/backslash·pyc/native/다른 ZIP/resource·압축·symlink/DOS directory·timestamp·profile 구조 거부, 늦은 import 실패도 전체 차단 |
| AR19 | 같은 ZIP의 반복 실행을 검증. 재설치/원격 환경 인증·범용 재현 builder·분리 패키징은 구현/검증하지 않음 |

Windows 파일 접근 오류는 연산에 따라 CRT errno13만 있거나 WinError32/replace의 WinError5로 나타났다. 실패 표현을32로만 고정하지 않고 **동일 파일의 보호 전 접근·보호 중 차단·종료 후 변경 성공**을 확인했다. 별도의 실제 CreateFileW writer subprocess는 보호 전/후 성공과 보호 중 정확한 ERROR_SHARING_VIOLATION(32)을 확인했다. 고정 sleep으로 상태를 추측하지 않는다.

개발 중 초기 단독 실행은 workspace TEMP 설정 누락으로 pytest 임시 경로 준비가 실패했다. 기존 프로젝트와 같은 명시 TEMP/TMP 설정으로 재실행했다. 이후 native 테스트의 오류 표현 및 communicate가 stdin을 닫아 EOF를 유발하던 timeout fixture를 수정했다. timeout은 동기화 후 wait(timeout)으로 검사하고 자식은 finally에서 kill/communicate로 회수한다. 기존 테스트/기대값은 수정하지 않았다.

### 완료 범위·다음 단계

**IMPLEMENTED:** 외부 표준 라이브러리 bootstrap, 합성 기대 SHA 직접 지정 verify-only, Windows 읽기 handle 수명, ZIP/profile/환경·옵션·전체 import 출처·함수 origin 대조, 고정 출력/실패, 합성 fixtures·실제 subprocess/native sharing tests.

**NOT IMPLEMENTED:** production code artifact/builder·엔진 hash/Manifest 발행·Manifest loader/full release 준비·source 사용 gate·검토 artifact 본문 대응·Coverage/Acceptance 업무 평가·same-call adapter·Bridge/Cashflow·서버/서명/배포 플랫폼.

최종 판단은 **SYNTHETIC_ARTIFACT_VERIFY_ONLY_COMPLETE**다. M2.52의 READY_TO_IMPLEMENT 판정을 이 작은 구현 범위에서 완료로 구체화하며 실제 backend/정책 배포 완료 판정은 아니다. 다음 최소 작업 한 개는 **Acceptance 검토 artifact의 구조화된 원본 대응 계약을 문서로 설계**하는 것이다.21필드 record와 당시 BenefitSnapshot/claim 근거·검토 ref의 정확한 대응을 닫되 새 범용 검토 framework를 자동 도입하지 않는다.

### M2.53 검증 기록

사전 전체 **6962 passed in 16.80s**. 신규 suite의 최초 전체 통과는 **103 passed in 47.28s**였고, source metadata2개·없는 artifact1개를 보완한 최종 신규 수는 **106개**다. 최종 전체 회귀는 **7068 passed in 67.01s**, skipped0/failed0이다. 기존6962개와 신규106개가 모두 포함됐다. 독립 helper unit 검사와 실제 Windows-native subprocess 검증을 함께 실행했으며 mock 성공을 native 성공으로 대신하지 않았다.

실제 실행 OS/runtime은 **Windows win32 / AMD64 / CPython3.12.14**다. read 공유와 zipimport의 양립, 다른 프로세스의5가지 변경 차단, 실제 CreateFileW writer의 sharing violation32·종료 전후 성공, 기존 writer 충돌, 정상/오류/timeout/kill 뒤 해제를 확인했다. 이 결과는 합성 source ZIP의 실행 대응이며 actual 정책/production 배포/Review 진실성 검증이 아니다.

SHA256 대조에서 사전 backend/tests/data/docs166개 중 **164개 동일·승인된 문서2개만 수정·삭제0개**다. 새 bootstrap과 새 합성 테스트2개가 추가돼 tools를 포함한 최종 source 문서 집합은168개다. 루트 설정4개 및 실제 release6개의 **SHA256 모두 동일**하며, release 경로/크기/수정시각도 동일하다. Coverage 동결 source/명세·GV01~GV15·Benefit/BV01~BV16·기존 모든 tests/fixture/기대값·Acceptance/Cashflow/ResidenceHistory를 보존했다.

문서26개 절·ARCHITECTURE53개 절의 연속 순서·표 열 수·코드 블록·한국어 표기와 기존 AR01~AR19 수동 표의 유일/연속 ID를 확인했다. 실제 source ZIP 배포물·production engine/implementation SHA·Manifest·Review/Acceptance·혜택 금액은 생성하지 않았다. 실제 안산 DRAFT/CONDITION_SLICE·정책 반영0원 원칙, ResidenceHistory **OFFICIAL_INQUIRY_REQUIRED**와 Coverage freeze는 유지한다.

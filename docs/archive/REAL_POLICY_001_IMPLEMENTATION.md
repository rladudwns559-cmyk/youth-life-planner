# 실제 정책 001 구현 — M1.15

확인일: **2026-10-20 / Asia/Seoul**. 최종 판단: **FIRST_REAL_POLICY_SLICE_COMPLETE**.
실제 정책 전체 판정 또는 production 승인이 아니다. 이전 분석의 역사적 구현 상태는 이 문서의 현재 범위와 구별한다.

## 1. 이번 구현 범위

2026년 안산시 청년기본소득의 **신청일 기준 안산시 주민등록 조건 leaf 하나**를 실행했다.

```text
실제 sources.json → 기존 strict SourceRegistry loader
실제 PolicyEnvelope JSON → 기존 strict Envelope loader
  → 기존 m1.1 parser → ResidentRegistrationRule / Policy / PolicyEnvelope
  → validate_envelope_sources(envelope, registry)
  → evaluate_policy_tree → 기존 Resolver → 기존 Adapter → RuleEvaluation
```

원문 조건을 기존 일반 region 비교로 대체하지 않았다. Resolver/Adapter/routing/evaluator/Fact/결과 타입/근거 validator는 변경하지 않았다.
실제 자료를 합성 True/True로 변환하지 않았다. 코드 변경은 models.py, loader.py, policy_data/loader.py의 실제 flags 수용 경계뿐이다.

## 2. 사용 공식 출처

2026-10-20에 아래 URL의 내용을 직접 재조회했다. 공고 게시물은 웹 도구에서 timeout이 발생해 공식 URL을 읽기 전용 HTTP로 확인했고, 첨부 HWP는 메모리에서 OLE/압축 본문을 추출했다. 정책 페이지와 3분기 안내도 공식 HTML 본문을 확인했다.

| 출처 | 확인한 내용 | 날짜 |
|---|---|---|
| [공고 게시물](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308) | 고시공고번호 제2026-399호, 담당 청년정책관, 제목·첨부 연결 | 공고일은 첨부 원문의 2026-02-19로 확인 |
| [첨부 HWP 원문](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP) | 신청개요의 안산시 대상, 거주요건 산정 기준이 신청일임을 확인 | 원문 공고일 2026-02-19 |
| [공식 정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545) | 지급조건에 신청일 기준 안산시 주민등록을 명시 | 게시일·수정일 미확인 → null |
| [3분기 공식 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) | 3분기 지급 대상 문장에서도 같은 기준을 확인 | 등록일 2026-08-31 |

이번 주민등록 조건에서 의미 변경·충돌은 발견하지 않았다. HWP는 **61,952 bytes**, SHA256 `b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106`으로 M1.8 확인본과 같다.
HWP 추출에서 공고번호 숫자 일부가 누락되는 형식 특성이 있어 번호는 게시물 metadata로 확인했다. 원문을 수정하거나 번호를 본문 추출 결과라고 주장하지 않는다.

기존 범위 밖 차이도 재확인했다. 초본 발급 기준은 공고의 신청기간 내 발급과 정책 페이지의 신청일 이후 발급이라는 차이가 남아 있다. 연초 자동신청 안내와 3분기 신규자 중단 안내도 절차의 적용 대상·시점을 별도로 검토해야 한다. 둘 다 이번 주민등록 지역 leaf에 섞지 않았으며 해결했다고 표시하지 않는다. 3분기 안내의 이미지 첨부는 이번 근거가 아니다.

## 3. source_document_id

| 내부 ID | 문서 버전 | 근거 역할 |
|---|---|---|
| ANSAN-2026-399-HWP | d0001 | 우선 공고 근거, 공식 공고번호는 notice_number에 별도 보존 |
| ANSAN-C0001545 | d0001 | 주민등록 요건의 명시적 표현 |
| ANSAN-B0238-1681390 | d0001 | 3분기 공식 안내 교차 확인 |

이 ID는 프로젝트 내부 안정 식별자이며 정부 발급 식별자가 아니다. d0001은 첫 실제 인코딩 확인본이고 이전 설계 문서의 후보를 발행된 데이터로 취급하지 않는다.

## 4. evidence locator

세 문서 모두 `eligibility-resident-registration`을 사용한다. 원격 HTML anchor가 아닌 내부 semantic locator다.

| 문서 | 사람이 다시 찾을 위치 |
|---|---|
| 공고 HWP | □ 신청개요 → ○ 신청대상 및 ☞ 거주요건 산정 주석 |
| 정책 페이지 | 사업개요 → 지급조건 첫 항목 |
| 3분기 안내 | 본문 두 번째 문단 → 3분기 지급 대상 설명 문장 |

정확한 HWP 쪽번호를 검증하지 않아 page는 null이다. 원문 전체 대신 짧은 의미 요약을 저장한다.
PASS/FAIL/UNKNOWN 모두 `RuleEvaluation.evidence_refs → parse_evidence_ref → registry.resolve / get_source → official_url / attachment_url`로 역추적된다.
정책 근거는 evidence_refs, 가상 사용자 사실의 출처·날짜·지역은 details.evidence로 분리된다.

## 5. policy / edition / rule ID

| 항목 | 값 |
|---|---|
| canonical policy_id | KR-GG-ANSAN-YOUTH-BASIC-INCOME |
| edition_id | 문자열 2026 |
| rule_id | ANSAN_YBI_2026_RESIDENT_AT_APPLICATION |
| rule_version | r0001 |
| dataset_version | ansan-youth-2026-10-20-001 |
| envelope / rule / source schema | policy-data-1.0 / m1.1 / source-registry-1.0 |

r0001은 정규화된 주민등록 규칙 버전으로 공고번호·분기·공고일이 아니다. 연도 edition은 현재 계약 그대로이며 분기별 edition granularity는 기술부채다. engine_version=m1.0은 기존 호환 표지이며 이번 빌드 식별자가 아니다.

## 6. 실제 데이터 파일 위치

기존 POLICY_DATA_ENVELOPE_SPEC.md 21절의 배치를 따른다. releases라는 경로명은 운영 승인이 아니다.

```text
data/releases/ansan-youth-2026-10-20-001/
  README.md
  sources.json
  policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json
tests/test_real_policy_001_slice.py
```

sources.json은 원문 metadata, policies의 JSON은 정규화된 실행 envelope다. 원본 HWP·사용자 입력·별도 raw 복제본은 저장하지 않았다. data/synthetic 전체와 기존 테스트 파일은 변경하지 않는다.

## 7. 주민등록 rule 및 최소 flags 변경

root는 `ResidentRegistrationRule` 한 개다. required_region은 GYEONGGI/ANSAN, reference_date_source는 APPLICATION_DATE다. 지역 key는 기존 MVP_INTERNAL_REGION_V1 내부 값이며 공식 행정코드라고 주장하지 않는다.

| flags | 처리 |
|---|---|
| True / True | 기존 합성 경로 그대로 허용 |
| False / False | 실제 자료. 도메인·parse_policy_set에서 allow_real_data=True 명시 시 허용 |
| True / False, False / True | Data Error |
| 정수 0/1, 문자열, null 등 | Data Error |

기존 직접 Policy/PolicySet 생성과 parse_policy_set의 기본값은 합성 전용으로 유지했다. 실제 Envelope loader는 외부/내부 flags의 일치를 확인하고 False/False인 경우만 기존 parser를 명시적으로 opt-in 호출한다. 합성 경로 호출은 기존 인자 형태를 유지한다. PolicySet 내부 정책 flags도 컨테이너와 일치해야 한다.

`allow_real_data`는 keyword-only InitVar로 **생성 시 허용 인자**일 뿐 데이터 필드·JSON 키·검토 상태가 아니다. 구조화 결과나 fingerprint에 저장되지 않는다. 따라서 실제 Policy/PolicySet을 dataclasses.replace로 다시 생성할 때도 allow_real_data=True를 명시해야 한다. 기본 load_policy_set(path)는 합성 전용이며 실제 파일은 load_policy_envelope(path)를 사용한다.
이 최소 명시 경계는 기존 False/False 기본 생성 거부 테스트까지 그대로 유지하기 위한 선택이다. 서비스 접근권한·운영 승인 기능이 아니다.

## 8. verification / coverage 및 Manifest

- Envelope: **DRAFT / CONDITION_SLICE**, source locator 확인일 최소값인 2026-10-20을 last_verified_at으로 보존.
- coverage.included_rule_ids: 주민등록 rule_id 하나만 포함.
- coverage.excluded_conditions: 연령, 이력, 국적/등록분류, 신청창, 절차, 지급 계산을 명시.
- SourceDocument/SourceEvidence: 해당 공식 자료와 locator를 이번에 직접 확인하여 VERIFIED. 그 상태가 전체 정책 구현 검증이나 운영 사용 승인으로 전파되지 않는다.
- ACTIVE: 이번 근거를 철회·대체한 사실을 확인하지 않은 참조 상태다. 접수 중·지급 중이라는 뜻이 아니다.
- 효력 시작/종료일: 이 slice의 독립 효력 날짜를 확인하지 않아 null. edition 연도나 신청기간을 대신 넣지 않는다.

**DatasetManifest는 이번에 생성하지 않았다.** 모델상 DRAFT 객체도 담을 수 있으나 engine_artifact_sha256이 필수이고 현재 검증된 배포 artifact가 없다. 가상 hash나 소스 파일 하나의 hash를 실제 엔진 artifact로 주장하지 않기 위해 사용자가 허용한 생략을 택했다. Manifest JSON loader·빌드 도구·review 파일을 추가하지 않았다. 이 상태는 release-ready가 아니다.

## 9. 실제 실행 테스트

공식 정책 데이터는 실제 파일을 로드하고, 입력 사실은 전부 테스트용 가상 SELF_REPORTED다. 평가일=2026-10-20, 기본 신청일=2026-09-15를 명시했다. 이 날짜는 재현 가능한 사례 입력이며 공식 효력일을 새로 설정한 것이 아니다. 신청창은 평가하지 않는다.

| 사례 | 입력 | 주민등록 leaf 실행 결과 |
|---|---|---|
| A | 신청일과 같은 날 안산 fact | PASS / RESIDENT_REGION_MATCH |
| B | 신청일과 같은 날 수원 fact | FAIL / RESIDENT_REGION_MISMATCH |
| C | fact 없음 | UNKNOWN / RESIDENT_REGISTRATION_MISSING |
| D | profile.region=ANSAN만 있음 | UNKNOWN / RESIDENT_REGISTRATION_MISSING |
| E | 신청일 하루 전 안산 fact만 있음 | UNKNOWN / RESIDENT_REGISTRATION_DATE_UNPROVEN |
| F | 같은 신청일 안산·수원 fact 충돌 | Data Error / CONFLICTING_RESIDENT_REGISTRATION_FACTS |
| G | 신청일=2026-10-21, 평가일보다 미래 | UNKNOWN / RESIDENT_REFERENCE_DATE_IN_FUTURE |

신규 파일의 테스트는 **46개**다. A~G 외 실제 strict load·cross-validation·근거 추적·resolver→adapter 호출·잘못된 flags·생성 opt-in·DRAFT/coverage·입력 불변성·결정성도 검증한다. 잘못된 문서 버전/locator/수명/적용 정책은 Data Error다.

합성↔실제 registry를 단순 교환하면 SOURCE_NOT_FOUND다. source binding/refs를 상대 자료로 다시 연결해도 적용 정책 목록이 달라 POLICY_EVIDENCE_MISMATCH다. Source schema에 새 synthetic 플래그나 전역 출처 분류기는 추가하지 않았다. 이는 현재 데이터의 참조 무결성 격리이며, 공격자가 ID·적용 목록·본문을 모두 조작한 자료의 진위를 인증하는 기능은 아니다.

PowerShell 재실행:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TEMP=(Resolve-Path '.\tmp\python-temp').Path
$env:TMP=$env:TEMP
& '.\.venv\Scripts\python.exe' -m pytest tests/test_real_policy_001_slice.py -q
& '.\.venv\Scripts\python.exe' -m pytest -q
```

작업 전 **1,736 passed in 5.10s**, 최종 전체 실행은 **1,782 passed in 5.79s**다. 기존 1,736개 기대값을 수정하지 않고 신규 46개를 더해 모두 통과했다.
Git 저장소가 아니므로 기존 backend/tests/data/docs 61개 파일의 SHA256 기준선과 비교했다. 코드 3개(models.py, loader.py, policy_data/loader.py) 및 계약 문서 3개(ARCHITECTURE.md, DATA_MODEL.md, POLICY_DATA_ENVELOPE_SPEC.md)만 변경됐고 나머지 55개는 동일하다. 기존 모든 테스트 파일과 data/synthetic 전체도 동일하다. 신규 파일은 실제 데이터 2개·데이터 README·이 구현 문서·테스트 파일로 총 5개다.

## 10. PASS 의미

**청년기본소득 주민등록 조건 leaf PASS**다. 주어진 fact가 명시한 신청일의 안산시 주민등록지역과 일치한다는 뜻이다. 자기신고 사실의 진위를 행정기관에서 인증했다는 뜻은 아니다.

## 11. FAIL 의미

**주민등록 조건 leaf FAIL**이다. 주어진 신청일의 유효한 지역 fact가 요구지역과 다르다는 뜻이다. 전체 정책의 법적 불가·영구 제외·다른 신청 회차 판정을 만들지 않는다.

## 12. UNKNOWN 의미

주민등록 fact 부족·기준 날짜 미입증·미래 기준일 등 기존 Resolver 계약의 확인 부족이다. profile.region이나 과거 사실로 채우지 않는다. UNKNOWN을 PASS로 바꾸지 않으며 모순 데이터 오류를 UNKNOWN으로 숨기지 않는다.

## 13. 전체 정책으로 해석하면 안 되는 이유

PolicyEvaluation.overall_status는 현재 root 한 개의 집계다. root에 미구현 조건이 없는 것은 조건이 면제되거나 충족되었다는 뜻이 아니다. 기존 결과 타입은 coverage를 직접 포함하지 않으므로 호출자는 **Envelope의 scope/coverage/verification을 함께 보관·해석해야 한다**. 이 단계는 사용자 화면이나 추천 API를 제공하지 않는다.
실제 자료 False/False, 공식 locator VERIFIED, 구조 검증 통과, leaf PASS는 각각 전체 정책의 production approval과 다르다. “신청 가능/수급 가능” 확정 표현의 근거로 쓸 수 없다.

## 14. 미구현 조건과 한계

분기별 생년월일/연령, 경기도 최근 연속 3년 및 합산 10년, 등록분류·국적·귀화일과 인정기간, ApplicationWindow/시간 경계, 자동·소급신청, 서류 발급 기준 차이·대리신청, 지급분기·일시금·지원금 계산을 구현하지 않았다.
공식자료의 자동 갱신·7일 freshness enforcement·production acceptance·검토 서명·원문 보관·빌드 artifact 검증도 없다. 마지막 확인일 이후 변경은 재확인이 필요하다. API/UI/DB/금융/What-if/LLM은 이번 범위가 아니다.

## 15. 다음 단계

다음 가장 작은 작업 **1개**: **실제 2026년 3분기 생년월일 조건 한 개의 공식 경계·입력·PASS/FAIL/UNKNOWN 계약을 문서로 검토한다.** 구현 없이 날짜 양끝 포함, 지급 분기 기준일과 현재 나이의 차이, 생년월일 최소 수집 및 기존 연도 edition과의 연결 GAP을 정리한다. 주민등록 leaf와 합쳐 전체 자격으로 실행하는 작업은 별도 승인 대상이다. 추가 generic infrastructure를 만들지 않는다.

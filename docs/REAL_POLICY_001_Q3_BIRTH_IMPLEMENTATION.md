# 실제 정책 001 — Q3 Birth 통합 구현 (M1.16K)

확인일: **2026-10-20 / Asia/Seoul**. 최종 판단: **Q3_BIRTH_SLICE_COMPLETE**. 생년월일 조건의 최종 integration milestone을 완료했다. 전체 정책 자격·운영 승인은 포함하지 않는다.

## 1. Milestone 목적

공식 SourceRegistry → actual Birth evidence → resident/birth ALL → 기존 strict Envelope loader → source cross-validation → 기존 routing → 상태·근거·결정적 직렬화까지 연결했다. 새 데이터·테스트·문서만 추가했으며 core engine을 변경하지 않았다. 제품의 Python 판정/AI 설명 역할 분리와 개인정보 비영구 저장 원칙을 유지한다.

Source of Truth는 승인된 REAL_POLICY_001_Q3_BIRTH_INTEGRATION_SPEC.md와 기존 구현·Birth 모델/결과/routing/loader·Envelope/Rule 계약이다. 현재 코드의 지원 범위를 역사적 미구현 기록과 구별했다.

## 2. 새 release ID

**ansan-youth-2026-10-20-002**. 생성 전 경로가 없음을 확인했다. 현재 날짜·명명 계약에 맞는 J의 미사용 후보를 사용했으며 파일을 x 모드로 생성해 기존 JSON을 덮어쓰지 않았다.

```text
data/releases/ansan-youth-2026-10-20-002/
  sources.json
  policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json
  README.md
tests/test_real_policy_001_q3_birth_slice.py
docs/REAL_POLICY_001_Q3_BIRTH_IMPLEMENTATION.md
```

## 3. Old release 관계

001은 resident-only / r0001 / d0001 snapshot으로 불변 보존한다. 새 release는 같은 policy_id/edition을 사용하지만 dataset_version/rule_version/source 확인본이 다르다. 두 release는 독립 경로로 선택하고 한 실행에 old sources와 new policy를 혼합하지 않는다. 기존 resident integration tests는 수정하지 않았다.

## 4. 공식 출처

다음 세 자료를 이번 K에서 직접 재확인했다. 게시물·첨부·정책 페이지·안내를 읽기 전용 HTTP로 읽고 HWP를 메모리에서 OLE/압축 해제했다. 정책/안내는 웹 도구에서도 열었다. 원문 전체를 저장소에 복제하지 않았다.

| ID / d0002 | 공식 URL / 직접 근거 |
|---|---|
| ANSAN-2026-399-HWP | [공고](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308), [첨부](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP): 공고번호·첨부 연결 및 Q3 표 행/연령기준 |
| ANSAN-C0001545 | [정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545): 2026년 지급일정 및 방법 표의 3분기 대상 출생일 |
| ANSAN-B0238-1681390 | [3분기 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390): 두 번째 본문 문단의 전체 연도 출생일 |

셋 모두 범위를 직접 명시한다. S1·S2 축약 표기는 S3의 2001/2002 표기와 대조했다. HWP는 **61,952 bytes**, SHA256 **b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106**으로 기존 확인본과 같다. source URL/공고정보를 발명하지 않고 001에서 재사용했다.

d0002는 새 locator를 포함한 **normalized metadata 확인본 버전**이며 공식 공고 개정 번호가 아니다. resident locator는 동일하고 supersedes/철회 상태를 새로 만들지 않았다. 자료 간 Q3 범위 충돌은 없었다. 다른 행정·절차 쟁점을 해결했다고 표시하지 않는다.

## 5. Q3 birth range

JSON의 min_birth_date=2001-07-02, max_birth_date=2002-07-01이며 양끝 포함이다. 공식 대상 구간과 연령 기준일 경계가 일치하는 정규화 해석을 사용했다. age reference date=2026-07-01의 직접 근거는 S1이다. 기준일은 source 의미 요약에 보존하며 evaluator에 새 인자로 넣지 않았다. [공고 첨부](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP), [3분기 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390).

실제 정책 값은 release JSON에 있으며 loader/evaluator/router 코드에 하드코딩하지 않았다. 테스트의 명시적 expected 경계는 공식값에 대한 회귀 계약이다. 현재일·평가일·신청일·연도로 구간을 선택하지 않는다.

## 6. Locator

세 문서에 **eligibility-birth-date-2026-q3**를 추가했다. semantic locator이지 원격 anchor가 아니다.

| 문서 | 사람이 찾을 위치 |
|---|---|
| 공고 HWP | 신청개요 → 연령기준 및 신청기간 및 지급일정 표 → 3분기 행/지급대상자 생년월일 열 |
| 정책 페이지 | 주요내용 → 2026년 지급일정 및 방법 → 같은 행/열 |
| Q3 안내 | 본문 두 번째 문단 → 3분기 지급 대상 설명 |

실제 필드명 applicable_policy_ids를 사용했다. verified_at=2026-10-20, VERIFIED/ACTIVE이며 page=null, table_position은 표 두 개에만 있다. 요약은 조건 의미만 짧게 담았다. S2/S3가 별도 연령 기준일을 직접 명시한다고 주장하지 않는다.

## 7. Rule IDs

| 역할 | 내부 안정 ID |
|---|---|
| ALL root | ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE |
| resident | ANSAN_YBI_2026_RESIDENT_AT_APPLICATION |
| birth | ANSAN_YBI_2026_Q3_BIRTH_RANGE |

기존 resident leaf는 요구지역·APPLICATION_DATE·ID·refs까지 old와 전체 객체 equality가 성립한다. 모든 노드 ID는 기존 검증으로 유일하다.

## 8. Rule version / edition

r0002를 사용한다. 트리 구조·계산 범위·coverage 변화이므로 r0001을 재사용하지 않았다. edition_id는 **2026** 그대로이며 2026-Q3 문법은 추가하지 않았다. policy_name에 3분기·조건 일부를 명시하고 coverage·근거·README에도 같은 범위를 보존했다. schema는 policy-data-1.0 / m1.1 / source-registry-1.0이다.

## 9. ALL tree

```text
ALL / ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE
├─ ResidentRegistrationRule / 신청일 exact-date / GYEONGGI·ANSAN
└─ BirthDateRule / 2026 Q3 출생일 양끝 포함 구간
```

자식 순서는 resident → birth다. root-first 결과는 group, resident, birth 세 개다. 기존 Status 집계·공통 결과 조립·직렬화를 그대로 사용했다. age 원자 leaf나 분기 selector를 추가하지 않았다.

## 10. Coverage

included_rule_ids는 resident/birth 두 leaf ID와 정확히 일치한다. group ID는 넣지 않는다. excluded_conditions 7개에 다른 분기·연간 전체/자동선택, 연속 3년, 합산 10년, 등록분류/국적/귀화, 신청창, 자동/소급/서류·절차, 지급 계산을 명시한다. 미구현 항목을 PASS나 실행 UNKNOWN placeholder로 만들지 않았다.

## 11. DRAFT 의미

Envelope는 DRAFT / CONDITION_SLICE / 실제 False·False다. SourceDocument/locator VERIFIED가 전체 정책 구현·운영 승인으로 전파되지 않는다. ACTIVE는 접수 중을 뜻하지 않는다. 독립 효력 시작/종료일은 null이다. last_verified_at=사용한 여섯 locator 확인일 최솟값인 2026-10-20이다.

## 12. Actual execution results

신규 테스트 **56 passed in 0.31s**. 기존 실제 경로를 그대로 사용했다.

```text
load_source_registry(new sources.json)
load_policy_envelope(new policy JSON)
  → 기존 m1.1 parser / 실제 False·False opt-in 경로
validate_envelope_sources(envelope, registry)
evaluate_policy_tree(profile, envelope.policy, context,
                     facts=typed facts, reference_context=명시적 신청일)
  → 기존 resident Resolver/Adapter + birth evaluator
  → 기존 ALL / PolicyEvaluation / to_dict
```

기본 가상 입력은 평가일=2026-10-20, 신청일=2026-09-15, 같은 날 안산 SELF_REPORTED resident fact다. 출생일도 단일 SELF_REPORTED BirthFact이며 실제 신청자 데이터가 아니다. 단일 router가 dataset_version을 Envelope와 자동 대조한다고 가정하지 않고 명시적으로 같은 버전을 전달한다.

## 13. Boundary results

아래는 새 실제 JSON을 로드하고 기존 경로로 실행한 **조건 일부**의 결과다.

| 가상 출생일 | Birth | reason | resident+Q3 birth slice |
|---|---|---|---|
| 2001-07-01 | FAIL | BIRTH_DATE_BEFORE_RANGE | FAIL |
| 2001-07-02 | PASS | BIRTH_DATE_WITHIN_RANGE | PASS |
| 2001-12-15 | PASS | BIRTH_DATE_WITHIN_RANGE | PASS |
| 2002-07-01 | PASS | BIRTH_DATE_WITHIN_RANGE | PASS |
| 2002-07-02 | FAIL | BIRTH_DATE_AFTER_RANGE | FAIL |

## 14. UNKNOWN results

BirthFact 없음은 UNKNOWN/MISSING, evaluated_value=None, birth_source=None, missing_fields=(birth.birth_date,)다. 날짜만 None인 Fact는 같은 UNKNOWN이고 실제 BirthSource를 보존한다. 세 BirthSource 모두 테스트했다. resident PASS 아래 전체 slice는 UNKNOWN이다. age=24로 채우지 않는다.

## 15. Resident/birth truth table

기존 ALL의 **9조합 전부**를 actual tree로 실행했다.

| resident | birth | slice |
|---|---|---|
| PASS | PASS | PASS |
| PASS | FAIL | FAIL |
| PASS | UNKNOWN | UNKNOWN |
| FAIL | PASS | FAIL |
| FAIL | FAIL | FAIL |
| FAIL | UNKNOWN | FAIL |
| UNKNOWN | PASS | UNKNOWN |
| UNKNOWN | FAIL | FAIL |
| UNKNOWN | UNKNOWN | UNKNOWN |

최종 FAIL이어도 다른 leaf의 UNKNOWN·missing_fields가 남는다. resident fact가 신청일 하루 전/뒤에만 있으면 DATE_UNPROVEN/UNKNOWN이며 birth PASS로 보완하지 않는다. 같은 날 안산/수원 충돌은 오류로 전파한다. reference context 자체 부재도 정상 UNKNOWN이 아닌 ContextValidationError다.

## 16. Evidence trace

두 leaf의 여섯 refs 모두 새 Registry에서 resolve된다. leaf ref → source_document_id/locator → d0002 SourceDocument → official_url/attachment_url → 사람이 읽을 section/table_position으로 역추적했다. 요구 정책 ID 적용 목록과 ACTIVE/VERIFIED·확인일도 명시적 assertion으로 확인했다.

없는 birth locator, 문서 버전 불일치, coverage 누락, source binding 누락, 다른 정책 적용 목록, WITHDRAWN locator, 확인일 불일치는 기존 오류로 거부했다. actual Envelope/synthetic Registry 교환은 SOURCE_NOT_FOUND, 합성 ref/binding을 실제 자료에 섞으면 POLICY_EVIDENCE_MISMATCH다. source schema에 synthetic 분류기를 새로 추가하거나 조작된 원문의 진위를 인증하는 기능은 없다.

## 17. Serialization

PASS/FAIL/UNKNOWN에서 반복 실행 객체·dict·고정 옵션 JSON이 동일하다. group/resident/birth 순서, 관찰 출생일과 요구 날짜 ISO, BirthSource, evidence_refs, missing_fields, rule_version/context를 기존 결과 모델이 보존한다. 반환 dict를 변경해도 원래 결과는 불변이다.

고정 Q3 자료에 신청일을 1월/11월로 바꿔 같은 날 resident fact를 제공해도 birth 구간은 변하지 않는다. 이는 해당 달의 신청 가능 판정이 아니며 분기 자동선택이 없다는 검증이다. 프로필 age=None/23/24/25와 무관하게 유효 BirthFact는 PASS, BirthFact 부재는 UNKNOWN이다.

## 18. Old release SHA

작업 전/후 아래 SHA256이 동일하다. 기존 resident-only 테스트 파일도 변경하지 않았으며 old release를 별도로 로드해 BirthFact 없이 resident-only 결과가 재현됨을 테스트했다.

| 001 상대 파일 | SHA256 |
|---|---|
| README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |

## 19. Synthetic SHA

기존 합성 자료 8개를 모두 보존했다.

| data/synthetic/ 파일 | 작업 전/후 동일 SHA256 |
|---|---|
| policies_m11_birth.json | 2ad1757b3c2f5897a1d74d0477a2c19492111c09f2f93fcd674abe83276ccf01 |
| policies_m11.json | 121287d4b4c7c9a12205318e2ad12e7fb6c2d5d8eddd8625a82c265c1248ef0f |
| policies.json | 59ea3f0ea1033ab84e6ce506f4479019ed23e5de752c6c18d1c05b351ded73ef |
| policy_envelope_m11.json | ada139c90f41932eaad625a04bf7f9ac46ccc8f7633511807fb83b2fabfed2a5 |
| profile.json | 46aca31d8c0d5443d99fbc5451be8780f4fc8299fc78f88c24d28bd17ae3916f |
| README.md | 8f17baa6482dc3962ed1e3ad582d671d0297fa9b30a927e7123359b374a0cd77 |
| SOURCES_README.md | 6e5c4d9830aea8854f3b957a0221e7cfe41ee972394934650988dbffdf30406b |
| sources.json | 0c77e2604c5ead6d80dd9fa6d8a681543b784d7c7b32e3eef747e74c6927f84e |

위 8개 파일의 해시를 각각 회귀 테스트로 고정했다.

## 20. Omitted conditions

경기도 최근 연속 3년 OR 합산 10년 이력·산정, 등록분류/국적·귀화 후 인정기간, 신청창·시간 경계, 자동·소급신청, 제출서류·대리 절차, 지원금·지급분기·일시금 예외, 다른 분기 Birth 범위는 미구현이다. 초본 발급일 문구 차이 등 기존 미해결 행정 쟁점도 남는다. API/UI/LLM/계정/DB/사용자 입력 저장은 추가하지 않았다.

## 21. Wording boundary

결과는 **resident + 2026 Q3 birth implemented condition slice PASS/FAIL/UNKNOWN**이다. 연간 전체 eligibility나 신청·수급 가능 확정으로 표현하지 않는다. PolicyEvaluation에는 coverage가 직접 없으므로 Envelope의 DRAFT/CONDITION_SLICE/제외 조건과 함께 해석한다. 기존 display_status만 단독 노출해 전체 정책 결과로 일반화할 수 없다.

## 22. Manifest 생략 이유

검증된 engine artifact hash가 여전히 없어 실제 DatasetManifest/review JSON은 생성하지 않았다. engine_version=m1.0은 호환 표지이며 배포 빌드 지문이 아니다. 가상 hash나 HWP hash를 엔진 hash로 쓰지 않았다. 파일 SHA와 데이터·규칙 버전은 기록하지만 완전한 실행 artifact 재현·production gate·freshness enforcement를 보장한다고 하지 않는다. Manifest infrastructure는 추가하지 않았다.

## 23. 최종 판단 / 검증 기록

**Q3_BIRTH_SLICE_COMPLETE**. 실제 Q3 생년월일 조건의 모델→로딩→근거 검증→판정 통합은 이 milestone으로 종료한다. 추가 Birth infrastructure는 필요 작업으로 제안하지 않는다.

- 작업 전: **2316 passed in 7.03s**.
- 신규 실제 Q3 통합: **56 passed in 0.31s**.
- 최종 전체: **2372 passed in 4.65s**.
- 기존 2316개 테스트·기대값은 수정하지 않았다. core engine·기존 loader/router/evaluator/모델도 변경하지 않았다.
- Git 저장소가 아니므로 git status는 not a git repository였고 파일 SHA256 기준선을 사용했다. 작업 전 backend/tests/data/docs 81개 파일의 해시를 기록했다. 최종 무결성 대조는 아래 추가 기록을 따른다.

최종 해시 대조에서 **기존 81개 파일 전부 동일**했다. old release 3개·synthetic 8개·기존 테스트·core engine·기존 문서를 모두 보존했다. 추가 파일은 이 구현 문서, 신규 테스트, 새 release 세 파일로 **총 5개**다. 구현 문서의 24개 절·신규 파일의 한국어 문서·JSON 문법도 확인했다.

| 새 002 release 상대 파일 | 최종 SHA256 |
|---|---|
| README.md | 8955e554cd484240f0d8dddffec5494d342c2b5732e789666b45eb261b58ca99 |
| sources.json | 711f1e3bbb8ddb4bcbaaddd189b6f35f7c9a6ef8b4a81f0208e4dd818629e620 |
| policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | d4aaa62f1a1c46392af213c05c6e24ff59e44f17333f3b3785bde2d4b3161e92 |

## 24. 다음 정책 조건

다음 가장 작은 작업 한 개는 **경기도 거주기간: 최근 연속 3년 OR 합산 10년의 공식 산정 기준·필요 이력 입력·UNKNOWN/오류 경계를 문서로 설계**하는 것이다. 윤년·전출입 구간 끝점·도내 이동·귀화일·불완전 이력의 근거를 확인하고 임의의 3×365일/소수 년으로 계산하지 않는다. 실제 거주기간 구현·트리 통합은 후속 승인 범위다.

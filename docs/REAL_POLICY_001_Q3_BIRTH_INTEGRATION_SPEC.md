# 실제 정책 001 — Q3 Birth 통합 계약 (M1.16J)

검토일: **2026-10-20 / Asia/Seoul**. **문서 전용**. 이번 산출물은 이 문서 하나이며 아래 JSON과 파일 경로는 후속 M1.16K의 후보다. 실제 release·source·PolicyEnvelope·코드·테스트·합성 fixture는 변경하지 않는다.

최종 판단: **READY_TO_INTEGRATE_REAL_Q3_BIRTH**. 명시적으로 선택한 **2026 Q3 CONDITION_SLICE / DRAFT**의 로컬 통합 준비 상태다. 연간 전체 자격·현재 접수 가능·운영 배포 승인이 아니다.

## 1. 목적

공식 Q3 출생일 범위, 근거 위치, resident+birth 트리, 연간 edition 안의 적용 범위, coverage·확인본·규칙·release 버전을 실제 파일 변경 전에 정한다. Python의 기존 비교·집계와 AI의 설명 역할 분리를 유지한다. 입력 경제정보·생년월일을 영구 저장하거나 로그·LLM으로 전송하는 기능은 추가하지 않는다.

검토 자료: REAL_POLICY_001_ANALYSIS.md, REAL_POLICY_001_IMPLEMENTATION.md, REAL_POLICY_001_BIRTH_SLICE_SPEC.md, REAL_POLICY_001_BIRTH_RESULT_CONTRACT.md, REAL_POLICY_001_BIRTH_ROUTING_SPEC.md, REAL_POLICY_001_BIRTH_LOADER_SPEC.md, POLICY_DATA_ENVELOPE_SPEC.md, POLICY_RULE_SPEC.md, RULE_ROUTING_SPEC.md, DATA_MODEL.md, ARCHITECTURE.md. 역사적 미구현 기록보다 최신 구현 절과 현재 코드·실제 파일을 우선한다.

현재 release `data/releases/ansan-youth-2026-10-20-001/`의 sources.json, 정책 Envelope, README를 확인했다. r0001 단일 resident root, 세 resident evidence_refs, 연도 edition=2026, DRAFT/CONDITION_SLICE, False/False다. M1.16I가 구현한 것은 합성 Birth 로딩 경로이며 실제 Birth locator는 아직 없다.

## 2. 공식 source 재확인

아래 공식 주소를 이번 작업에서 다시 읽었다. 과거 문서의 날짜를 재검증 기록으로 대신 쓰지 않았다.

| ID / 우선순위 | 공식 자료 | 직접 확인한 위치·내용 | 이번 접근 |
|---|---|---|---|
| S1 / 1 | [공고 제2026-399호 게시물](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308) 및 [첨부 HWP](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP) | 게시물의 번호·제목·첨부 연결. 첨부의 신청개요 → 연령기준, 신청기간 및 지급일정 표 → 3분기 행 | 웹 도구 게시물 timeout 후 같은 공식 URL을 읽기 전용 HTTP로 확인. HWP OLE/압축 텍스트를 메모리에서 추출 |
| S2 / 2 | [안산시 청년기본소득 정책 페이지](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545) | 주요내용 → 2026년 지급일정 및 방법 → 3분기 행 / 지급대상자 생년월일 열 | 웹 도구로 본문·표 확인 |
| S3 / 3 | [3분기 공식 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) | 본문 두 번째 문단의 3분기 지급 대상 설명. 전체 연도 2001/2002 표기. 등록일 2026-08-31 | 웹 도구 및 같은 URL의 읽기 전용 HTTP로 확인 |

S1 HWP는 **61,952 bytes**, SHA256 **b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106**으로 기존 확인본과 같다. 파일·원문 전체는 저장소에 복제하지 않았다. 정확한 쪽번호는 검증하지 않아 만들지 않는다. S3 이미지 첨부는 근거로 사용하지 않았다. S2 게시일·수정일은 미확인이므로 publication_date=null을 유지한다.

이번 검토 범위의 Q3 출생일·분기 식별에서 충돌은 없다. 초본 발급 기준 차이와 자동신청 경과조치는 기존 미해결 절차로 남는다. 이후 직접 근거가 충돌하거나 접근·의미 확인에 실패하면 K의 실제 인코딩을 중단한다.

## 3. Q3 birth range

실행할 조건은 **2001-07-02 ≤ birth_date ≤ 2002-07-01**이다. S1·S2의 축약 연도는 S3 전체 연도와 대조했다. 세기·구간을 현재 나이에서 추정하지 않았다. [S1 첨부](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP), [S2 표](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545), [S3 대상 문단](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390).

양끝 포함은 명시된 대상 출생일 구간과 공식 연령 기준일의 경계가 일치한다는 **정규화 해석**이다. 공식 문서에 수학적 부등호나 inclusive 필드가 있다는 뜻은 아니다. 경계 제외 문구는 이번 자료에서 발견하지 않았다. 기존 BirthDateRule의 inclusive 의미를 그대로 사용한다.

| 출생일 | Birth 기대 |
|---|---|
| 2001-07-01 | FAIL / BIRTH_DATE_BEFORE_RANGE |
| 2001-07-02 | PASS / BIRTH_DATE_WITHIN_RANGE |
| 2002-07-01 | PASS / BIRTH_DATE_WITHIN_RANGE |
| 2002-07-02 | FAIL / BIRTH_DATE_AFTER_RANGE |

## 4. Age reference date

Q3 연령 기준일은 **2026-07-01**이다. 직접 근거는 S1 첨부의 신청개요 → 연령기준 항목이다. 분기 시작 월 첫날을 제시한다. S2·S3에 그 기준일이 별도 명시돼 있다고 확대 해석하지 않는다. [공고 첨부 원문](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP).

이 날짜는 source locator의 의미 요약과 README·이 문서에 보존하는 검토 metadata다. BirthDateRule에 새 필드로 넣지 않고 나이 산식으로 min/max를 생성하지 않는다. 신청일은 resident 판단, 평가일은 재현 context, 출생일은 birth 비교에 각각 사용한다. 신청일·평가일·효력일·연령 기준일을 서로 대체하지 않는다.

## 5. Q3-specific 의미

이 leaf는 **2026년 3분기 지급대상 생년월일 조건**이다. 2026년 모든 지급분기에 같은 구간을 적용하는 연간 조건이 아니다. Q1/Q2/Q4, 소급 분기 또는 접수 가능한 회차는 판단하지 않는다. Q3 신청기간이 끝났더라도 이 고정 조건의 비교가 OPEN/CLOSED를 반환하는 것은 아니다.

K의 정책 표시 이름은 `2026년 안산시 청년기본소득 — 3분기 주민등록·생년월일 조건 일부`로 한다. canonical policy_id는 유지한다. 이 이름은 공식 사업 명칭 변경을 주장하는 것이 아니라 저장된 부분 실행 정의의 범위를 명시한다.

## 6. Annual edition 문제

| 방안 | 검토 | 결정 |
|---|---|---|
| A. edition=2026 안의 명시적으로 선택된 Q3 부분 조건 | 현 계약으로 단일 고정 slice를 표현 가능. 연간 전체 계산과 구별 필요 | **K의 제한된 DRAFT 통합에 채택** |
| B. edition=2026-Q3 | 현재 ASCII 4자리 연도 validator가 거부. edition 계약 변경 필요 | 이번에 구현하지 않음 |
| C. quarter context/selector | 회차 선택·입력·불일치 검증 등 별도 설계 필요 | 이번에 구현하지 않음 |

**edition은 연도 자료의 식별자이며 모든 분기의 조건이 구현됐다는 선언이 아니다.** 다음 값을 함께 보존해야 A의 Q3 의미가 손실되지 않는다.

| 저장 위치 | 확정할 표현 |
|---|---|
| dataset_version / 선택 경로 | 새 release를 명시적으로 선택. 연도만으로 파일을 선택하지 않음 |
| policy_name | 5절의 3분기·조건 일부 명시 |
| root / birth rule_id | Q3를 포함한 안정 내부 ID, 8절 |
| coverage.included_rule_ids | resident + Q3 birth 두 leaf만 포함 |
| coverage.excluded_conditions | Q1/Q2/Q4 및 연간 전체·자동 분기 선택이 미구현임을 명시 |
| birth evidence locator / meaning_summary | 2026 Q3, 공식 범위, S1의 연령 기준일 보존 |
| release README 및 본 문서 | Q3 DRAFT 범위, 직접 고정 경로 선택, 금지 해석 명시 |

현재 모델에 typed quarter·scope qualifier가 없으므로 **자동 분기 범위 검증은 제공하지 않는다**. ID의 Q3 문자열을 엔진이 해석하지 않으며 excluded_conditions도 실행 가드가 아니다. 위 조합은 수동 검토된 오프라인 DRAFT의 의미 보존에는 충분하다. 임의 분기의 서비스 요청을 자동 검증·차단하는 요구가 생기면 이 계약으로 충분하다고 주장하지 않고 별도 scope 모델을 먼저 검토해야 한다. 이번에는 자동 적용 요청·서비스 API가 없다.

## 7. Quarter auto-selection 금지

K에서도 오늘·application_date·context.as_of·edition=2026으로 Q3를 선택하거나 날짜 구간을 만들지 않는다. 테스트 호출자가 **새 Q3 slice release의 정확한 경로**를 선택한다. 다른 분기를 요청하면 이 고정 slice를 그 분기의 결과로 재표시할 수 없다. 현재 public API에 quarter 요청 인자는 없다.

`effective_from/to`에 7월~9월 또는 신청기간을 넣어 분기 가드를 흉내 내지 않는다. 지금까지 독립 효력 범위를 확정하지 않았으므로 null을 유지한다. application_date의 월이 9월이어야 한다는 비교도 추가하지 않는다.

## 8. Policy Tree 변경안

```text
ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE (ALL)
├─ ANSAN_YBI_2026_RESIDENT_AT_APPLICATION
│    ResidentRegistrationRule / APPLICATION_DATE / GYEONGGI·ANSAN
└─ ANSAN_YBI_2026_Q3_BIRTH_RANGE
     BirthDateRule / [2001-07-02, 2002-07-01]
```

resident ID·요구지역·기준일·세 evidence_refs는 그대로 보존한다. birth ID는 M1.16에서 제안한 안정 내부 ID를 채택한다. group에도 기존 rule_id 필드를 사용하며 `op` 대신 **operator**를 사용한다. 순서는 resident → birth로 고정하고 root-first 결과 순서를 유지한다. `age==24` 원자 조건을 덧붙이지 않는다.

## 9. ALL 결과 의미

PASS는 **현재 구현된 resident + 2026 Q3 birth 두 조건이 모두 PASS**라는 뜻이다. FAIL은 이 부분 트리의 조건 중 하나 이상이 FAIL, UNKNOWN은 FAIL이 없고 미확인이 있다는 뜻이다. 미구현 조건은 통과·면제됐다는 뜻이 아니다. ALL의 기존 진리표·전체 자식 평가·누락 근거 보존을 그대로 쓴다.

PolicyEvaluation에는 coverage/verification/edition이 직접 포함되지 않는다. 따라서 호출자는 Envelope의 dataset_version/rule_version/scope/coverage/DRAFT와 결과를 함께 해석해야 한다. `display_status`의 일반 문구만 단독 노출해 전체 정책 가능성을 말할 수 없다. 이번 단계는 결과 API/UI를 만들지 않으며 결과 타입도 확장하지 않는다.

## 10. Coverage

현재 included는 resident 한 ID이고 excluded에 분기별 연령·생년월일 전체가 있다. K에서는 아래 후보로 교체한다. group ID는 leaf 목록에 넣지 않는다.

```json
{
  "included_rule_ids": [
    "ANSAN_YBI_2026_RESIDENT_AT_APPLICATION",
    "ANSAN_YBI_2026_Q3_BIRTH_RANGE"
  ],
  "excluded_conditions": [
    "2026 Q1·Q2·Q4 생년월일 조건 및 연간 전체 판정·분기 자동선택",
    "경기도 최근 연속 3년 주민등록 거주기간",
    "경기도 합산 10년 주민등록 거주기간",
    "등록분류·국적 및 귀화일에 따른 인정기간",
    "분기별 신청기간·시각·ApplicationWindow",
    "자동신청·소급신청·제출서류·대리신청 절차",
    "지원금·지급분기·일시금 예외 계산"
  ]
}
```

PolicyCoverage는 두 leaf ID의 정확한 집합과 미구현 설명을 저장할 수 있다. Q3 의미는 6절 metadata·근거와 함께 보존한다. **오프라인 DRAFT 표현에는 COVERAGE_MODEL_GAP이 없다.** 다만 coverage 문자열의 의미/Q3 요청 일치를 자동 검증하는 기능은 없다. 이를 이미 구현된 quarter guard라고 설명하지 않는다. 미구현 거주기간의 OR 관계를 새 Rule이나 UNKNOWN placeholder로 만들지 않는다.

## 11. Verification status

Envelope는 **DRAFT 유지**, evaluation_scope는 **CONDITION_SLICE 유지**다. SourceDocument/SourceEvidence의 확인 완료와 전체 정책의 구현·검토 완료를 분리한다. source locator가 VERIFIED여도 Envelope를 VERIFIED로 승격하지 않는다. production acceptance·freshness enforcement·review 승인을 통과했다고 기록하지 않는다.

lifecycle_status=ACTIVE는 접수 중·수급 가능의 의미가 아니다. effective_from/to=null도 무기한 유효가 아니다. last_verified_at은 사용한 모든 leaf locator 확인일의 최솟값이다. K가 같은 날 재확인하면 2026-10-20이고, 더 늦은 날 일부 locator만 확인해도 기존 날짜를 일괄 최신으로 덮지 않는다.

## 12. SourceDocument 전략

**기존 세 SourceDocument에 birth locator를 추가하는 A를 채택**한다. 각각 같은 공식 문서의 다른 의미 위치이므로 같은 URL의 별도 문서를 복제하지 않는다. 기존 문서 ID·공고번호·publication_date·URL은 확인한 사실이 바뀌지 않으면 유지한다.

기존 resident locator는 같은 의미·ID·기록을 보존한다. birth locator가 원문 전체를 대체하거나 resident 근거를 재해석하지 않는다. Source schema에 synthetic/quarter/applies_to_policy_id 같은 새 키를 추가하지 않는다. 실제 필드명은 **applicable_policy_ids**다.

## 13. Locator

**eligibility-birth-date-2026-q3**를 최종 후보로 채택한다. 기존 lowercase-hyphen 문법에 맞고 지급 연도·분기를 명시한다. 원격 HTML anchor·DOM selector가 아닌 내부 semantic locator다. URL이 바뀌어도 같은 의미라면 ID를 유지하고 확인본·위치 metadata를 새로 기록한다.

| SourceDocument | section 후보 | table_position 후보 | meaning_summary에 기록할 의미 |
|---|---|---|---|
| ANSAN-2026-399-HWP | 첨부 HWP: 신청개요 → 연령기준 및 신청기간 및 지급일정 표 | 3분기 행 / 지급대상자 생년월일 열 | 2026 Q3 출생일 범위, 양끝 포함 정규화, 연령 기준일 2026-07-01. 연간 전체·다른 분기 조건이 아님 |
| ANSAN-C0001545 | 주요내용 → 2026년 지급일정 및 방법 | 3분기 행 / 지급대상자 생년월일 열 | 축약 표기의 출생일 범위. 전체 연도는 S3와 대조. 기준일은 이 표 자체의 직접 근거라고 하지 않음 |
| ANSAN-B0238-1681390 | 본문 두 번째 문단 → 3분기 지급 대상 설명 | null | 4자리 연도로 명시한 Q3 출생일 범위. 다른 분기에 일반화하지 않음 |

모든 page는 null이다. 각 locator는 applicable_policy_ids=[KR-GG-ANSAN-YOUTH-BASIC-INCOME], verified_at=실제 의미 확인일, verification_status=VERIFIED, status=ACTIVE를 기록할 수 있다. K에서 재확인이 실패하면 VERIFIED 후보를 그대로 쓰지 않는다. 짧은 요약만 저장하고 긴 원문을 복제하지 않는다.

S1 SourceEvidence의 문서 내 후보 예시는 다음과 같다. 아직 sources.json에 추가한 데이터가 아니다.

```json
{
  "locator_id": "eligibility-birth-date-2026-q3",
  "section": "첨부 HWP: 신청개요 → 연령기준 및 신청기간 및 지급일정 표",
  "page": null,
  "table_position": "3분기 행 / 지급대상자 생년월일 열",
  "meaning_summary": "2026 Q3 지급대상 출생일은 2001-07-02~2002-07-01이며 양끝 포함으로 정규화한다. 연령 기준일은 2026-07-01이다. 이 범위를 연간 전체 또는 다른 분기에 적용하지 않는다.",
  "applicable_policy_ids": ["KR-GG-ANSAN-YOUTH-BASIC-INCOME"],
  "verified_at": "2026-10-20",
  "verification_status": "VERIFIED",
  "status": "ACTIVE"
}
```

## 14. Evidence source selection

분류는 **조건별**로 판단한다. DIRECT는 그 자료 자체에서 대상 범위를 읽을 수 있다는 뜻이며 출처 개수를 맞추기 위한 규칙이 아니다.

| 출처 | Q3 출생일 범위 | 4자리 연도 확정 | 연령 기준일 | Birth evidence_refs 선택 |
|---|---|---|---|---|
| S1 첨부 HWP | DIRECT: Q3 표 행 | CORROBORATING: 01/02 축약, S3 대조 필요 | DIRECT | 포함 |
| S2 정책 페이지 | DIRECT: Q3 표 행 | CORROBORATING: 같은 축약 | NOT_APPLICABLE: 별도 기준일 표기는 확인 못함 | 포함 |
| S3 Q3 안내 | DIRECT: 대상 문장 | DIRECT: 2001/2002 명시 | NOT_APPLICABLE: 별도 날짜 표기는 확인 못함 | 포함 |

세 자료 모두 범위를 직접 명시하므로 이번 Birth leaf에는 세 refs를 사용한다. S1 게시물 metadata만으로 범위를 증명하지 않고 첨부를 근거로 쓴다. 표의 축약 해석은 S3와 대조한 정규화 기록을 남긴다. S2/S3로 연령 기준일을 추가 증명했다고 하지 않는다. 후속에 직접 근거가 사라지면 단순히 개수를 유지하지 않고 검토·새 release 결정으로 돌아간다.

## 15. Document version

**세 문서 모두 K의 새 snapshot에서 d0002 후보**다. POLICY_DATA_ENVELOPE_SPEC.md 10절의 document_version은 문서 ID별 **확인본 metadata/locator 버전**이며 URL·확인일만 바뀌어도 새 버전이다. 따라서 locator 추가인데 d0001을 그대로 수정하는 것은 기존 계약과 충돌한다.

구분해야 할 변화:

| 구분 | 이번 확인 / 후속 처리 |
|---|---|
| 공식 공고 번호·원문 개정 | 제2026-399호 유지. 공식 개정 사실을 새로 주장하지 않음 |
| HWP 원문 bytes | 같은 SHA256. 기존 content_sha256 유지 가능 |
| normalized 확인본 | locators 증가 → d0001에서 d0002 |
| sources.json 파일 bytes / Registry 내용 지문 | 변경됨. 새 release의 해시·지문은 새로 계산 |
| policy source_bindings | 세 source ID를 각각 d0002에 고정 |

같은 원문이므로 d0002가 정부의 개정판 번호라는 표현을 쓰지 않는다. 원문 hash와 sources.json 파일 hash를 혼동하지 않는다. S2/S3 HTML은 탐색 메뉴·동적 요소로 bytes가 달라질 수 있어 원문 개정 판단의 단독 근거가 아니다.

이번 metadata 추가만으로 공식 대체를 의미하는 supersedes를 만들거나 d0001을 SUPERSEDED로 바꾸지 않는다. 이전 d0001은 old release 안에서 그대로 보존한다. 새 Registry에는 각 문서의 d0002 하나씩 존재하고 loader가 최신 버전을 자동 선택하지 않는다.

## 16. Rule version

**r0001 → r0002**가 필요하다. 원문 내용이 변하지 않아도 resident-only에서 ALL(resident,birth)로 트리 구조·계산 정의·커버리지가 달라진다. 기존 version 계약 10절의 증가 조건에 정확히 해당한다. 단순 evidence 갱신만의 경우와 다르다.

leaf에 rule_version을 추가하지 않고 policy.rule_version 하나로 유지한다. 기존 resident ID와 의미는 동일하고 old release는 r0001 그대로다. r0002는 Q3 부분 트리 버전이며 연간 전체 규칙 완료 버전이 아니다. rule schema=m1.1, envelope schema=policy-data-1.0, source schema=source-registry-1.0은 유지한다.

## 17. Release/version 전략

**기존 release 수정 A를 배제하고 새 release 생성 B를 채택**한다. 같은 날 다음 사용 가능 후보는 `ansan-youth-2026-10-20-002`다. 실제 생성은 K 승인 후이며 이번에 폴더·파일을 만들지 않는다.

| 항목 | old | K 후보 |
|---|---|---|
| dataset_version / directory | ansan-youth-2026-10-20-001 | ansan-youth-2026-10-20-002 |
| edition_id | 2026 | 2026 |
| rule_version | r0001 | r0002 |
| 세 document_version | d0001 | d0002 |
| root | resident | ALL(resident,Q3 birth) |
| verification / scope | DRAFT / CONDITION_SLICE | 동일 |

Assumption A1: K가 2026-10-20에 실행되고 002가 미사용일 때 위 후보를 사용한다. 실행일이 바뀌거나 이름이 이미 사용 중이면 실제 생성 전에 새 확인일과 사용하지 않은 release ID를 정하고 문서·JSON·테스트의 dataset_version을 함께 맞춘다. 기존 디렉터리에 덮어쓰거나 임의로 current/latest 링크를 만들지 않는다.

sources.json, PolicyEnvelope JSON, README를 **같은 새 release 안에 함께 snapshot**한다. old sources와 new policy 또는 반대 조합을 섞지 않는다. artifact hash와 normalized fingerprint는 필요 시 기존 함수를 사용하며 새로운 Manifest infrastructure는 만들지 않는다.

## 18. Old release immutability

old release 파일은 bytes 단위 불변으로 유지한다. old README의 resident-only 의미도 갱신하지 않는다. 잘못된 점을 추후 발견하면 새 release와 설명 문서를 만들며 과거 확인 결과를 조용히 수정하지 않는다.

현재 작업 전 기록과 후속 K에서 다시 대조할 SHA256:

| old release 상대 경로 | SHA256 |
|---|---|
| README.md | 4183c73c37d3cb7ec76bad21656b50a2c41b064e1298c2d4934db0d4e536a09f |
| sources.json | a47e53da0b298c93c1ad04480e8c7fed96f2e45144ad4d58991c9ec86aaa9e3b |
| policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json | 9c6e22ddc1c936e365ecb9b3be355a73f8cfbdc6f02f99d66e2fb843e0187025 |

현재 과거 release 덮어쓰기를 자동 방지하는 배포 시스템은 없다. 이 계약은 파일 보존·작업 전후 해시 비교·기존 테스트 유지로 집행한다. 운영용 historical replay 기능까지 구현됐다는 뜻은 아니다.

## 19. Candidate actual Birth rule

**문서상의 후보**다. 여섯 키는 현재 m1.1 문법이며 실제 Registry의 새 locator는 K 전에는 존재하지 않는다.

```json
{
  "kind": "rule",
  "rule_type": "birth_date",
  "rule_id": "ANSAN_YBI_2026_Q3_BIRTH_RANGE",
  "min_birth_date": "2001-07-02",
  "max_birth_date": "2002-07-01",
  "evidence_refs": [
    "ANSAN-2026-399-HWP#eligibility-birth-date-2026-q3",
    "ANSAN-C0001545#eligibility-birth-date-2026-q3",
    "ANSAN-B0238-1681390#eligibility-birth-date-2026-q3"
  ]
}
```

## 20. Candidate Policy JSON

아래는 **새 release용 전체 Envelope 후보**다. 같은 날짜 재확인과 002 미사용이라는 17절 Assumption을 적용한다. 기존 파일 수정본이나 실행 완료 데이터가 아니다. source_bindings의 d0002와 birth refs는 새 release의 sources.json과 함께 검증해야 한다.

```json
{
  "schema_version": "policy-data-1.0",
  "rule_schema_version": "m1.1",
  "policy_id": "KR-GG-ANSAN-YOUTH-BASIC-INCOME",
  "edition_id": "2026",
  "jurisdiction": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
  "category": "YOUTH_SUPPORT",
  "dataset_version": "ansan-youth-2026-10-20-002",
  "evaluation_scope": "CONDITION_SLICE",
  "coverage": {
    "included_rule_ids": [
      "ANSAN_YBI_2026_RESIDENT_AT_APPLICATION",
      "ANSAN_YBI_2026_Q3_BIRTH_RANGE"
    ],
    "excluded_conditions": [
      "2026 Q1·Q2·Q4 생년월일 조건 및 연간 전체 판정·분기 자동선택",
      "경기도 최근 연속 3년 주민등록 거주기간",
      "경기도 합산 10년 주민등록 거주기간",
      "등록분류·국적 및 귀화일에 따른 인정기간",
      "분기별 신청기간·시각·ApplicationWindow",
      "자동신청·소급신청·제출서류·대리신청 절차",
      "지원금·지급분기·일시금 예외 계산"
    ]
  },
  "source_bindings": [
    {"source_document_id": "ANSAN-2026-399-HWP", "document_version": "d0002"},
    {"source_document_id": "ANSAN-C0001545", "document_version": "d0002"},
    {"source_document_id": "ANSAN-B0238-1681390", "document_version": "d0002"}
  ],
  "verification_status": "DRAFT",
  "last_verified_at": "2026-10-20",
  "lifecycle_status": "ACTIVE",
  "effective_from": null,
  "effective_to": null,
  "synthetic": false,
  "test_only": false,
  "policy": {
    "policy_id": "KR-GG-ANSAN-YOUTH-BASIC-INCOME",
    "policy_name": "2026년 안산시 청년기본소득 — 3분기 주민등록·생년월일 조건 일부",
    "rule_version": "r0002",
    "synthetic": false,
    "test_only": false,
    "root": {
      "kind": "group",
      "rule_id": "ANSAN_YBI_2026_Q3_IMPLEMENTED_SLICE",
      "operator": "ALL",
      "children": [
        {
          "kind": "rule",
          "rule_type": "resident_registration",
          "rule_id": "ANSAN_YBI_2026_RESIDENT_AT_APPLICATION",
          "required_region": {"sido": "GYEONGGI", "sigungu": "ANSAN"},
          "reference_date_source": "APPLICATION_DATE",
          "evidence_refs": [
            "ANSAN-2026-399-HWP#eligibility-resident-registration",
            "ANSAN-C0001545#eligibility-resident-registration",
            "ANSAN-B0238-1681390#eligibility-resident-registration"
          ]
        },
        {
          "kind": "rule",
          "rule_type": "birth_date",
          "rule_id": "ANSAN_YBI_2026_Q3_BIRTH_RANGE",
          "min_birth_date": "2001-07-02",
          "max_birth_date": "2002-07-01",
          "evidence_refs": [
            "ANSAN-2026-399-HWP#eligibility-birth-date-2026-q3",
            "ANSAN-C0001545#eligibility-birth-date-2026-q3",
            "ANSAN-B0238-1681390#eligibility-birth-date-2026-q3"
          ]
        }
      ]
    }
  }
}
```

## 21. Actual test scenarios

아래는 **후속 K를 위한 수동 기대값**이며 이번에 실행한 통합 테스트가 아니다.

기본값: 명시적으로 새 Q3 release를 선택, 평가일=2026-10-20, 신청일=2026-09-15, 같은 신청일의 안산 SELF_REPORTED resident fact, 단일 SELF_REPORTED BirthFact를 쓴다. 실제 데이터에 가상 사용자 입력을 대입하며 신청자 개인정보를 파일에 저장하지 않는다. 출생일 기본 중간값은 2001-12-15다.

R_P=같은 날 안산, R_F=같은 날 수원, R_U=유효 reference context와 resident fact 없음. B_P=중간값, B_F=하한 하루 전, B_U=BirthFact 없음이다. context 자체 부재는 R_U가 아닌 호출 오류다.

최소 열 가지 필수 기대: R_P+하한=P, R_P+중간=P, R_P+상한=P, R_P+하한-1=F, R_P+상한+1=F, R_P+B_U=U, R_U+B_P=U, R_F+B_P=F, R_P+B_P+age=25=P, R_P+BirthFact 없음+age=24=U. 세부 사유·증거와 나머지 조합은 27절에 고정한다.

## 22. User-facing wording boundary

허용: `2026 Q3 주민등록·생년월일 조건 일부 충족`, `implemented condition slice PASS`, `resident + Q3 birth slice PASS`. FAIL/UNKNOWN도 반드시 같은 부분 범위를 붙인다. 미구현 조건과 DRAFT를 함께 설명한다.

금지: `청년기본소득 신청 가능`, `청년기본소득 대상 확정`, `전체 정책 eligibility PASS`, `2026년 모든 분기 대상`. 여기서 금지 문구를 적은 것은 향후 결과에서 그 표현을 사용하도록 지시하는 것이 아니다.

기존 PolicyEvaluation.display_status의 값은 변경하지 않는다. 후속 서비스에서는 범위·상태 metadata를 동반하는 별도 표현 계약이 필요하다. LLM이 생년월일/age를 다시 비교하거나 미구현 거주기간을 충족했다고 채우지 못하게 해야 하며 이번에 explanation service는 만들지 않는다.

## 23. Cross-validation

K의 순서는 기존 loader → 별도 cross-validator → 기존 router다. 검증 실패를 UNKNOWN으로 바꾸지 않는다.

| 점검 | 후속 완료조건 / 현재 검증 범위 |
|---|---|
| policy ID / edition | 외부·내부 canonical ID 일치, edition 정확히 2026 |
| rule/schema version | r0002, m1.1, policy-data-1.0. golden 기대를 테스트에서 명시 |
| source bindings | leaf 근거 source ID 합집합과 정확히 일치. 세 문서 모두 새 Registry의 d0002 |
| evidence refs | birth locator 존재, ACTIVE, 해당 policy 적용, resident refs 보존 |
| document versions | d0001/d0002 혼합 또는 old/new Registry 결합 거부 |
| coverage | included=두 leaf ID 집합, 제외 설명과 Q3 범위를 수동·golden 대조 |
| verification / flags | DRAFT, CONDITION_SLICE, 외부·내부 False/False를 명시 검증 |
| confirmation dates | 사용 locator verified_at 최솟값과 last_verified_at 일치 |
| actual SourceRegistry resolution | 각 leaf ref → 정확한 SourceEvidence → 부모 문서 URL/첨부/위치 추적 |
| Q3 의미 | 공식 범위·기준일·명칭·제외 범위를 별도 고정 기대와 대조. generic validator가 원문 의미를 읽지는 않음 |
| dataset/context | 선택 경로와 envelope.dataset_version이 같고 context도 그 버전을 명시. 단일 router가 자동 대조한다고 가정하지 않음 |
| 결과 | root-first 순서, 세 노드 결과, 원래 leaf 사유·provenance·근거, 버전/context와 직렬화 재현 |

Source VERIFIED/freshness·DRAFT 유지·금지 문구·공식 의미는 구조 validator의 완전 자동 보장이 아니다. 현 source cross-validator는 참조·버전·적용 정책·최소 확인일을 검증하며, 운영 승인 gate는 구현하지 않았다. K의 명시적 assertion·수동 검토와 구별해서 보고한다.

## 24. Manifest 처리

현재 검증된 engine artifact SHA256이 없다는 M1.15 조건이 유지되므로 **실제 DatasetManifest 생략을 유지**한다. engine_version=m1.0은 호환 표지이고 Birth 지원 빌드 hash가 아니다. 가상 hash·소스 한 파일 hash·공식 HWP hash를 엔진 artifact hash로 넣지 않는다.

새 Manifest loader·빌드 시스템·review JSON·가상의 팀원 승인을 만들지 않는다. K의 README에 실제 파일 SHA256, 버전, 실행 명령·결과와 Manifest 부재를 기록한다. 파일 hash만으로 완전한 실행 artifact 재현이나 production acceptance가 완료됐다고 하지 않는다. 같은 실행 코드·선택 데이터·가상 입력 아래 old/new 조건 결과를 재현한다는 범위다.

## 25. Old/new release coexistence

기존 `tests/test_real_policy_001_slice.py`와 resident-only release는 보존한다. 기존 테스트를 새 root에 맞춰 고치지 않는다. 새 파일 `tests/test_real_policy_001_q3_birth_slice.py`에서 새 release만 직접 로드하고 old release 해시·r0001·resident-only root를 별도로 확인한다.

두 release는 같은 policy_id/edition을 가지지만 dataset_version/rule_version/source 확인본으로 구별된다. 같은 Manifest의 서로 다른 정책 두 개로 합치거나 두 edition을 동시에 선택하지 않는다. 새 release 하나가 선택된 호출과 old release 하나가 선택된 호출을 독립 비교한다. old 결과를 r0002의 결과로 다시 이름 붙이지 않는다.

## 26. Actual/synthetic isolation

기존 synthetic Birth fixture와 sources는 그대로 둔다. 실제 Envelope는 실제 Registry의 실제 refs만 사용한다. 사용자 facts가 테스트용 가상이라는 사실은 정책 flags를 True/True로 바꾸는 이유가 아니다.

현재 자료에서 actual Envelope + synthetic Registry는 SOURCE_NOT_FOUND이며, 실제 birth ref를 합성 ref로 바꾸고 binding까지 맞춰도 target policy 적용 목록이 다르면 POLICY_EVIDENCE_MISMATCH다. 실제 flags와 내부 flags를 섞는 경우도 기존 로더 오류다. Source schema에는 synthetic flag가 없으므로 새 전역 공식성 판별기가 있는 것처럼 설명하지 않는다. ID·적용 목록·원문까지 모두 조작한 자료의 진위를 현재 validator가 인증한다는 보장도 없다.

## 27. 수동 통합 시나리오

**45개 수동 기대값이며 이번에 실행한 신규 테스트가 아니다.** P/F/U는 PASS/FAIL/UNKNOWN이다. Data Error에는 정상 PolicyEvaluation이 없다. 범위/문구/버전 관련 일부 행은 수동·golden 검토이며 generic validator의 자동 보장으로 표시하지 않는다.

| ID | 입력 / 점검 | 기대 / 검증 경계 |
|---|---|---|
| QBI01 | R_P + birth=2001-07-01 | F / Birth BEFORE |
| QBI02 | R_P + birth=2001-07-02 | P / 하한 포함 |
| QBI03 | R_P + birth=2001-12-15 | P / 중간 |
| QBI04 | R_P + birth=2002-07-01 | P / 상한 포함 |
| QBI05 | R_P + birth=2002-07-02 | F / Birth AFTER |
| QBI06 | R_P + BirthFact 없음 | U / birth.birth_date 누락, source=None |
| QBI07 | R_P + BirthFact 날짜=None | U / provenance 보존 |
| QBI08 | R_P + B_P | P / ALL_PASS |
| QBI09 | R_P + B_F | F / ALL_FAIL |
| QBI10 | R_P + B_U | U / ALL_UNKNOWN |
| QBI11 | R_F + B_P | F |
| QBI12 | R_F + B_F | F / 두 leaf FAIL 보존 |
| QBI13 | R_F + B_U | F / Birth UNKNOWN·누락도 보존 |
| QBI14 | R_U + B_P | U |
| QBI15 | R_U + B_F | F / Resident UNKNOWN·누락도 보존 |
| QBI16 | R_U + B_U | U / 두 누락 경로 보존 |
| QBI17 | R_P + B_P, profile.age=25 | P / age 불일치로 재판정 없음 |
| QBI18 | R_P + BirthFact 없음, age=24 | U / age fallback 없음 |
| QBI19 | R_P + B_F, age=24 | F / age로 덮지 않음 |
| QBI20 | R_P + B_P, age=None | P / 불필요한 age 누락 없음 |
| QBI21 | 실제 두 leaf의 여섯 refs resolve | source ID/d0002/locator/적용 정책/공식 URL·위치 일치 |
| QBI22 | 없는 birth locator 참조 | SourceValidationError / LOCATOR_NOT_FOUND |
| QBI23 | binding=d0001, 실제 Registry=d0002 | EnvelopeValidationError / SOURCE_VERSION_MISMATCH |
| QBI24 | 새 policy + old Registry | SOURCE_VERSION_MISMATCH. 버전을 억지로 맞춰도 birth locator 미존재 |
| QBI25 | old 세 release 파일 SHA256 대조 | 18절과 같음. 기존 resident-only 결과 재현 |
| QBI26 | 새 release strict load + cross-validation | 정상 도메인 객체 / 공식 의미 검토는 별도 |
| QBI27 | 새 트리인데 r0001 유지 | 후속 golden/version 검토 실패. generic loader가 과거 이력을 감지한다고 주장 안 함 |
| QBI28 | coverage에서 birth ID 누락 | COVERAGE_RULE_MISMATCH |
| QBI29 | coverage에 group ID를 추가 | COVERAGE_RULE_MISMATCH |
| QBI30 | DRAFT/CONDITION_SLICE/False·False 유지 | 후속 명시적 assertion 성공 |
| QBI31 | VERIFIED로 임의 변경 | K의 acceptance assertion 실패. loader 자체는 enum을 허용할 수 있음 |
| QBI32 | actual Envelope + synthetic Registry | SOURCE_NOT_FOUND |
| QBI33 | birth를 합성 ref/binding으로 치환, 혼합 Registry | 실제 policy 적용 목록 불일치로 POLICY_EVIDENCE_MISMATCH |
| QBI34 | 같은 가상 입력·자료·context 반복 직렬화 | dict/고정 encoding JSON 동일 |
| QBI35 | 결과 순서 확인 | root → resident → birth, leaf refs·reason·details 보존 |
| QBI36 | 결과 P를 전체 eligibility/신청 가능으로 서술 | 문구 검토 실패. slice 범위로만 표현 |
| QBI37 | edition=2026-Q3로 변경 | INVALID_EDITION_ID |
| QBI38 | profile.region=ANSAN만 있고 resident fact 없음, B_P | U / region fallback 없음 |
| QBI39 | resident reference context 자체 생략 | ContextValidationError / 정상 U 아님 |
| QBI40 | context 객체는 유효, application_date=None, B_P | U / RESIDENT_REFERENCE_DATE_MISSING |
| QBI41 | 신청일만 평가일 이후로 변경, B_P | Resident 미래 기준일 U → ALL U. Birth P는 그대로 |
| QBI42 | 고정 Rule/Fact에 평가일 변경, 신청일은 과거 유지 | Birth leaf 동일. 상위 context JSON은 달라짐 |
| QBI43 | Q3 ID/locator에 Q2 범위를 잘못 복사 | 공식 묶음 golden 검토 실패. 순서만 유효하면 generic parser는 거부 못함 |
| QBI44 | used locator 최소 확인일과 envelope 날짜 불일치 | LAST_VERIFIED_DATE_MISMATCH |
| QBI45 | 같은 날짜 resident 안산/수원 충돌, B_P | 기존 충돌 오류 전파. Birth P로 오류 숨김 없음 |

## 28. M1.16K 예상 변경 파일

이번에 생성하지 않는다. K는 이 문서의 승인 후 별도 작업이다.

```text
data/releases/ansan-youth-2026-10-20-002/                 신규 후보
  sources.json                                          세 d0002 / birth locator 추가
  policies/KR-GG-ANSAN-YOUTH-BASIC-INCOME__2026.json        r0002 / ALL / Q3 범위 / DRAFT
  README.md                                             제한·확인본·해시·재실행 기록
tests/test_real_policy_001_q3_birth_slice.py               신규 실제 자료 통합 테스트
docs/REAL_POLICY_001_Q3_BIRTH_IMPLEMENTATION.md             신규 후속 구현 기록 후보
```

기존 docs 갱신이 필요하면 해당 K 지시 범위에서 구현 상태만 반영한다. old release·old resident tests·synthetic fixture는 변경하지 않는다. loader/router/evaluator/모델/Manifest infrastructure 수정은 예상하지 않는다. 필요성이 발견되면 데이터 추가로 위장해 변경하지 않고 먼저 계약 문제를 보고한다.

## 29. 미해결 문제 / Assumptions

| 항목 | 상태 / 통합 영향 |
|---|---|
| Assumption A1 | 17절의 같은 날·사용 가능 002 후보. 실제 K 실행일·경로 충돌을 확인해야 함 |
| Assumption A2 | 호출자는 명시적으로 선택한 Q3 DRAFT를 평가하는 오프라인 통합 테스트다. 임의 분기 서비스가 아님 |
| Assumption A3 | 사용자 facts는 한 가상 사용자·요청 단위. source enum은 인증이 아님 |
| Q3 자동 범위 검증 | typed quarter/selector 미구현. 이번 단일 DRAFT의 metadata·coverage·근거·golden 검토로 범위를 고정. 일반 서비스 확장 전 별도 설계 필요 |
| 공식 행정 쟁점 | 거주기간·등록분류/국적·귀화 인정기간·초본 발급 문구 차이·자동/소급신청의 효력은 미구현·기존 미해결 유지 |
| 출처 최신성 | 이번 확인일 이후 변경 가능. K에서 직접 근거/위치/해석을 재확인하고 충돌 시 중단 |
| Artifact/Manifest | 검증된 실행 배포 artifact 부재. 생략 상태를 명시하며 production release-ready 주장 금지 |
| Source version 의미 | 기존 계약상 metadata/locator 확인본 버전. d0002는 공식 원문 개정 번호가 아님. 선택 확정 |
| 전체 정책·UI/LLM | CONDITION_SLICE 결과의 범위 동반·설명 계약은 후속 서비스 단계. 실제 입력 영구 저장·로그·LLM 전송은 허용하지 않음 |

이번 제한된 K를 막는 공식 범위 충돌·release/version 미결정·coverage 표현 GAP은 없다. 위 한계를 해결된 기능으로 보고하지 않는다.

## 30. 최종 판단

**READY_TO_INTEGRATE_REAL_Q3_BIRTH**

근거: 세 공식 직접 근거의 Q3 범위 일치, S1의 기준일 확인, 연간 edition 안의 명시적 Q3 DRAFT 범위 보존, ALL/coverage 해석, 세 d0002·r0002·새 release·old 불변성, 실제/합성 격리와 45개 수동 기대값을 확정했다.

**다음 가장 작은 작업 1개:** M1.16K에서 재확인한 공식 근거로 **새 immutable Q3 resident+birth DRAFT release 한 개와 별도 통합 테스트**를 추가한다. 기존 release를 보존하고 source/coverage/version/결과를 대조한다. 분기 selector·전체 정책 자격·Manifest infrastructure는 포함하지 않는다.

### 이번 작업 검증 기록

작업 전 전체 pytest: **2316 passed in 7.53s**. 새 실행 테스트·실제 데이터 인코딩은 없다. 27절은 수동 기대표이고 실제 Q3 통합 테스트를 실행했다는 뜻이 아니다. 작업 전 backend/tests/data/docs **80개** 파일의 SHA256을 기록했다. 최종 대조 결과와 문서 형식 확인은 아래에 기록한다.

문서 작성 후 전체 pytest: **2316 passed in 6.98s**. 기존 테스트·기대값은 변경하지 않았다. 기존 80개 파일 전부의 SHA256이 동일하고 추가 파일은 이 문서 하나다. old release의 세 파일도 18절과 일치한다. Git 저장소가 아니므로 파일 해시로 대조했다.

필수 30개 절, 중복·누락 없는 QBI01~QBI45, 네 JSON 예시의 문법, Birth leaf 단독 예시와 Envelope 내부 leaf의 일치, 문서 언어를 확인했다. 이는 문서 형식·기존 회귀 확인이며 candidate actual JSON의 신규 통합 실행이나 production 검증을 뜻하지 않는다.

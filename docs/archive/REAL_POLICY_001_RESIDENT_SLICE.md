# 실제 정책 001 주민등록 조건 검토

단계: **M1.8 / 문서 확정 전용**. 확인일: **2026-10-20, Asia/Seoul, 날짜 정밀도**.

판단: **READY_TO_ENCODE_REAL_RESIDENT_RULE**. 이는 아래 단일 조건의 의미와 기존 계산 계약이 일치한다는 판단이다. 실제 정책 데이터 로딩, 전체 정책 자격 판정, 운영 배포를 승인하는 의미는 아니다.

## 1. 정책 식별

| 항목 | 내용 |
|---|---|
| 정책 | 2026년 안산시 청년기본소득 |
| 공고 | 안산시 공고 제2026-399호 |
| 공고 제목 | 2026년 안산시 청년기본소득 신청 일정 공고 |
| 공고일 | 2026-02-19. 첨부 공고문에 적힌 날짜로 재확인 |
| 담당 기관 | 안산시 / 청년정책관 |
| 내부 정책 식별자 후보 | `ANSAN_YOUTH_BASIC_INCOME_2026` — 공식 식별자가 아닌 문서상 제안 |
| 선행 분석 | [M1.5 전체 정책 분석](REAL_POLICY_001_ANALYSIS.md) |

제품 범위의 Source of Truth는 프로젝트 기획 PDF다. 이 행정조건의 근거는 아래 공식 원문이다. 이 문서가 기존 전체 정책 분석을 대체하거나 범위 밖 조건을 승인하지 않는다.

## 2. 이번 slice 범위

질문 하나만 다룬다: **해당 신청일에 주민등록상 지역이 안산시인가?**

정책 요구지역과 기준일의 의미, 사용자 사실의 날짜·지역 비교, 근거 연결을 검토한다. 실제 인물의 주민등록자료를 수집하거나 진위 검증하지 않는다. 수동 사례는 모두 가상이다.

## 3. 공식 출처 목록

| 출처 | 우선순위 / 재확인 자료 |
|---|---|
| S1 | 1순위: [공고 게시물](https://www.ansan.go.kr/danwongu/common/bbs/selectBbsDetail.do?bbs_code=WWW13&bbs_seq=1664308) 및 [HWP 공고 원문](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1771511062365JEVSJ0BIMRJGDD3MSS84HYWFP) |
| S2 | 2순위: [안산시 청년기본소득 정책 안내](https://www.ansan.go.kr/www/common/cntnts/selectContents.do?cntnts_id=C0001545) |
| S3 | 3순위: [안산시 공식 3분기 안내](https://www.ansan.go.kr/www/common/bbs/selectBbsDetail.do?bbs_code=B0238&bbs_seq=1681390) |

S3은 안산시가 직접 게시한 공식 보도자료이며 독립 언론 기사가 아니다. 단독으로 공고를 대체하지 않고 S1·S2와 교차 확인한다. 검색결과 요약, 민간 기사, 블로그, AI 요약은 근거로 채택하지 않았다.

## 4. 출처 메타데이터

### S1: 공고 게시물과 첨부 원문

| 필드 | 값 |
|---|---|
| source_document_id | `ANSAN-2026-399-HWP` — 기존 M1.5 식별자 후보 유지 |
| 기관 | 안산시 / 담당부서 청년정책관 |
| 제목 | 2026년 안산시 청년기본소득 신청 일정 공고 |
| 공고번호 | 안산시 공고 제2026-399호. 게시물의 ‘고시공고번호’에서 확인 |
| source_date | `2026-02-19` / 첨부 원문 공고일. 게시물에 별도 게시일을 확인했다고 간주하지 않음 |
| 공식 URL | 위 S1 공고 게시물 |
| 첨부 URL | 위 S1 HWP 원문 |
| 첨부명 | 2026년 안산시 청년기본소득 신청일정 공고문.hwp |
| last_verified_at | `2026-10-20` / Asia/Seoul, 날짜 정밀도 |
| locator | 첨부의 ‘□ 신청개요’ → ‘○ 신청대상’, 그 아래 경기도 거주이력 문장 및 ‘☞ 거주요건’ 주석. 게시물은 제목·공고번호·첨부명 연결 확인에 사용 |

이번에 다시 받은 HWP는 **61,952 bytes**, SHA256은 `b0d9f1e9f2de6844157021cab963b2e1dedd49183550036a9777dafa1de78106`이다. M1.5 기록과 일치한다. 원문은 메모리에서 텍스트를 추출해 확인했으며 저장소에 복제하지 않았다. HWP 쪽 배치를 렌더링하지 않았으므로 쪽번호를 부여하지 않는다. 추출 순번·HTML DOM 선택자를 영구 locator로 쓰지 않는다.

### S2: 정책 안내 페이지

| 필드 | 값 |
|---|---|
| source_document_id | `ANSAN-C0001545` |
| 기관 | 안산시 / 콘텐츠 관리부서 청년정책관 청년지원팀 |
| 제목 | 청년기본소득 |
| 공고번호 | 본문에서 별도 확인되지 않음 |
| source_date | `null` / 게시일·최종 수정일 미확인. 확인일로 대체 금지 |
| 공식 URL | 위 S2 정책 안내 |
| 첨부 원문 URL | 이 조건의 근거로 사용한 별도 첨부 없음 |
| last_verified_at | `2026-10-20` / Asia/Seoul, 날짜 정밀도 |
| locator | ‘사업개요’ → ‘지급조건’의 첫 번째 항목 |

### S3: 공식 분기 안내

| 필드 | 값 |
|---|---|
| source_document_id | `ANSAN-B0238-1681390` |
| 기관 | 안산시 / 등록부서 홍보담당관, 주관부서 청년정책관 청년지원팀 |
| 제목 | 안산시, 24세 청년 대상 청년기본소득 3분기 접수 시작 |
| 공고번호 | 본문에서 별도 확인되지 않음 |
| source_date | `2026-08-31` / 게시물의 등록일 |
| 공식 URL | 위 S3 공식 3분기 안내 |
| 첨부 URL | [안내 이미지 JPG](https://www.ansan.go.kr/common/file/FileDown.do?file_id=1788138732609LBC64DZ3X7QS6729WEE7GPTSL) — 게시물 다운로드 식별자로 URL 연결만 확인. 이미지 내용은 이번 근거로 사용하지 않음 |
| last_verified_at | `2026-10-20` / 본문·첨부 링크 확인, 날짜 정밀도 |
| locator | 내용 본문 두 번째 문단, ‘3분기 지급 대상은’으로 시작하는 문장 |

**접근 기록:** 웹 도구에서 S1 게시물·HWP 접근 오류가 발생했다. 이후 읽기 전용 HTTP 접근으로 S1 게시물·HWP, S2 본문, S3 본문을 모두 다시 받아 확인했다. 따라서 이번 확인은 이전 분석이나 검색 캐시에만 의존하지 않는다. 확인일은 정책이 수정되지 않을 것이라는 보증이나 문서 발행일이 아니다.

## 5. 출처 간 일치 여부

판정: **MINOR_WORDING_DIFFERENCE** — 이번 주민등록 조건의 실질적 충돌은 발견되지 않았다.

| 출처 | 해당 위치의 의미 | 비교 |
|---|---|---|
| S1 | 대상지역을 안산시로 제시하며 거주요건 산정 기준을 신청일로 정함. 경기도 거주이력은 별도 문장에 있음 | 지역·산정일을 항목과 주석으로 나누어 표현 |
| S2 | 신청일의 안산시 주민등록을 지급조건 첫 항목으로 명시 | 주민등록 사실과 날짜를 한 항목에서 직접 표현 |
| S3 | 해당 분기 대상 설명에서 신청일의 안산시 주민등록을 명시 | S2와 같은 의미, 문장 형태만 다름 |

S1만으로 주민등록 조건의 모든 표현이 한 문장에 있다고 주장하지 않는다. S1의 대상지역·신청일 기준을 S2의 명시적 주민등록 조건과 대조하고, S3으로 재확인했다. 분기 연령 기준일을 주민등록 기준일로 합성하지 않는다.

전체 정책 자료에는 별도 검토할 차이가 있다. S1과 S2의 초본 발급 시점 안내가 다르고 S3에는 자동신청 절차 변경이 있다. 이는 이번 단일 조건의 불일치로 판정하지 않으며, 전체 정책이 동일하다는 결론도 내리지 않는다. 세부 사항은 기존 M1.5 분석의 미해결 사항을 유지한다.

## 6. 공식 조건의 의미

| 구분 | 결론 |
|---|---|
| 요구하는 사실 | 신청일 현재 주민등록상 주소의 시 단위 지역이 안산시라는 사실 |
| 생활지역·실거주지 | 이것만으로 해당 조건 충족을 입증하지 못함 |
| 기준일 | 신청일. 분기 연령 기준일이나 조회 당일로 바꾸지 않음 |
| 거주기간 | 이번 leaf의 비교값이 아님. 별도 조건으로 평가해야 함 |
| 증빙의 의미 | 입력 fact는 사용자 사실의 표현이다. source enum을 지정했다고 공적 증명서 진위가 검증되는 것은 아님 |

행정기관의 심사·서류 인정·예외 적용까지 판단하는 규칙이 아니다. 원문에 필요한 주민등록번호나 전체 주소이력을 이 단일 조건 계산을 위해 수집하지 않는다.

## 7. reference date 분석

**`ReferenceDateSource.APPLICATION_DATE`가 일치한다.** S1의 신청일 산정 주석, S2·S3의 주민등록 조건이 근거다.

바인딩 경로:

```text
ResidentRegistrationRule.reference_date_source = APPLICATION_DATE
PolicyReferenceContext.application_date
    → Resolver.reference_date
EvaluationContext.as_of
    → Resolver.evaluation_date
ResidentRegistrationFact.as_of_date
    → 주민등록 사실이 성립한다고 입력한 날짜
```

- `application_date`는 해당 정책 신청의 날짜다. 신청기간 시작일, 초본 발급일, 분기 시작일, 서버 오늘 날짜로 자동 채우지 않는다.
- context 객체가 존재하지만 날짜가 `None`이면 `UNKNOWN / RESIDENT_REFERENCE_DATE_MISSING`이다.
- context 자체가 없거나 다른 정책에 바인딩되면 호출 계약 오류다. 이를 날짜 미입력 UNKNOWN과 혼동하지 않는다.
- 미래 신청일은 현재 계약상 UNKNOWN이다. 정확히 같은 날짜의 fact가 필요하며 과거·미래 fact를 보간하지 않는다.
- **Assumption:** 이 단계에서 호출자는 어느 신청 회차를 평가하는지 정한 뒤 날짜를 명시한다. 자동신청의 효력일·소급 회차별 날짜 결정 방식은 미확정이며 이 leaf가 추론하지 않는다.

## 8. required region 분석

요구 범위는 **안산시 전체**다. 특정 구·동이나 경기도 전체로 넓히거나 좁히지 않는다. 현재 `RegionRef`의 시 단위 완전한 쌍으로 표현 가능하다.

다만 사용자 입력의 ‘안산’이 생활지역이라는 이유만으로 주민등록 fact로 바꿀 수 없다. 주민등록 지역을 별도로 질문해야 한다. 불완전한 주민등록 지역은 `Fact.region=None`으로 남긴다.

## 9. 내부 canonical 매핑

| 공식 의미 | 내부 표현 | 판단 |
|---|---|---|
| 안산시 주민등록. 안산시가 경기도에 속하는 지역 체계 | `RegionRef(sido="GYEONGGI", sigungu="ANSAN")` | 이 단일 시 지역 비교에 필요한 의미를 보존 |

namespace는 `MVP_INTERNAL_REGION_V1`이다. 문자열은 **공식 행정코드가 아닌 프로젝트 내부 key**다. 주소 파싱·행정코드 변환을 구현했다고 간주하지 않는다. `GYEONGGI`만으로 경기도 전체를 매치하는 wildcard 규칙도 아니다.

지역 구조는 현재 안산·수원·종로의 유효 쌍만 지원한다. 전국 지역 입력 수용은 별도 확장 대상이다. 안산시 내 구·동을 보관하지 않는 것은 이번 시 단위 조건의 의미 손실이 아니지만, 향후 더 세밀한 조건에는 별도 검토가 필요하다.

## 10. candidate rule 표현

아래는 **문서 안의 m1.1 leaf 후보**다. 실행 파일·production JSON·전체 정책 envelope가 아니다.

```json
{
  "kind": "rule",
  "rule_type": "resident_registration",
  "rule_id": "ANSAN_YBI_2026_RESIDENT_AT_APPLICATION",
  "required_region": {
    "sido": "GYEONGGI",
    "sigungu": "ANSAN"
  },
  "reference_date_source": "APPLICATION_DATE",
  "evidence_refs": [
    "ANSAN-2026-399-HWP#eligibility-resident-registration",
    "ANSAN-C0001545#eligibility-resident-registration",
    "ANSAN-B0238-1681390#eligibility-resident-registration"
  ]
}
```

현재 loader의 resident leaf 필수 키와 일치한다. 로딩 시 지역은 `RegionRef`, 기준일 종류는 enum, 근거 목록은 `tuple[str, ...]`로 변환된다. `rule_version`은 leaf 키가 아니며 현재 `Policy`에 속한다. source 메타데이터를 leaf에 추가하면 strict loader가 거부하므로 섞지 않는다.

후보 slice의 `rule_version`은 **`m1.8-resident-slice-draft.1` 제안**이다. 실행·운영 버전으로 발행되지 않았다. `schema_version="m1.1"`과 원문 발행일은 각각 별개다.

**현재 Policy/PolicySet은 `synthetic=True`, `test_only=True`를 강제한다.** 실제 정책을 합성 데이터라고 표시해 이 제한을 우회하지 않는다. 실제 데이터 envelope 수용은 다음 별도 설계·승인 대상이다.

## 11. policy evidence 연결

참조 형식은 `source_document_id#eligibility-resident-registration`으로 정한다. fragment는 내부 논리 locator ID이며 원격 페이지의 실제 HTML anchor라는 뜻이 아니다.

| evidence_ref의 문서 ID | logical locator가 가리키는 사람용 위치 | 역할 |
|---|---|---|
| `ANSAN-2026-399-HWP` | 신청개요의 신청대상 및 거주요건 산정 주석 | 우선 공고 근거 |
| `ANSAN-C0001545` | 사업개요 / 지급조건 첫 항목 | 주민등록 조건의 명시적 표현 |
| `ANSAN-B0238-1681390` | 3분기 지급 대상 설명 문장 | 분기 안내 교차 확인 |

문서상 연결 계약:

```text
rule_id + rule_version
  → evidence_refs tuple
  → source_document_id + logical locator ID
  → section 4의 공식 URL / attachment URL / 사람이 찾을 locator
     + source_date + last_verified_at + 확인본 fingerprint(가능한 경우)
```

현재 단계에서는 이 문서의 표가 메타데이터 매핑 역할을 한다. 향후 registry에는 최소 `source_document_id`, `official_url`, `attachment_url`, `source_date`, `last_verified_at`, `locators`를 두고, `rule_version`과 참조의 연결 버전을 기록하는 방안을 제안한다. 아직 저장 형식·새 클래스·스키마는 확정하지 않는다.

URL 변경 시 내부 ID를 유지하고 URL 이력을 남긴다. 원문 내용 변경 시 이전 확인본·검토 기록을 덮어쓰지 않고 개정 이력을 남긴 뒤 rule 재검토 여부를 결정한다. 같은 URL이나 ID라는 사실만으로 동일 내용이라고 보지 않는다.

`RuleEvaluation.evidence_refs`는 **정책 원문 근거**이고 `details.evidence`는 **선택된 사용자 fact의 출처·날짜·지역 스냅샷**이다. 후자의 `source=OFFICIAL_DATA`가 전자의 공고문 ID를 대신하지 않는다. 현재 엔진은 참조 문자열을 보존하지만 문서 존재·URL 접근·최신성·원문과 규칙의 일치까지 자동 검증하지 않는다.

## 12. current engine coverage

평가 대상은 위 단일 leaf의 의미·계산·결과 전달이다. 실제 정책 전체 운영 준비도와 구분한다.

| 항목 | 평가 | 현재 지원 / 경계 |
|---|---|---|
| ResidentRegistrationRule | SUPPORTED | 요구지역·기준일 종류·근거 참조의 불변 모델 |
| RegionRef | SUPPORTED | 이번 요구지역 안산의 완전한 내부 쌍 지원. 전국 주소체계 아님 |
| APPLICATION_DATE | SUPPORTED | 공식 조건과 의미 일치. 다른 날짜로 대체하지 않음 |
| PolicyReferenceContext | SUPPORTED | policy_id 바인딩과 명시적인 신청일/None |
| EvaluationFacts | SUPPORTED | 주민등록 fact tuple 전달, 선택·추론하지 않음 |
| ResidentRegistrationFact | SUPPORTED | 지역·해당 날짜·source, 지역/날짜 누락 표현 |
| Resolver | SUPPORTED | 정확한 날짜 비교, PASS/FAIL/UNKNOWN, 중복 처리와 충돌 오류 |
| Adapter | SUPPORTED | 상태·reason·missing_fields 및 fact 스냅샷 보존 |
| m1.1 Loader | PARTIALLY_SUPPORTED | 후보 leaf 형태 지원. **실제 정책 envelope는 synthetic/test_only 제한 때문에 지원하지 않음** |
| routing | SUPPORTED | `evaluate_policy_tree` 단일 정책 경로에서 전문 leaf를 Resolver→Adapter로 전달. 기존 배치 API가 이 경로를 지원한다고 확대 해석하지 않음 |
| RuleEvaluation | SUPPORTED | expected / evaluated_value / details / reason / 근거 참조 표현 |
| evidence_refs | PARTIALLY_SUPPORTED | 불변 문자열 tuple 전달 지원. source registry·참조 해석·freshness 검증 미구현 |

**NOT_SUPPORTED인 계산 필수 항목은 없다.** 부분 지원 두 항목은 다음 실제 데이터 수용 단계의 명시적 작업이다. 현재 엔진이 production 정책을 로드할 수 있다는 주장은 하지 않는다. 이번 조건에 새 날짜 연산자나 지역 비교 로직이 필요하다는 증거도 없다.

검토 코드: `specialized_rules/resident_registration.py`, `facts/resident_registration.py`, `evaluation_inputs.py`, `resolvers/resident_registration.py`, `adapters/resident_registration.py`, `loader.py`, `routing.py`, `result_types.py`, `models.py` — 모두 `backend/policy_engine/` 아래의 기존 파일이다.

## 13. 수동 판정 시나리오

**21개 수동 기대 결과**다. 새 자동 테스트나 실제 정책 로딩 실행 결과가 아니다. 기본값은 신청일 D=`2026-09-10`, 평가일 E=`2026-09-11`, 요구지역 안산, 올바른 정책 context, source=`SELF_REPORTED`다. 달리 적지 않은 fact는 D의 완전한 지역이다. 날짜들은 가상 평가 입력이며 현재 시스템 날짜와 무관하다.

| 번호 | 입력 차이 | 기대 결과 | reason / 오류와 근거 |
|---|---|---|---|
| 1 | D의 안산 fact | PASS | `RESIDENT_REGION_MATCH` |
| 2 | D의 수원 fact | FAIL | `RESIDENT_REGION_MISMATCH` |
| 3 | 주민등록 facts 없음 | UNKNOWN | `RESIDENT_REGISTRATION_MISSING`; missing=`resident_registration` |
| 4 | D-1의 안산 fact만 있음 | UNKNOWN | `RESIDENT_REGISTRATION_DATE_UNPROVEN`; 이전 날짜를 연장하지 않음 |
| 5 | context.application_date=None, 안산 fact 존재 | UNKNOWN | `RESIDENT_REFERENCE_DATE_MISSING`; missing=`reference_date` |
| 6 | 신청일 D > E, D의 안산 fact | UNKNOWN | `RESIDENT_REFERENCE_DATE_IN_FUTURE` |
| 7 | 동일 날짜·지역·source의 안산 fact 2개 | PASS | `RESIDENT_REGION_MATCH`; 선택 근거 중복 제거 |
| 8 | D의 안산/수원 fact 동시 존재 | Data Error | `CONFLICTING_RESIDENT_REGISTRATION_FACTS`; source로 우선순위 선택 금지 |
| 9 | UserProfile.region=ANSAN, 주민등록 facts 없음 | UNKNOWN | `RESIDENT_REGISTRATION_MISSING`; profile fallback 없음 |
| 10 | D의 안산 / SELF_REPORTED | PASS | `RESIDENT_REGION_MATCH`; 자기신고임을 근거에 보존 |
| 11 | D의 안산 / MANUALLY_VERIFIED | PASS | `RESIDENT_REGION_MATCH`; source만으로 판정 변경 없음 |
| 12 | D의 안산 / OFFICIAL_DATA | PASS | `RESIDENT_REGION_MATCH`; enum이 진위 검증을 수행하지 않음 |
| 13 | D의 fact.region=None | UNKNOWN | `RESIDENT_REGION_MISSING`; missing=`resident_registration.region` |
| 14 | 안산 fact.as_of_date=None, 정확한 날짜 fact 없음 | UNKNOWN | `RESIDENT_REGISTRATION_DATE_MISSING`; missing=`resident_registration.as_of_date` |
| 15 | D+1의 안산 fact만 있음 | UNKNOWN | `RESIDENT_REGISTRATION_DATE_UNPROVEN`; 이후 날짜를 소급하지 않음 |
| 16 | D-1의 수원 fact + D의 안산 fact | PASS | `RESIDENT_REGION_MATCH`; 다른 날짜의 이사를 충돌로 보지 않음 |
| 17 | reference_context 객체 자체가 없음 | Data Error | `ContextValidationError`; 올바른 context의 날짜 None과 다름 |
| 18 | context.policy_id가 평가 정책과 다름 | Data Error | `ContextValidationError`; 다른 신청일을 혼용하지 않음 |
| 19 | RegionRef의 sido만 있고 sigungu가 None | Data Error | `INVALID_REGION`; 부분 RegionRef는 유효하지 않음. 정보 부족은 Fact.region=None으로 표현 |
| 20 | D의 안산 fact + D-1의 안산/수원 충돌 | Data Error | `CONFLICTING_RESIDENT_REGISTRATION_FACTS`; 대상 날짜 밖 충돌도 먼저 검증 |
| 21 | application_date=None + 동일 날짜 안산/수원 충돌 | Data Error | `CONFLICTING_RESIDENT_REGISTRATION_FACTS`; 구조·충돌 검증이 UNKNOWN 판정보다 먼저 |

정보 부족 UNKNOWN은 추가 질문 대상으로 표시한다. Data Error는 데이터·호출 계약 오류로 분리하며 정상 FAIL/UNKNOWN으로 감추지 않는다. 동일 날짜 안산 fact 3개가 source만 서로 다르면 PASS이며 세 source 근거가 보존된다. 이것은 10~12번의 상태 불변 계약과 같다.

## 14. 전체 정책과의 경계

아래 항목은 이번 rule에 포함하지 않는다.

- 나이·대상 생년월일과 분기별 연령 기준일
- 경기도 연속 3년 / 합산 10년 및 해당 이력의 증명
- 외국인·거주불명·재외국민·귀화, 국적 취득 전 거주기간 등 예외·신분 조건
- 신청기간 open/closed, 접수시각, 자동신청·소급신청 및 회차 결정
- 지급금액·지급일·지역화폐 지급 방식과 서류 인정 절차

**resident leaf PASS는 전체 policy eligibility PASS가 아니다.** 이 leaf 하나만 담은 테스트용 트리가 집계상 PASS를 내더라도 전체 정책 조건을 평가했다는 뜻이 아니다. 미구현 조건을 ALL 그룹에서 빠뜨린 채 실제 전체 정책 결과로 노출해서는 안 된다.

## 15. user-facing 해석 한계

| 내부 결과 | 향후 조건별 표시 예 | 표현 한계 |
|---|---|---|
| PASS | 입력한 사실 기준으로 신청일의 안산시 주민등록 조건 확인 | ‘청년기본소득 신청 가능’, ‘수급 확정’ 금지 |
| FAIL | 입력한 사실 기준으로 신청일의 주민등록 지역이 안산시와 다름 | 전체 정책의 행정 심사 결과처럼 표시하지 않음 |
| UNKNOWN | 신청일 또는 해당 날짜의 주민등록 정보 추가 확인 필요 | 누락·다른 날짜·미래 기준일 등 reason별로 설명 |
| Data Error | 입력 데이터 또는 평가 요청을 확인해야 함 | 정책 조건 미충족으로 바꾸지 않음 |

SELF_REPORTED이면 자기신고 기준이라는 한계를 함께 표시해야 한다. 공적 서류를 검증했다고 표시하지 않는다. source별 신뢰도를 가정해 PASS/FAIL을 바꾸지 않는다. LLM은 구조화된 상태·reason·근거를 설명할 수 있지만 날짜·사실·최종 자격을 새로 만들 수 없다.

## 16. freshness/version 관리

| 필드 | 의미 / 이번 값 |
|---|---|
| source_date | 원문 공고·게시 날짜. S1=2026-02-19, S2=null, S3=2026-08-31 |
| last_verified_at | 이번 실제 재확인 날짜 2026-10-20. 날짜 정밀도·Asia/Seoul |
| schema_version | 후보 leaf 해석 계약 m1.1 |
| rule_version | `m1.8-resident-slice-draft.1` 제안. 운영 버전 미발행 |
| fingerprint | S1 HWP의 이번 수신 bytes SHA256을 4절에 기록. HTML의 메뉴·배너 변경은 조건 변경과 구분 |

재검토 트리거: **새 분기 공고·안내, 정정 공고, 정책 페이지의 대상지역·신청일·주민등록 조건 변경, 원문 첨부 교체, URL 변경·원문 접근 불가**.

재검토 시 대상 문장과 locator를 다시 대조한다. 의미가 바뀌면 새 rule_version으로 검토하고 기존 판정의 버전·출처 연결을 보존한다. 표현만 바뀌거나 URL만 바뀌면 근거 메타데이터 변경 이력을 기록하고 의미 유지 여부를 명시한다. 새 분기 안내가 게시되었다는 사실만으로 자동 유효 처리하지 않는다.

**미결정:** 확인 주기·담당자·만료 기준 및 실행 시 stale 상태 처리. 현재 엔진에는 freshness 자동 차단 기능이 없다. 이를 이번에 구현하거나 확인 날짜만으로 최신성을 보장하지 않는다.

## 17. 미해결 질문

| 항목 | 이번 조건 의미 확정의 차단 여부 | 다음 단계에서 필요한 결정 |
|---|---|---|
| 실제 정책 데이터 수용 | 의미 확정은 가능. 현재 production 로딩은 불가 | 합성·실제 자료 경계, envelope/버전 계약을 별도 설계하고 승인 |
| source registry | 계산은 가능. 근거의 자동 추적 기능은 미완성 | 저장 형식, locator 개정 이력, 참조 무결성 검증 범위 |
| 자동·소급 신청의 날짜 | 이번 명시적 신청일 비교를 막지 않음 | 해당 절차를 다룰 때 회차별 신청일 의미를 공식 자료로 재확인 |
| S2 발행일·수정이력 | 이번 명시적 문장 대조는 가능 | 확인되지 않은 날짜는 null 유지. 새 이력 확보 시 추가 |
| 원문 간 서류·절차 차이 | 이번 주민등록 leaf의 충돌 아님 | 전체 정책 확장 전 M1.5 미해결 사항 별도 해결 |
| 사용자 fact 확보·검증 | 계산 계약의 의미는 확정 가능 | 초기에는 최소 자기신고 입력을 검토. 실제 기관 연동·증빙 업로드는 승인되지 않음 |
| freshness 운영 | 이번 확인일의 근거 연결은 가능 | 주기·책임자·변경 감지와 사용 중단 기준 결정 |

Assumption은 7절의 명시적 회차·신청일 제공에 한정한다. 나머지 미결정 운영 사항을 구현 완료로 간주하지 않는다.

## 18. 최종 판단

**READY_TO_ENCODE_REAL_RESIDENT_RULE**

1. 공고 원문을 재확인했고, 공식 정책 페이지와 분기 안내는 주민등록 지역·신청일 기준에 같은 의미를 제시한다. 판정은 MINOR_WORDING_DIFFERENCE다.
2. 조건 의미는 `required_region=GYEONGGI/ANSAN`, `reference_date_source=APPLICATION_DATE`로 표현할 수 있다. 기존 Resolver·Adapter·routing의 의미 변경은 필요하지 않다.
3. source locator와 stable evidence 참조를 연결했고 수동 기대 결과 21개를 기록했다. 전체 정책 자격과는 분리한다.
4. m1.1 loader의 실제 데이터 제한과 근거 registry 부재는 남아 있다. 이 판단은 **의미를 보존한 단일 rule 인코딩 설계 준비**에 한정하며 실제 데이터 수용 완료를 뜻하지 않는다.
5. 기존 전체 테스트는 **702 passed**다. 이번 산출물은 이 문서 1개이며 기존 엔진·테스트·합성 JSON을 변경하지 않았다. 실제 정책 JSON을 생성하지 않았다.

**다음 가장 작은 작업 1개:** 실제 주민등록 leaf 한 개의 수용을 위한 **production 데이터 envelope와 source metadata 연결 계약을 문서로 설계**한다. 기존 합성 데이터 제한의 유지·분리 방식과 strict validation 범위를 먼저 명시하며, 이 작업에서도 엔진 변경·실제 정책 JSON 생성을 시작하지 않는다.

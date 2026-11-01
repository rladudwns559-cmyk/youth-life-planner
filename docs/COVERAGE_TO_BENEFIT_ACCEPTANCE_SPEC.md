# Coverage에서 Benefit Acceptance로 연결하는 계약 — M2.41

작성일: **2026-10-22 / Asia/Seoul**. **문서 전용**. 최종 판단: **READY_FOR_BENEFIT_SNAPSHOT_DESIGN**.

이번 산출물은 이 문서 한 개다. 아래 Acceptance/Benefit/평가 결과/API는 후속 설계 후보이며 구현된 타입이 아니다. 동결된 Coverage, 기존 코드·테스트·명세·실제 releases를 변경하지 않는다. 실제 안산 Acceptance·CoverageResult·Review·혜택 금액을 만들지 않는다.

## 1. 목적과 재검토 기준

고정된 범위의 자격조건 구현·검토가 완결됐다는 사실과, 그 확인본의 특정 혜택 정의를 서비스 시뮬레이션에서 사용하도록 검토했다는 사실 사이의 계약을 정한다. 수용 기록 발급, 현재 사용 가능성, 개인별 월 현금 반영을 분리한다.

| 다시 확인한 자료 | 이번 판단에 사용한 계약 |
|---|---|
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | FULL/SLICE, 공개 API, 지문·검토 의미 동결, legacy 연결·실제 정책별 미완료 |
| ELIGIBILITY_COVERAGE_RESULT_SPEC.md 36~37절 | 저장8필드/파생 status, 공식 public 생성 경로, current baseline, 감사 한계 |
| COVERAGE_INTEGRATION_GATE_SPEC.md 39~40절 | findings의 현재 지문·검토 결과, 순서·오류/정상 미완료 구별 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md 전체27절 | M2.4의 정의·상태·버전·accepted_terms·기한·근거·개인/월 적용 경계 |
| CASHFLOW_BENEFIT_BRIDGE_SPEC.md 전체26절 | M2.3의 후보·stable ID·중복·현금 유형·합산·제외 계약 |
| POLICY_COVERAGE_SPEC.md, 특히20·24절 | accepted_scope/inventory_version 보완, legacy source 연결 한계 |
| POLICY_DATA_ENVELOPE_SPEC.md | 기존 Policy verification, source/review/freshness 및 immutable release 의무 |
| DATA_MODEL.md / ARCHITECTURE.md | 독립 Cashflow와 실제 Coverage 구현 상태·의존 경계 |
| 현재 backend 코드 / 실제 releases 001·002 | 실제 타입·필드·미구현 Acceptance/Bridge·DRAFT/slice 상태 |

현재 `EligibilityCoverageStatus`와 legacy `EvaluationScope`는 서로 다른 Enum이다. 전자는 FULL_POLICY/CONDITION_SLICE, 후자는 여전히 CONDITION_SLICE 하나다. `PolicyEnvelope.verification_status`의 실제 타입은 `PolicyVerificationStatus`이며 DRAFT/VERIFIED/STALE이다. `PolicyLifecycleStatus.ACTIVE/ENDED`나 source의 `VerificationStatus`로 대체하지 않는다.

`BenefitCandidate`, `PolicyBenefitAcceptance`, 혜택 정의 snapshot 및 Bridge 실행 코드는 현재 backend에 없다. 이름이 비슷한 기존 acceptance 테스트를 Benefit Acceptance 구현으로 해석하지 않는다. Cashflow 모델·계산기만 독립적으로 구현되어 있다.

계약 우선순위: 동결 Coverage 계약 → 이 문서의 명시적 후속 경계 → M2.4 및 M2.3의 유지 조항. 과거 문서의 당시 미구현 설명은 역사 기록으로 남긴다. 이번에 재정의하는 것은 Acceptance 연결 계약이며 Coverage 의미가 아니다.

## 2. FULL Coverage와 Acceptance의 관계

FULL_POLICY는 **해당 policy_id/scope의 eligibility representation·implementation·review coverage**가 현재 고정 baseline에서 완결됐다는 뜻이다. 공식 의미와 사람의 검토 진실성은 여전히 외부 전제다. FULL은 Acceptance의 필요조건이며 충분조건이 아니다.

| 현재 Coverage | 새 ACCEPTED 발급 | 과거 기록 보존 | 현재 사용 |
|---|---|---|---|
| FULL_POLICY | verification·혜택·근거·snapshot·기한 검토까지 완료한 경우만 | 가능 | 다른 gate도 모두 통과해야 가능 |
| CONDITION_SLICE | 금지 | 기존 불변 기록은 보존 | 정상 unusable |
| Coverage Data Error | 금지 | 오류와 별개로 보존 | 정상 결과 없이 오류 전파 |

정상 MISSING/STALE·missing 조건은 SLICE를 만든다. Acceptance가 누락 조건을 PASS로 채우거나 review를 MATCHED로 고치지 않는다. 이후 FULL→SLICE가 되어도 과거 ACCEPTED record 자체를 REVOKED로 변이시키지 않는다.

## 3. Acceptance의 의미와 비의미

**Acceptance는 정확한 정책·scope·Coverage 확인본과 특정 혜택 정의를 서비스의 시뮬레이션에서 사용할 수준으로 검토했다는 불변 기록이다.** 사용자 표시 문구는 M2.4의 “시뮬레이션 반영 검토 완료”를 유지한다.

행정기관의 신청/지급 승인, 수급 보장, 입금 사실, 특정 사용자 PASS, 모든 월의 적용, 자유 현금 분류, production 배포 승인을 뜻하지 않는다. `SIMULATION_ACCEPTED`라는 개념과 record의 `ACCEPTED` 상태를 혼동해 새 정책 자격 상태로 추가하지 않는다.

수용된 분기 지역화폐 정의도 설명·시뮬레이션 자료로 검토될 수 있지만 현행 직접 월 현금 Bridge에서는 제외된다. Acceptance evaluator가 돈을 합산하거나 지급주기를 월로 환산하지 않는다.

## 4. Target identity

| 차원 | 제안 identity | 역할 |
|---|---|---|
| 안정 혜택 계보 | `(policy_id, benefit_id)` | M2.3의 stable benefit identity·중복 방지 유지 |
| 수용 대상 | `(policy_id, scope, benefit_id)` | 적용 회차/연도까지 고정 |
| 수용 기록 | `(policy_id, scope, benefit_id, acceptance_version)` | 불변 검토/철회 revision 식별 |
| 검토 대상 내용 | Coverage binding + Benefit snapshot binding | 그 대상의 정확한 정의·자료·구현 확인본 |

scope는 기존 `ApplicabilityScope(edition_id, quarter)` 값 그대로 사용한다. edition_id를 별도 저장하면 scope.edition_id와 중복되므로 record의 canonical identity는 scope에 한 번만 둔다. 외부 표시에 edition이 필요하면 파생한다. M2.4의 edition-only identity는 scope를 포함하도록 보완한다.

현재 대상의 policy_id 또는 benefit_id와 다른 record를 직접 전달하면 잘못된 대상 연결이므로 Data Error다. 동일 계보의 올바른 과거 scope record를 비교하는 경우는5절의 정상 snapshot 변경이다. ID의 자동 strip·대소문자 변환·표시명 매칭은 없다.

## 5. Scope binding과 과거 ref의 구별

2026/Q3, 2026/Q4, 2026/annual, 2027/Q3는 서로 다른 수용 대상이다. Q3 FULL/Acceptance를 다른 범위에 자동 승계하지 않는다. scope는 target_month나 시스템 날짜에서 추론하지 않는다.

이번 단일 대상 evaluator는 **같은 policy/benefit 계보의 과거 record와 현재 scope를 비교할 수 있다**. 기록이 정직하게 자신의 Q3 identity를 가진 상태에서 현재 Q4와 비교되면 정상 `COVERAGE_SNAPSHOT_CHANGED`이며 사용할 수 없다. 이는 잘못된 명시 참조와 다르다.

외부 ref가 Q4/a0001이라고 선언했는데 실제 resolve된 record가 Q3/a0001이면 broken/wrong-target reference Data Error다. ref=None은 정상 미수용, 명시 ref가 있으나 record가 없으면 Data Error다. 순수 evaluator는 resolved record 또는 None만 받으며 ref 조회는 외부 책임이다.

M2.4의 “새 edition에 과거 ref를 연결하면 오류”는 **ref가 선언한 identity와 resolve된 record의 일치 검사**로 유지한다. 정상적인 역사 record 대 현재 scope 비교까지 오류로 만들던 해석은 이 절로 대체한다. 현재 범위에 맞는 record가 없으면 실서비스 준비 계층은 원칙적으로 None을 공급한다.

## 6. Coverage snapshot binding과 identity matrix

record에는 아래 현재 값을 승인 당시의 scalar/value snapshot으로 고정한다. 이름·의미는 CoverageResult를 재사용하고 별도 승인용 Coverage 상태 Enum을 만들지 않는다.

| 항목 | Acceptance binds? | 변경 시 무효화/오류 | 이유 |
|---|---|---|---|
| policy_id | 예 | 다른 대상 직접 연결은 Data Error | 잘못된 정책 승인 차단 |
| scope | 예 | 정상 변경은 unusable | 회차·연도 자동 승계 금지 |
| inventory_version | 예 | 정상 변경은 unusable | 조건 목록 확인본 변경 |
| inventory_fingerprint | 예, findings에서 추출 | 같은 Inventory identity/version에서 다르면 Data Error | immutable 목록 내용 보호 |
| rule_version | 예 | 정상 변경은 unusable | 규칙 확인본 변경 |
| policy_tree_fingerprint | 예, findings에서 추출 | 같은 policy/rule version에서 다르면 Data Error | 트리·근거 순서까지 현재 동결 지문 의미 유지 |
| dataset_version | 예, 발급 시 필수 | 정상 변경은 unusable | 선택 release 고정 |
| source_registry_fingerprint | 예, 발급 시 필수 | 같은 dataset에서 다르면 Data Error | registry 내용의 무단 교체 차단 |
| implementation_fingerprint | 예, 발급 시 필수 | 다른 값은 정상 unusable | 별도 구현 version 없이 artifact 교체 판별 |
| benefit_id | 예 | 다른 대상 직접 연결은 Data Error | component별 수용 |
| benefit definition version/fingerprint | 예, 후속 명세 필요 | 정상 새 version은 unusable, 같은 identity/version의 다른 내용은 Data Error | 혜택 정의의 변경/모순 구별 |

Coverage binding은 policy_id, scope, inventory_version, inventory_fingerprint, rule_version, policy_tree_fingerprint, dataset_version, source_registry_fingerprint, implementation_fingerprint의 **9개 값**이다. status는 중복 저장하지 않는다. 발급 시 FULL을 확인했다는 사실·당시 검토 refs/artifacts는 실제 acceptance review artifact에 연결한다.

guard의 비교 domain은 정확해야 한다. Inventory의 같은 identity는 `(policy_id, scope, inventory_version)`, Tree는 `(policy_id, rule_version)`, Registry는 고정 dataset이다. 다른 scope에 같은 i0001이 있다는 이유로 Inventory 충돌로 판정하지 않는다. 다만 scope가 달라도 policy/rule version이 같고 Tree 지문이 다르면 독립 Tree 모순은 오류다.

버전 변경은 **그 비교 쌍**만 내용 동등성 의무에서 면제한다. rule_version 변경이 같은 Inventory version의 다른 지문을 숨기지 않는다. dataset 변경도 같은 rule version의 Tree 모순을 숨기지 않는다. implementation 변경·만료·SLICE·REVOKED도 독립 모순을 정상 stale로 낮추지 않는다.

현재 Coverage gate가 새 Review들에 대해 성공했어도 과거 Acceptance에 묶인 같은 version의 지문이 다를 수 있다. 따라서 Acceptance 연결 시 이 cross-record guard가 별도로 필요하다. frozen Review matcher의 코드를 바꾸는 작업이 아니다.

## 7. CoverageResult 사용 방식

**현재 `EligibilityCoverageResult`는 evaluator의 명시 입력으로 받고, record에는6절의 identity snapshot만 저장하는 방향을 선택한다.** Result 전체의 영속 포함은 채택하지 않는다. 별도 Coverage wrapper 모델도 이번에 확정하지 않는다.

| 방안 | 비교 | 판단 |
|---|---|---|
| Result 전체 저장 | 당시 findings를 쉽게 볼 수 있으나 private findings 구조에 영속 수용 모델이 결합됨 | 미채택 |
| scalar/value identity + 외부 불변 review artifact | 현재 Result와 정확히 대조하고 수용 모델의 책임을 제한할 수 있음 | 채택 방향 |
| FULL bool만 저장 | 대상·내용·구현/자료 변경을 판별할 수 없음 | 금지 |

Result 전체를 저장해도 과거 선택 Review의 원본·artifact bytes·source 내용을 모두 보존한 archive가 되지 않는다. subtree 지문·condition/root/ref 목록·검토 자료는 원래 Coverage 자료와 acceptance review artifact에서 추적하고 runtime record에 중복 복제하지 않는다.

현재 값은 공식 `evaluate_eligibility_coverage()` 경로의 결과여야 한다. private findings/factory/sentinel을 Acceptance 코드가 import해 FULL을 만들지 않는다. 필요한 지문은 Result.findings의 기존 값으로 읽으며 Coverage를 재판정하지 않는다. frozen Result의8필드·9key serializer·일반 생성 제한을 유지한다.

## 8. Policy Verification 축과 실제 기존 모델

**현재 `PolicyEnvelope` 전체를 verification 입력으로 사용하는 방향을 추천한다.** 독립 status 문자열이나 새로운 VerificationResult를 발명하지 않는다. Envelope에는 policy_id/rule_version을 제공하는 Policy, edition_id, dataset_version, source_bindings, verification_status, last_verified_at, lifecycle_status와 효력일이 이미 있다.

현재 Coverage와 현재 Envelope는 policy_id·scope.edition_id·rule_version·present dataset_version이 일치해야 한다. 현재 입력끼리의 불일치는 과거 Acceptance stale가 아니라 Data Error다. 외부 준비 계층은 동일 Policy 트리의 기존 Tree 지문과 Result의 Tree 지문까지 대응시키며 버전 문자열만 일치시켜 다른 트리를 결합하지 않는다.

Envelope의 `PolicyVerificationStatus.VERIFIED`는 필수다. DRAFT/STALE이면 정상 unusable이다. source/locator의 VERIFIED나 lifecycle ACTIVE는 이 gate를 대신하지 않는다. 현행 Envelope.evaluation_scope를 FULL로 바꾸거나 이를 새 Coverage status의 근거로 삼지 않는다. **eligibility 완결성은 새 Result, 정책 metadata 검토는 기존 Envelope**가 공급한다.

VERIFIED 선언만으로 source freshness·검토 진실성이 증명되지 않는다. 기존 고정 source의 ACTIVE/VERIFIED·locator 적용 대상·명시적 data_use_date·manifest.freshness_max_age_days·실제 review 검토 의무를 유지한다. Acceptance valid_until은 이 의무를 대신하지 않는다. 정책 source 사용요건이 실패하면 `POLICY_NOT_VERIFIED`라는 사용 불가 사유를 반환하며 원래 Envelope Enum 값을 변이시키지 않는다.

기존 `validate_envelope_sources`와 `validate_dataset_manifest`는 메모리 참조/내용 정합성 검사다. source freshness·실제 승인·파일 bytes 검증이 구현됐다고 해석하지 않는다. 자료 준비의 artifact bytes 확인은 외부, 명시 입력의 날짜·상태/버전 대조는 향후 pure gate 책임이다. 기존 legacy→FULL release 연결은 별도 미완료이며 이번에는 해결하지 않는다.

## 9. Benefit metadata 축

자격조건의 Coverage FULL·정책 VERIFIED·혜택 metadata 검토는 독립이다. FULL이어도 금액·주기·수단·제한·적용 월·근거 검토가 끝나지 않았다면 발급/사용 불가다. 정책 Tree 지문은 benefit metadata를 포함하지 않는다.

M2.4의 첫 지원 범위는 **한 회 고정 금액과 열거 가능한 공통 적용월**이다. 확정된 정확한 int≥0만 ACCEPTED 대상이다. 상한액·범위·소득별 미계산액·개인 일정이 필요한 정의를 임의 고정액으로 바꾸지 않는다. 현재 미검토 정의/미확정 금액은 정상 미수용이며 잘못된 타입·음수는 Data Error다.

분기/지역화폐/바우처/저축 매칭도 metadata 자체를 검토할 수 있다. 해당 정의가 정확히 검토됐는지를 판단할 뿐, Acceptance에서 MONTHLY/UNRESTRICTED_CASH만 허용하는 필터를 넣지 않는다. 그 필터는 Bridge 책임이다.

## 10. Acceptance status

M2.4의 **기록 없음 + ACCEPTED/REVOKED**를 유지한다. 검토 중/거절은 승인 record를 발급하지 않는다. PENDING/REJECTED/EXPIRED/STALE을 record status에 추가하지 않는다.

ACCEPTED는 과거 검토 행위의 상태다. 현재 사용 가능성은 별도 평가한다. 따라서 `record.status == ACCEPTED`와 `evaluation.usable`은 같지 않다. REVOKED는 정상 unusable이며 존재하는 합법적 역사 기록이다. absent도 오류 상태가 아니다.

## 11. Acceptance version

`acceptance_version`은 기존 a0001부터의 명시적 양의 버전 방향을 유지한다. 수용 대상 `(policy_id, scope, benefit_id)` 안의 기록 revision이며 rule/dataset/benefit version의 별칭이 아니다. 시스템 날짜·파일명·최댓값 검색으로 자동 생성하거나 최신 revision을 고르지 않는다.

검토 기간 연장·정의/자료 재수용·철회·재승인에는 새 revision과 실제 review_ref를 사용한다. 같은 acceptance identity의 다른 내용은 불변 기록 충돌이다. 동일 입력 하나만으로 과거 overwrite를 발견할 수는 없으므로 이력 대조는 외부 발급/선택 책임이다.

## 12. Expiry와 revocation

날짜명은 M2.4와 같은 **`data_use_date`**로 통일한다. 예시의 use_date와 동의어지만 API에 두 이름을 동시에 두지 않는다. `reviewed_at <= data_use_date <= valid_until` 양끝 포함이다. 세 날짜는 명시적인 exact date이며 현재 시각으로 기본값을 채우지 않는다.

| 경우 | 현재 사용 |
|---|---|
| data_use_date < reviewed_at | 정상 불가: ACCEPTANCE_NOT_YET_VALID |
| reviewed_at 또는 valid_until과 같음 | 해당 날짜 gate 통과 |
| data_use_date > valid_until | 정상 불가: ACCEPTANCE_EXPIRED |
| valid_until < reviewed_at / datetime 등 잘못된 타입 | Data Error |
| 선택 record=REVOKED | 정상 불가: ACCEPTANCE_REVOKED |

valid_until의 기본 일수·무기한 기본값은 없다. 정책 source freshness의 기존 명시 기준과 Acceptance 기한을 별개로 확인한다. target_month는 예산 대상 월이며 data_use_date에서 파생하지 않는다.

철회는 같은 대상의 새 acceptance_version REVOKED 기록으로 남긴다. 과거 ACCEPTED를 수정/삭제하지 않는다. 외부가 현재 사용할 승인/철회 revision을 완전하게 선택하며 evaluator는 registry/history를 검색하지 않는다. 철회 기록을 누락하고 옛 ACCEPTED만 공급한 입력으로는 순수 함수가 철회를 발견할 수 없다. 과거 재현과 현재 서비스 사용은 외부 호출 목적에서 구별한다.

## 13. Benefit snapshot identity와 최소 정의 필드

현재 혜택 정의와 과거 승인 정의를 구별하려면 **현재 Benefit definition snapshot**이 필요하다. M2.3의 CashflowBenefitCandidate는 사용자/월 applicability와 eligibility를 가진 runtime 후보이므로 그 객체를 정책 정의로 그대로 재사용하지 않는다.

아래는 다음 문서에서 exact 타입·필수성·serializer를 확정할 최소 설계 입력이다. 지금 클래스를 생성하거나 version 문법을 임의 확정하지 않는다.

| 후보 필드/값 | 의미 |
|---|---|
| policy_id / scope / benefit_id | 안정 계보와 특정 범위 |
| benefit_definition_version | 해당 `(policy_id, scope, benefit_id)`의 명시적 불변 정의 버전 |
| amount_krw | 지급 한 회의 고정 원 단위 금액; 미확정 정의는 수용 대상에서 제외 |
| payment_cadence | M2.3 주기 분류 유지; 월 환산 금지 |
| benefit_medium | M2.3 경제유형 포함 분류 유지 |
| restriction | 수단 분류가 나타내는 사용처/목적/저축·인출 제한의 검토 내용 |
| applicable_months | M2.4의 정렬·중복 없는 유효 YYYY-MM tuple; 임의 일정 생성 금지 |
| benefit_evidence_refs / source_bindings | 혜택 의미 근거와 정확한 document version |
| benefit_definition_fingerprint | 위 내용·대상을 고정할 지문; 아직 계산 계약 없음 |
| 검토 참조·검토일 연결 | 해당 정의/근거를 검토한 실제 불변 기록 추적; 구조만으로 검토 사실 인증 안 됨 |

수용 record는 현재 정의를 참조하는 live object가 아니라, 승인한 version/fingerprint와 사람이 읽을 `accepted_terms`를 고정한다. 기존 accepted_terms를 지문 하나로 대체해 의미를 감추지 않는다. restriction은 새 bool들을 Bridge candidate에 복제하는 것이 아니라 정의 검토에서 누락을 막기 위한 항목이다. 최소 표현이 기존 medium과 근거 설명으로 충분한지, 별도 제한 값이 필요한지는 다음 snapshot 설계에서 결정한다.

초기에는 검토 완료 여부를 새 workflow로 만들지 않는다. 미검토 정의는 명시적 검토 연결 부재 등으로 표시하고 `BENEFIT_METADATA_NOT_REVIEWED`로 사용 불가다. 선언한 ref가 해석되지 않는 것은 정상 미검토와 달리 Data Error다. 실제 review의 요구 항목은 M2.4 15절을 유지한다.

## 14. Benefit fingerprint 필요성과 선행 설계

| 대안 | 충분한 점 | 부족한 점 | 선택 |
|---|---|---|---|
| M2.4 accepted_terms 직접 equality만 | 금액/주기/수단/월/근거 값 비교 가능 | 명시적 현재 정의 version이 없어 정상 개정과 같은 버전 모순을 구별하기 어려움 | 단독 사용 안 함 |
| 명시 version + 전체 정의 equality | 작은 순수 값 비교만으로 변경/모순 구별 가능 | 영속 검토 artifact와 다른 호출 사이에 같은 payload 경계가 필요 | 유효한 최소 대안 |
| 명시 version + 명시 payload fingerprint + accepted_terms | 기존 immutable snapshot 비교 방식과 일관되고 검토 artifact 연결이 명료 | payload·정렬·evidence/restriction 포함 범위·golden 계약이 선행되어야 함 | 추천 방향 |

지문을 쓰는 이유는 equality가 불가능해서가 아니다. **누가 무엇을 고정했는지 같은 내용 계약으로 비교하기 위해서**다. 현재 benefit 모델/내용 payload가 없으므로 해시 유틸부터 추가하지 않는다. Coverage Tree 지문, Registry 지문, source bytes hash를 Benefit 지문처럼 쓰지 않는다.

다음 단계에서 Benefit snapshot의 필드·version namespace·source/evidence 포함 범위·검토 metadata 제외 여부·canonical bytes·strict encoding·golden을 문서로 결정한다. 기존 Coverage의3개 schema·GV01~GV15를 복제/변경하거나 확장하지 않는다. Benefit fingerprint 역시 공식성·의미·검토 사실을 인증하는 서명이 아니다.

이 선행 계약이 없으므로 지금 `READY_TO_IMPLEMENT_BENEFIT_ACCEPTANCE_MODEL`이라고 판단하지 않는다. 최종 선택은 **READY_FOR_BENEFIT_SNAPSHOT_DESIGN**이다. 이는 Benefit fingerprint 계약이 아직 필요하다는 사실을 포함한다.

## 15. Evidence와 source binding

정책 근거와 혜택 근거의 검토 범위는 합집합이지만 저장 위치는 구별한다. 정책 leaf 근거는 기존 Envelope bindings, Benefit 근거는 별도 snapshot bindings에 둔다. **혜택 전용 source를 legacy Envelope.source_bindings에 넣지 않는다.** 현행 생성자는 그 집합이 leaf 근거의 source ID와 정확히 같아야 하기 때문이다.

두 묶음의 같은 source ID가 서로 다른 document_version을 주장하면 current input 모순이다. 외부가 선택한 고정 Registry/Manifest의 source_versions와 연결하고, 모든 혜택 ref의 locator 존재·policy 적용·ACTIVE/VERIFIED·날짜/신선도를 확인한다. ref 문자열과 공식 URL이 존재한다는 사실만으로 검토 완료로 보지 않는다.

Acceptance artifact에는 정책·혜택 source binding 합집합, Coverage9개 값, Benefit version/fingerprint/accepted_terms, 실제 검토 refs·수동 사례·발급/철회 사유를 연결한다. runtime record에 긴 원문·전체 source 객체·검토자 실명·사용자 facts를 복사하지 않는다.

정상 document version 갱신은 자동 승계하지 않는다. policy source 변경은 새 dataset/Registry 결합으로 수용 불가, benefit source/refs 변경은 Benefit 정의의 새 version·재검토로 이어져야 한다. 같은 Benefit version에서 근거 내용이 바뀌면 정의 모순이다. dataset이 달라진 경우 Registry guard만 면제될 뿐, 같은 source ID/version 내용 overwrite를 허용하는 것은 아니다. 그 이력 검증은 불변 원본을 가진 외부 발행 감사 책임이다.

## 16. 현재 Acceptance 사용 가능성 평가

발급과 평가를 구별한다. **발급**은 외부의 실제 근거·교차 검토 행위이며 이 pure 함수가 새 ACCEPTED record를 생성하지 않는다. **평가**는 현재 명시 입력과 선택된 과거 record를 대조한다.

제안 순서:

1. 입력 타입/필수 구조·현재 대상 일관성·선택 record/ref 정합성을 검사한다.
2. 현재 Envelope/Registry/Manifest/Benefit/Coverage가 같은 고정 자료라는 결합을 확인한다. 외부 준비에서 이미 계산한 지문/검증 결과를 임의 bool로 바꾸어 신뢰하지 않는다.
3. record가 있으면6절의 독립 guarded comparisons를 모두 검사한다. 다른 정상 실패가 있어도 같은 version의 내용 모순을 숨기지 않는다. 해당 guard의 version domain이 다를 때만 비교를 면제한다.
4. 정상 gate: 현재 FULL, 정책 verification/source 사용요건, Benefit metadata 검토·source 사용요건, record 존재·ACCEPTED, 기한, Coverage/Benefit snapshot 정확한 일치를 모두 확인한다.
5. 정상 실패 사유를18절 순서의 중복 없는 tuple로 반환한다. 사유가 없을 때만 usable이다. 사용자 PASS/개인 적용/target_month/현금 유형/합산은 수행하지 않는다.

SLICE의 baseline이 모두 None인 것은 유효한 현재 결과다. 이를 “Acceptance identity 누락” 오류로 만들지 않는다. **record의** 승인 binding은 항상 완전해야 하며, current None baseline과 비교할 때 unknown을 old 값으로 채우지 않는다. 비교 가능한 Inventory/Tree guard는 계속 검사하고 baseline 부재는 COVERAGE_NOT_FULL로 추적한다. present 값의 실제 변경이 있을 때만 해당 snapshot change 사유를 추가한다.

M2.4처럼 REVOKED면 lifecycle 사유는 ACCEPTANCE_REVOKED 하나로 충분하다. 정상 만료/아직 유효 전 사유는 중복 부여하지 않는다. 다만 독립 Coverage/Benefit 변경·정책/혜택 미검토 사유와 Data Error 검사까지 생략하지 않는다. ACCEPTED record가 오래되고 만료됐으면 변경·만료 이유 둘 다 보존한다.

## 17. 정상 unusable과 Data Error

| 정상 unusable | Data Error |
|---|---|
| record 없음 / 미발급 | 잘못된 타입·ID·상태·날짜 구간·음수·불완전한 record binding |
| 현재 SLICE / review MISSING·STALE | Coverage public gate 자체의 오류; SLICE로 catch 금지 |
| 정책 DRAFT/STALE·정상 freshness 사용요건 실패 | current Envelope/Coverage/Manifest/Registry 대상·버전·내용 모순 |
| Benefit 미검토·미확정 정의 | 명시 evidence/review/ref가 깨짐·다른 정책 근거 연결 |
| 선택 record REVOKED·기한 전/후 | record가 다른 policy_id/benefit_id의 승인 |
| 같은 계보의 정상 scope/version/artifact 변경 | 동일 version domain에서 서로 다른 내용 지문/accepted_terms |
| 현재 범위 record가 없어 None | ref가 선언한 scope/version과 resolve된 record 불일치 |

Data Error면 부분 usable 결과·Bridge 합계·임의 0원 정상 결과를 반환하지 않는다. 오류는 소득·개인정보를 메시지에 넣지 않는다. Coverage 오류는 frozen 예외 그대로 전달하며 Acceptance 전용 오류 타입/code의 정확한 구현은 다음 모델 설계에서 결정한다. 새 Coverage 오류/상태를 만들지 않는다.

## 18. 최소 reasons와 Bridge 사유 대응

아래 이름은 **문서 후보**이며 Enum 구현이 아니다. bool만 반환하면 철회/만료/버전/검토 원인을 잃으므로 typed reasons를 선택한다. Data Error는 reason tuple에 넣지 않는다.

| 고정 순서 / 후보 reason | 의미 | 기존 Bridge reason으로 대응 |
|---|---|---|
| 1 NO_ACCEPTANCE | record 없음 | SIMULATION_NOT_ACCEPTED |
| 2 ACCEPTANCE_REVOKED | 선택 revision 철회 | SIMULATION_NOT_ACCEPTED |
| 3 ACCEPTANCE_NOT_YET_VALID | 명시 사용일이 검토일 이전 | SIMULATION_NOT_ACCEPTED |
| 4 ACCEPTANCE_EXPIRED | 사용기한 초과 | ACCEPTANCE_EXPIRED |
| 5 COVERAGE_NOT_FULL | 현재 정상 SLICE | POLICY_NOT_FULLY_EVALUATED |
| 6 POLICY_NOT_VERIFIED | 기존 정책 검토/근거 사용요건 미충족 | POLICY_NOT_VERIFIED |
| 7 BENEFIT_METADATA_NOT_REVIEWED | 혜택 정의/근거 검토 사용요건 미충족 | SIMULATION_NOT_ACCEPTED |
| 8 COVERAGE_SNAPSHOT_CHANGED | 현재 scope/inventory/rule/dataset/registry/implementation의 정상 변경 | ACCEPTANCE_VERSION_MISMATCH |
| 9 BENEFIT_SNAPSHOT_CHANGED | 현재 혜택 정의 version/근거의 정상 변경 | ACCEPTANCE_VERSION_MISMATCH |

reasons 순서는 Acceptance 내부 순서다. Bridge는 매핑 후 중복을 제거하고 **M2.4 23절의 기존 Bridge 순서**로 출력한다. details에는 변경된 값의 필드명과 필요한 작은 identity snapshot을 보존할 수 있으나 raw 문서/사용자 정보를 넣지 않는다. 새로운 Bridge exclusion code를 임의 추가하지 않는다.

source freshness 실패를 설명할 때 원래 Envelope가 VERIFIED라는 저장 사실을 지우지 않는다. POLICY_NOT_VERIFIED는 현재 사용요건 실패라는 사유이며 새 Verification Enum 값이 아니다. 혜택 source 쪽 실패는 BENEFIT_METADATA_NOT_REVIEWED로 구별해 보존한다.

## 19. Benefit Bridge 입력과 책임

**raw Acceptance record collection을 Bridge에 공급하던 M2.4 19~20절 대신, 현재 평가한 작은 Acceptance 결과를 해당 BenefitCandidate와 결합하는 방향을 선택한다.** Bridge는 record resolve·Coverage/Benefit version matching·수용 expiry·철회를 다시 판단하지 않는다.

결과는 usable bool만 넘기지 않는다. 현재 policy/scope/benefit, Coverage binding, Benefit version/fingerprint, 명시 data_use_date, 선택 acceptance identity 또는 None, typed reasons가 현재 후보와 대응해야 한다. Bridge가 다른 후보/날짜/확인본의 결과를 섞었는지 검사하는 것은 **입력 결합 검사**이며 Acceptance 재평가가 아니다.

Bridge의 기존 책임은 유지한다: batch 구조/정책 edition·snapshot 일관성, stable identity 중복 거부, 사용자 FULL 범위 PASS와 개인/월 applicability, 적용월 목록, 원래 cadence/medium, 고정 int 금액, 정렬·제외·합산이다. 같은 정책 component별 Acceptance가 서로 달라도 가능하다. verification/coverage/개인 판정의 정책 단위 값은 동일 확인본이어야 한다.

BridgeContext는 target_month/data_use_date/assessment_ref를 유지하되 raw acceptances tuple·acceptance_ref resolution은 Acceptance 앞단으로 이동한다. Bridge에는 record history 대신 후보별 evaluated result를 전달한다. 결과 결합 형태의 exact 필드는 후속 AcceptanceResult/Bridge 모델 단계에서 확정한다. 아직 새 Context/후보를 구현하지 않는다.

원본 결과의 정상 실패를 Bridge 이유로 매핑해 전체 이유를 남긴다. 구조/대상 모순은 전체 실패다. 동일 혜택 반복은 usable 여부와 관계없이 기존 stable dedupe 오류다. 현재 지원 유형·정렬·0원 applied·부분 합계 금지 계약을 바꾸지 않는다.

## 20. Cashflow 경계

향후 흐름은 고정 데이터 준비 → Coverage 공식 평가 → Acceptance 현재 평가 → 개인/월 정규화와 Benefit Bridge → 명시 int → 새 CashflowInput → 기존 calculate_cashflow다. 발급/검토는 이 runtime 흐름과 별개다.

Cashflow는 `monthly_policy_cash_benefit`에 공급된 정확한 월 int의 산술만 담당한다. Acceptance/Policy/Bridge를 import하거나 승인 여부·금융 자격을 검사하지 않는다. `monthly_income`에 이미 포함된 지급을 중복 반영하지 않도록 개인 정규화가 확인해야 한다.

이번에는 아무 연결도 구현하지 않으며 CashflowInput/Result·계산식·기본 혜택값0을 변경하지 않는다. 현재 실제 정책으로부터 자동 양수 금액을 만드는 경로는 없다. 가상 양수 산술 테스트는 실제 정책 승인이 아니다.

## 21. 사용자 eligibility와 개인 적용 경계

Coverage FULL과 Benefit Acceptance 모두 특정 사용자 PASS를 뜻하지 않는다. 수용 record에는 사용자 ID·소득·주소·facts·신청일·평가 결과를 저장하지 않는다. 정책 정의 수용 시 특정 사용자의 PASS를 요구하지 않는다.

반영 시 같은 scope/rule/dataset의 사용자 PASS가 필요하다. FAIL/UNKNOWN이면 ELIGIBILITY_NOT_PASS로 정상 제외하며 수용 record 자체는 바뀌지 않는다. 해당 시나리오·월 적용, 지급액/소득 중복, 의미상 중복·병급/선택형 충돌은 기존 applicability CONFIRMED 책임이다.

LLM·사용자가 FULL/VERIFIED/ACCEPTED/CONFIRMED를 직접 선언해서 gate를 통과시키는 API를 만들지 않는다. 정책 법적 자격·신청/지급을 확정하는 문구를 사용하지 않는다. 사용자 경제정보는 요청 단위로 계산하고 영구 저장하지 않는다.

## 22. 현재 실제 안산 상태

| 확인본 | 실제 상태 | 이번 결론 |
|---|---|---|
| ansan-youth-2026-10-20-001 | 2026/r0001, 주민등록 한 조건, Envelope DRAFT/CONDITION_SLICE | 수용 발급 불가 |
| ansan-youth-2026-10-20-002 | 2026/r0002, ALL(resident,birth)의 Q3 일부 조건, Envelope DRAFT/CONDITION_SLICE | 수용 발급 불가 |

정책 ID는 KR-GG-ANSAN-YOUTH-BASIC-INCOME이다. 실제 전체 Inventory/Bindings/Reviews/FULL CoverageResult는 없다. ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**로 계속 보류한다. 등록분류/국적과 최종 목록·공식 검토·자료 연결 등 다른 미완료도 남아 있다.

실제 acceptance record를 만들지 않는다. source VERIFIED·resident/birth PASS·generic core 완료로 실제 정책을 승격하지 않는다. 실제 Envelope에는 검토 완료된 Benefit component/금액/적용월 정의가 없다. 가짜 실제 benefit_id·version·fingerprint·review_ref도 생성하지 않는다.

**현재 정책의 direct Cashflow 반영은0원 유지**라는 연결 금지 결론이다. 아직 없는 Bridge가 실제 실행되어0을 반환했다는 주장이 아니다. 분기/지역화폐 특성은 기존 기획의 제외 근거이며 신규 검증 완료 metadata가 아니다. 향후 정확히 검토된 정의도 QUARTERLY/LOCAL_CURRENCY라면 현행 Bridge의 NON_MONTHLY_PAYMENT/RESTRICTED_MEDIUM으로0이다.

## 23. 합성 시나리오의 기준

이하 F/A는 **문서상 가정**이며 runtime record/정책 파일로 만들지 않는다. F는 가상 P-A / 2026-Q3 / CASH-A의 공식 경로 FULL 결과, 같은 현재 Envelope VERIFIED, source/review/freshness 요건 충족, Coverage9개 값 완전, 검토된 고정 Benefit 정의 B1이다. A는 그 확인본에 묶인 ACCEPTED a0001이다.

가상 혜택은 한 회100,000원, MONTHLY/UNRESTRICTED_CASH, 적용월=(2026-09), reviewed_at=2026-09-01, valid_until=2026-10-31, data_use_date=2026-10-22다. source freshness는 각 사례의 명시 사용일에 유효한 가상 준비본을 전제한다. 실제 source를 미래 재확인한 것으로 표시하지 않는다. target_month=2026-09와 data_use_date는 독립이다.

Bridge까지 설명하는 사례에만 같은 확인본의 사용자 PASS·개인 CONFIRMED·대상월 적합을 추가 가정한다. FULL→SLICE 사례는 기존 gate가 만들 수 있는 정상 조합으로 구성하며 fabricated Result를 정상 fixture로 권장하지 않는다. Inventory STALE+Implementation MISSING 같은 불가능한 single-Context 조합을 만들지 않는다.

## 24. 신뢰 경계와 외부 자료 준비

| 책임 | 담당 |
|---|---|
| 공식 의미·혜택 제한·금액·회차를 원문과 대조, 실제 교차검토 | 외부 팀 검토 |
| immutable release/artifact bytes·Registry/Manifest·같은 version 이력 확인 | 외부 자료 준비/발행 감사 |
| explicit ref resolve, 현재 승인/철회 revision 완전 선택 | 외부 자료 준비 |
| 현재 자료의 source/locator 상태·명시 날짜 기준 사용요건 | 향후 명시 입력에 대한 pure Acceptance gate; 기존 검증 의무 재사용 |
| Coverage 구조/검토/지문·FULL 파생 | 동결된 public Coverage evaluator |
| 현재 수용 binding/기한/검토 요건·정상 사유 | 향후 Acceptance evaluator |
| 사용자·월 적용·중복·현금 유형·합산 | 정규화와 Bridge |

문법상 유효한 ref·지문·review metadata를 가짜로 만든 경우, 값 모델·순수 비교가 사람의 실제 검토를 인증하지 못한다. 구조가 정상인 조작 입력이 로컬 검사에 통과할 수 있음을 명시하며 그것을 실제 승인으로 사용하지 않는다. 신뢰된 내부 준비 경로가 전제다. 이 한계를 이유로 전자서명·권한 서버·review workflow 플랫폼을 추가하지 않는다.

evaluator 안에서는 review artifact 파일/DB/공식 사이트를 찾지 않는다. 외부가 읽어 고정한 객체만 입력한다. source 날짜 검사에 네트워크가 필요하지 않다. source의 실제 변경·철회 누락은 외부 재검토 없이는 발견할 수 없다. 자동 로그/감사 저장을 이유로 개인정보를 수집하지 않는다.

## 25. 불변성·결정성

record와 결과는 작은 frozen 값 방향을 유지한다. accepted_terms·source bindings·scope를 포함해 입력은 변경하지 않는다. 새 revision을 만들 때도 과거 기록은 동일해야 한다. expiry는 data_use_date에 따른 결과이며 원본 status를 바꾸지 않는다.

같은 명시 입력 반복은 같은 usable/reasons/identity snapshot을 반환해야 한다. 새 primitive serialization은 원본을 변이시키지 않는다. 현재시각·난수·환경·캐시·전역 선택·파일·네트워크를 사용하지 않는다. 단일 record 평가에 최신 revision 검색을 넣지 않는다.

같은 acceptance_version으로 내용이 달라진 이력은 발급 경계에서 거부한다. 현재 전달 record 하나의 구조 검사와 과거 모든 기록의 진실성·완전성 인증은 다르다. 이 제약을 숨기지 않는다.

## 26. Pure API와 최소 결과 후보

bool 반환은 원인·대상을 잃는다. `(bool, typed reasons)`만 반환하면 다른 snapshot 결과를 Bridge 후보에 섞는 것을 추적하기 어렵다. **작은 불변 BenefitAcceptanceEvaluation 하나**를 추천한다. usable은 reasons가 비었을 때만 파생하고 이중 저장하지 않는다. candidate/record/result의 세 역할만 구별하며 별도 matching framework는 만들지 않는다.

결과 최소 정보 방향: 현재 policy_id/scope/benefit_id, 현재 Coverage binding의 값(정상 SLICE의 None 허용), Benefit version/fingerprint, data_use_date, 선택 acceptance identity 또는 None, reasons tuple. record의 전체 검토 artifact·원문·사용자 데이터는 넣지 않는다. exact 필드/오류/serializer는 Benefit snapshot 확정 후 결과 설계에서 결정한다.

```text
evaluate_benefit_acceptance(
    coverage_result: 기존 EligibilityCoverageResult,
    policy_envelope: 기존 PolicyEnvelope,
    benefit_snapshot: 향후 Benefit 정의 값,
    acceptance: 향후 PolicyBenefitAcceptance 또는 None,
    *,
    source_registry: 기존 SourceRegistry,
    dataset_manifest: 기존 DatasetManifest,
    data_use_date: 명시적 date,
) -> 향후 BenefitAcceptanceEvaluation
```

이것은 **서명 후보**다. source freshness를 숨은 전역이나 새 Verification bool로 처리하지 않기 위해 기존 두 자료 객체를 명시한다. 별도 VerificationResult/AcceptanceContext 서비스는 추가하지 않는다. Manifest/Registry의 전체 자료 준비 검증은 외부에서 성공해야 하며, evaluator는 해당 policy/benefit의 source 사용요건과 현재 binding만 검사한다. 전체 dataset loader/파일 hash를 다시 실행하지 않는다.

현재 입력끼리의 동일 snapshot 대응·기존 Envelope의 Tree 대조는 외부 준비에서 기존 public fingerprint/validator로 수행한다. Context의 implementation_fingerprint를 Manifest.engine_artifact_sha256과 무조건 같다고 가정하지 않는다. 어떤 정확한 input/evaluator artifact bytes를 뜻하는지는 기존 외부 준비 계약을 따른다. 후속 adapter에서 이 명시 대응을 검증해야 한다.

발급 API나 record 생성 기능은 이 함수에 넣지 않는다. 현재 verification/freshness의 실행 gate, Benefit snapshot과 record/result 타입 모두 미구현이다. 위 후보만으로 구현 준비 완료를 선언하지 않는다. Receipt/서명/저장소/자동 최신 선택도 도입하지 않는다.

## 27. M2.4 전체 compatibility audit

분류: **A 유지 / B 표현·결합 보완 / C 해당 책임 대체 / D 후속 미확정**. 한 절에 여러 분류가 있으면 변경 부분만 대체하고 나머지는 유지한다. 기존 파일은 수정하지 않는다.

| M2.4 절 | 분류 | 유지·보완·대체 내용 |
|---|---|---|
| 1 목적 | A/B | 시뮬레이션 수용 분리 유지; 현재 frozen Coverage를 기준으로 보완 |
| 2 validity/verification/acceptance | A | 서로 독립, 상태 하나로 합치지 않음 |
| 3 의미 | A | 배포·행정 승인과 구별, 표시 문구 유지 |
| 4 최소 구조 | B/D | scope 포함 identity·Coverage9개 binding·Benefit version/fp 추가 방향; accepted_terms 유지, exact 모델은 선행 snapshot 뒤 |
| 5 상태 | A | 없음+ACCEPTED/REVOKED, expiry 파생 |
| 6 Coverage | B/C | FULL 필수 유지; legacy slice만으로 판단하던 설명을 frozen Result 입력으로 대체, legacy 연결 한계는 남음 |
| 7 Verification | A/B | 기존 Envelope Enum·freshness 유지; Bridge가 아닌 Acceptance gate에서 현재 수용 사용요건 검사 |
| 8 사용자 eligibility | A | 발급과 개인 PASS 분리, 적용 시 같은 scope PASS 필요 |
| 9 metadata | A/B | 금액·주기·수단·월·근거 유지, restriction 누락 방지·정의 identity 보완 |
| 10 rule binding | A/B | 정상 새 version 제외·같은 version 모순 오류 유지; frozen Tree payload 기준으로 cross-record guard 명시 |
| 11 dataset/source | A/B | 정확한 고정본·재검토 유지, Registry fp와 policy/benefit 별도 bindings 결합 |
| 12 개인 적용 | A | CONFIRMED·소득/병급/중복 확인은 개인 정규화/Bridge |
| 13 대상 월 | A | target_month와 data_use_date 분리, 유한 월 목록·무환산 |
| 14 금액 | A/B | fixed int≥0·0원·None 구별 유지; 같은 버전 정의 모순은 Acceptance 앞단, candidate 불일치는 Bridge 입력 오류 |
| 15 근거/검토자 | A/B | 실제 교차 검토 유지, Coverage·Benefit binding을 artifact에 명시 |
| 16 기한/철회 | A/B/C | 날짜·새 revision·완전 선택 유지; 검사 책임은 Acceptance evaluator로 이동 |
| 17 실제 안산 | A/B | DRAFT/slice·반영0 유지; generic core 완료와 실제 blocker 구별 |
| 18 미래 full 예 | A | 수용된 quarterly/local도 Bridge0 유지 |
| 19 Candidate 연결 | C | raw acceptance_ref 해석을 Bridge 밖으로 이동, 평가 결과 결합으로 대체; component별 수용은 유지 |
| 20 BridgeContext | B/C | 월/사용일/assessment 유지, raw acceptances tuple·resolve/version/expiry 검사를 앞단으로 이동 |
| 21 제외 이유 | A/B | 기존 Bridge code 유지,18절 매핑·기존 순서, typed Acceptance 이유는 별도로 보존 |
| 22 오류/제외 | A/B | 정상 stale/absent·오류 분리 유지; 정상 과거 scope 비교와 잘못된 ref 구별을5절로 정밀화 |
| 23 순서 | B/C | 구조·독립 오류 우선과 Bridge reason 순서 유지; Acceptance 검사를 앞단에서 수행 |
| 24 MVP 구조 | B/C/D | 후보+record+context만으로 충분하다는 결론은 현재 평가 결과 필요성으로 보완; exact 모델/배치는 후속 결정 |
| 25 PA01~PA40 | A/B | gate 의미 보존; scope/ref·검사 담당 변경은 이 문서가 우선, 실제 실행 테스트 아님 |
| 26 미해결 | B/D | generic Coverage 기반 차단은 해소; Benefit snapshot·legacy/full 실제 연결·개인/월·발급/선택 신뢰는 미완료 |
| 27 당시 판단 | B | 당시 NEEDS_POLICY_COVERAGE_MODEL_REVISION 기록 보존; 지금 다음 선행은 Benefit snapshot 설계 |

특히 M2.4의 “accepted_coverage 중복 저장 안 함”은 상태/객체 중복 금지로 유지하되 **정확한 Coverage identity9개 값 저장**으로 보완한다. POLICY_COVERAGE_SPEC20절의 accepted_scope/inventory_version 요구를 포함한다. M2.4의 순수 Bridge 철회/만료 검사는 앞단으로 이동하며 계산·지원 유형을 변경하는 것이 아니다.

## 28. M2.3 Bridge compatibility audit

| M2.3 절 | 분류 | 영향 |
|---|---|---|
| 1 목적 | A | 직접 월 자유 현금·제외/오류 분리 |
| 2 책임 | B | 정규화 앞단에 Acceptance 현재 평가 추가, 합산 책임 유지 |
| 3 입력 | B/C | acceptance_status scalar는 typed 평가 결과로 대체; scope·동일 snapshot 대응 보완 |
| 4 stable ID | A | `(policy_id, benefit_id)` dedupe 유지; scope는 승인/재현 dimension |
| 5 edition 관계 | A/B | 같은 batch의 정책 edition/snapshot 일관성 유지; scope도 명시 결합 |
| 6 eligibility | A/B | FULL+PASS 유지; legacy scope 대신 공식 CoverageResult 기반 정규화 |
| 7 verification | A/B/C | 기존 Enum·source 검토 유지; acceptance 원자료 검사는 앞단, 결과와 후보 대응은 Bridge |
| 8 medium | A | 허용/제외 분류 변경 없음 |
| 9 cadence | A | MONTHLY만 적용, 분기/일시금 무환산 |
| 10 금액 | A | 정확한 int≥0·None·큰 int·한 회 의미 유지 |
| 11 적용조건 | A/B | 모든 gate 필요, Acceptance 평가 결과로 수용 확인; 개인 CONFIRMED 유지 |
| 12 제외 | A | 정상 미충족0·이유, 정책 FAIL로 덮지 않음 |
| 13 중복 | A | 제외 후보도 stable identity 중복은 전체 오류 |
| 14 충돌 | A/B | 정책 metadata 동일성 유지; Acceptance는 M2.4대로 component별 다를 수 있음 |
| 15 결과 | A/B | 합계/applied/excluded 유지, Acceptance 결과의 작은 trace 결합 |
| 16 이유 | B | M2.4의 POLICY_NOT_ACCEPTED→SIMULATION_NOT_ACCEPTED 및 version/expiry/month 코드·순서 유지 |
| 17 오류/제외 | A/B | 정상 제외/전체 오류 유지, 앞단 오류를0원 정상 결과로 catch하지 않음 |
| 18 실제 안산 | A | 수용·실제 연결 불가/0원, 미래 예시는 합성 |
| 19 복수 혜택 | A | component별 유형/수용 다름 허용·중복/병급 확인 유지 |
| 20 결정성 | A | 순수·정렬·불변·전체 실패 |
| 21 What-if | A/B | 같은 정의/자료 고정·각 개인 적용 재평가, Acceptance 결과도 동일 기준에 결합 |
| 22 흐름 | B | Bridge 앞에 Acceptance evaluator 추가, Cashflow 명시 int 경계 유지 |
| 23 BB01~BB40 | A/B | 유형·중복 기대 유지, scalar 수용 표현만 미래 결과 결합으로 전환 |
| 24 미해결 | B/D | generic Coverage 해결, Benefit 정의·수용·개인 적용/실제 연결은 미완료 |
| 25 구조 | A/B/D | 형제 패키지/독립 Bridge 유지; Acceptance 배치는 승인 후 최소 단위로 결정 |
| 26 당시 판단 | B | 과거 NEEDS_POLICY_ACCEPTANCE_CONTRACT 기록 보존, 현재 문서가 다음 경계를 보완 |

**지원 유형·분기 나누기 금지·제외 의미·stable dedupe·합산 계약은 변경하지 않는다.** Bridge가 수용 원자료를 다시 판정하지 않도록 입력과 책임만 정밀화한다.

## 29. 후속 순서와 완료조건

한 단계씩 승인받아 진행하며 이번에는 아래 단계에 착수하지 않는다.

| 순서 | 가장 작은 작업 | 선행조건 | 완료조건/검증 방법 |
|---|---|---|---|
| 1 | **Benefit definition snapshot을 문서로 설계** | 이번 계약 검토 | fields/version/scope/restriction/evidence·payload 포함/제외·직접 equality 비교·지문 필요성과 golden 계획이 일관됨; 수동 변경/모순 사례로 검토 |
| 2 | 승인한 최소 Benefit 값 모델 | 1 승인 | 합성 exact 타입·불변성·금액/월/근거 경계 unit tests; 실제 데이터 없음 |
| 3 | 승인한 Benefit fingerprint 순수 함수 | payload/golden 승인 | literal canonical bytes/지문·필드 변화·정렬·인코딩 테스트; Coverage golden 불변 |
| 4 | Acceptance record 모델 | Benefit snapshot 안정화 | 완전 Coverage binding·scope/benefit identity·상태/기한·불변 revision 테스트 |
| 5 | 최소 Acceptance 평가 결과 모델 | record/이유/trace 계약 승인 | usable 파생·사유 조합·snapshot 대응·serializer 테스트 |
| 6 | pure Acceptance evaluator | 현재 자료 검증/신선도·source/Benefit review 입력 계약 승인 | 이번 정상/오류/독립 guard·명시 날짜·동일성 사례 테스트; 실제 발급 없음 |
| 7 | Bridge 값 모델·순수 합산 | 결과 입력/개인·월 정규화 계약 승인 | 기존 유형·중복·0원·무환산·오류/제외·결과 연결 테스트 |
| 8 | 검토된 정책 연결·Cashflow 매핑 | 실제 FULL·VERIFIED·혜택/수용/개인 확인 모두 완료 | 같은 고정본으로 end-to-end 확인; 실제 안산 blocker 해소 전 양수 연결 금지 |

문서 승인 없이 모델·지문·evaluator를 한꺼번에 구현하지 않는다. Generic Acceptance 합성 준비는 공식 거주기간 답변과 독립적으로 진행할 수 있다. 실제 안산 FULL/수용/반영은 계속 차단한다. 새 loader/DB/API/UI/검토 서버를 선행 구현하지 않는다.

## 30. 수동 시나리오 — CA01~CA96

**96개 문서상 계약 사례다. 실행 테스트/실제 기록이 아니다.** 기본은23절 F/A다. 변경 사례는 명시한 관련 version·current review를 함께 갱신해 유효한 현재 입력을 만든다. “같은 version 모순” 사례만 의도적으로 불변 계약을 위반한다. E는 향후 Acceptance 평가, B는 향후 Bridge를 뜻한다.

| ID | 입력·변경 | 기대 |
|---|---|---|
| CA01 | F + 정확한 A | E usable; 사용자/월 반영은 별도 |
| CA02 | missing condition으로 정상 SLICE | 발급 금지, E COVERAGE_NOT_FULL |
| CA03 | completeness_review_ref=None, Context present의 Inventory MISSING | 정상 SLICE·E 불가; 오류로 승격 안 함 |
| CA04 | Inventory review가 정상 구version이라 STALE | 정상 SLICE·E 불가 |
| CA05 | Context=None, existing Implementation MISSING | 정상 SLICE·baseline 모두 None; E 불가 |
| CA06 | 정상 구현 artifact 교체로 Implementation STALE | 정상 SLICE; E 불가·snapshot 변경 추적 |
| CA07 | 현재 2026-Q3, A도 Q3 | scope gate 통과 |
| CA08 | 현재 Q4, 정직한 과거 Q3 record 비교 | 정상 COVERAGE_SNAPSHOT_CHANGED |
| CA09 | 현재 annual, 과거 Q3 record | 정상 불가, Q3 확대 금지 |
| CA10 | 현재 2027-Q3, 과거 2026-Q3 record | 정상 불가, 연도 자동 승계 없음 |
| CA11 | 같은 scope/i version·Inventory fp 모두 같음 | 해당 guard 통과 |
| CA12 | 새 i version·검토 완료된 새 FULL | 정상 snapshot 변경, 이전 A 불가 |
| CA13 | 같은 rule version·Tree fp 같음 | 해당 guard 통과 |
| CA14 | 새 rule version·검토 완료된 새 FULL | 정상 COVERAGE_SNAPSHOT_CHANGED |
| CA15 | 같은 dataset·Registry fp 같음 | 해당 guard 통과 |
| CA16 | 새 dataset·유효 current review | 정상 변경, A 재사용 불가 |
| CA17 | 같은 source/Registry 확인본 | source binding gate 통과 |
| CA18 | source 새 d version·새 dataset/검토 | 정상 변경, 금액 같아도 재수용 필요 |
| CA19 | 같은 implementation fp | 해당 binding 통과 |
| CA20 | 새 implementation fp·새 current review로 FULL | 정상 변경, A는 불가 |
| CA21 | 정확한 benefit_id | 대상 검사 통과 |
| CA22 | 다른 benefit_id의 A 직접 전달 | Data Error |
| CA23 | 새 Benefit 정의 version | 정상 BENEFIT_SNAPSHOT_CHANGED |
| CA24 | 같은 Benefit version에서 금액만 변경 | Data Error; 새 version이면 정상 변경 |
| CA25 | 같은 Benefit version에서 cadence 변경 | Data Error; 월 환산 금지 |
| CA26 | 같은 Benefit version에서 medium 변경 | Data Error |
| CA27 | 같은 Benefit version에서 restriction 변경 | Data Error |
| CA28 | 같은 Benefit version에서 evidence/benefit source binding 변경 | Data Error; 새 정의 version 필요 |
| CA29 | F, record=None | 정상 NO_ACCEPTANCE |
| CA30 | F, 완전한 현재 ACCEPTED | E usable |
| CA31 | F, 외부가 선택한 새 REVOKED revision | 정상 ACCEPTANCE_REVOKED |
| CA32 | F, 사용일이 valid_until 다음날 | 정상 ACCEPTANCE_EXPIRED |
| CA33 | 다른 policy_id의 record 직접 전달 | Data Error |
| CA34 | ref는 Q4라 주장, resolved record는 Q3 | Data Error; CA08과 구별 |
| CA35 | 같은 대상의 옛 정상 rule/dataset record | 정상 COVERAGE_SNAPSHOT_CHANGED |
| CA36 | 모든 current binding 정확히 일치 | binding gate 통과, 다른 요건도 필요 |
| CA37 | 현재 Envelope VERIFIED·source 사용요건 유효 | 정책 검토 gate 통과 |
| CA38 | 현재 Envelope DRAFT 또는 STALE | 정상 POLICY_NOT_VERIFIED |
| CA39 | Coverage FULL, Envelope DRAFT | 여전히 불가, FULL을 VERIFIED로 매핑 금지 |
| CA40 | 구조상 정상인 가짜 review/ref metadata를 공급 | 로컬 타입/동등성만으론 검토 진실성 인증 못 함; 실제 발급/연결 금지 |
| CA41 | 검토된 MONTHLY/UNRESTRICTED_CASH, 개인/월도 확인 | E usable, B 합성100,000 반영 가능 |
| CA42 | 검토된 QUARTERLY cash | E usable 가능, B NON_MONTHLY_PAYMENT·0원 |
| CA43 | 검토된 LOCAL_CURRENCY | E usable 가능, B RESTRICTED_MEDIUM·0원 |
| CA44 | 검토된 VOUCHER | E usable 가능, B RESTRICTED_MEDIUM·0원 |
| CA45 | 검토된 ONE_TIME | E usable 가능, B NON_MONTHLY_PAYMENT·0원 |
| CA46 | 검토된 SAVINGS_MATCH | E usable 가능, B RESTRICTED_MEDIUM·0원 |
| CA47 | 현재 실제 안산002의 slice | FULL로 만들지 않음, 실제 Acceptance 발급 금지 |
| CA48 | 현재 실제 안산, 수용 record 없음 | usable 수용 없음; 가짜 record 생성 금지 |
| CA49 | 현재 실제 안산의 Cashflow 연결 판단 | 반영0 유지; 없는 Bridge의 실행 결과라고 주장 안 함 |
| CA50 | 합성 FULL + no acceptance | NO_ACCEPTANCE, B0 |
| CA51 | 합성 FULL + 정확한 accepted + 개인/월/유형 통과 | E usable, B 합성100,000 |
| CA52 | 합성 FULL + revoked | E 불가, B SIMULATION_NOT_ACCEPTED |
| CA53 | 합성 FULL + expired | E 불가, B ACCEPTANCE_EXPIRED |
| CA54 | 합성 새 FULL + old rule acceptance | 정상 변경, B ACCEPTANCE_VERSION_MISMATCH |
| CA55 | 합성 새 FULL + old dataset acceptance | 정상 변경, B ACCEPTANCE_VERSION_MISMATCH |
| CA56 | data_use_date=reviewed_at | 유효성 하한 포함 |
| CA57 | data_use_date=valid_until 전날 | 날짜 gate 통과 |
| CA58 | data_use_date=valid_until | 유효성 상한 포함 |
| CA59 | data_use_date=valid_until 다음날 | 만료, 원본 status는 ACCEPTED 유지 |
| CA60 | 시스템 날짜를 달리해 같은 명시 입력 반복 | 결과 동일; date.today/now 사용 없음 |
| CA61 | 평가 전후 A/accepted_terms/scope | 값·원본 불변 |
| CA62 | 철회 시 a0002 REVOKED 새 revision 선택 | a0001 보존·새 revision만 현재 사용 평가 |
| CA63 | 빈/잘못된 ID·알 수 없는 상태 | Data Error·자동 보정 없음 |
| CA64 | 같은 Inventory identity/version, 다른 fp | Data Error |
| CA65 | record의 baseline9개 중 필수 일부 누락 | Data Error; 정상 current None과 구별 |
| CA66 | Benefit snapshot P-A/CASH-A, record P-A/CASH-B | wrong target Data Error |
| CA67 | 과거 A가 있으나 현재 정상 SLICE | 정상 unusable, A 수정·삭제 없음 |
| CA68 | 아직 검토하지 않아 record 미발급 | 정상 NO_ACCEPTANCE·PENDING record 안 만듦 |
| CA69 | 정상 REVOKED 선택 | 정상 불가, 예외로 처리 안 함 |
| CA70 | 정상 stale snapshot 선택 | 정상 불가, 과거 승인 승계 없음 |
| CA71 | E usable지만 사용자 UNKNOWN/FAIL | E 그대로, B ELIGIBILITY_NOT_PASS·0원 |
| CA72 | E usable | 행정 승인·신청/지급 확정 출력 금지 |
| CA73 | E 실행 | 금액 합산/Cashflow 호출 없음 |
| CA74 | 수단/주기만 다른 정확히 검토된 정의와 그 A | E에서 Bridge 유형 필터 실행 안 함 |
| CA75 | 같은 명시 입력100회 평가 | 같은 reasons/값 표현 |
| CA76 | review artifact가 필요하다는 이유로 파일 접근 시도 | pure 계약 위반; 외부에서 먼저 resolve |
| CA77 | 공식 링크 최신화 명목 네트워크 접근 | pure 계약 위반 |
| CA78 | 같은 정의/범위의 재검토로 새 a revision | 새 record 명시 선택, 자동 최신 선택 없음 |
| CA79 | 새 Benefit version, 의미/금액 같음 | 이전 A 자동 승계 없음 |
| CA80 | 새 policy scope의 별도 승인 필요 | 기존 계보 유지 가능, 승인 identity는 별개 |
| CA81 | 새 dataset + 같은 rule version의 다른 Tree fp | stale가 독립 Tree 모순을 숨기지 못함, Data Error |
| CA82 | 새 rule version + 같은 Inventory version의 다른 fp | 독립 Inventory 모순 Data Error |
| CA83 | 같은 dataset + 다른 Registry fp | Data Error, 정상 source 갱신으로 취급 금지 |
| CA84 | Q3→Q4, 각각 scoped i0001·정상 다른 Inventory | scope 정상 변경; 그 차이를 same-version 충돌로 오진 안 함 |
| CA85 | 만료+새 정상 dataset | 변경/만료 모두 보존, Bridge 기존 순서로 매핑 |
| CA86 | REVOKED+같은 version Tree 모순 | lifecycle보다 구조/내용 guard 우선, Data Error |
| CA87 | current Envelope와 Coverage의 policy/rule/dataset 불일치 | current input Data Error; stale acceptance 아님 |
| CA88 | source VERIFIED지만 명시 날짜 기준 freshness 경과 | current 사용 gate 불가; valid_until 안이어도 통과 안 함 |
| CA89 | 고정 Benefit metadata 구조는 정상, 검토 연결 없음 | BENEFIT_METADATA_NOT_REVIEWED; FULL만으론 부족 |
| CA90 | benefit evidence 명시 ref가 고정 Registry에 없음 | broken evidence Data Error |
| CA91 | 다른 snapshot/date의 AcceptanceEvaluation을 후보에 결합 | B input Data Error; Bridge가 Acceptance 재판정하지 않음 |
| CA92 | 같은 stable benefit 후보 중복, 하나가 미수용 | B 전체 duplicate 오류; 부분 합산 없음 |
| CA93 | E usable·개인 PASS/CONFIRMED지만 target_month가 목록 밖 | B TARGET_MONTH_NOT_APPLICABLE, expiry와 구별 |
| CA94 | 검토된 확정0원 정의·모든 gate 통과 | E usable, B applied0원; None과 구별 |
| CA95 | 현재 정상 SLICE·baseline 모두 None | E 정상 불가; old baseline 보충·partial identity 오류 오진 금지 |
| CA96 | 같은 a identity를 다른 valid_until/내용으로 overwrite | 외부 이력 감사 Data Error; 새 revision 필요, 단일 record만으론 이력 인증 불가 |

단독 gate 사례는 실제로 모순된 record를 발급해도 된다는 뜻이 아니다. source 사용일·review/manifest·버전 guard와 모순되지 않도록 합성 준비본을 함께 고정한다. 표의 지문 값은 실제 안산에서 계산/저장하지 않았다.

## 31. 미해결 문제와 Assumptions

| 항목 | 현 상태/다음 책임 |
|---|---|
| Benefit snapshot | 명시 version·내용 필드·restriction 표현·review 연결·payload/canonical bytes/golden 미확정; **다음 선행 작업** |
| Acceptance record/result exact 구조 | 이번에는 방향만 결정, Benefit 선행 계약 뒤 필드·오류·serializer 승인 필요 |
| 현재 verification/source freshness 실행 gate | 기존 의무는 유지하나 현재 실행 구현 없음; 기존 Registry/Manifest/date 명시 입력으로 pure 범위 확정 필요 |
| legacy Envelope/Manifest와 full 자료 연결 | 미구현, actual full release 발행 전에 별도 설계/검증 필요 |
| 실제 검토·현재 철회 선택·artifact 이력 | 외부 준비 책임; 모델/지문으로 진실성 인증 불가 |
| 개인/월 정규화·중복/병급 확인 | 미구현, Acceptance로 대체 불가 |
| actual Ansan | DRAFT/slice·공식 거주기간/다른 목록·조건 검토 미완료, 수용 불가 |

**Assumption A1:** 초기 수용 범위는 M2.4의 고정 금액·열거 가능한 공통 적용월이다. 개인별 금액 공식/일정 엔진으로 확대하지 않는다.

**Assumption A2:** 신뢰된 내부 자료 준비가 동일 immutable 원본·정책/혜택 근거·실제 검토와 현재 승인/철회 revision을 공급한다. 외부 사용자/LLM의 선언을 신뢰하지 않는다. 누락 철회·가짜 검토를 로컬 비교만으로 탐지한다고 주장하지 않는다.

**Assumption A3:** 정상 과거 scope record 비교는 진단 목적으로 허용하지만 다른 현재 대상의 승인을 대체하지 않는다. ref 자체의 잘못된 대상 연결은 오류다. 이 구별은5절의 명시적인 M2.4 보완이며 암묵적 허용이 아니다.

현재 결정을 미룬 항목을 기본값으로 채워 구현하지 않는다. 다음 작업은 위 첫 번째 항목 하나의 문서 설계다. Coverage freeze 변경이 필요한 충돌은 이번 검토에서 발견하지 못했다.

## 32. 최종 판단과 검증 기록

**READY_FOR_BENEFIT_SNAPSHOT_DESIGN**

CoverageResult의 기존 identity/findings와 외부 Acceptance binding만으로 연결을 설계할 수 있다. Coverage API·FULL/SLICE·구조/결합·지문·review matching·Result를 변경할 이유가 없다. FULL은 필요조건, 정책/혜택 검토·정확한 snapshot·기한/철회는 별도, 개인/월/현금 유형·산술은 후단이라는 경계를 유지한다.

현재 Benefit 정의에는 안정적인 내용 version/fingerprint 계약이 없으므로 Acceptance 코드로 진행하지 않는다. **다음 가장 작은 작업 한 개: Benefit definition snapshot의 최소 필드·version identity·restriction/evidence/source 결합·fingerprint payload와 golden 검증 계획을 문서로 설계한다.** 코드·실제 정책자료·수용 기록은 만들지 않는다.

사전 전체 회귀: **5687 passed in 14.45s**. 문서 작성 후 전체 회귀: **5687 passed in 14.19s**. 신규 실행 테스트는 추가하지 않으며 이 회귀가 미구현 Acceptance/Bridge를 검증한 것은 아니다.

문서의32개 절·CA01~CA96의 연속/유일 ID·표 열 수·code fence·한국어 표기를 확인했다. 사전 actual releases/pycache 제외 backend/tests/data/docs148개 파일의 SHA256 대조에서 **기존148개 모두 동일, 이 문서 한 개만 추가되어149개**이며 수정/삭제는 없다. Coverage freeze 파일·source·GV01~GV15 및 기존 기대값·Cashflow·ResidenceHistory 관련 자료를 보존했다.

실제 release6개 파일은 경로/크기/수정시각이 모두 동일하다. 실제 Ansan 지문·CoverageResult·Review·Acceptance·혜택 금액을 새로 계산/생성/저장하지 않았다. runtime 코드와 기존 문서는 변경하지 않았다.

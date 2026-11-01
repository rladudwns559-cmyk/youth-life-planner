# M2.58 — Acceptance Review Artifact Content Validator Contract

## 1. 목적·보장 범위·결론

검토 Artifact가 선언한 **당시 Acceptance revision·Benefit/Coverage 확인본·문서 version·claim 근거**의 대응을 검증하는 계약이다. 원문이 claim을 의미상 지지한다는 판단은 별도 사람 검토다. Loader 성공·도메인 지문 일치·ArtifactReference 존재를 실제 내용 검토 완료로 확대하지 않는다.

이번에는 이 문서1개만 추가한다. validator/preparation/Source Gate/evaluator/Bridge·새 모델/범용 framework·실제 정책 검토를 구현하지 않는다.

**최종 판단: NEEDS_HISTORICAL_ARTIFACT_PREPARATION_CONTRACT.** 기계적 비교 항목·최소 입력·오류/신뢰 경계는 아래에 정했다. 그러나 검토 참조의 bytes와 공급된 역사 객체를 **동일 bytes의 strict 복원으로 결합하는 계약**이 일부 없다. 현재 존재하지 않는 decoder를 성공했다고 가정하여 전체 validator 구현 준비 완료로 판정하지 않는다. 이 구체적인 공백과 다음 한 작업은22절이다.

## 2. Source of Truth와 실제 구현 확인

| 확인 문서 | 이번에 적용한 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md 4~23·30절 | 당시 원본 참조·5claim·정책/혜택 source 합집합·ACCEPTED/REVOKED·구조/내용 분리 |
| BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_LOADER_SPEC.md 3~21·28절 | raw bytes/20값 검증·원본 is 보존·여러 entry·P0~P9와 미구현 외부 preparation |
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md |21필드·7 Coverage+4 Benefit binding·날짜/status·초기 발급 기준 |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md |4필드·명시 ref·철회 target/11binding·독립 재승인·공유 artifact |
| BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md |9필드·12 reason·현재 usability와 과거 결정 구분 |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | A/C/B·8입력·동일 호출 원본·source/verification/completeness 경계 |
| BENEFIT_SNAPSHOT_SPEC.md |16필드·정의 fingerprint와 provenance·FIXED/UNKNOWN/VARIABLE |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | Coverage/Benefit 수용과 개인/월/Bridge 적용 분리 |
| POLICY_DATA_ENVELOPE_SPEC.md | 기존 Envelope/Source/Manifest의 최신 구현 절, raw와 진단 serializer 구분 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | FULL_POLICY·현재/역사 자료·legacy Envelope 연결 blocker·GV 동결 |
| DATA_MODEL.md / ARCHITECTURE.md | 기존 모델·loader·public/private 경계와 미구현 사항 |

실제 Review 모델4개/Claim Enum·strict bytes loader, PolicyBenefitAcceptance/Context, BenefitSnapshot/fingerprint, EligibilityCoverage/EligibilityCoverageResult/CoverageReviewContext, ArtifactReference/SourceBinding, SourceRegistry/SourceDocument/SourceEvidence, DatasetManifest/PolicyEnvelope/PolicyDataError를 확인했다. 기존 validate_dataset_manifest/validate_envelope_sources/validate_evidence_refs·지문·review matching 및 실제 공개 parse/load 함수도 확인했다.

중요한 실제 사실:

- SourceBinding은 source_document_id/document_version의2필드다. locator/status/verified_at는 없다.
- PolicyEnvelope.coverage는 legacy PolicyCoverage이며 generic EligibilityCoverage와 다른 타입이다. Envelope 자체에 quarter 필드는 없다.
- EligibilityCoverageResult는8 stored fields와 파생 status다. inventory_fingerprint/policy_tree_fingerprint라는 저장 필드나 당시 모든 원본을 복원하는 public parser는 없다.
- Coverage inventory 지문은 inventory의 의미 payload를 고정한다. completeness_review_ref·Coverage.bindings·전체 ReviewContext를 모두 포함하는 Coverage 파일 hash가 아니다.
- SourceDocument.content_sha256는 optional이다. Registry metadata의 존재가 공식 원문 bytes 확보를 뜻하지 않는다.
- typed BenefitSnapshot/EligibilityCoverage/CoverageReviewContext/DatasetManifest의 strict 역사 bytes decoder는 현재 없다. to_dict는 그 decoder가 아니다.

## 3. 구현 능력 현황

| 항목 | 기존 타입·함수 | 현재 가능한 검증 | 필요한 외부 자료 | 현재 보장하지 못하는 것 |
|---|---|---|---|---|
| Benefit definition fp | fingerprint_benefit_snapshot | 실제 공급 Snapshot의 정의 payload 지문 | 당시16필드 원본 | 그 객체가 accepted_terms_ref bytes에서 복원됐는지 |
| Benefit provenance | Snapshot.dataset_version/source_registry_fingerprint | record·Manifest·실제 Registry 지문과 값 대조 | 당시 Manifest/Registry | 파일 label만으로 당시 release 진실성 |
| Coverage inventory fp | fingerprint_condition_inventory | 실제 inventory의 의미 지문 | 당시 EligibilityCoverage.inventory | Coverage.bindings/검토 refs 전체 bytes identity |
| Policy Tree fp | fingerprint_policy_tree | Envelope.policy의 rule tree 지문 | 당시 Envelope/Policy | 이 구현이 당시 공고 전체 조건을 충족하는지 |
| implementation fp | record/ReviewContext·Manifest.engine_artifact_sha256 | 공급 값 간 대응, 명시 ZIP bytes가 있으면 raw SHA | 당시 실행 ZIP/환경 | 실제 해당 ZIP 코드에서 계산/실행됐는지 |
| Coverage review records | CoverageReviewContext·기존 resolver/matching | 명시 review ref/condition/root/version/지문 대응 | 당시 Coverage/ReviewContext·정확한 rule roots | 실제 사람 검토/권한·review artifact 원문 |
| Manifest identity | DatasetManifest·fingerprint()·validate_dataset_manifest | 전체 Envelope/Registry 구성·domain 지문·버전 비교 | 당시 전체 release·Manifest bytes | 파일 raw SHA/strict 복원·과거 engine 실행 |
| Registry identity | fingerprint_source_registry·SourceRegistryReference | 실제 Registry domain 지문·source/version 집합 | 당시 Registry 원본 bytes | 현재 공식 사이트 최신성·실제 의미 |
| SourceBinding version | registry.get_source | 문서 ID/d version 일치 | 당시 Registry | 공식 원문 진실성 |
| Evidence locator | parse_evidence_ref/validate_evidence_refs/registry.resolve | 문법·중복·source/locator 존재·ACTIVE | 당시 Registry/locator metadata | VERIFIED/freshness·그 위치의 문장 의미 |
| 공식 source bytes | ReviewSourceOriginal·SourceDocument.content_sha256 | 명시 bytes SHA와 고정 참조 대조 가능 | 원문 immutable bytes | 문서가 실제 공식 원문인지·claim 지지 |
| ArtifactReference | path/sha256 exact2필드 | 참조 형식·값 equality | 실제 bytes·해당 형식 decoder | 파일 존재·객체와 bytes 결합 |
| Claim mapping | ClaimEvidenceMapping/Entry |5claim·순서/중복은 이미 모델에서 검사, 원본 refs 부분목록 비교 가능 | 당시 Snapshot·Registry·공식 원문 | 자동 의미 해석/검토 완료 |
| Review Artifact hash | load_acceptance_review_artifact_bytes | raw SHA/C1·구조·외부 record20값·원본 보존 | 정확한 bytes/expected records | companion bytes/공식 내용·검토자 인증 |
| Review target identity | loader 결과 entries·기존 Acceptance | 정확한 원본 ref/version/target/binding·is 보존 | 같은 호출의 loader 반환값/원본 | caller가 직접 만든 비슷한 객체가 loader 결과인지 |

validate_dataset_manifest는 전체 envelopes를 요구하며 ENGINE_VERSION도 비교한다. 과거 engine과 현재 engine이 다르면 현재 함수의 ENGINE_COMPATIBILITY_MISMATCH를 역사 원본이 거짓이라는 증거로 오해하지 않는다. 이 경우의 역사 검증 환경 확보는 준비 책임이다. 기존 validator를 약화하거나 engine 비교를 몰래 생략하지 않는다.

## 4. 검증 수준과 성공의 의미

| 수준 | 명칭 | 확인 내용 | 담당 |
|---|---|---|---|
| L1 | 정의·참조 대응 | 당시 typed Snapshot/Coverage/Manifest/Registry와 record·claim refs의 대응 | 향후 pure validator·기존 지문/validator |
| L2 | 원본 bytes·복원 대응 | 선언 ArtifactReference와 실제 bytes SHA, **같은 bytes에서 복원한 typed 원본**·locator 연결 | 외부 preparation의 strict decode + pure 대조 |
| L3 | 공식 의미 검토 | 실제 원문이 AMOUNT/CADENCE/MEDIUM/RESTRICTION/APPLICABLE_MONTHS를 지지하는지 | 사람/승인된 외부 검토 절차 |

L1은 L2를 대신하지 않고 L1/L2는 L3를 대신하지 않는다. page/table_position/meaning_summary는 검토 위치/요약 metadata이지 자동 의미 증명서가 아니다. 새로운 L3 판정 모델·LLM 심사·권한 서버를 이번에 만들지 않는다.

향후 pure 함수의 None 성공은 **필요한 L1/L2 기계적 대응**만 뜻한다. L3 수행 기록의 원본 위치와 대상은 Artifact에 있지만 실제 수행·정당성/권한은 외부다. 전체 서비스 사용은 A/C에서 그 외부 책임까지 확인해야 한다. 현재 L2 strict 복원 경로가 닫히지 않아 전체 None 성공 경로 구현 승인을 보류한다.

## 5. 선택한 최소 pure API 후보

아래는 비교해서 선택한 후속 후보 계약이다. 현재 구현된 함수나 안전한 public 진입 API가 아니다.22절의 원본 복원 계약을 닫기 전 전체 validator를 구현하지 않는다.

```python
_validate_acceptance_review_artifact_content(
    *,
    artifact: AcceptanceReviewArtifact,
    acceptance: PolicyBenefitAcceptance,
    historical_benefit: BenefitSnapshot,
    historical_coverage: EligibilityCoverage,
    historical_reviews: CoverageReviewContext,
    historical_manifest: DatasetManifest,
    historical_envelopes: tuple[PolicyEnvelope, ...],
    historical_registry: SourceRegistry,
    historical_artifact_bytes: tuple[tuple[ArtifactReference, bytes], ...],
    acceptance_context: BenefitAcceptanceContext | None,
    revoked_target_artifact: AcceptanceReviewArtifact | None,
) -> None
```

정확히11개 입력이다. 모두 필수 keyword-only이고 기본값이 없다. nullable2개도 명시한다. 기존 타입은 exact, 바깥 collection/안쪽 pair는 exact tuple, bytes는 exact bytes다. PreparedContext/VerifiedSnapshot/approval bool 같은 새 타입을 추가하지 않는다.

| 후보 | 장점 | 부족한 점/결정 |
|---|---|---|
| Artifact+Snapshot만 | 입력이 적음 | Coverage/release/source version/원본 bytes를 비교할 수 없음 |
| CoverageResult+verified bool | 호출이 짧음 | 원본/FULL producer/실행 대응을 증명하지 못하고 bool로 우회 가능. 제외 |
| 기존 원본 타입+한정된 bytes 쌍 | 기존 타입으로 비교 재료와 책임 명시 | 선택한 후보. bytes와 typed 원본 결합이 미완료여서 구현 준비 완료는 아님 |

## 6. 입력의 필요성·취득·누락 경계

| 입력 | 비교할 사실/중복이 아닌 이유 | 외부 취득/누락 시 처리 |
|---|---|---|
| artifact | loader가 확인한 entry/원본 참조/mapping | 같은 호출의 실제 loader 반환 원본. 미확보는 준비 실패 |
| acceptance | 명시 선택 identity와 entry.acceptance의 is 대응 | 신뢰된 기존 record. body에서 새로 발급하지 않음 |
| historical_benefit | readable terms16값과 실제 정의 fp | accepted_terms_ref의 동일 bytes에서 복원 필수 |
| historical_coverage | inventory/version/fp·bindings/review refs | coverage_snapshot_ref에서 복원. Result 단독 대체 불가 |
| historical_reviews | 당시 review records/implementation baseline | coverage_reviews_ref에서 복원. 자기 선언 MATCHED로 대체 불가 |
| historical_manifest | dataset/Registry/source/engine 확인본·기대 참조 | dataset_manifest_ref의 당시 원본. domain fp와 raw SHA는 별개 |
| historical_envelopes | 전체 release 구성/Policy tree/source bindings | Manifest 전체 policy refs의 원본. 선택 Envelope 단독으로 부족 |
| historical_registry | locator/version/policy·whole Registry fp | source_registry_ref의 동일 bytes에서 복원 |
| historical_artifact_bytes | 선언 참조와 실제 raw SHA 비교 | 한 번 확보한 immutable bytes. hash 문자열만으로 대체하지 않음 |
| acceptance_context | REVOKED의 기존 검증된 edge | ACCEPTED는 None. REVOKED는 B 원본을 포함한 exact Context 필수 |
| revoked_target_artifact | B가 철회하는 A의 정확한 검토 원본 | ACCEPTED는 None. REVOKED는 A를 포함한 실제 loader 반환 원본. 같은 물리 자료면 artifact 자신도 가능 |

추가하지 않는 입력은 current Benefit/Registry·data_use_date, 중복 selected Envelope, caller가 준 current fp/FULL bool/평가 결과/claim reviewed bool이다. Envelope는 historical_envelopes에서 policy ID로 한 번 선택한다. 전체 Context를 새 모델로 복제하지 않는다.

REVOKED도 historical_*는 모두 필요하며 **target A의 당시 원본**을 공급한다. B의 None인7개 참조를 A 값으로 바꾸지 않는다. 미확보를 nullable로 표현해서 성공 처리하지 않는다.

## 7. 동일 호출과 Acceptance revision 결합

Artifact의 명시 acceptance_ref entry를 찾고 그 entry.acceptance가 인자 acceptance와 **동일 객체**인지 확인한다. root ref도 record.review_artifact_ref와 같아야 한다. 다른 ref·동일 값의 record 복사본·다른 Artifact와의 혼합은 대응 오류다. loader의20값 비교/재구성을 다시 구현하지 않는다.

다만 is/equality/타입만으로 실제 loader 통과를 증명하지 못한다. private A/C가 **같은 호출에서 실제 loader를 실행하고 그 반환값을 직접 전달**해야 한다. 외부 Artifact/검증 bool을 받는 public 우회 경로를 만들지 않는다. Review bytes hash를 content 쪽에서 다시 계산하는 대체 API도 만들지 않는다.

대상 identity는 기존 record의 ref/version/status·policy/scope/benefit·Coverage7/Benefit4 binding·reviewed_at/valid_until/revokes다. 서명·사람 권한·전체 이력 완전성까지 로컬 계산으로 인증하지는 못한다.

## 8. Historical BenefitSnapshot 대조

실제 historical_benefit에 기존 fingerprint_benefit_snapshot을 적용하여 대상 record의 benefit_fingerprint와 비교한다. 다음 축은 각각 독립적으로 비교한다.

| 축 | 대응 |
|---|---|
| identity | policy_id/scope/benefit_id/benefit_version과 대상 record의 exact equality |
| 정의 내용 | 기존 함수가 계산한 실제15key 정의 payload fp |
| provenance | Snapshot.dataset_version=record.benefit_dataset_version=당시 Manifest.dataset_version |
| Registry | Snapshot.source_registry_fingerprint=record 값=실제 당시 Registry domain fp |

정의 fp는 dataset/whole Registry를 포함하지 않으므로 별도 비교를 생략하지 않는다. raw file SHA와도 다르다. 잘못된 역사 version·같은 version의 다른 내용·같은 정의의 다른 provenance는 **당시 원본의 대응 모순**이며 정상 stale로 낮추지 않는다.

Snapshot.benefit_evidence_refs는 값과 fingerprint에서 순서/중복을 보존한다. 사용 시 duplicate는 validate_evidence_refs로 거부한다. 복사/dedupe하여 다른 정의로 수정하지 않는다.

## 9. Historical Coverage와 FULL

| record 축 | 비교 원본 |
|---|---|
| policy_id/scope | coverage.inventory/ReviewContext/Benefit와 선택 Envelope의 policy/edition |
| coverage_inventory_version/fingerprint | 당시 inventory와 fingerprint_condition_inventory의 실제 결과 |
| coverage_rule_version/policy_tree_fingerprint | 당시 envelope.policy와 fingerprint_policy_tree의 실제 결과 |
| coverage_dataset_version | 당시 Manifest/ReviewContext/Envelope dataset |
| coverage_source_registry_fingerprint | 실제 당시 Registry fp와 ReviewContext |
| coverage_implementation_fingerprint | 당시 ReviewContext baseline·Manifest engine ZIP·명시 ZIP raw SHA |

Envelope.edition_id와 scope.edition_id는 비교할 수 있다. quarter를 Envelope의 연도/공고일에서 만들지는 않는다. generic Coverage scope가 분기/연간의 명시 원본이다. legacy Envelope.coverage/evaluation_scope를 generic FULL로 변환하지 않는다.

명시 Review refs는 Inventory.completeness_review_ref와 각 ConditionBinding.implementation_review_ref에서 당시 ReviewContext로 연결한다. 실제 존재하는 _resolve_inventory_review/_resolve_implementation_review와 _match_inventory_review/_match_implementation_review의 대상/version/fp 규약을 재사용한다. root의 존재/소속은 기존 Coverage 구조 규약, 필요한 subtree fp는 fingerprint_rule_subtree를 사용한다. MATCHED/STALE/MISSING을 문자열로 조작하지 않는다.

당시 원본으로 공급된 Review가 없거나 다른 version이면 당시 확인본을 재현하지 못한 것이다. 독립 same-version 모순은 기존 Data Error를 우선한다. 기존 matcher의 STALE은 공급된 역사 자료 내부의 비교 결과이며, 이를 현재 Acceptance의 정상 변경으로 자동 변환하지 않는다. 원본이 부족한 상태에서 검증 성공을 반환하지 않는다.

**결정: Content Validator는 Coverage evaluator를 자동 재실행하지 않고, 외부 FULL bool/Result도 받지 않는다.** L1/L2 binding 검사와 FULL gate는 별개다. 발급 시 FULL 확인은 당시 trusted producer/검토 기록을 보존한다. 재현이 필요하면 명시된 당시 ZIP/환경에서 official evaluate_eligibility_coverage를 실행한다. 현재 engine으로 계산한 결과에 과거 implementation SHA를 붙이지 않는다. current C의 producer1회도 별도 현재 자료를 사용한다.

EligibilityCoverageResult에는 inventory/tree fp 저장 필드가 없어 단독으로 원본군을 대신하지 못한다. private factory/token도 외부 실행 인증이나 영구 감사 증명이 아니다. M2.53은 합성 verify-only이며 당시 업무 실행 worker는 아직 없다.

Manifest engine SHA와 implementation SHA를 같은 ZIP에 결합하는 것은 M2.52의 공유 source ZIP 프로파일을 확인한 경우의 규칙이다. 모든 과거 모델의 서로 다른 hash 영역을 일괄 같다고 강제하지 않는다. 과거 프로파일/실행 대응이 미확보면 준비 부족으로 보고하고 기존 label/literal을 새 hash로 고치지 않는다.

## 10. Manifest·Registry 대조

선택 Envelope는 historical_envelopes의 유일한 원본이다. 전체 tuple을 validate_dataset_manifest에 공급한다. 구현 호환성이 성립하는 당시 환경에서 기존 validator를 쓰고, 선택 Envelope 하나를 전체 release로 취급하지 않는다. policy refs/source_versions·Registry fp·Envelope fp/edition/rule/schema/dataset을 확인한다. validate_envelope_sources의 source version·leaf refs·policy applicability·last_verified_at 도출도 이용한다.

과거 Manifest.engine_version이 검증 실행 코드와 다르면 **역사 검증 환경 준비 부족**이다. 기존 validator를 복제해 ENGINE_VERSION 비교만 삭제하지 않는다. 현재 환경과 호환되지 않는다는 이유로 정당한 역사 자료를 거짓으로 단정하지 않는다.

entry.source_registry_ref와 Manifest.source_registry.artifact, 선택 policy_envelope_ref와 해당 PolicyEditionReference.artifact는 exact 대응을 요구한다. Manifest.review_manifest는 기존 정책 검토 자료의 참조이며 coverage_reviews_ref와 자동으로 같은 의미/타입이라고 가정하지 않는다.

DatasetManifest.fingerprint()/fingerprint_policy_envelope/fingerprint_source_registry는 각각 domain 지문이다. dataset_manifest_ref.sha256은 실제 파일 bytes 지문이므로 domain fp와 직접 같다고 비교하지 않는다. Registry 전체 fp와 개별 문서 d version도 별개다.

## 11. 5 Claim과 정의값 대조

| Claim | 기존 Snapshot 값 | 공식 의미 검토 |
|---|---|---|
| AMOUNT | amount_type/amount_krw/amount_description | 금액·정액/변동 근거 |
| CADENCE | payment_cadence | 월/분기/단발 등의 의미 |
| MEDIUM | benefit_medium | 현금/지역화폐/바우처 등의 수단 |
| RESTRICTION | restriction/restriction_details | 사용 대상·제한·예외 |
| APPLICABLE_MONTHS | applicable_months | 명시 적용/지급월 |

5행 필수·순서·행 내부 duplicate·nonempty refs는 기존 Entry/Mapping이 이미 검사한다. 새 순서/중복 규칙을 만들지 않는다. 각 mapping ref가 당시 Snapshot.benefit_evidence_refs에 포함돼야 한다. **부분목록의 membership**을 검사하며 상대 순서가 Snapshot과 같아야 한다는 제약을 추가하지 않는다. mapping의 원래 순서·복수 근거·claim 간 공유를 보존한다.

Snapshot의 보충 ref가 mapping에서 미사용이어도 허용한다. 삭제하지 않고 source 사용 검증에는 포함한다. Snapshot 밖 ref는 Registry에 존재해도 대응 오류다. SOURCE_BINDING claim은 추가하지 않는다.

## 12. SourceBinding·Registry·locator

대상 entry.source_bindings는 **당시 Envelope.source_bindings ∪ 당시 Snapshot.source_bindings**의 정확한 합집합이다. 같은 source ID/다른 d version·누락·추가·duplicate를 거부한다. 기존 Entry의 ID 정렬/유일성을 변경하지 않는다. source_documents도 이 순서/개수/binding 값과 일치해야 한다.

각 binding은 Registry.get_source로 SourceDocument를 찾아 document_version을 비교한다. Benefit refs 전체를 validate_evidence_refs로 검사하고 SourceEvidence.applicable_policy_ids에 대상 policy가 있는지 확인한다. Envelope leaf refs는 validate_envelope_sources를 사용한다. Inventory 조건의 evidence refs도 각 조건 단위로 문법/중복/Registry/policy 대응을 확인할 수 있다.

Inventory refs가 정책+Benefit 합집합 밖 source를 쓰는 경우, 그 사실만으로 기존 정상 모델을 Data Error로 만들거나 Entry에 binding을 몰래 추가하지 않는다. 이 합집합은 M2.54의 고정 계약이다. Inventory 완결성의 별도 공식 원문 증거는 당시 Coverage Review의 준비 책임이다. 필요한 증거가 미확보라면 그 검토가 끝났다고 주장하지 않는다. 모든 leaf/조건 refs를 flatten해서 정상 공통 근거를 duplicate로 거부하지도 않는다.

registry.resolve는 문서/locator의 ACTIVE도 검사한다. VERIFIED/검증일/freshness·공식 의미 인증은 하지 않는다. 존재만 확인하는 has_evidence로 resolve를 대체하지 않는다. Registry 등록이 현재 공식 사이트 최신성을 인증하지 않는다.

## 13. ArtifactReference와 실제 bytes의 결합 공백

historical_artifact_bytes 후보는 새 모델이 아닌 exact `(ArtifactReference, bytes)` pair의 유한 tuple이다. 대상 entry의7참조, Manifest 전체 policy artifact/Registry artifact/review_manifest(있으면), source_documents의 공식 원문 artifact를 대상으로 한다. 같은 exact 참조가 여러 역할이면1pair 공유를 허용한다. 같은 path/다른 hash·중복 pair·필수 pair 누락·무관한 pair 추가는 대응 오류다. supersedes/URL을 따라가는 범용 재귀 store는 만들지 않는다.

외부 preparation이 한 번 확보한 immutable bytes를 공급한다. pure 계산에서 실제 SHA256과 선언 sha256을 비교할 수 있다. 공식 원문의 SourceDocument.content_sha256가 있으면 그것과도 일치해야 한다. None이면 ReviewSourceOriginal의 raw hash에 결합하되 공식성이 인증됐다고 말하지 않는다.

다음 두 검사는 별개다.

1. bytes B의 hash가 ArtifactReference의 H와 같다.
2. typed object T가 **그 동일 B를 승인된 strict decoder로 복원한 값**이다.

현재1은 계산할 수 있지만 Benefit/Coverage/ReviewContext/Manifest의2를 닫는 decoder/준비 계약이 없다. `(ref, T)`와 `(ref, B)`를 함께 전달했다는 사실, T의 domain fp가 record와 같다는 사실만으로2를 증명하지 못한다. T.to_dict를 canonical화한 hash를 B의 raw hash 대신 쓰지도 않는다.

**구체적 예:** Coverage1의 bytes B는 H에 맞는다. 다른 Coverage2는 같은 inventory/tree를 갖지만 bindings/review_ref가 다를 수 있다. inventory/tree fp는 Coverage 파일 전체의 일치를 증명하지 못한다. 올바른 B와 잘못된 Coverage2를 혼합하는 경로를 bool/tuple 선언으로 막았다고 가정하지 않는다.

parse_policy_envelope/parse_source_registry는 기존 구조 복원에 사용할 수 있다. 다만 raw bytes 확보/SHA/그 동일 bytes 파싱의 연결은 외부 준비가 담당해야 한다. 나머지4개 원본도 to_dict만 보고 loader를 발명하지 말고 형식을 먼저 닫아야 한다. Review Artifact C1을 다른 원본에 일괄 적용하지 않는다. ZIP raw hash 일치는 실제 그 코드의 실행 대응과도 별개다.

## 14. Historical 원칙

당시 Benefit/Coverage/ReviewContext/Manifest/Registry/공식 원문을 공급한다. current b0002를 A가 검토한 b0001의 대체물로 쓰지 않는다. 현재 Registry도 과거 문서 version/locator의 대체물이 아니다.

| 상황 | 분류 |
|---|---|
| 정확한 당시 원본과 record 대응 | L1 정상 후보, L2 복원/L3는 별도 |
| 당시 원본 미확보·strict 복원 경로 없음 | 외부 준비 미완료, 성공 없음 |
| 당시 것으로 공급한 version/dataset/Registry가 record와 다름 | 대응 Data Error, 정상 stale로 낮추지 않음 |
| 당시 원본 정확, current b0002 | 본 함수 입력 밖. 후속 current evaluator가 정상 변경 판단 |
| 같은 version의 내용 모순 | Data Error. 다른 변경/만료/철회로 숨기지 않음 |

공식 source가 나중에 바뀌거나 철회돼도 당시 보존 원문을 수정하지 않는다. 과거 정확성과 현재 source 사용요건은 별도이며 current gate는 현재 자료와 명시 사용일로 확인한다.

## 15. ACCEPTED·REVOKED

ACCEPTED의 effective subject는 선택R이며 대상 entry는 artifact의 R이다. FIXED·알려진 cadence/medium/restriction·명시 finite applicable_months가 필요하다.0원 FIXED도 정상이다. VARIABLE/UNKNOWN/불완전한 역사 승인 정의는 발급 기준과 모순되는 Data Error이며 정상 current reason9로 바꾸지 않는다. QUARTERLY/LOCAL_CURRENCY만으로 검토 대상에서 제외하지 않고 월 현금 변환/Bridge도 판단하지 않는다.

REVOKED의 effective subject는 기존 Context의 target ACCEPTED A다. 선택 결정은 B로 유지한다. Context의 B가 인자 원본인지 확인하고, 기존 Context가 보장한 target 존재/ACCEPTED/11binding 일치·후행 revision/날짜·단일 edge를 이용한다. 철회 알고리즘을 복제하지 않는다. target A의 entry는 revoked_target_artifact의 실제 loader 반환값에서 A와 is로 연결한다.

B의 빈 claim/source 목록과7참조 None을 유지한다. A의 당시 원본을 추적해 철회 대상 snapshot을 특정하지만 B에5claim 재승인표를 만들지 않는다. B의 review_note/검토일/기한/manual_scenario_ids는 철회 사유 기록이다. 실제 철회 권한은 외부 책임이며 A의 정의를 B가 다시 승인한 것이 아니다.

Target 원본/Artifact 미확보는 준비 실패다. B를 이력에서 제거하거나 B의 기한 경과를 이유로 A를 복구하지 않는다. 후속 evaluator에서도 B가 USABLE이 되지 않는다.

## 16. Source 사용요건과 실제 의미 검토

Source Usage Gate는 미구현 별도 gate다. 역사 발급 시 기준은 effective subject A.reviewed_at과 당시 Manifest.freshness_max_age_days다. 현재 기준은 후속 evaluator의 data_use_date/현재 Manifest다. 문서와 사용 locator의 ACTIVE/VERIFIED·verified_at를 각각 확인하고 `0 <= (기준일 - verified_at).days <= N`이라는 기존 방침을 유지한다. 자동7일·현재시각·효력일/신청일과의 자동 동일시는 없다.

resolve의 ACTIVE 참조 오류는 기존 Data Error다. 유효하게 구성된 DRAFT/STALE·미확인/오래된 검증일은 source 사용요건 미완료로 구분해 외부 gate를 닫는다. content 쪽에서 기존12reason으로 변환하지 않는다. SourceBinding에 없는 상태 필드를 추가하지 않는다.

L3는 해당 Snapshot 값과 **L2에서 결합한 동일 공식 원문 bytes**를 준비자/별도 검토자가 실제로 열어 대조하는 책임이다. '분기별 25만 원'의 의미 검토를 ref 존재로 대체하지 않는다. LLM이 조건/금액/claim 지지를 만들어내거나 심사하지 않는다.

기존 entry의 mapping·준비/검토 handle·review_note·검토일·manual_scenario_ids는 그 대상에 대해 검토했다고 기록하는 곳이다. 실제 수행·독립성·권한·내용 지지의 진실성은 그 metadata만으로 인증하지 못한다. 미실시/지지 불명은 미검토, 지지하지 않는다고 확인되면 외부 검토 불합격으로 중단한다. 새 전자서명/권한 framework나 bool로 해결한 것처럼 하지 않는다.

## 17. Pure 검증·단계 순서

아래는 원본 복원 계약을 닫은 뒤의 구현 후보 순서다. 현재 실행된 기능이 아니다.

| 단계 | 검사/책임 |
|---|---|
| A0 외부 | Review bytes→실제 loader, 당시 자료 확보·strict 복원·같은 호출 결합 |
| CV0 |11입력 exact 타입/tuple/pair/nullable/status 조합 |
| CV1 |entry/record is와 ref, REVOKED Context/target Artifact 결합 |
| CV2 |historical Benefit identity/실제 정의 fp/provenance 독립 비교 |
| CV3 |historical Coverage9축·명시 Review/condition/root 대응. FULL 생성 없음 |
| CV4 |호환되는 당시 환경에서 전체 Manifest/Registry/Envelope 대조 |
| CV5 |source 합집합·version·locator/policy·원래 tuple 내부 중복 |
| CV6 |claim refs의 당시 Snapshot membership과 공식 참조 대응 |
| CV7 |유한 참조/bytes 집합·실제 SHA·동일 bytes에서 typed 원본 복원 결합 |
| CV8 |기계적 L1/L2 완료 때만 None, 부분 성공 없음 |
| A/C 외부 |Source 요건/L3·권한/필요한 역사 FULL 근거 확인. 미완료면 중단 |

기존 모델의 claim 순서/duplicate와 Context의11binding 규칙을 재구현하지 않는다. 새 함수는 상대 원본이 필요한 비교에 한정한다. filesystem/network/Git/environment/current time/전역 mutable cache/LLM/사용자 자격/현금흐름 계산을 사용하지 않는다. explicit bytes SHA와 domain fp는 순수 계산이다.

공급된 독립 Data Error를 L3 미실시·만료·source 미검토 같은 정상 미완료로 숨기지 않는다. 자료 자체가 없으면 A0에서 함수 진입을 닫는다. 이때 미확보 자료까지 검사했다고 주장하지 않는다. 부분 진단을 전체 성공으로 반환하지 않는다.

## 18. Data Error·준비 실패·미검토

| 상황 | 분류/기대 |
|---|---|
| A 공급 원본의 target/version/fp/provenance 모순 | Data Error, PolicyDataError. 정상 reason/UNKNOWN으로 바꾸지 않음 |
| B 명시 source/locator 없음·version/SHA 불일치 | Data Error, 기존 참조 예외 또는 고정 대응 오류 |
| C 원본 미확보·필요 decoder/역사 환경 없음 | 외부 준비 실패/미완료. 성공 None/정상 Result 없음 |
| D 원문이 claim을 지지하지 않는다고 확인 | 외부 내용 검토 불합격, 발급/사용 준비 실패로 중단 |
| E 미실시·지지 불명·권한 미확인 | 정상 검토 미완료로 외부에서 중단. 구조 모순과 별개 |
| F L1/L2 모두 성립 | pure 함수 None 후보. L3/current gate는 포함하지 않음 |
| L1/L2와 외부 L3/사용요건 모두 완료 | A/C가 current 평가로 진행할 조건. 지급/Bridge 승인 아님 |

기존 SourceValidationError/EnvelopeValidationError/ManifestValidationError는 원래 PolicyDataError로 전파한다. 신규 prefix 후보는 INVALID_ACCEPTANCE_REVIEW_CONTENT_INPUT, ACCEPTANCE_REVIEW_CONTENT_IDENTITY_MISMATCH, ACCEPTANCE_REVIEW_CONTENT_SNAPSHOT_MISMATCH, ACCEPTANCE_REVIEW_CONTENT_SOURCE_MISMATCH, ACCEPTANCE_REVIEW_CONTENT_CLAIM_MISMATCH, ACCEPTANCE_REVIEW_CONTENT_ORIGINAL_MISMATCH다. 현재 구현된 오류/함수가 아니다. payload/ref/path/원문을 오류에 출력하지 않는다.

미확보/decoder 부재/실제 검토 미실시를 이 모순 prefix로 위장하지 않는다. 외부 준비 실패와 정상 미검토를 구분한다. loader의15prefix와 기존 AcceptanceReason12개는 변경하지 않는다. B~E를 BENEFIT_METADATA_NOT_REVIEWED 하나로 합치지 않는다.

## 19. 성공 반환 계약

**A: 성공 시 None, 기계적 모순 시 PolicyDataError**를 선택한다. 새 결과 모델이나 Artifact 재반환은 입력 identity 재게시만 늘리고 재사용 가능한 인증처럼 보일 위험이 있어 선택하지 않는다. prepared=True 같은 bool도 없다.

None은 같은 호출의 공급 원본에 대한 L1/L2 비교만 의미한다. 다른 snapshot/Context/일자/요청에서 쓸 cache/token이 아니다. L3 미실시를 보완하지 않는다. 지금은 L2 결합이 미완료여서 전체 함수의 성공 경로 구현 승인을 보류한다.

## 20. Same-call A/C 연결

```text
trusted A/C의 한 호출
  →실제 Review loader(전체 expected 원본)→그 Artifact/record 직접 보존
  →당시 Snapshot/Coverage/Review/Manifest/Registry/공식 원문/ZIP 확보
  →같은 bytes hash·승인된 decoder→그 typed 원본 직접 보존
  →Content Validator의 L1/L2 기계 검사
  →외부 L3/Source 사용요건/필요한 역사 FULL 근거 확인, 미완료면 중단
  →현재 release/Benefit은 별도 현재 원본으로 확인
  →current Coverage official producer1회
  →기존8-input 내부 Acceptance evaluator B
  →같은 current Benefit 원본으로 candidate
```

Context/사용일/원본/명시 ref가 바뀌면 새 호출이다. precomputed Result/verified flag/다른 호출의 None 성공을 받지 않는다. 후보11입력을 B에 추가하지 않는다. 역사 원본과 현재 원본을 서로 대체하지 않는다.

orchestration·Source Gate·evaluator/candidate/Bridge는 아직 없다. C가 실제 loader/decoder/validator를 호출해야 하며 private 이름/is/tuple만으로 악의적인 같은 process caller를 격리하지 못한다.

## 21. 합성 검증 시나리오 — 48개

문서 계획48개이며 실행 테스트0개다. 정상 사례는 당시 원본과 L2 준비 계약이 성립한 미래 합성 fixture를 전제로 한다. L3의 진실성을 기계 fixture로 실증하지 않는다. V=향후 pure 검사, P=외부 준비, H=사람/권한, C=같은 호출, B=후속 current 평가다.

| ID | 입력/전제 | 예상 결과/분류 | 책임 | 후속 실행 테스트 |
|---|---|---|---|---|
| RC01 |정확한 loader/R/모든 당시 원본 |L1/L2 정상, L3 별도 |V/P |준비 계약 후 가능 |
| RC02 |잘못된 acceptance_ref |identity Data Error |V |가능 |
| RC03 |같은 값의 record 복사본으로 교체 |same-call identity 오류 |V/C |가능 |
| RC04 |정확한 b0001/정의 fp |정의 대응 정상 |V |가능 |
| RC05 |과거 원본으로 current b0002 공급 |historical version 오류 |V |가능 |
| RC06 |같은 b version/다른 fp |Data Error, stale로 낮추지 않음 |V |가능 |
| RC07 |정의 같고 dataset 다름 |historical provenance 오류 |V |가능 |
| RC08 |정의 같고 Registry fp 다름 |historical Registry 오류 |V |가능 |
| RC09 |Inventory version/fp 다름 |Coverage 대응 오류 |V |가능 |
| RC10 |당시 tree fp 다름 |Coverage 대응 오류 |V |가능 |
| RC11 |ZIP SHA/implementation baseline 다름 |Data Error, 실제 실행 별개 |V/P |hash 부분 가능 |
| RC12 |Review ref/condition/root 정확 |참조 대응 정상, FULL 생성 없음 |V |가능 |
| RC13 |Review ref 없음/다른 root |기존 참조 오류/원본 부족 |V/P |가능 |
| RC14 |전체 Manifest/Registry/Envelopes 정상 |release domain 대응 정상 |V/P |호환 환경에서 가능 |
| RC15 |일부 Manifest Envelope 누락 |전체 release 대응 오류 |V/P |가능 |
| RC16 |당시 engine과 현재 engine 비호환 |역사 환경 준비 부족 |P |경계 검사 가능 |
| RC17 |5claim/Snapshot refs 부분집합 |L1 정상, 의미는 미인증 |V/H |기계 부분 가능 |
| RC18 |한 ref를 여러 claim이 공유 |허용, 의미는 H |V/H |기계 부분 가능 |
| RC19 |Snapshot 밖 claim ref |Registry에 있어도 오류 |V |가능 |
| RC20 |Snapshot 보충 ref가 mapping 미사용 |허용, source 검사는 수행 |V |가능 |
| RC21 |Snapshot refs duplicate |기존 duplicate 오류 |V |가능 |
| RC22 |정확한 source 합집합/d version |source 대응 정상 |V |가능 |
| RC23 |source binding 추가/누락 |Data Error |V |가능 |
| RC24 |source 문서 d version 다름 |Data Error |V |가능 |
| RC25 |source/locator 없음 |기존 참조 오류 |V |가능 |
| RC26 |다른 policy의 evidence |policy applicability 오류 |V |가능 |
| RC27 |정확한 원문 ref/bytes SHA |bytes 대응만 정상 |V/P |가능 |
| RC28 |공식 원문 bytes SHA 불일치 |Data Error |V/P |가능 |
| RC29 |content_sha256 존재/불일치 |Data Error |V |가능 |
| RC30 |content_sha256=None |Review raw hash 사용, 공식성 별개 |V/H |기계 부분 가능 |
| RC31 |bytes는 맞고 typed Coverage 교체 |decoder 결합 없으면 미완료 |P/V |준비 계약 후 가능 |
| RC32 |같은 inventory/tree, 다른 bindings/ref |지문만으로 전체 원본 일치 아님 |P/V |준비 계약 후 가능 |
| RC33 |공식 원문 ref만 있고 bytes 없음 |외부 준비 실패 |P |가능 |
| RC34 |과거 Benefit 원본 미확보 |준비 실패, current 대체 없음 |P |가능 |
| RC35 |strict decoder 없이 to_dict만 있음 |L2 미완료, 성공 없음 |P |준비 계약 대상 |
| RC36 |원문 대조 미실시 |정상 검토 미완료, 중단 |H/C |상태 경계만 가능 |
| RC37 |claim 지지 여부 불명 |정상 검토 미완료, 중단 |H/C |상태 경계만 가능 |
| RC38 |원문이 claim을 지지하지 않음 |외부 검토 불합격 |H |실제 의미는 사람 |
| RC39 |ACTIVE이나 DRAFT/확인일 부족 |source 사용요건 미완료 |H/C |상태/날짜 부분 가능 |
| RC40 |FIXED/알려진 metadata/finite 월 |역사 정의 완전성 정상 |V |가능 |
| RC41 |VARIABLE/UNKNOWN 역사 승인 |발급 기준 모순 오류 |V |가능 |
| RC42 |완전한 QUARTERLY/LOCAL_CURRENCY |정의 대응 허용, Bridge 별도 |V/B |기계 부분 가능 |
| RC43 |B와 Context의 정확한 A |target 대응, 재승인 없음 |V/P |가능 |
| RC44 |B의 target Artifact 미확보 |준비 실패, B 제거/A 복구 없음 |P/C |경계 검사 가능 |
| RC45 |Loader 성공/ref 유효만 있음 |companion L2/L3 완료 아님 |C/P/H |경계 검사 가능 |
| RC46 |Content 기계 검증 정상/Policy DRAFT |VERIFIED/current USABLE 아님 |C/B |후속 gate 검사 |
| RC47 |Content 정상/current b0002/SLICE |역사 보존, current gate 별도 |C/B |후속 gate 검사 |
| RC48 |기계 대응 정상/Bridge 비지원·권한 불명 |지급/Cashflow 승인 없음 |C/H/B |경계 검사 가능 |

실제 원문의 의미를 사람이 올바르게 해석했다는 사실까지 synthetic pytest로 증명하지 않는다. 현재 기능 테스트를 추가하거나 기존 loader/value tests를 content 검증 완료로 세지 않는다.

## 22. 미해결 사항과 다음 최소 작업

**핵심 공백은13절의 bytes→typed 원본 결합이다.** 현재 타입과 명시 bytes만으로 미확정 raw 형식을 임의 해석해 모든 L2 검사가 가능하다고 말할 수 없다. Verified DTO/성공 bool을 추가해도 해결되지 않는다.

다음 최소 작업은 **Historical BenefitSnapshot Artifact Preparation Contract** 한 개다. accepted_terms_ref의 동일 bytes에 대해 exact raw16key·Enum·Scope·YYYY-MM·null·strict decode·raw SHA·기존 BenefitSnapshot 복원·같은 호출의 원본 보존을 확정한다. 새 정의 모델을 만들지 않고 기존16필드로 복원한다. Review Artifact C1을 자동 전용하지 않고 원본 자체의 형식/기대값/오류 순서를 명시한다.

전체7파일의 범용 플랫폼이 아니라 첫 실제 경로인 accepted terms부터 닫는다. Coverage/ReviewContext/Manifest의 유사한 공백은 여전히 남으며 이 작은 작업으로 모두 완료됐다고 하지 않는다.

Source Usage Gate는 기존 status/date/N으로 표현 가능하지만 미구현이다. L3는 기존 Artifact 대상/기록과 외부 사람 검토의 책임으로 연결한다. 새 증거/권한 framework를 먼저 만드는 것을 결론으로 삼지 않는다. 역사 engine/FULL 실행과 actual legacy→FULL 공백도 남는다.

Assumption A1: 신뢰된 준비자가 정확한 원본과 누락 없는 이력을 공급한다. A2: 사람이 같은 공식 원문을 실제로 대조하며 권한/독립성도 외부에서 확인한다. hash가 이 가정을 보장하지 않는다. 실제 archive/decoder/공식 내용/검토 기록을 확보하거나 발급한 것처럼 표현하지 않는다.

## 23. 최종 판단

**NEEDS_HISTORICAL_ARTIFACT_PREPARATION_CONTRACT**

최소 API 후보11입력과 기계적 비교/None 반환 의미를 선택했다. 하지만 필요한 원본 일부의 strict bytes 복원 계약이 없어 모든 필수 L2 대응을 기존 기능으로 검증할 수 없다. 따라서 Content Validator 전체의 구현 준비 완료를 승인하지 않는다.

기존 모델/loader/freeze와 충돌하지 않는다. 원본 미검증을 입력 선언으로 숨기지 않기 위한 구현 순서 판단이며 기존 core/M2.57을 폐기하는 판단이 아니다. 다음은22절의 accepted_terms 한 경로다.

## 24. 검증·보존 기록

- 작업 전 전체 pytest: **7,673 passed in 70.74s / skipped0 / failed0 / timeout0**.
- 신규 실행 테스트: **0개**. 문서 시나리오48개와 보조 검수는 실행 테스트 수에 더하지 않는다.
- 작업 후 전체 pytest: **7,673 passed in 63.08s / skipped0 / failed0 / timeout0**. 전후 모두 timeout이 재발하지 않았고 테스트/timeout 설정 변경도 없다. 기존 loader332개/value273개/bootstrap106개를 포함한다.
- 사전 backend/tests/data/docs/tools174개(실제 releases·pycache 별도)의 SHA256이 모두 동일하다. 새 문서1개만 추가해 최종175개이며 기존 파일 수정/삭제0개다. 기존 모든 테스트/fixture/기대값·GV01~GV15/BV01~BV16 literal·Coverage freeze·strict loader·기존 Acceptance/Benefit/Cashflow·기존 문서를 보존했다.
- 실제 release6개는 SHA256·경로·크기·수정시각 모두 동일하다. actual Review Artifact/Acceptance/역사 Snapshot/정책 금액·새 정책 지문·실행 ZIP은 생성하지 않았다.
- 문서 검수:24개 절과 RC01~RC48 연속/유일성, 표 column/fence·UTF-8·한국어 본문, 후보 API11개 필수 keyword-only 인자를 확인했다. 검수는 새 기능 구현/실행 테스트로 세지 않는다.
- ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. actual Ansan DRAFT/CONDITION_SLICE·정책 혜택 Cashflow 반영0원 원칙을 유지한다. 실제 검토/원본/금액/새 정책 지문은 생성하지 않는다.

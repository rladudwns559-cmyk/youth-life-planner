# M2.54 — Acceptance Review Artifact Content Binding Contract

## 1. 목적과 범위

특정 Acceptance revision에서 정확한 Coverage/Benefit 정의와 공식 근거를 대조했다고 기록한 **불변 검토 산출물**을 정의한다. `review_artifact_ref`의 존재와 실제 자료 확보·내용 대응을 구별한다. 문서 설계만 수행하며 코드·테스트·실제 정책 자료를 생성하거나 변경하지 않는다.

기준은 M2.45~M2.53의 확정 계약이다. 특히 RECORD_SPEC 17절, CONTEXT_SPEC의 공유 artifact 허용, EVALUATOR_SPEC 11~12절을 구체화한다. 검토 자료는 행정기관 승인·지급 결정·실제 사람의 판단 진실성 또는 권한을 암호학적으로 보장하지 않는다. 사용자 경제정보·실명·LLM 선언을 승인 근거로 수집하지 않는다.

## 2. 확인한 Source of Truth와 구현 상태

| 확인한 문서 | 유지할 계약 |
|---|---|
| BENEFIT_ACCEPTANCE_RECORD_SPEC.md | 21필드, ACCEPTED/REVOKED, readable terms·5claim·원본·검토 metadata의 artifact 보존 |
| BENEFIT_ACCEPTANCE_CONTEXT_SPEC.md | 4필드, 명시 선택, 철회 연결, AC113의 여러 revision에 의한 artifact 공유 |
| BENEFIT_ACCEPTANCE_EVALUATION_RESULT_SPEC.md | 9필드+파생 status, 12개 reason |
| BENEFIT_ACCEPTANCE_EVALUATOR_SPEC.md | 8개 내부 입력, 외부 준비 A/순수 계산 B/동일 호출 C, 역사 원본과 current 비교 분리 |
| COVERAGE_TO_BENEFIT_ACCEPTANCE_SPEC.md | Coverage·정의·provenance·현재 사용·개인/월 적용의 분리 |
| BENEFIT_SNAPSHOT_SPEC.md | 16필드, 초기 FIXED 한정 수용, 정확한 지급월/제한·중복 보존 |
| POLICY_BENEFIT_ACCEPTANCE_SPEC.md | accepted terms·근거·기한·철회 의미; 저장 위치는 후속 RECORD_SPEC 보완 적용 |
| RELEASE_ARTIFACT_EXECUTION_BINDING_SPEC.md | 실행 ZIP identity·같은 bytes 실행 검증, 합성 verify-only 한계 |
| ELIGIBILITY_COVERAGE_CORE_FREEZE.md | FROZEN_WITH_POLICY_SPECIFIC_BLOCKERS |
| DATA_MODEL.md / ARCHITECTURE.md | 현재 모듈 경계와 구현 상태, 실제 안산 SLICE/DRAFT 제한 |

실제 코드의 PolicyBenefitAcceptance/BenefitAcceptanceStatus, BenefitSnapshot, fingerprint_benefit_snapshot, SourceBinding/SourceEvidence/SourceDocument/SourceRegistry, DatasetManifest/ArtifactReference, ApplicabilityScope, PolicyDataError 및 source/evidence validators를 확인했다. SourceBinding은 **source_document_id·document_version의 2필드뿐**이다. ApplicabilityScope의 quarter=None은 연간 범위이며 날짜로 추론하지 않는다.

현재 구현됨: Snapshot/지문, Acceptance/Context/private resolver/결과 모델, frozen Coverage, 기존 메모리 source 검증, 합성 ZIP bootstrap. 미구현: 아래 Review Artifact 타입·loader·validator·발급 과정·A/C 결합·Acceptance evaluator·전체 Source Gate·Bridge. 이 문서의 타입/함수 이름은 모두 **후속 구현 제안**이다.

## 3. 세 종류 Artifact의 차이

| 종류 | 의미 | 이 자료만으로 증명하지 못하는 것 |
|---|---|---|
| 실행 코드 ZIP | M2.52/M2.53 코드 bytes·import 실행 대응 | 정책 내용의 정확성, 혜택 검토 수행 |
| 공식 Source | 공고·안내 원문과 Registry의 문서/locator 설명 | 특정 Benefit 정의의 검토·승인 |
| Acceptance Review Artifact | 특정 revision·원본·claim별 근거·승인 또는 철회 판단 기록 | 행정 승인, 검토자 권한/진실성, 현재 usability |

M2.53 합성 verify-only 성공을 실제 실행 release 또는 Review Artifact 검증으로 확대하지 않는다.

## 4. Artifact identity 방식 결정

**A: content-addressed ref를 선택한다.** 새 자료 준비 프로파일은 정확히 `acceptance-review:sha256:<소문자 16진 64자리>`다. 공백 제거·대소문자 교정·URL 추정·latest 선택을 하지 않는다.

| 후보 | 장점 | 추가 책임/선택 |
|---|---|---|
| A 내용 주소 | 기존 ref 하나에 기대 raw bytes SHA256 포함, 별도 index 불필요 | 새 외부 프로파일 parser만 필요; 선택 |
| B opaque ref+불변 index+SHA256 | 기존 ref를 그대로 resolve 가능 | index 자체 identity·신뢰 anchor·overwrite/이력 검증이 추가됨; MVP 제외 |
| C 기존 Source/Manifest 재사용 | 기존 참조 타입 일부 재사용 가능 | SourceType은 공식 자료 용도이고 review_manifest는 기존 정책 검토 자료 참조; Acceptance index/결정 mapping이 아님. 의미 전용 금지 |

**영향을 먼저 명시한다:** 기존21필드 constructor의 opaque nonblank 문자열 계약은 그대로다. 기존 opaque 값도 구조적으로 유효하다. 단 이번 외부 content-binding 프로파일로 실제 검증하려면 위 ref가 필요하다. legacy opaque 자료는 자동 신뢰·문자열 치환·무음 migration 없이 외부 준비 차단한다. 실제 Acceptance 자료는 아직 없으므로 실제 migration 대상0개다. 기존 합성 opaque fixture/기대값도 수정하지 않는다. 향후 실제 legacy 자료가 생기면 원본을 확보한 새 검토/revision 발급이 필요하다.

## 5. 기대 hash 보관·조회·bytes 검증

기대 hash는 신뢰된 원본 Acceptance의 `review_artifact_ref` suffix에 보관한다. Artifact가 본문에 써 놓은 hash를 기대값으로 믿지 않는다. 조회는 외부에서 명시한 archive root 아래 `acceptance-reviews/<H>.json`으로 고정한다. root는 사용자 입력/LLM/ref에서 얻지 않는다. companion ArtifactReference.path도 같은 archive root 기준이다. 저장소 서비스·검색 index·서명 시스템은 만들지 않는다.

외부 preparation이 파일을 한번 확보한 **동일 불변 bytes**의 SHA256을 기대 H와 비교하고 그 bytes를 strict parse한다. 다시 경로를 열어 다른 내용으로 parse하지 않는다. 같은 ref에 다른 내용이면 SHA256 불일치로 차단한다. raw bytes hash이므로 공백·key 순서·배열 순서·개행 변경도 다른 ref다. canonical JSON 도메인 지문과 혼용하지 않는다. SHA256은 선택된 bytes의 대응이며 원본 record/검토자 자체의 신뢰성을 증명하지 않는다.

본문은 UTF-8 JSON, BOM 없음, duplicate key/NaN/Infinity/누락·extra key 거부다. 배열 순서를 보존하고 tuple로 명시 파싱한다. 값·날짜·Enum 변환은 외부 strict loader 책임이며 도메인 constructor에 coercion을 넣지 않는다. 압축·ZIP·자동 추출·원격 fetch는 이 프로파일에 없다. 경로 이탈·다른 bytes 재열기 방지는 후속 preparation 구현의 검증 대상이다.

**자기 hash 순환 방지:** raw 본문은 `schema_version`, `entries`의 정확한2key다. schema_version은 고정 `benefit-acceptance-review-1.0`. 자기 ref/hash를 본문에 넣지 않는다. 각 entry의 `acceptance`는7절의20key projection이다. 메모리 모델은 외부 ref를 결합한 기존21필드 원본을 재사용한다. body 작성·고정 → raw SHA256/ref 확정 → 해당 ref의 Acceptance 발급 순서다. 임시 가짜 Acceptance/ref를 실제 이력으로 발급하지 않는다.

## 6. 최소 value model 결정

후속 별도 모듈 후보는 `backend/policy_engine/policy_data/benefit_acceptance_review_artifact.py`다. 새 dataclass는 모두 frozen/slots/kw_only이며 모든 인자를 명시한다. None/빈 tuple도 필수 인자다. 기존 객체를 재생성·정규화하지 않는다.

| 제안 타입 | 저장 필드 수 | 필요한 정보/기존 타입으로 부족한 이유 |
|---|---:|---|
| BenefitReviewClaim(str, Enum) | 해당 없음 | 5개 claim 이름. 기존 Enum에는 claim 개념 없음 |
| ClaimEvidenceMapping | 2 | claim, evidence_refs. Snapshot 전체 refs만으로 claim 대응을 표현 못함 |
| ReviewSourceOriginal | 2 | binding: 기존 SourceBinding, artifact: 기존 ArtifactReference. Registry metadata만으로 공식 원문 bytes를 고정 못함 |
| AcceptanceReviewEntry | 15 | 기존 Acceptance와 원본 참조·mapping·검토 metadata를 연결. Context/Registry 복제 아님 |
| AcceptanceReviewArtifact | 2 | review_artifact_ref, entries. 하나의 불변 본문에 명시된 revision 목록 |

AcceptanceReviewEntry의 **정확한15필드와 순서**:

| # | 필드 | exact 타입/의미 |
|---:|---|---|
| 1 | acceptance | 기존 PolicyBenefitAcceptance 원본21필드 객체 |
| 2 | accepted_terms_ref | ArtifactReference 또는 None; 기존16key Snapshot 원본 |
| 3 | coverage_snapshot_ref | ArtifactReference 또는 None; 기존 EligibilityCoverage(inventory+bindings) 원본 |
| 4 | policy_envelope_ref | ArtifactReference 또는 None; 기존 PolicyEnvelope 원본 |
| 5 | coverage_reviews_ref | ArtifactReference 또는 None; 기존 CoverageReviewContext 원본 |
| 6 | dataset_manifest_ref | ArtifactReference 또는 None; 기존 DatasetManifest 원본 |
| 7 | source_registry_ref | ArtifactReference 또는 None; 기존 SourceRegistry 원본 |
| 8 | implementation_artifact_ref | ArtifactReference 또는 None; 당시 실행 코드 ZIP 원본 |
| 9 | claim_evidence | exact tuple[ClaimEvidenceMapping, ...] |
| 10 | source_bindings | exact tuple[SourceBinding, ...]; 정책+혜택 합집합 |
| 11 | source_documents | exact tuple[ReviewSourceOriginal, ...]; 위 source별 고정 공식 원문 |
| 12 | prepared_by | exact 비공백 str; 팀 handle |
| 13 | reviewed_by | exact 비공백 str; 별도 검토자 handle |
| 14 | review_note | exact 비공백 str; 승인 또는 철회 이유 |
| 15 | manual_scenario_ids | 비어 있지 않은 exact tuple[비공백 exact str, ...]; 검토한 사례 ID |

handles는 exact equality로 달라야 하며 strip은 blank 검사에만 쓴다. 실제 사람이 서로 다른지/권한이 있는지는 governance다. scenario IDs는 중복 거부·순서 보존, 임의 prefix 정규식 강제 없음. 검토일·기한은 acceptance의 reviewed_at/valid_until을 사용하여 중복 날짜 필드를 만들지 않는다. SOURCE_BINDING은 별도 claim이 아닌 모든 원문/mapping의 참조 정합성 축이다.

Root entries는 비어 있지 않은 exact tuple[AcceptanceReviewEntry,...], 입력 순서 보존이다. acceptance_ref는 전체에서 유일하고 `(policy_id, scope, benefit_id, acceptance_version)`도 유일하다. 각 entry.acceptance.review_artifact_ref는 root ref와 정확히 같아야 한다. 여러 target이 있어도 전역 승인/자동 선택을 의미하지 않는다. revision/target별 정확한 entry만 사용한다.

ReviewSourceOriginal은 exact SourceBinding과 exact ArtifactReference의2필드를 검사하고 외부 원문은 열지 않는다. root.review_artifact_ref만4절의 exact content-addressed 문법을 검사한다. entry의 기존 acceptance 객체에 별도 ref 문법을 강제하지 않으며, root 결합 시 equality로 이 프로파일 소속을 확인한다. raw entry는 위15key를 그대로 사용하되 acceptance만7절20key projection이다. root와 entry 어느 곳에도 자체 raw hash를 저장하지 않는다.

로컬 검사 순서: 필드 순서의 exact 타입/문법·중첩 원소 타입 → handle/scenario 중복 → status별 조합 → claim 순서·중복/비어 있음 → source 정렬·중복·original 목록 대응. Root는 ref 문법 → entries 타입/원소 → 전체 ref 유일성 → revision key 유일성 → root ref equality다. 로컬 새 오류는 기존 PolicyDataError의 `INVALID_ACCEPTANCE_REVIEW_ARTIFACT: <field>: <reason>` prefix다. missing/extra 인자는 Python TypeError다. 후속 모델 serializer는 저장 필드 순서의 새 primitive dict를 반환하고 nested 기존 to_dict를 재사용한다. 그 진단 dict는 raw body가 아니며 bytes 무결성 인증서가 아니다.

## 7. Acceptance revision binding

entry.acceptance는 기존 원본을 재사용한다. 별도20/21필드 결정 모델은 만들지 않는다. raw entry.acceptance는 다음 **20개 허용 key만** 가진다. 기존 to_dict 전체를 미래 필드까지 자동 복사하는 계약이 아니다.

```text
acceptance_ref, acceptance_version, status, policy_id, scope, benefit_id,
coverage_inventory_version, coverage_inventory_fingerprint,
coverage_rule_version, coverage_policy_tree_fingerprint,
coverage_dataset_version, coverage_source_registry_fingerprint,
coverage_implementation_fingerprint, benefit_version, benefit_fingerprint,
benefit_dataset_version, benefit_source_registry_fingerprint,
reviewed_at, valid_until, revokes_acceptance_ref
```

자기 주소인 review_artifact_ref만 외부 원본에서 결합한다. scope는 기존2key 객체, Enum은 value, 날짜는 정확한 ISO date다. strict loader가 외부 record와 이20개를 전부 대조한다. 같은 ref라도 version/status/target/날짜/철회 link/어느 binding 하나라도 다르면 대응 Data Error다. loader는 body를 권위 있는 새로운 Acceptance로 발급하지 않는다. 기존 원본과 대응 성공 후 같은 객체를 entry에 보존한다.

공유 artifact에서는 여러 revision을 body에 **각각 명시**해야 한다. 한 entry가 다른 revision을 묵시적으로 승인하지 않는다. 기존 content-addressed bytes에 새 entry를 추가하면 새 ref이며 기존 record를 overwrite하지 않는다. 사전에 함께 고정한 정확한 revision들은 같은 ref를 공유할 수 있다. AC113과 artifact가 revision 유일성 key가 아니라는 계약을 유지한다.

## 8. Coverage snapshot binding

공유 policy_id/scope와 아래7값, 합계9축을 원래 자료와 대조한다.

| Acceptance 값 | 필요한 원본/비교 |
|---|---|
| coverage_inventory_version | coverage.inventory.inventory_version |
| coverage_inventory_fingerprint | 기존 Inventory 지문 함수의 당시 inventory 결과 |
| coverage_rule_version | 당시 envelope.policy.rule_version |
| coverage_policy_tree_fingerprint | 기존 Policy Tree 지문 함수의 당시 policy 결과 |
| coverage_dataset_version | 당시 Manifest/Envelope/ReviewContext dataset |
| coverage_source_registry_fingerprint | 당시 Registry 실제 domain fingerprint 및 ReviewContext |
| coverage_implementation_fingerprint | 당시 ReviewContext 구현지문과 실제 코드 ZIP 확인본 |

원본 Coverage/Envelope/ReviewContext와 기존 Review refs·자료를 보존한다. 별도 CoverageResult 복사/공개 factory/저장 FULL bool을 만들지 않는다. FULL 여부는 **기존 evaluate_eligibility_coverage**가 원래 inputs로 만든 결과만 사용한다. Artifact constructor/지문 equality가 FULL을 계산하지 않는다. 발급 당시 official producer 결과를 확인하고 원재료를 보존한다. 후속 역사 재검증이 필요하면 당시 구현 환경에서 그 producer를 별도 실행하며 current 호출 producer를 대체하지 않는다.

M2.52 동일 source ZIP 프로파일에서 Manifest.engine_artifact_sha256와 ReviewContext.implementation_fingerprint는 **해당 ZIP raw bytes hash**와 대응한다. 일반적으로 이름이 다른 hash를 모두 같다고 가정하지 않는다. 현재는 합성 verify-only만 구현됐으며 실제 release 실행/legacy→FULL·역사 review 원문 검증의 blocker는 남는다.

## 9. Benefit snapshot binding

| 저장 binding | 실제 원본 비교 |
|---|---|
| policy_id/scope/benefit_id/benefit_version | 당시 Snapshot의 exact identity |
| benefit_fingerprint | `fingerprint_benefit_snapshot(당시 원본)` 실제 결과 |
| benefit_dataset_version | 당시 Snapshot.dataset_version과 당시 Manifest.dataset_version |
| benefit_source_registry_fingerprint | 당시 Snapshot 값 및 당시 Registry 실제 domain fingerprint |

definition fingerprint와 dataset/whole Registry provenance는 독립 축이다. Benefit 지문은 후자의 두 값을 포함하지 않는다. 파일 SHA256은 또 별도 축이다. 같은 version/다른 정의 지문 모순과 정상 새 version을 구별한다. Artifact 내부 hash 문자열끼리 같다는 사실만으로 실제 Snapshot 대조를 생략하지 않는다.

## 10. accepted_terms 위치 선택

**후보 B: 별도 불변 기존 BenefitSnapshot 원본 참조**를 선택한다.

| 구조 | 검토/재현 | 중복/오염/난이도 |
|---|---|---|
| A 본문에 정의 복제 | 단일 문서 열람 쉬움 | 16필드 또는 부분 terms의 두 표현을 계속 동기화해야 함 |
| B accepted_terms_ref로 원본 연결 | 참조 원본을 함께 열면 정확한16key 복원 | 추가 terms 모델 없음, raw SHA+domain fp 모두 대조 필요; 선택 |

ArtifactReference의 path/SHA256을 통해 확보한 **당시16key 원본**이 accepted_terms다. 원본 없이 지문만 남기는 것은 허용하지 않는다. 검토 시 두 자료를 함께 열고 대응표를 읽어야 한다. 별도10필드/16필드 terms DTO를 만들지 않는다.

| 원본 필드 | 검토 claim/책임 |
|---|---|
| amount_type / amount_krw / amount_description | AMOUNT |
| payment_cadence | CADENCE |
| benefit_medium | MEDIUM |
| restriction / restriction_details | RESTRICTION |
| applicable_months | APPLICABLE_MONTHS |
| benefit_evidence_refs | 모든 claim mapping의 허용 refs와 원래 순서 |
| source_bindings | 원본 evidence의 문서 version 대응, 합집합 검증 |

나머지6필드 policy_id/scope/benefit_id/benefit_version/dataset_version/source_registry_fingerprint도 원본에 그대로 존재한다. 사람이 읽을 필드별 값 없이 자유형 review_note 하나로 승인하지 않는다.

## 11. Claim ID와 Mapping

BenefitReviewClaim은 정확히 **AMOUNT, CADENCE, MEDIUM, RESTRICTION, APPLICABLE_MONTHS**의5member며 값도 같은 문자열이다. claim_evidence의 ACCEPTED 순서는 이 순서로 고정한다. SOURCE_BINDING이라는 여섯 번째 claim은 없다. 기존 EVALUATOR_SPEC의5claim과 일치한다.

ClaimEvidenceMapping은 `claim: BenefitReviewClaim`, `evidence_refs: tuple[str,...]` 정확한2필드다. raw string Enum·list·subclass는 모델 입력으로 허용하지 않는다. claim당 refs는 비어 있지 않아야 하고 기존 canonical evidence ref 문법을 따른다. source ID뿐인 문자열·URL·자유형 문장은 evidence ref가 아니다. 문법은 기존 source validator의 규약을 재사용한다.

## 12. 순서·중복·누락·추가 근거

| 사항 | 결정 |
|---|---|
| 한 claim에 여러 evidence | 허용, 입력 순서 보존 |
| 한 evidence가 여러 claim 지원 | 허용, 의미 충족은 사람 검토 |
| 같은 claim 중복/필수 claim 누락/추가 claim | 구조 오류; 정확한5행 필요 |
| 한 claim 행 내부 duplicate evidence | 오류, 자동 dedupe 금지 |
| 당시 Snapshot refs duplicate | Snapshot/지문은 그대로 보존; Acceptance 사용 검증에서는 기존 duplicate 오류로 거부 |
| Mapping ref가 Snapshot refs 밖에 있음 | Registry에 존재해도 대응 오류 |
| Snapshot refs 중 mapping에서 미사용 | 보충 맥락으로 허용; 삭제/자동 삽입 안 함. 그 ref도 source 사용 검증 대상 |
| claim 순서 변경 | 구조 오류; 자동 재정렬 금지 |
| 한 행의 evidence 순서 변경 | 구조적으로 허용; 다른 bytes이므로 새 Artifact ref 필요, 기존 ref 아래 overwrite 금지 |
| Snapshot refs 순서 변경 | 기존 지문이 바뀜; 같은 version이면 모순, 새 version이면 현재 평가의 정상 변경 축 |

Mapping에서 중복을 거부하는 것과 fingerprint가 순서/중복을 보존하는 것은 서로 다른 책임이다. set으로 순서를 없애거나 중복을 숨기지 않는다.

## 13. SourceBinding과 공식 원문 대응

ACCEPTED entry.source_bindings는 **당시 Envelope.source_bindings ∪ 당시 Snapshot.source_bindings**의 source ID 정렬된 정확한 합집합이다. 같은 ID/다른 d version은 오류다. 중복·불필요 추가·누락을 거부한다. 단 실제 Envelope 필드명은 `source_bindings`이며 별도 가상 bindings 필드를 추가하지 않는다.

source_documents는 합집합과 같은 순서·같은 개수이고 각 ReviewSourceOriginal.binding이 같은 위치 binding과 정확히 같아야 한다. source_document_id당 원문 하나를 지정하며 각 artifact는 기존 path/SHA256 참조다. SourceDocument.content_sha256가 있으면 이 raw 원문 hash와 같아야 한다. 없더라도 Review Artifact에 연결된 원문 SHA256으로 당시 검토한 bytes를 고정한다. 그 bytes가 실제 공식 자료인지는 외부 대조가 필요하다. 현재 URL이 바뀌었다고 역사 원문을 새 다운로드로 교체하지 않는다.

| 검사 | 로컬 모델만 가능 | 원본 Registry/기타 자료 필요 |
|---|---|---|
| ref 문법, 행 중복, binding exact 타입/정렬/유일성 | 가능 | 없음 |
| mapping이 Snapshot refs 부분목록, 합집합 정확성 | 불가 | 당시 Snapshot/Envelope |
| source ID, SourceDocument identity와 d version, locator 존재 | 불가 | 당시 Registry; SourceBinding에 locator/status 필드는 없음 |
| policy applicability | 불가 | 해당 SourceEvidence.applicable_policy_ids |
| ACTIVE/VERIFIED/검증일·freshness | 불가 | SourceDocument와 SourceEvidence, 당시/현재 명시 날짜 및 Manifest |
| whole Registry fingerprint/dataset/source versions 대응 | 불가 | 당시 Registry/Manifest, 기존 지문/manifest validators |
| 원문 raw SHA/공식성/claim 의미 | 불가 | 고정 공식 원문 bytes·출처 대조·검토자 |

`validate_evidence_refs`의 문법→중복→resolve를 재사용한다. resolve는 source/locator ACTIVE를 확인하지만 VERIFIED/날짜·freshness까지 보장하지 않는다. `validate_envelope_sources`, `validate_dataset_manifest`도 실제 파일 SHA·사람 검토·전체 source gate를 수행하지 않는다. 전체 Manifest 검증은 그 release의 **전체 envelopes**를 공급해야 하며 한 Envelope만 넣어 통과한 것으로 취급하지 않는다.

## 14. ACCEPTED Artifact 최소 계약

로컬 구조: 원본 record.status=ACCEPTED,7개 companion refs 모두 non-None,5개 정확한 claim 행, 비어 있지 않은 source_bindings/source_documents, revokes_acceptance_ref=None. Source/claim correspondence는 실제 원본과 추가 대조한다.

| 수준 | 요구 | 이 수준만으로 부족한 것 |
|---|---|---|
| A 구조 | 기존16필드 Snapshot constructor 성공 | 미완전/미검토 값도 구조적으로 가능 |
| B 완전성 | amount_type=FIXED, exact 비음수 금액, 알려진 cadence/medium/restriction, 명시적 finite applicable_months | UNKNOWN/VARIABLE 초기 수용 금지; 근거 의미는 미확인 |
| C claim 검토 | 정확한5claim 각각 공식 원문과 대조, 제한/금액/지급월 해석 기록 | refs membership만으로 의미 입증 안 됨 |
| D 외부 수용 | 준비자/별도 검토자, 검토일·기한·이유·사례와 정확한 binding을 확인하여 시뮬레이션 정의 사용 승인 기록 | 행정 지급 승인·현재 usability·개인 적용 아님 |

발급 시 당시 Coverage FULL·Policy VERIFIED·source 사용요건을 별도로 확인한다. 승인됐다고 주장하는 역사 원본이 UNKNOWN/VARIABLE/미완전이면 정상 current metadata reason으로 감추지 않고 대응 Data Error로 발급/사용 진입을 막는다. 현재 Snapshot의 정상 미완전은 기존 BENEFIT_METADATA_NOT_REVIEWED다. cadence가 분기·medium이 지역화폐인 완전한 정의도 검토 대상일 수 있으나 Bridge의 월 현금 반영을 허용하지 않는다.

## 15. REVOKED Artifact

REVOKED는 혜택 재승인 없이 **B가 정확한 과거 ACCEPTED A를 왜 철회했는지** 기록한다. B의 원본21필드에 current ref/version/status/target/binding9+Benefit binding/검토일·기한·revokes_acceptance_ref가 있다.

REVOKED entry는7 companion refs=None, claim_evidence/source_bindings/source_documents=빈 tuple을 요구한다. prepared_by/reviewed_by/review_note/manual_scenario_ids는 필수다. 철회 사유와 사례를 남기되5claim 승인표를 새로 작성하지 않는다.

기존 Context가 target 존재·ACCEPTED·11개 binding 일치·후행 revision/date·단일 incoming revoke를 검증한다. Artifact 모델은 Context/철회 그래프를 복제하지 않는다. 참조 검증은 B의20key 원본 대응 후 그 Context의 정확한 A와 A.review_artifact_ref의 **명시 entry**를 연결한다. A의 원본 Coverage/Benefit/Source를 통해 철회 대상 snapshot을 추적한다. 다른 snapshot을 가리키거나 target ref가 다르면 오류다.

별도 target artifact ref 필드를 중복 저장하지 않는다. Context A에서 읽으므로 A/B가 같은 물리 artifact를 공유해도 자기 hash 순환이 생기지 않는다. A entry는 B와 같은 root 또는 다른 content-addressed root에서 찾을 수 있고, 어느 경우에도 명시 A만 선택한다. REVOKED를 연쇄 target으로 허용하는 새 framework는 없다.

확인된 B를 artifact 미확보 때문에 이력에서 빼거나 A를 복구하지 않는다. B의 valid_until 경과/미래 reviewed_at을 이유로 철회를 해제하지 않는 기존 계약을 유지한다. 필수 자료 미확보 시 진입 차단하며 정상 사용 결과를 만들지 않는다.

## 16. Historical 원본과 current usability

외부 발급/보존 책임자는 검토 artifact·당시16key Benefit 원본·Registry·공식 원문·Manifest와 전체 Envelope·Coverage/Review 원본·실행 ZIP을 함께 불변 보존한다. 현재 객체로 역사 원본을 대체하지 않는다.

| 상황 | 처리 |
|---|---|
| 당시 b0001 원본+artifact 확보, binding 일치 | b0001에 대한 구조/참조 대응을 확인 가능; 실제 검토 진실성은 별도 |
| 역사 원본 미확보 | 재검증 미완료/외부 준비 차단; 과거 claim 전체 재검증 성공을 주장하지 않음 |
| 당시 원본은 정확, current b0002 | 정상 BENEFIT_SNAPSHOT_CHANGED; b0002를 b0001 artifact에 대조해 오류로 만들지 않음 |
| 같은 b version인데 current 지문 다름 | 독립 모순 Data Error; 다른 축 변경/철회/만료로 숨기지 않음 |
| 정의 같고 current dataset/Registry만 변경 | 정상 BENEFIT_PROVENANCE_CHANGED; 같은-version dataset/Registry 내부 모순은 별도 오류 |

current B의 최소 책임은 M2.51의 current 원본 일관성·명시 선택·날짜·binding 비교다. raw 역사 자료 검증은 A/C다. current metadata 비교만으로 정상 변경을 진단하는 내부 계산은 가능하지만 그것을 역사 검토 완료로 표현하지 않는다. 서비스의 안전한 진입은 필요한 역사 원본과 검토 대응이 확보된 경우에만 연다. 현재 실제 원본·Acceptance는 발급하지 않는다.

## 17. 세 단계 검증과 책임

| 단계 | 입력/수행자 | 확인 가능한 사실 | 확인 불가 |
|---|---|---|---|
| 1 Structural | strict loader + 새 value constructor | exact 형식·필드·claim/순서/유일성·status 조합 | 실제 bytes hash, 다른 원본 대응, 실제 검토 |
| 2 Reference/snapshot | preparation의 동일 bytes hash + pure 비교 | 정확한 record/당시 원본/지문·provenance·evidence membership/문서 identity 대응 | 원문이 claim을 의미상 지지하는지, 사람 권한 |
| 3 Evidence/content | 공식 원문과 정의를 대조하는 사람/승인된 외부 절차 | 금액·주기·수단·제한·월의 근거 대조를 수행하고 기록 | 그 진술의 진실성/권한을 로컬 모델만으로 인증 |

2단계 통과를3단계 수행 성공으로 표시하지 않는다.3단계 기록이 존재해도 실제 사람 독립성/권한·이력 누락/overwrite 여부는 외부 governance다. 생성형 AI가 이 결정을 발급하지 않는다.

## 18. 정상 미검토·오류·준비 차단

| 상황 | 고정 경계/기대 |
|---|---|
| 정상 아직 검토 전, record 없음/미선택 | 기존 NO_ACCEPTANCE_* / ACCEPTANCE_NOT_SELECTED 의미 유지 |
| 정상 current Benefit 완전성 부족 | 기존 BENEFIT_METADATA_NOT_REVIEWED; 가짜 ACCEPTED를 발급하지 않음 |
| 명시 artifact 없음/접근 불가/역사 원본 미확보 | 외부 준비 차단, B 정상 Result 없음. 실제 부재/일시 접근 실패를 검토 미완료 reason으로 낮추지 않음 |
| 확보 body의 ref/version/target/status/날짜가 다름 | PolicyDataError, `ACCEPTANCE_REVIEW_BINDING_MISMATCH: <field>` 방향 |
| 확보 역사 Snapshot 지문/원본 binding 모순 | 같은 대응 Data Error |
| 실제 hash 불일치 | 외부 preparation의 PolicyDataError, `ACCEPTANCE_REVIEW_INTEGRITY_MISMATCH: <field>` 방향 |
| broken evidence/source/locator, inactive 원본 | 기존 source/evidence PolicyDataError 그대로 전파 |
| Snapshot 외 ref/합집합/문서 version 모순 | 대응 Data Error; 기존 validator 오류가 있으면 기존 오류 우선 |
| 형식/참조는 정상인데 원문이 claim을 지지하지 않음 | 외부 내용 검토 실패, 발급/사용 준비 차단; Python membership 성공으로 덮지 않음 |
| 실제 검토·권한을 확인하지 못함 | governance 준비 미완료, 검토 성공 bool 입력으로 우회 금지 |

준비 차단은 새 Evaluation reason/일곱 번째 status/정상 금액0원 반환이 아니다. 후속 I/O 경계가 자료 미확보를 명시 실패로 보고하고 C/B를 호출하지 않는다. Value 모델은 I/O 예외를 소유하지 않는다. 향후 callable 오류 세부 우선순위는 그 validator 구현 설계에서 닫되 위 정상/오류 경계를 바꾸지 않는다.

기존12개 reason은 그대로: NO_ACCEPTANCE_CONTEXT, NO_ACCEPTANCE_RECORDS, ACCEPTANCE_NOT_SELECTED, ACCEPTANCE_REVOKED, ACCEPTANCE_NOT_YET_VALID, ACCEPTANCE_EXPIRED, COVERAGE_NOT_FULL, POLICY_NOT_VERIFIED, BENEFIT_METADATA_NOT_REVIEWED, COVERAGE_SNAPSHOT_CHANGED, BENEFIT_SNAPSHOT_CHANGED, BENEFIT_PROVENANCE_CHANGED.

## 19. Policy verification·Source Gate와의 관계

Coverage FULL, Envelope VERIFIED, Benefit metadata reviewed, Artifact raw integrity, Source usage validity는 별도 축이다. 어느 한 성공이 다른 성공을 대체하지 않는다. SourceEvidence/SourceDocument.status와 verification_status는 서로 다르며 SourceBinding에 없는 상태를 검사한다고 쓰지 않는다.

당시 사용요건은 당시 reviewed_at과 Manifest를, 현재 사용요건은 명시 data_use_date와 current Manifest를 기준으로 대조한다. M2.51의 source/locator ACTIVE·VERIFIED·검증일·freshness 경계를 유지하며 자동7일/현재시각 추정 없음. 검증일~검증일+freshness_max_age_days 양끝 포함이다. 모든 관련 refs(미사용 보충 ref 포함)를 검사한다. 실제 공식성·의미 확인도 별도다. 전체 Source Gate 모델/함수·실제 release 승격을 이번에 구현하지 않는다.

## 20. External preparation의 책임

1. trusted 원본 Context/명시 ref/현재 release와 archive root를 고정한다. 자동 최신 선택 없음.
2. 명시 ref가 실제 supplied record에 해당하면 그 record의 review_artifact_ref를 사용해 동일 bytes를 확보·해시·strict parse한다. 이 단계의 조회는 I/O 준비 대상을 정할 뿐 B의 기존 resolver/정상 selection 계산을 대체하지 않는다. ref가 supplied record에 없거나 미선택이면 임의 artifact/record를 합성하지 않고 기존 B의 selection/오류 계약을 따른다.
3. 선택 A에 known incoming 철회 B가 있으면 B 자료도 포함한다. 직접 B를 선택하면 target A 자료도 포함한다. 관련 없는 역사 revision의 자료까지 일괄 확보하는 새 이력 시스템은 만들지 않는다. 하나의 root에 여러 entry가 있으면 구조는 전체 검사하되 선택된 결정에 대한 승인 효과를 다른 entry로 확장하지 않는다.
4. 정확한 당시 companion refs와 공식 원문 bytes를 같은 raw SHA로 확인하고 원래 domain 객체로 strict load한다. Manifest에 따른 전체 release 참조도 확보한다. 원본 미확보/알 수 없는 프로파일이면 중단한다.
5. 아래 pure 비교를 실행하고 실제 내용 검토 기록/독립성·외부 보존 책임을 확인한다. 원문 의미나 권한을 검증 bool로 받아 넘기지 않는다.
6. 현재 원본과 준비한 자료를 한 호출 동안 고정하여 C로 결합한다. file/network·hash·실행 ZIP 대응은 B에 넣지 않는다.

외부 준비 실패가 B 진입 전에 발생할 수 있다는 기존 M2.51 단계0을 유지한다. B 내부의 오류/selection/독립 guard 순서는 바꾸지 않는다. 이 문서는 production adapter signature 또는 실제 준비 완료를 선언하지 않는다.

## 21. Pure validation의 책임

후속 pure 비교의 명시 재료는 **artifact/정확한 원본 Acceptance/검증된 supplied Context의 관련 target/당시 BenefitSnapshot·EligibilityCoverage·Envelope·CoverageReviewContext·Manifest·전체 envelopes·Registry**다. 기존 타입을 그대로 공급한다. bytes/hash/file handle/원문 다운로드/현재시각/외부 성공 bool은 pure 입력이 아니다. 실제 원문 claim 의미와 외부 진실성은 pure가 계산하지 않는다.

순수 검사는 record20값/외부 ref 대응, 기존 지문 함수의 실제 원본 계산,9 Coverage 축/7 Benefit 축, source 합집합·mapping 부분목록·중복·문서 version/locator/policy 적용·provenance 대응을 확인한다. 기존 validator를 재사용하고 정상 반환은 별도 usable/verified token 없이 `None` 방향이다. 실패는 PolicyDataError다. None을 캐시 가능한 승인 증거로 외부에서 주입할 수 없다.

공식 Coverage producer의 FULL 판정, 전체 current Source Gate, 실제 bytes/실행 검증, 사람 판단은 해당 계층 책임이다. constructor가 이들을 자동 실행하지 않는다. 정확한 callable 분할·signature·복합 오류 순서·원본 strict loader는 후속 설계/구현 대상이며 이번 value model 준비 완료와 구별한다.

## 22. 기존 8-input evaluator 연결 결정

**A: 동일 호출의 외부 A/C에서 Artifact 검증·결합**을 선택한다.8개 입력만으로 raw artifact bytes/원문/역사 자료를 검증할 수 없다. B 입력을 늘리지 않고 B를 private 순수 함수로 유지한다. 이것은 기존8개만 있으면 전체 검증이 끝난다는 선언이 아니다.

```text
trusted 단일 호출
  A: 선택 결정·관련 철회·역사 원본 bytes 확보/해시/본문·claim 대응
  C: 동일한 현재 원본 고정
     → 전체 current Manifest/Envelopes/Registry 기존 validator 1회
     → 같은 current Coverage/Policy/ReviewContext의 공식 producer 1회
     → B(그 CoverageResult, 같은 Envelope, 같은 Benefit,
          같은 Context, explicit ref, 같은 Manifest, 같은 Registry, 명시 date)
     → 같은 Benefit 원본으로 후속 candidate
```

B의 기존 private resolver는 명시 selection 단계에서1회 호출하는 계약을 유지한다. A가 준비할 exact ref를 Context에서 찾는 것은 B resolver를 다시 호출해 최신 선택하거나 별도 Result를 만드는 것이 아니다. selection 오류는 B의 기존 계약대로 남기고 자료가 있는 척하지 않는다. A에서 current producer를 미리 호출하여 C의 결과를 대체하지 않는다. 당시 FULL 재현이 필요한 감사 실행은 별도 당시 환경에서 수행한다.

검증 후 자료/날짜/Context/ref가 바뀌면 새 호출이다. 외부 precomputed CoverageResult/AcceptanceEvaluation·verified/allow_stale/skip_validation 인자 없음. Python private 표시/불변 dataclass가 악의적 동일 프로세스 코드까지 격리하지는 않는다. C가 실제 검사 함수를 자기 호출에서 실행하도록 구현하고 우회 public 경로를 제공하지 않는 것이 안전한 사용 경계다. A/C와 evaluator는 여전히 미구현이며 이번 문서로 production USABLE 경로를 열지 않는다.

## 23. 기존 모델/API·migration 영향

PolicyBenefitAcceptance21, BenefitSnapshot16, BenefitAcceptanceEvaluation9+파생 status, BenefitAcceptanceContext4와 frozen Coverage는 **필드/생성자/serializer/함수 의미 모두 유지**한다. bootstrap/Cashflow/SourceRegistry/Manifest도 변경하지 않는다. 새 value 타입은 기존 record·SourceBinding·ArtifactReference·Scope를 재사용하며 ReviewContext/Registry/Envelope 복제 모델을 만들지 않는다.

후속 모델 구현의 public export 후보는 위 Enum+4개 value 타입뿐이다. resolver/pure validator/loader/adapter는 이번 다음 모델 작업에 포함하지 않는다. root2·entry15·mapping2·source-original2 외에 stored is_verified/FULL/usable/accepted_terms 복제/hash 필드를 추가하지 않는다. schema_version은 serializer 프로파일 상수이며 root stored field가 아니다. raw body용20key projection/loader는 모델 진단 to_dict와 구별한다.

실제 migration0개, 기존 synthetic fixture/기대값 변경0개. opaque fixture는 기존 타입의 유효성 테스트로 유지한다. 향후 새 타입 테스트는 합성 자료만 사용하고 golden literal을 재계산/교체하지 않는다. 실제 안산 Benefit/Acceptance/검토 artifact를 발급하지 않는다.

## 24. 수동 검증 시나리오

아래 **52개는 문서상 설계 사례**이며 신규 실행 테스트0개다. 책임 S=구조, P=순수 참조 비교, X=외부 준비/bytes, H=사람/거버넌스, B=기존 current evaluator, C=동일 호출 결합. 원본 약어 R=Acceptance/Context, A=Artifact bytes, T=당시16key Snapshot, G=당시 Registry/공식 원문, K=Coverage/Envelope/Review/Manifest/코드 원본, U=current 원본이다. 각 사례의 원본은 실제 확보를 전제로 하며 자리 hash를 검증된 값으로 간주하지 않는다.

| ID | 입력·전제 | 검증 가능한 사실 | 기대 | 필요한 원본 | 책임 | 후속 실행 테스트 |
|---|---|---|---|---|---|---|
| RA01 | 명시 ref/모든20값 일치 | 해당 revision 대응 | 정상 참조 | R,A | P | 가능 |
| RA02 | 다른 acceptance_ref | identity 불일치 | Data Error | R,A | P | 가능 |
| RA03 | 같은 ref/다른 a version | revision 불일치 | Data Error | R,A | P | 가능 |
| RA04 | policy/scope/benefit 중 하나 다름(각 변형) | target 불일치 | Data Error | R,A | P | 가능 |
| RA05 | status/검토일/기한/link 다름(각 변형) | 결정 내용 불일치 | Data Error | R,A | P | 가능 |
| RA06 | 여러 revision 명시 entry가 같은 root 공유 | 개별 entry 정확성 | 허용, 묵시 승인 없음 | R,A | S,P | 가능 |
| RA07 | 정확한 T의 actual Benefit fp | 정의 binding 일치 | 정상 참조 | R,A,T | P | 가능 |
| RA08 | 역사 T=b0001, U=b0002 | 정상 version 변경 | BENEFIT_SNAPSHOT_CHANGED | R,A,T,U | P,B | 가능 |
| RA09 | 같은 b version, 다른 지문 | 독립 정의 모순 | Data Error | R,A,T,U | P,B | 가능 |
| RA10 | 정의 유지/current dataset만 변경 | provenance 변경 | BENEFIT_PROVENANCE_CHANGED | R,T,U | B | 가능 |
| RA11 | 정의 유지/current Registry만 변경 | provenance 변경 | BENEFIT_PROVENANCE_CHANGED | R,T,G,U | B | 가능 |
| RA12 | AMOUNT 근거 행·원문 확보 | membership/금액 의미 구별 | 구조 정상, 의미 H 확인 | A,T,G | P,H | 구조 가능/의미 수동 |
| RA13 | CADENCE 근거 행·원문 확보 | 주기 대응 | 구조 정상, 의미 H 확인 | A,T,G | P,H | 구조 가능/의미 수동 |
| RA14 | MEDIUM 근거 행·원문 확보 | 지급수단 대응 | 구조 정상, 의미 H 확인 | A,T,G | P,H | 구조 가능/의미 수동 |
| RA15 | RESTRICTION 근거 행·원문 확보 | 제한/상세 대응 | 구조 정상, 의미 H 확인 | A,T,G | P,H | 구조 가능/의미 수동 |
| RA16 | APPLICABLE_MONTHS 근거 행·원문 확보 | 명시 월 대응 | 구조 정상, 의미 H 확인 | A,T,G | P,H | 구조 가능/의미 수동 |
| RA17 | 필수 claim 누락 | 정확한5행 아님 | 구조 오류 | A | S | 가능 |
| RA18 | 행 내부 duplicate ref | 중복 | 오류, dedupe 없음 | A | S | 가능 |
| RA19 | T refs 자체 duplicate | Snapshot은 보존, 사용은 중복 | 기존 duplicate 오류 | T,G | P | 가능 |
| RA20 | T 밖 evidence 추가 | 부분목록 위반 | Data Error | A,T | P | 가능 |
| RA21 | T 안 보충 ref가 mapping 미사용 | 전체 refs는 여전히 검증 대상 | 허용 | A,T,G | P | 가능 |
| RA22 | 행 evidence 순서만 변경 | 의미와 raw identity 분리 | 새 hash/ref 필요, 기존 ref면 불일치 | A | S,X | 가능 |
| RA23 | claim 순서 변경/중복/추가(각 변형) | 고정5행 위반 | 구조 오류 | A | S | 가능 |
| RA24 | 한 ref가 여러 claim 지원 | 행간 공유 허용 | 구조 정상, 의미 H 확인 | A,T,G | S,P,H | 구조 가능 |
| RA25 | 정확한 source 합집합/원문 | ID/version/locator/policy 대응 | 정상 참조 | A,T,G,K | P,X | 가능 |
| RA26 | source ID 없음 | resolve 실패 | 기존 source 오류 | T,G | P | 가능 |
| RA27 | 다른 document version | binding 모순 | Data Error | A,T,G,K | P | 가능 |
| RA28 | locator 없음 | resolve 실패 | 기존 locator 오류 | T,G | P | 가능 |
| RA29 | source/locator 미검토·날짜 없음 | 참조 존재≠VERIFIED | 기존 source 사용요건 불충족, 발급 차단 | G,K | P,H | 날짜/상태 가능 |
| RA30 | source/locator inactive | referenceable 아님 | 기존 reference 오류 | T,G | P | 가능 |
| RA31 | policy applicability 불일치 | 근거 소속 모순 | Data Error | T,G,K | P | 가능 |
| RA32 | source binding 누락/추가/중복(각 변형) | 합집합 위반 | Data Error | A,T,G,K | S,P | 가능 |
| RA33 | 정확한 raw bytes SHA | 명시 ref와 bytes 대응 | 무결성 정상, 내용은 별도 | R,A | X | 가능 |
| RA34 | 같은 ref 아래 다른 내용 | 원본 bytes 바뀜 | 무결성 Data Error | R,A | X | 가능 |
| RA35 | 일부 bytes 손상/공백 변경 | raw hash 불일치 | 무결성 Data Error | R,A | X | 가능 |
| RA36 | artifact 미확보 | 본문 검사 불가 | 외부 준비 차단, 정상 Result 없음 | R | X | 가능 |
| RA37 | artifact가 다른 Acceptance만 포함 | exact entry 없음 | 대응 Data Error | R,A | P | 가능 |
| RA38 | opaque legacy ref | 새 프로파일로 hash 추출 불가 | 구조 유효/준비 차단, 무음 migration 없음 | R | X | 가능 |
| RA39 | ACCEPTED 완전성/5claim/외부검토 충족 | 발급 요건 기록 대응 | 발급 가능 전제, 현재 사용 별도 | R,A,T,G,K | P,H | 구조 가능/실제 수동 |
| RA40 | 역사 승인 T.amount_type=UNKNOWN | 초기 승인 요건 모순 | Data Error/발급 차단 | R,A,T | P | 가능 |
| RA41 | 역사 승인 T.amount_type=VARIABLE | 초기 fixed-only 위반 | Data Error/발급 차단 | R,A,T | P | 가능 |
| RA42 | REVOKED B 정확히 A target | 기존 Context+철회 이유 대응 | 철회 기록 유효, 재승인 없음 | R,A,T,K | S,P | 가능 |
| RA43 | B가 다른 snapshot/target 철회 | Context 또는 body 모순 | Data Error | R,A,T,K | P | 가능 |
| RA44 | 역사 T/G/K 모두 확보 | 당시 원본 참조 재현 | 당시 대응 확인, 진실성 별도 | R,A,T,G,K | P,X,H | 기계 부분 가능 |
| RA45 | 역사 T 또는 공식 원문 미확보 | 과거 claim 재검증 불가 | 준비 차단, 성공 주장 금지 | R,A | X | 가능 |
| RA46 | JSON 형식만 유효 | 단계1만 수행 | 내용 검토 완료 아님 | A | S,P | 가능 |
| RA47 | binding 모두 일치/검토자 실재 미확인 | 대응≠진실성/권한 | governance 미완료 | R,A,T,G,K | H | 로컬 증명 불가 |
| RA48 | artifact 검증됐지만 Coverage SLICE | FULL과 독립 | COVERAGE_NOT_FULL, 발급 불가 | R,A,K,U | B | 가능 |
| RA49 | artifact 검증됐지만 Envelope DRAFT | VERIFIED와 독립 | POLICY_NOT_VERIFIED, 발급 불가 | R,A,K,U | B | 가능 |
| RA50 | 완전한 분기 지역화폐 정의 수용 | metadata 검토와 월 현금 Bridge 분리 | Bridge 무환산/반영 차단 | R,A,T,U | B,C | 후속 Bridge 가능 |
| RA51 | 실행 ZIP만 verify-only 성공 | 코드 대응만 검증 | review 검증 미완료 | 코드 ZIP,R | X,C | 가능 |
| RA52 | 검증 후 Context/ref/date/Benefit 교체 | 동일 호출 원본 깨짐 | 새 호출 필요/우회 차단 | R,A,T,U | C | 후속 adapter 가능 |

## 25. 미구현 책임·Assumptions

**Assumption A1:** trusted 내부 발급/자료 준비자가 정확한 record 원본·관련 철회 누락 없는 Context·불변 archive를 공급한다. 해시만으로 악의적 record 동시 교체/이력 누락/권한을 인증하지 못한다.

**Assumption A2:** 실제 검토자가 공식 원문을 열어5claim과 제한/지급월을 대조하고 별도 handle로 기록한다. LLM/사용자가 채운 mapping·handle을 실제 검토 증거로 자동 신뢰하지 않는다.

확정: content-addressed identity/기대 hash 위치, root/entry/claim/source-original 구조, accepted_terms 원본 참조, source 합집합, ACCEPTED/REVOKED 차이, 기존8input 외부 결합 선택. 이 부분은 미결정으로 남기지 않는다.

미구현: value 모델, strict raw serializer/loader·companion 원본 loader, 실제 bytes preparation, pure validator 세부 API/오류 우선순위, A/C 강제 경로, 전체 source gate, evaluator/Bridge. 실제 source ZIP/실행 환경 및 안산 FULL·VERIFIED/다른 조건/검토 원본 확보도 별도다. 이번 문서는 이들을 구현 완료 또는 실제 발급 준비 완료로 승인하지 않는다. archive root의 실제 운영 위치·보존 담당자 handle·실제 정책별 근거는 실제 자료 발급 때 명시해야 하며 지금 가상 값으로 결정하지 않는다.

ResidenceHistory는 **OFFICIAL_INQUIRY_REQUIRED**다. 공식 거주기간 의미를 추정하거나 새 Rule/합산 로직을 구현하지 않는다. 정책 혜택 Cashflow 반영0원 원칙과 개인정보 비저장을 유지한다.

## 26. 다음 가장 작은 작업 한 개

**Acceptance Review Artifact value model만 합성 테스트로 구현한다.** Enum5member+4개 frozen value 타입(root2/entry15/mapping2/source-original2)·로컬 exact 타입/조합/순서/중복·기존 객체 보존·진단 serializer를 구현한다. 새 모델의 public export는 이5개 이름뿐인 방향이다.

완료조건은6~7·11~12·14~15·23절의 로컬 구조 계약과 ACCEPTED/REVOKED/공유 root 사례, 기존 테스트 보존이다. 모델 constructor에서 file/hash/SourceRegistry lookup/Benefit fingerprint/FULL/현재 usability를 실행하지 않는 것을 확인한다. raw loader/preparation/pure validator/evaluator/Source Gate/Bridge/실제 데이터는 포함하지 않는다. 다음 승인 없이 구현하지 않는다.

## 27. 최종 판단

**READY_TO_IMPLEMENT_ACCEPTANCE_REVIEW_ARTIFACT_MODEL**

최소 구조와 immutable identity는 닫혔다. 기존21/16/9/4필드·Coverage freeze와 충돌하는 모델 변경은 없다. 외부 content-addressed 프로파일은 기존 opaque ref constructor를 변경하지 않고 새 검증 경계에만 적용한다. 모델 준비 완료를 외부 bytes/내용 검증 완료·실제 Acceptance 발급·production evaluator 준비 완료로 해석하지 않는다.

## 28. 검증 기록

- 작업 전 전체 pytest: **7,068 passed in 65.56s**. skip/fail 없음.
- 신규 실행 테스트: **0개**. 수동 설계 사례52개는 실행 테스트 수에 포함하지 않는다.
- 최초 사후 실행: **7,066 passed / 2 failed in 536.42s**. bootstrap 하위 프로세스의 `test_invalid_expected_hash_is_not_normalized` 한 매개변수와 `test_corrupt_zip_with_correct_expected_bytes_is_format_error`가 TimeoutExpired로 실패했다. 코드/timeout/기대값을 수정하지 않았다. 시간 초과의 근본 원인을 이번 문서 작업에서 확정하지 않는다.
- 두 실패 계열을 재실행: **8 passed, 98 deselected in 3.37s**. 이어 전체 재실행: **7,068 passed in 68.51s**, 최종 skip/fail 없음. 기존 bootstrap106개 회귀를 포함한다.
- backend/tests/data/docs/tools 중 actual releases·pycache를 제외한 사전168개 파일의 SHA256이 모두 동일하다. 새 파일은 이 문서1개뿐, 기존 파일 수정/삭제0개, 최종169개다. root4개 파일도 SHA256 동일이다.
- GV01~GV15/BV01~BV16 literal·fixture·기존 tests 전체, Coverage freeze 문서/source·기존 Artifact 계약/도구·Benefit/Acceptance/Context/Result·Cashflow를 변경하지 않았다.
- 실제 release6개 파일은 SHA256·경로·크기·수정시각이 모두 동일하다. 실제 Snapshot/Acceptance/Review Artifact/ZIP·새 정책 지문/금액은 생성하지 않았다. ResidenceHistory는 OFFICIAL_INQUIRY_REQUIRED를 유지한다.
- 문서 검수:29개 절 연속성, RA01~RA52 유일/연속성, 표 column 수, code fence 쌍, UTF-8 손상 문자 부재를 확인했다. raw20key projection이 실제21필드에서 review_artifact_ref만 제외한 정확한 순서임을 대조했다. 이 검수는 신규 pytest로 계산하지 않는다.

## 29. 최종 보고 대응

사용자 보고1~2=1·3절,3~5=4~5절,6=7절,7=8절,8=9절,9=10절,10~11=11~12절,12=13절,13=14절,14=15절,15=16절,16=17절,17=18절,18=20절,19=21절,20=22절,21=23절,22=24절,23~25=28절,26~27=25절,28=27절,29=26절. 실행 증거와 설계상 판단을 구별한다.

## 30. M2.55 — IMPLEMENTED: Review Artifact Value Models

M2.54의6·11·14·15·23절에서 확정한 Enum+4개 모델만 구현했다. 앞 절의 미구현 표시는 M2.54 시점 기록이며 이번 상태는 이 절을 따른다. 구현 파일은 `backend/policy_engine/policy_data/benefit_acceptance_review_artifact.py`, 합성 테스트는 `tests/test_benefit_acceptance_review_artifact.py`다.

다음은 구현 전에 추출한 계약의 명시 표다. 모든 필드는 required·keyword-only·정확한 타입이며 기본값/default_factory가 없다. nullable7필드도 생략할 수 없다. 모든 모델은 frozen/slots·전체 필드 value equality/hash를 사용한다.

Enum `BenefitReviewClaim(str, Enum)`의 members/value/iteration 순서는 AMOUNT, CADENCE, MEDIUM, RESTRICTION, APPLICABLE_MONTHS이며 alias/추가 member가 없다. raw 문자열을 자동 변환하지 않는다.

### ClaimEvidenceMapping

| # | 필드 | exact 타입 | required / nullable | nested / 로컬 규칙 | to_dict 표현 |
|---|---|---|---|---|---|
| 1 | claim | BenefitReviewClaim | required / 불가 | 정확한5member Enum | canonical value str |
| 2 | evidence_refs | tuple[str, ...] | required / 불가 | 비어 있지 않음·canonical ref·행 내부 중복 거부·순서 보존 | 새 list[str] |

### ReviewSourceOriginal

| # | 필드 | exact 타입 | required / nullable | nested / 로컬 규칙 | to_dict 표현 |
|---|---|---|---|---|---|
| 1 | binding | SourceBinding | required / 불가 | 기존2필드 원본 보존 | source_document_id/document_version 새 dict |
| 2 | artifact | ArtifactReference | required / 불가 | 기존2필드 원본 보존 | path/sha256 새 dict |

### AcceptanceReviewEntry

| # | 필드 | exact 타입 | required / nullable | nested / 로컬 규칙 | to_dict 표현 |
|---|---|---|---|---|---|
| 1 | acceptance | PolicyBenefitAcceptance | required / 불가 | 기존21필드 객체 보존 | 기존21key to_dict, Scope·ISO date 포함 |
| 2 | accepted_terms_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 3 | coverage_snapshot_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 4 | policy_envelope_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 5 | coverage_reviews_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 6 | dataset_manifest_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 7 | source_registry_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 8 | implementation_artifact_ref | ArtifactReference 또는 None | required / 허용 | ACCEPTED 값 필수 / REVOKED None | 새 path/sha256 dict 또는 null |
| 9 | claim_evidence | tuple[ClaimEvidenceMapping, ...] | required / 불가 | ACCEPTED 정확한5행·고정 순서 / REVOKED 빈 tuple | 새 nested dict list |
| 10 | source_bindings | tuple[SourceBinding, ...] | required / 불가 | ACCEPTED nonempty·ID 정렬/유일 / REVOKED 빈 tuple | 새2key dict list |
| 11 | source_documents | tuple[ReviewSourceOriginal, ...] | required / 불가 | ACCEPTED binding과 개수/순서/값 동일 / REVOKED 빈 tuple | 새 nested dict list |
| 12 | prepared_by | str | required / 불가 | 비공백 팀 handle, 정규화 없음 | 원래 str |
| 13 | reviewed_by | str | required / 불가 | 비공백·prepared_by와 exact 값 다름 | 원래 str |
| 14 | review_note | str | required / 불가 | 비공백 승인/철회 사유 | 원래 str |
| 15 | manual_scenario_ids | tuple[str, ...] | required / 불가 | nonempty·비공백·유일·순서 보존 | 새 list[str] |

### AcceptanceReviewArtifact

| # | 필드 | exact 타입 | required / nullable | nested / 로컬 규칙 | to_dict 표현 |
|---|---|---|---|---|---|
| 1 | review_artifact_ref | str | required / 불가 | 정확한 acceptance-review:sha256:소문자64hex | 원래 str |
| 2 | entries | tuple[AcceptanceReviewEntry, ...] | required / 불가 | nonempty·ref/revision key 유일·각 entry의 외부 ref 동일 | 새 nested dict list |

### 로컬 검증과 기존 객체 보존

기존 SourceBinding/ArtifactReference에는 to_dict가 없으므로 기존 Snapshot/Manifest 방식대로 명시2key 새 dict를 만든다. 나머지 nested serializer는 기존 것을 재사용한다. serializer는 저장 필드 순서 그대로2/2/15/2key를 반환한다. 반환 dict/list 수정은 원래 객체나 다음 출력에 영향을 주지 않는다.

검사 순서는6절대로다. 타입/문법·모든 nested 원소 타입을 먼저 확인하고 handle/scenario 중복 → status별 원본 참조 조합 →5claim 고정 순서 → source 목록 정렬/유일성/원문 대응을 검사한다. Root는 exact ref 문법 → entries/원소 → acceptance_ref 유일성 → target/version key 유일성 → 외부 ref equality다. 오류는 기존 PolicyDataError와 고정 INVALID_ACCEPTANCE_REVIEW_ARTIFACT prefix를 사용하고 입력 payload를 출력하지 않는다. 기존 nested ID/version/revocation 구조는 해당 타입의 constructor 책임이며 재구현하지 않는다.

원본 객체·tuple·문자열을 그대로 보존한다. 값이 같은 별개 SourceBinding도 원문 목록 대응에 사용할 수 있다. 동일 물리 자료를 공유하는 여러 revision 및 b0001/b0002 역사 기록을 표현하되 current Snapshot을 받거나 비교하지 않는다. 단독 REVOKED entry의 target 조회/11binding 대조는 하지 않는다.

### 이번 구현의 정확한 경계

**IMPLEMENTED:** BenefitReviewClaim+4개 불변 모델·로컬 구조/조합/중복/순서·진단 serializer, package public export5개.

**NOT IMPLEMENTED:** raw artifact loader/bytes integrity·external evidence resolution·원본 Snapshot/FIXED completeness·정의 지문/SourceBinding 합집합/locator 존재 대조·source usage gate·공식 내용 검토·검토자 권한 인증·Acceptance evaluator·same-call adapter·Bridge/Cashflow.

entry.acceptance에는 원래21필드 전체가 있으며 진단 serializer에도21key가 나온다. 이는7절의 **외부 raw body20key projection과 다르다**. root 진단 출력에는 외부 ref가 있으며 schema_version은 없다. 이를 hash 대상 파일로 저장하는 loader/serializer를 만들지 않았다. 자기 hash 생성·검증·ref 갱신·실제 파일 저장은 없다. approved raw 계약을 변경하거나 새 canonical bytes 규약을 확정하지 않았다.

### M2.55 검증 기록과 다음 단계

작업 전 전체 **7,068 passed in 71.46s**, skip/fail0·timeout0. 신규 합성 테스트는 **273 passed in 1.40s**이며 최종 전체 **7,341 passed in 69.21s / skipped0 / failed0**이다. 기존7,068개와 bootstrap106개를 모두 포함한다. M2.54의 timeout2건은 이번 작업 전/후 전체 실행에서 재발하지 않았다. 테스트·timeout 설정·기존 테스트/fixture/기대값 변경0개다.

273개는 reflection/모든 필드 필수성·동결/진단 serializer·합성 정상/오류/경계 사례의 실제 pytest 수다. 수동52개를 더하지 않는다. RA06·RA17·RA18·RA23·RA24의 로컬 부분, RA22의 근거 순서 보존, RA25/RA32의 로컬 binding/원문 대응, RA38의 opaque record 보존과 root 프로파일 제한, RA39/RA42의 ACCEPTED/REVOKED 구조를 검증했다. RA01~05의 외부 원본 결정20값 대조·실제 SHA·Registry/공식 내용·역사 원본·current evaluator/adapter 사례는 실행 완료로 계산하지 않는다. 외부 Snapshot/Registry 없이 canonical이지만 로컬 source 목록 밖인 ref도 표현할 수 있음을 별도 경계 테스트로 확인했다.

신규 테스트 개발 중 dataclasses.replace의 positional-only 인자를 helper에서 keyword로 전달하여42개가 실패한 것을 확인하고 **새 테스트 helper 호출만** 수정했다. 모델 계약/기존 기대값을 완화하지 않았다. 수정 후273개 및 전체7,341개가 통과했다. bootstrap timeout 또는 기존 기능 실패는 아니었다.

사전 backend/tests/data/docs/tools169개 중 기존165개 SHA256은 동일하고 변경4개는 package __init__.py·이 명세·DATA_MODEL.md·ARCHITECTURE.md다. 새 코드/테스트2개를 추가해 총171개이며 삭제0개다. 기존 모든 tests/fixture·GV01~GV15/BV01~BV16 literal·Coverage freeze source/문서·Benefit/Acceptance/Context/Result·bootstrap·Cashflow는 동일하다. 실제 release6개는 SHA256·경로·크기·수정시각 모두 동일하다. 실제 검토 파일/Acceptance/Benefit/실행 ZIP·새 정책 지문·혜택 금액을 생성하지 않았다.

검수:4개 모델의 필드/순서/타입·required/nullable·slots/frozen/keyword-only·공개5개 이름을 reflection과 명세 표로 대조했다. 새 코드와 테스트 구문·UTF-8·문서 표/fence를 확인했다. 이 보조 검수는 신규 pytest 수에 포함하지 않는다.

최종 판단은 **READY_FOR_REVIEW_ARTIFACT_LOADER_DESIGN**이다. 다음 최소 작업은 외부 ref와 명시 원본 Acceptance를 받아 raw body20key를 읽는 strict loader의 입력·동일 bytes hash 검증·원본 결합·오류 순서를 설계하는 한 작업이다. loader/validator/adapter를 이번에 구현하지 않는다. 실제 자료·Coverage freeze·기존21/16/9/4필드·ResidenceHistory OFFICIAL_INQUIRY_REQUIRED를 유지한다.

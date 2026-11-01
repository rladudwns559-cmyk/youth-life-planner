"""합성 값 모델의 구조만 검증한다. 실제 자료·지문·원문 검토 성공을 주장하지 않는다."""

import ast
from dataclasses import FrozenInstanceError, MISSING, fields, replace
from datetime import date
from enum import Enum
import inspect
import json
from pathlib import Path
import re
from typing import get_type_hints

import pytest

from backend.policy_engine import policy_data
from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import (
    AcceptanceReviewArtifact, AcceptanceReviewEntry, ApplicabilityScope, ArtifactReference,
    BenefitAcceptanceStatus, BenefitReviewClaim, ClaimEvidenceMapping, PolicyBenefitAcceptance,
    ReviewSourceOriginal, SourceBinding,
)
from backend.policy_engine.policy_data import benefit_acceptance_review_artifact as domain
from backend.policy_engine.sources import SourceRegistry


ARTIFACT_REF = "acceptance-review:sha256:" + "a" * 64
CLAIMS = ("AMOUNT", "CADENCE", "MEDIUM", "RESTRICTION", "APPLICABLE_MONTHS")
REF_FIELDS = ("accepted_terms_ref", "coverage_snapshot_ref", "policy_envelope_ref", "coverage_reviews_ref",
              "dataset_manifest_ref", "source_registry_ref", "implementation_artifact_ref")
ENTRY_FIELDS = ("acceptance", *REF_FIELDS, "claim_evidence", "source_bindings", "source_documents",
                "prepared_by", "reviewed_by", "review_note", "manual_scenario_ids")
CONTRACTS = (
    (ClaimEvidenceMapping, ("claim", "evidence_refs"),
     {"claim": BenefitReviewClaim, "evidence_refs": tuple[str, ...]}),
    (ReviewSourceOriginal, ("binding", "artifact"),
     {"binding": SourceBinding, "artifact": ArtifactReference}),
    (AcceptanceReviewEntry, ENTRY_FIELDS,
     {"acceptance": PolicyBenefitAcceptance, **{name: ArtifactReference | None for name in REF_FIELDS},
      "claim_evidence": tuple[ClaimEvidenceMapping, ...], "source_bindings": tuple[SourceBinding, ...],
      "source_documents": tuple[ReviewSourceOriginal, ...], "prepared_by": str, "reviewed_by": str,
      "review_note": str, "manual_scenario_ids": tuple[str, ...]}),
    (AcceptanceReviewArtifact, ("review_artifact_ref", "entries"),
     {"review_artifact_ref": str, "entries": tuple[AcceptanceReviewEntry, ...]}),
)


def record(**changes):
    # 모든 hash는 합성 문법 자리값이다. 실제 bytes/Benefit 지문으로 계산한 값이 아니다.
    return PolicyBenefitAcceptance(**{
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001",
        "status": BenefitAcceptanceStatus.ACCEPTED, "policy_id": "SYNTH-POLICY",
        "scope": ApplicabilityScope("2026", 3), "benefit_id": "SYNTH-BENEFIT",
        "coverage_inventory_version": "i0001", "coverage_inventory_fingerprint": "1" * 64,
        "coverage_rule_version": "r0001", "coverage_policy_tree_fingerprint": "2" * 64,
        "coverage_dataset_version": "SYNTH-D1", "coverage_source_registry_fingerprint": "3" * 64,
        "coverage_implementation_fingerprint": "4" * 64, "benefit_version": "b0001",
        "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": date(2026, 1, 1),
        "valid_until": date(2026, 12, 31), "review_artifact_ref": ARTIFACT_REF,
        "revokes_acceptance_ref": None, **changes,
    })


def ref(path="synthetic/original.json"):
    return ArtifactReference(path=path, sha256="b" * 64)


def mapping(claim=BenefitReviewClaim.AMOUNT, refs=("SYNTH-SOURCE-A#amount",)):
    return ClaimEvidenceMapping(claim=claim, evidence_refs=refs)


def entry_values(*, revoked=False, **changes):
    bindings = (SourceBinding("SYNTH-SOURCE-A", "d0001"), SourceBinding("SYNTH-SOURCE-B", "d0002"))
    acceptance = (record(acceptance_ref="SYNTH-REVOKE-B", acceptance_version="a0002",
                         status=BenefitAcceptanceStatus.REVOKED, revokes_acceptance_ref="SYNTH-ACCEPT-A")
                  if revoked else record())
    return {
        "acceptance": acceptance,
        **{name: None if revoked else ref("synthetic/" + name + ".json") for name in REF_FIELDS},
        "claim_evidence": () if revoked else tuple(mapping(claim) for claim in BenefitReviewClaim),
        "source_bindings": () if revoked else bindings,
        "source_documents": () if revoked else tuple(
            ReviewSourceOriginal(binding=binding, artifact=ref("synthetic/" + binding.source_document_id + ".pdf"))
            for binding in bindings),
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER",
        "review_note": "합성 구조 검토 사례", "manual_scenario_ids": ("RA39", "RA06"), **changes,
    }


def entry(*, revoked=False, **changes):
    return AcceptanceReviewEntry(**entry_values(revoked=revoked, **changes))


def instances():
    row = mapping()
    original = ReviewSourceOriginal(binding=SourceBinding("SYNTH-SOURCE-A", "d0001"), artifact=ref())
    item = entry()
    root = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(item,))
    return row, original, item, root


def invalid(field, factory, *args, **kwargs):
    with pytest.raises(PolicyDataError) as error:
        factory(*args, **kwargs)
    assert type(error.value) is PolicyDataError
    assert str(error.value).startswith("INVALID_ACCEPTANCE_REVIEW_ARTIFACT: " + field + ": ")
    return str(error.value)


class StringSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class OtherClaim(str, Enum):
    AMOUNT = "AMOUNT"


def test_exact_enum_members_values_order_without_aliases():
    assert tuple(BenefitReviewClaim.__members__) == CLAIMS
    assert tuple(member.value for member in BenefitReviewClaim) == CLAIMS
    assert len(BenefitReviewClaim.__members__) == len(tuple(BenefitReviewClaim)) == 5
    assert issubclass(BenefitReviewClaim, str) and issubclass(BenefitReviewClaim, Enum)


@pytest.mark.parametrize("cls,names,types", CONTRACTS)
def test_reflection_exact_fields_types_order_required_frozen_slots_keyword_only(cls, names, types):
    actual = fields(cls)
    assert cls.__name__ in ("ClaimEvidenceMapping", "ReviewSourceOriginal", "AcceptanceReviewEntry",
                            "AcceptanceReviewArtifact")
    assert tuple(field.name for field in actual) == names == cls.__slots__
    assert get_type_hints(cls) == types
    assert all(field.default is MISSING and field.default_factory is MISSING and field.kw_only and field.compare
               for field in actual)
    assert cls.__dataclass_params__.frozen
    signature = inspect.signature(cls)
    assert tuple(signature.parameters) == names
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
               for p in signature.parameters.values())


def test_fields_match_extracted_contract_tables_in_spec():
    text = (Path(__file__).resolve().parents[1] / "docs/BENEFIT_ACCEPTANCE_REVIEW_ARTIFACT_SPEC.md").read_text(
        encoding="utf-8")
    for cls, names, _ in CONTRACTS:
        table = text.split("### " + cls.__name__ + "\n", 1)[1].split("\n### ", 1)[0]
        rows = re.findall(r"^\| (\d+) \| ([a-z_]+) \|", table, re.M)
        assert rows == [(str(i), name) for i, name in enumerate(names, 1)]
    section = text.split("## 6. ", 1)[1].split("## 7. ", 1)[0]
    assert re.findall(r"^\| (\d+) \| ([a-z_]+) \|", section, re.M) == [
        (str(i), name) for i, name in enumerate(ENTRY_FIELDS, 1)]


FIELD_CASES = [(i, name) for i, (_, names, _) in enumerate(CONTRACTS) for name in names]


@pytest.mark.parametrize("index,field", FIELD_CASES)
def test_every_field_is_required_even_none_and_empty_tuples(index, field):
    model = instances()[index]
    kwargs = {f.name: getattr(model, f.name) for f in fields(model)}
    del kwargs[field]
    with pytest.raises(TypeError):
        type(model)(**kwargs)


@pytest.mark.parametrize("index", range(4))
def test_positional_extra_fields_and_dynamic_attributes_are_not_supported(index):
    model = instances()[index]
    kwargs = {f.name: getattr(model, f.name) for f in fields(model)}
    with pytest.raises(TypeError):
        type(model)(*kwargs.values())
    with pytest.raises(TypeError):
        type(model)(**kwargs, verified=True)
    assert not hasattr(model, "__dict__")
    with pytest.raises((AttributeError, TypeError)):
        model.extra = True


@pytest.mark.parametrize("index,field", FIELD_CASES)
@pytest.mark.parametrize("operation", ["assign", "delete"])
def test_every_stored_field_rejects_assignment_and_deletion(index, field, operation):
    model = instances()[index]
    with pytest.raises(FrozenInstanceError):
        if operation == "assign":
            setattr(model, field, getattr(model, field))
        else:
            delattr(model, field)


@pytest.mark.parametrize("bad", [None, "AMOUNT", 1, True, OtherClaim.AMOUNT, StringSubclass("AMOUNT")])
def test_claim_does_not_convert_raw_strings_or_other_enums(bad):
    invalid("claim", ClaimEvidenceMapping, claim=bad, evidence_refs=("SYNTH-SOURCE-A#amount",))


@pytest.mark.parametrize("bad", [None, [], ["SYNTH-SOURCE-A#amount"], "SYNTH-SOURCE-A#amount",
                                TupleSubclass(("SYNTH-SOURCE-A#amount",)), (), (None,), (1,),
                                (StringSubclass("SYNTH-SOURCE-A#amount"),),
                                ("SYNTH-SOURCE-A#amount", "SYNTH-SOURCE-A#amount")])
def test_evidence_requires_exact_nonempty_unique_string_tuple(bad):
    invalid("evidence_refs", ClaimEvidenceMapping, claim=BenefitReviewClaim.AMOUNT, evidence_refs=bad)


@pytest.mark.parametrize("bad", ["", "SOURCE", "source#amount", " SOURCE#amount", "SOURCE#Amount",
                                "SOURCE#amount ", "SOURCE#amount#extra", "SOURCE#", "#amount",
                                "https://example.test/source", "SOURCE#amount_1", "SOURCE#-amount"])
def test_canonical_evidence_syntax_reuses_existing_pure_parser(bad):
    invalid("evidence_refs", ClaimEvidenceMapping, claim=BenefitReviewClaim.AMOUNT, evidence_refs=(bad,))


def test_multiple_evidence_and_cross_claim_reuse_preserve_original_order_and_objects():
    refs = ("SYNTH-SOURCE-B#second", "SYNTH-SOURCE-A#amount")
    rows = tuple(mapping(claim, refs) for claim in BenefitReviewClaim)
    item = entry(claim_evidence=rows)
    assert item.claim_evidence is rows
    for row in rows:
        assert row.evidence_refs is refs
        assert row.to_dict()["evidence_refs"] == list(refs)
    assert mapping(refs=refs) != mapping(refs=refs[::-1])


@pytest.mark.parametrize("index,field", [(1, "binding"), (1, "artifact"), (2, "acceptance"),
                                        *((2, name) for name in REF_FIELDS)])
@pytest.mark.parametrize("bad", [{}, "raw", True])
def test_nested_models_reject_non_domain_values(index, field, bad):
    model = instances()[index]
    invalid(field, replace, model, **{field: bad})


@pytest.mark.parametrize("index,field", [(1, "binding"), (1, "artifact"), (2, "acceptance"),
                                        *((2, name) for name in REF_FIELDS)])
def test_nested_model_subclasses_are_not_exact_domain_types(index, field):
    model = instances()[index]
    value = getattr(model, field)
    subclass = type("SyntheticSubclass", (type(value),), {})
    derived = subclass(**{f.name: getattr(value, f.name) for f in fields(value)})
    invalid(field, replace, model, **{field: derived})


@pytest.mark.parametrize("field", ("binding", "artifact"))
def test_source_original_requires_nonnullable_fields(field):
    invalid(field, replace, instances()[1], **{field: None})


@pytest.mark.parametrize("field", REF_FIELDS)
def test_accepted_requires_all_seven_original_references(field):
    invalid(field, entry, **{field: None})


@pytest.mark.parametrize("field", REF_FIELDS)
def test_revoked_rejects_each_accepted_only_reference(field):
    invalid(field, entry, revoked=True, **{field: ref()})


@pytest.mark.parametrize("field", ("claim_evidence", "source_bindings", "source_documents", "manual_scenario_ids"))
@pytest.mark.parametrize("bad", [None, [], {}, "raw", TupleSubclass(())])
def test_entry_collections_require_exact_tuple_even_when_revoked(field, bad):
    invalid(field, entry, revoked=True, **{field: bad})


@pytest.mark.parametrize("field", ("claim_evidence", "source_bindings", "source_documents"))
@pytest.mark.parametrize("bad_item", [None, {}, True])
def test_entry_collection_elements_require_exact_models(field, bad_item):
    invalid(field, entry, **{field: (bad_item,)})


@pytest.mark.parametrize("field", ("claim_evidence", "source_bindings", "source_documents"))
def test_entry_collection_element_subclasses_rejected(field):
    value = getattr(entry(), field)[0]
    subclass = type("SyntheticSubclass", (type(value),), {})
    derived = subclass(**{f.name: getattr(value, f.name) for f in fields(value)})
    invalid(field, entry, **{field: (derived,)})


@pytest.mark.parametrize("rows", [(), (mapping(),), tuple(mapping() for _ in range(5)),
                                 tuple(mapping(c) for c in reversed(tuple(BenefitReviewClaim))),
                                 tuple(mapping(c) for c in BenefitReviewClaim) + (mapping(),)])
def test_missing_duplicate_extra_or_reordered_claims_rejected_without_sorting(rows):
    invalid("claim_evidence", entry, claim_evidence=rows)


@pytest.mark.parametrize("field", ("claim_evidence", "source_bindings", "source_documents"))
def test_revoked_requires_empty_accepted_collections(field):
    invalid(field, entry, revoked=True, **{field: getattr(entry(), field)})


@pytest.mark.parametrize("field", ("prepared_by", "reviewed_by", "review_note"))
@pytest.mark.parametrize("bad", [None, "", " \t\n", 1, True, StringSubclass("handle")])
def test_review_metadata_exact_nonblank_strings(field, bad):
    invalid(field, entry, **{field: bad})


def test_handles_differ_without_trimming_or_authenticating_people():
    invalid("reviewed_by", entry, reviewed_by="SYNTH-PREPARER")
    item = entry(prepared_by=" handle ", reviewed_by="handle", review_note=" note ")
    assert item.prepared_by == " handle " and item.review_note == " note "
    assert item.reviewed_by == "handle"


@pytest.mark.parametrize("bad", [(), ("",), (" ",), (None,), (1,), (StringSubclass("RA01"),),
                                ("RA01", "RA01")])
def test_scenarios_are_nonempty_unique_exact_nonblank_strings(bad):
    invalid("manual_scenario_ids", entry, manual_scenario_ids=bad)


def test_scenarios_preserve_order_without_inventing_prefix_grammar():
    ids = ("custom-case", "RA01", " RA01 ")
    assert entry(manual_scenario_ids=ids).manual_scenario_ids is ids


def test_source_bindings_require_nonempty_sorted_unique_ids_and_exact_original_correspondence():
    item = entry()
    invalid("source_bindings", entry, source_bindings=())
    invalid("source_bindings", entry, source_bindings=item.source_bindings[::-1])
    invalid("source_bindings", entry, source_bindings=(item.source_bindings[0],) * 2)
    conflict = SourceBinding(item.source_bindings[0].source_document_id, "d0009")
    invalid("source_bindings", entry, source_bindings=(item.source_bindings[0], conflict))
    for originals in ((), item.source_documents[:1], item.source_documents[::-1], item.source_documents * 2):
        invalid("source_documents", entry, source_documents=originals)
    wrong = replace(item.source_documents[0], binding=conflict)
    invalid("source_documents", entry, source_documents=(wrong, item.source_documents[1]))


@pytest.mark.parametrize("changes", [{"source_document_id": "invalid"}, {"document_version": "d0000"},
                                     {"source_document_id": None}, {"document_version": None}])
def test_partial_or_malformed_nested_binding_is_rejected_by_existing_type(changes):
    with pytest.raises(PolicyDataError):
        SourceBinding(**{"source_document_id": "SYNTH-SOURCE", "document_version": "d0001", **changes})


@pytest.mark.parametrize("changes", [{"revokes_acceptance_ref": None}, {"revokes_acceptance_ref": " "},
                                     {"acceptance_version": "a0000"}, {"benefit_version": "b0000"},
                                     {"policy_id": "invalid"}, {"benefit_id": "invalid"}])
def test_record_local_identity_and_revocation_rules_remain_existing_type_responsibility(changes):
    with pytest.raises(PolicyDataError):
        record(**{"status": BenefitAcceptanceStatus.REVOKED, "revokes_acceptance_ref": "SYNTH-OLD", **changes})


def test_nested_immutable_objects_tuples_and_equal_distinct_bindings_preserved():
    data = entry_values()
    # 같은 값의 별개 binding도 허용하며 재생성하지 않는다.
    originals = tuple(replace(original, binding=replace(original.binding)) for original in data["source_documents"])
    data["source_documents"] = originals
    item = AcceptanceReviewEntry(**data)
    for name in ENTRY_FIELDS:
        assert getattr(item, name) is data[name]
    entries = (item,)
    root = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=entries)
    assert root.entries is entries and root.entries[0] is item
    assert item.source_documents[0].binding == item.source_bindings[0]
    assert item.source_documents[0].binding is not item.source_bindings[0]
    for nested in (item.acceptance, item.accepted_terms_ref, item.source_bindings[0], item.source_documents[0]):
        name = fields(nested)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(nested, name, None)
        with pytest.raises(FrozenInstanceError):
            delattr(nested, name)


@pytest.mark.parametrize("bad", [None, "", "opaque-review", "acceptance-review:sha256:" + "A" * 64,
                                "acceptance-review:sha256:" + "a" * 63,
                                "acceptance-review:sha256:" + "a" * 65,
                                "acceptance-review:sha256:" + "g" * 64,
                                " " + ARTIFACT_REF, ARTIFACT_REF + " ", ARTIFACT_REF + "\n",
                                StringSubclass(ARTIFACT_REF), True])
def test_root_content_addressed_reference_exact_grammar_without_hash_computation(bad):
    invalid("review_artifact_ref", AcceptanceReviewArtifact, review_artifact_ref=bad, entries=(entry(),))


@pytest.mark.parametrize("bad", [None, [], [entry()], (), TupleSubclass((entry(),)), (None,), ({},)])
def test_root_requires_nonempty_exact_entry_tuple(bad):
    invalid("entries", AcceptanceReviewArtifact, review_artifact_ref=ARTIFACT_REF, entries=bad)


def test_root_rejects_entry_subclass():
    derived_type = type("EntrySubclass", (AcceptanceReviewEntry,), {})
    invalid("entries", AcceptanceReviewArtifact, review_artifact_ref=ARTIFACT_REF,
            entries=(derived_type(**entry_values()),))


def test_opaque_record_reference_stays_valid_until_root_profile_binding():
    original = record(review_artifact_ref=" opaque original ")
    item = entry(acceptance=original)
    assert item.acceptance is original
    invalid("entries", AcceptanceReviewArtifact, review_artifact_ref=ARTIFACT_REF, entries=(item,))


def test_claim_source_membership_requires_external_originals_and_is_not_invented_locally():
    rows = tuple(mapping(claim, ("SYNTH-UNBOUND-SOURCE#unverified",)) for claim in BenefitReviewClaim)
    item = entry(claim_evidence=rows)
    # canonical 문법만 검사한다. 원래 Snapshot/Registry의 부분목록 여부를 확인한 것은 아니다.
    assert item.claim_evidence is rows
    assert item.claim_evidence[0].evidence_refs[0].startswith("SYNTH-UNBOUND-SOURCE#")


def test_root_duplicate_refs_revision_keys_and_mismatched_artifact_refs_are_rejected():
    first = entry()
    duplicate_ref = entry(acceptance=replace(first.acceptance, acceptance_version="a0002"))
    duplicate_version = entry(acceptance=replace(first.acceptance, acceptance_ref="SYNTH-OTHER"))
    wrong_ref = entry(acceptance=replace(first.acceptance, review_artifact_ref="acceptance-review:sha256:" + "c" * 64))
    for entries in ((first, first), (first, replace(first)), (first, duplicate_ref),
                    (first, duplicate_version), (wrong_ref,)):
        invalid("entries", AcceptanceReviewArtifact, review_artifact_ref=ARTIFACT_REF, entries=entries)


@pytest.mark.parametrize("target_change", [{"policy_id": "SYNTH-OTHER-POLICY"},
                                          {"scope": ApplicabilityScope("2026", None)},
                                          {"benefit_id": "SYNTH-OTHER-BENEFIT"}])
def test_same_a_version_for_different_targets_is_allowed(target_change):
    first = entry()
    second = entry(acceptance=record(acceptance_ref="SYNTH-OTHER", **target_change))
    root = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(first, second))
    assert root.entries == (first, second)


def test_historical_revision_sharing_and_revocation_do_not_resolve_or_compare_snapshots():
    first = entry()
    later = entry(acceptance=record(acceptance_ref="SYNTH-C", acceptance_version="a0003", benefit_version="b0002",
                                   benefit_fingerprint="c" * 64))
    revoked = entry(revoked=True)
    entries = (later, revoked, first)
    root = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=entries)
    assert root.entries is entries
    assert first.acceptance.benefit_version == "b0001" and later.acceptance.benefit_version == "b0002"
    assert revoked.acceptance.revokes_acceptance_ref == first.acceptance.acceptance_ref
    # target이 같은 collection에 없어도 constructor는 외부 Context를 조회하지 않는다.
    assert AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(revoked,)).entries == (revoked,)


def expected_record():
    return {
        "acceptance_ref": "SYNTH-ACCEPT-A", "acceptance_version": "a0001", "status": "ACCEPTED",
        "policy_id": "SYNTH-POLICY", "scope": {"edition_id": "2026", "quarter": 3},
        "benefit_id": "SYNTH-BENEFIT", "coverage_inventory_version": "i0001",
        "coverage_inventory_fingerprint": "1" * 64, "coverage_rule_version": "r0001",
        "coverage_policy_tree_fingerprint": "2" * 64, "coverage_dataset_version": "SYNTH-D1",
        "coverage_source_registry_fingerprint": "3" * 64, "coverage_implementation_fingerprint": "4" * 64,
        "benefit_version": "b0001", "benefit_fingerprint": "5" * 64, "benefit_dataset_version": "SYNTH-D1",
        "benefit_source_registry_fingerprint": "3" * 64, "reviewed_at": "2026-01-01",
        "valid_until": "2026-12-31", "review_artifact_ref": ARTIFACT_REF, "revokes_acceptance_ref": None,
    }


def expected_entry():
    bindings = [{"source_document_id": "SYNTH-SOURCE-A", "document_version": "d0001"},
                {"source_document_id": "SYNTH-SOURCE-B", "document_version": "d0002"}]
    return {
        "acceptance": expected_record(),
        **{name: {"path": "synthetic/" + name + ".json", "sha256": "b" * 64} for name in REF_FIELDS},
        "claim_evidence": [{"claim": name, "evidence_refs": ["SYNTH-SOURCE-A#amount"]} for name in CLAIMS],
        "source_bindings": bindings,
        "source_documents": [{"binding": dict(binding),
                              "artifact": {"path": "synthetic/" + binding["source_document_id"] + ".pdf",
                                           "sha256": "b" * 64}} for binding in bindings],
        "prepared_by": "SYNTH-PREPARER", "reviewed_by": "SYNTH-REVIEWER", "review_note": "합성 구조 검토 사례",
        "manual_scenario_ids": ["RA39", "RA06"],
    }


def test_serialization_exact_stored_field_order_and_nested_primitive_values():
    row, original, item, root = instances()
    assert row.to_dict() == {"claim": "AMOUNT", "evidence_refs": ["SYNTH-SOURCE-A#amount"]}
    assert original.to_dict() == {
        "binding": {"source_document_id": "SYNTH-SOURCE-A", "document_version": "d0001"},
        "artifact": {"path": "synthetic/original.json", "sha256": "b" * 64},
    }
    assert item.to_dict() == expected_entry()
    assert root.to_dict() == {"review_artifact_ref": ARTIFACT_REF, "entries": [expected_entry()]}
    for obj, (_, names, _) in zip((row, original, item, root), CONTRACTS):
        assert tuple(obj.to_dict()) == names
    assert tuple(item.to_dict()["acceptance"]) == tuple(expected_record())
    assert "schema_version" not in root.to_dict()
    assert len(item.to_dict()["acceptance"]) == 21  # 진단 출력이며 raw20key 본문은 아니다.


def test_revoked_serialization_explicit_null_empty_arrays_and_original_decision():
    output = entry(revoked=True).to_dict()
    assert all(output[name] is None for name in REF_FIELDS)
    assert all(output[name] == [] for name in ("claim_evidence", "source_bindings", "source_documents"))
    assert output["acceptance"]["status"] == "REVOKED"
    assert output["acceptance"]["revokes_acceptance_ref"] == "SYNTH-ACCEPT-A"


def test_serialization_changes_do_not_mutate_any_nested_original():
    row, original, item, root = instances()
    first = root.to_dict()
    first["entries"][0]["acceptance"]["scope"]["quarter"] = None
    first["entries"][0]["accepted_terms_ref"]["path"] = "changed"
    first["entries"][0]["claim_evidence"][0]["evidence_refs"].clear()
    first["entries"][0]["source_bindings"][0]["document_version"] = "d9999"
    first["entries"][0]["source_documents"][0]["binding"].clear()
    first["entries"][0]["source_documents"][1]["artifact"].clear()
    first["entries"][0]["manual_scenario_ids"].append("changed")
    row.to_dict()["evidence_refs"].clear()
    original.to_dict()["artifact"].clear()
    assert root.to_dict() == {"review_artifact_ref": ARTIFACT_REF, "entries": [expected_entry()]}
    assert row.evidence_refs == ("SYNTH-SOURCE-A#amount",)
    assert original.artifact.path == "synthetic/original.json"


@pytest.mark.parametrize("revoked", [False, True])
def test_one_hundred_repeated_equal_inputs_have_equal_values_hash_and_deterministic_serialization(revoked):
    baseline = entry(revoked=revoked)
    expected = json.dumps(baseline.to_dict(), ensure_ascii=False, separators=(",", ":"))
    for _ in range(100):
        current = entry(revoked=revoked)
        assert current == baseline and hash(current) == hash(baseline)
        assert json.dumps(current.to_dict(), ensure_ascii=False, separators=(",", ":")) == expected
        root = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(current,))
        assert root == AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(baseline,))
    for value in instances():
        assert replace(value) == value and hash(replace(value)) == hash(value)


def test_root_order_is_value_order_without_latest_selection():
    a, b = entry(), entry(revoked=True)
    left = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(a, b))
    right = AcceptanceReviewArtifact(review_artifact_ref=ARTIFACT_REF, entries=(b, a))
    assert left != right
    assert left.to_dict()["entries"][0]["acceptance"]["acceptance_ref"] == "SYNTH-ACCEPT-A"


def test_validation_phase_precedence_and_payload_not_echoed():
    # 뒤 필드의 타입 오류가 앞 status 조합 오류보다 먼저이며 nested 검증은 재실행하지 않는다.
    invalid("manual_scenario_ids", entry, accepted_terms_ref=None, manual_scenario_ids=["RA01"])
    invalid("reviewed_by", entry, accepted_terms_ref=None, reviewed_by="SYNTH-PREPARER")
    invalid("accepted_terms_ref", entry, accepted_terms_ref=None, claim_evidence=())
    invalid("claim_evidence", entry, claim_evidence=(), source_bindings=())
    secret = "SYNTH-private-value"
    message = invalid("evidence_refs", ClaimEvidenceMapping, claim=BenefitReviewClaim.AMOUNT,
                      evidence_refs=(secret,))
    assert secret not in message


def test_public_exports_only_add_the_five_approved_domain_names():
    for name in ("BenefitReviewClaim", "ClaimEvidenceMapping", "ReviewSourceOriginal",
                 "AcceptanceReviewEntry", "AcceptanceReviewArtifact"):
        assert getattr(policy_data, name) is getattr(domain, name)
        assert policy_data.__all__.count(name) == 1
    assert "_invalid" not in policy_data.__all__ and "_REFERENCE_FIELDS" not in policy_data.__all__


def test_current_model_dependencies_and_calls_have_no_io_hash_lookup_or_evaluation(monkeypatch):
    tree = ast.parse(inspect.getsource(domain))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert imports == {"dataclasses", "enum", "re", "errors", "sources.models", "benefit_acceptance",
                       "envelope", "manifest"}
    functions = [obj for obj in vars(domain).values() if inspect.isfunction(obj) and obj.__module__ == domain.__name__]
    functions += [getattr(cls, method) for cls, _, _ in CONTRACTS for method in ("__post_init__", "to_dict")]
    forbidden = {"open", "read_bytes", "read_text", "today", "now", "hashlib", "requests",
                 "resolve", "get_source", "_resolve_benefit_acceptance", "evaluate_eligibility_coverage",
                 "fingerprint_benefit_snapshot", "fingerprint_source_registry", "calculate_cashflow"}
    for function in functions:
        assert forbidden.isdisjoint(function.__code__.co_names)

    def fail(*args, **kwargs):
        pytest.fail("모델이 외부 조회/계산을 호출했습니다")

    monkeypatch.setattr(SourceRegistry, "resolve", fail)
    monkeypatch.setattr(SourceRegistry, "get_source", fail)
    monkeypatch.setattr(policy_data, "fingerprint_benefit_snapshot", fail)
    monkeypatch.setattr(policy_data, "evaluate_eligibility_coverage", fail)
    monkeypatch.setattr(Path, "read_bytes", fail)
    monkeypatch.setattr(Path, "read_text", fail)
    # 파일/Registry/Snapshot 없이 존재하지 않는 합성 경로와 문법상 지문도 모델로 표현 가능하다.
    assert instances()[3].to_dict()["entries"][0] == expected_entry()

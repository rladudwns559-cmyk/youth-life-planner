"""합성 review_ref resolution 전용. 현재 대상/버전/지문 matching은 수행하지 않는다."""

import ast
from dataclasses import replace
from datetime import date
import inspect

import pytest

from backend.policy_engine.errors import PolicyDataError
from backend.policy_engine.policy_data import ApplicabilityScope, CoverageReviewContext, ImplementationBindingReview, InventoryCompletenessReview
from backend.policy_engine.policy_data import coverage_review_resolution as domain


RESOLVERS = (domain._resolve_inventory_review, domain._resolve_implementation_review)


def inventory(**changes):
    values = dict(review_ref="SYNTH-INV-OLD", policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3),
                  inventory_version="i0001", inventory_fingerprint="a" * 64, dataset_version="SYNTH-OLD",
                  source_registry_fingerprint="b" * 64, reviewed_at=date(2024, 2, 29),
                  review_artifact_ref="SYNTH-NONEXISTENT-ARTIFACT")
    values.update(changes)
    return InventoryCompletenessReview(**values)


def implementation(**changes):
    values = dict(review_ref="SYNTH-IMPL-OLD", policy_id="SYNTH-POLICY", scope=ApplicabilityScope("2026", 3),
                  condition_id="SYNTH_CONDITION_A", rule_root_id="SYNTH_RULE_A",
                  inventory_version="i0001", inventory_fingerprint="a" * 64, rule_version="r0001",
                  policy_tree_fingerprint="c" * 64, subtree_fingerprint="d" * 64,
                  dataset_version="SYNTH-OLD", source_registry_fingerprint="b" * 64,
                  implementation_fingerprint="e" * 64, reviewed_at=date(2024, 2, 29),
                  review_artifact_ref="SYNTH-NONEXISTENT-ARTIFACT")
    values.update(changes)
    return ImplementationBindingReview(**values)


def context(inventory_reviews=(), implementation_reviews=()):
    return CoverageReviewContext("SYNTH-POLICY", ApplicabilityScope("2026", 3), "SYNTH-CURRENT",
                                 "0" * 64, "1" * 64, inventory_reviews, implementation_reviews)


@pytest.mark.parametrize("kind", ["inventory", "implementation"])
@pytest.mark.parametrize("mixed", [False, True])
def test_single_record_resolves_to_original_object(kind, mixed):
    inv, impl = inventory(), implementation()
    values = context((inv,) if kind == "inventory" or mixed else (),
                     (impl,) if kind == "implementation" or mixed else ())
    resolver, original = (RESOLVERS[0], inv) if kind == "inventory" else (RESOLVERS[1], impl)
    assert resolver(values, original.review_ref) is original


@pytest.mark.parametrize("kind", ["inventory", "implementation"])
@pytest.mark.parametrize("reverse", [False, True])
def test_historical_versions_same_condition_select_only_explicit_ref(kind, reverse):
    old_inv, old_impl = inventory(), implementation()
    new_inv = replace(old_inv, review_ref="SYNTH-INV-NEW", inventory_version="i0002",
                      inventory_fingerprint="2" * 64, reviewed_at=date(2026, 10, 21))
    new_impl = replace(old_impl, review_ref="SYNTH-IMPL-NEW", inventory_version="i0002", rule_version="r0002",
                       inventory_fingerprint="3" * 64, subtree_fingerprint="4" * 64, reviewed_at=date(2026, 10, 21))
    invs, impls = (old_inv, new_inv), (old_impl, new_impl)
    if reverse:
        invs, impls = tuple(reversed(invs)), tuple(reversed(impls))
    value = context(invs, impls)
    resolver, records = (RESOLVERS[0], invs) if kind == "inventory" else (RESOLVERS[1], impls)
    for original in records:
        assert resolver(value, original.review_ref) is original
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        resolver(value, "SYNTH-UNDECLARED-NEWEST")


@pytest.mark.parametrize("resolver", RESOLVERS)
@pytest.mark.parametrize("shape", ["empty", "inventory_only", "implementation_only", "mixed"])
def test_ref_absent_from_both_collections_is_broken_reference(resolver, shape):
    value = context((inventory(),) if shape in ("inventory_only", "mixed") else (),
                    (implementation(),) if shape in ("implementation_only", "mixed") else ())
    with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
        resolver(value, "SYNTH-ABSENT")


@pytest.mark.parametrize("kind", ["inventory", "implementation"])
@pytest.mark.parametrize("mixed", [False, True])
def test_ref_in_opposite_collection_is_wrong_type_not_missing(kind, mixed):
    inv, impl = inventory(), implementation()
    if kind == "inventory":
        value, resolver, wrong_ref = context((inv,) if mixed else (), (impl,)), RESOLVERS[0], impl.review_ref
    else:
        value, resolver, wrong_ref = context((inv,), (impl,) if mixed else ()), RESOLVERS[1], inv.review_ref
    with pytest.raises(PolicyDataError) as caught:
        resolver(value, wrong_ref)
    assert str(caught.value).startswith("WRONG_REVIEW_TYPE:")
    assert "REVIEW_REF_NOT_FOUND" not in str(caught.value)


class FakeContext:
    @property
    def inventory_reviews(self):
        pytest.fail("잘못된 Context의 collection을 읽었습니다")


class ContextSubclass(CoverageReviewContext):
    pass


class TextSubclass(str):
    pass


@pytest.mark.parametrize("resolver", RESOLVERS)
@pytest.mark.parametrize("bad", [None, {}, [], (), "SYNTH", 1, True, FakeContext()])
def test_context_must_be_exact_model_and_none_is_not_missing_outcome(resolver, bad):
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: context"):
        resolver(bad, "SYNTH-REF")


@pytest.mark.parametrize("resolver", RESOLVERS)
def test_context_subclass_is_rejected(resolver):
    value = ContextSubclass("SYNTH-POLICY", ApplicabilityScope("2026", 3), "SYNTH-CURRENT", "a" * 64, "b" * 64, (), ())
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: context"):
        resolver(value, "SYNTH-REF")


@pytest.mark.parametrize("resolver", RESOLVERS)
@pytest.mark.parametrize("bad", ["", " \t\n", None, 1, True, [], {}, TextSubclass("SYNTH-REF")])
def test_ref_requires_exact_nonblank_string_without_conversion(resolver, bad):
    with pytest.raises(PolicyDataError, match="^INVALID_MATCH_INPUT: review_ref"):
        resolver(context(), bad)


@pytest.mark.parametrize("kind", ["inventory", "implementation"])
def test_whitespace_and_case_are_preserved_as_distinct_identity(kind):
    factory, resolver = (inventory, RESOLVERS[0]) if kind == "inventory" else (implementation, RESOLVERS[1])
    records = tuple(factory(review_ref=ref) for ref in ("SYNTH-REF", " SYNTH-REF ", "synth-ref"))
    value = context(records, ()) if kind == "inventory" else context((), records)
    for original in records:
        assert resolver(value, original.review_ref) is original
    for wrong_ref in ("SYNTH-REF ", "SYNTH-REF-X", "Synth-Ref"):
        with pytest.raises(PolicyDataError, match="^REVIEW_REF_NOT_FOUND:"):
            resolver(value, wrong_ref)


@pytest.mark.parametrize("resolver", RESOLVERS)
def test_errors_are_deterministic_for_reordered_context_without_ref_payload_leak(resolver):
    invs = (inventory(), inventory(review_ref="SYNTH-INV-NEW", inventory_version="i0002"))
    impls = (implementation(), implementation(review_ref="SYNTH-IMPL-NEW", rule_version="r0002"))
    values = (context(invs, impls), context(tuple(reversed(invs)), tuple(reversed(impls))))
    absent = "SYNTH-private-absent-ref"
    messages = []
    for value in values:
        with pytest.raises(PolicyDataError) as caught:
            resolver(value, absent)
        messages.append((type(caught.value), str(caught.value)))
        assert absent not in str(caught.value)
    assert messages[0] == messages[1]
    wrong_ref = impls[0].review_ref if resolver is RESOLVERS[0] else invs[0].review_ref
    for value in values:
        with pytest.raises(PolicyDataError, match="^WRONG_REVIEW_TYPE:"):
            resolver(value, wrong_ref)


def test_resolver_does_not_read_target_versions_dates_or_fingerprints(monkeypatch):
    inv, impl = inventory(), implementation()
    value = context((inv,), (impl,))
    # current dataset/source/implementation과 달라도 ref만 보고 원래 record를 반환해야 한다.
    def review_access(record, name):
        if name != "review_ref":
            pytest.fail("Resolver가 review_ref 외의 record 필드를 읽었습니다")
        return object.__getattribute__(record, name)
    def context_access(current, name):
        if name not in ("inventory_reviews", "implementation_reviews"):
            pytest.fail("Resolver가 두 review tuple 외의 Context 필드를 읽었습니다")
        return object.__getattribute__(current, name)
    monkeypatch.setattr(InventoryCompletenessReview, "__getattribute__", review_access)
    monkeypatch.setattr(ImplementationBindingReview, "__getattribute__", review_access)
    monkeypatch.setattr(CoverageReviewContext, "__getattribute__", context_access)
    assert RESOLVERS[0](value, "SYNTH-INV-OLD") is inv
    assert RESOLVERS[1](value, "SYNTH-IMPL-OLD") is impl
    for resolver, opposite in ((RESOLVERS[0], "SYNTH-IMPL-OLD"), (RESOLVERS[1], "SYNTH-INV-OLD")):
        with pytest.raises(PolicyDataError, match="^WRONG_REVIEW_TYPE:"):
            resolver(value, opposite)


def test_100_resolutions_preserve_context_and_review_object_identity():
    inv, impl = inventory(), implementation()
    value = context((inv,), (impl,))
    before = value.to_dict()
    invs, impls = value.inventory_reviews, value.implementation_reviews
    for _ in range(100):
        assert RESOLVERS[0](value, inv.review_ref) is inv
        assert RESOLVERS[1](value, impl.review_ref) is impl
        assert value.to_dict() == before
    assert value.inventory_reviews is invs and value.implementation_reviews is impls


def test_resolution_does_not_reconstruct_or_revalidate_models_or_access_io(monkeypatch):
    inv, impl = inventory(), implementation()
    value = context((inv,), (impl,))
    def forbidden(*args, **kwargs):
        pytest.fail("Resolver에서 모델 재검증·hash·외부 상태를 호출했습니다")
    for model in (CoverageReviewContext, InventoryCompletenessReview, ImplementationBindingReview):
        monkeypatch.setattr(model, "__post_init__", forbidden)
        monkeypatch.setattr(model, "to_dict", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("hashlib.sha256", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("pathlib.Path.exists", forbidden)
    monkeypatch.setattr("os.getenv", forbidden)
    assert RESOLVERS[0](value, inv.review_ref) is inv
    assert RESOLVERS[1](value, impl.review_ref) is impl


def test_private_apis_require_only_context_and_ref_without_package_export():
    from backend.policy_engine import policy_data
    for resolver in RESOLVERS:
        signature = inspect.signature(resolver)
        assert list(signature.parameters) == ["context", "review_ref"]
        assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())
        assert resolver.__name__ not in policy_data.__all__
        assert not hasattr(policy_data, resolver.__name__)
        with pytest.raises(TypeError):
            resolver(context(), "SYNTH-REF", current_policy=None)


def test_direct_dependencies_and_record_access_are_only_resolution():
    tree = ast.parse(inspect.getsource(domain))
    assert {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {
        "errors", "coverage_review", "coverage_review_context", "implementation_review",
    }
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    assert all(node.name.startswith("_") for node in tree.body if isinstance(node, ast.FunctionDef))
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert attributes == {"inventory_reviews", "implementation_reviews", "review_ref", "strip"}
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not names & {"ReviewMatchStatus", "ReviewMissingReason", "ReviewStaleReason", "InventoryReviewMatch",
                        "ImplementationReviewMatch", "EligibilityCoverage", "ConditionInventory", "ConditionBinding",
                        "Policy", "CoverageResult", "hashlib", "date", "datetime"}

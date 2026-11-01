"""혜택 정의의 명시 payload 지문. 배포 provenance·검토/수용 상태는 계산하지 않는다."""

import hashlib
import json

from ..errors import PolicyDataError
from .benefit_snapshot import BenefitSnapshot


def _build_benefit_snapshot_fingerprint_payload(snapshot: BenefitSnapshot) -> dict[str, object]:
    """정의15key만 선택하고 근거·월·관련 binding의 원래 순서를 보존한다."""
    return {
        "fingerprint_schema": "benefit-snapshot-1.0",
        "policy_id": snapshot.policy_id,
        "scope": {"edition_id": snapshot.scope.edition_id, "quarter": snapshot.scope.quarter},
        "benefit_id": snapshot.benefit_id,
        "benefit_version": snapshot.benefit_version,
        "amount_type": snapshot.amount_type.value,
        "amount_krw": snapshot.amount_krw,
        "amount_description": snapshot.amount_description,
        "payment_cadence": snapshot.payment_cadence.value,
        "benefit_medium": snapshot.benefit_medium.value,
        "restriction": snapshot.restriction.value,
        "restriction_details": snapshot.restriction_details,
        "applicable_months": None if snapshot.applicable_months is None else list(snapshot.applicable_months),
        "benefit_evidence_refs": list(snapshot.benefit_evidence_refs),
        "source_bindings": [
            {"source_document_id": binding.source_document_id, "document_version": binding.document_version}
            for binding in snapshot.source_bindings
        ],
    }


def fingerprint_benefit_snapshot(snapshot: BenefitSnapshot) -> str:
    """정확한 정의 값 → canonical JSON/strict UTF-8 → SHA256. dataset/Registry 전체는 제외한다."""
    if type(snapshot) is not BenefitSnapshot:
        raise PolicyDataError("benefit snapshot fingerprint: 정확한 BenefitSnapshot이 필요합니다")
    payload = _build_benefit_snapshot_fingerprint_payload(snapshot)
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError):
        raise PolicyDataError("benefit snapshot fingerprint: canonical JSON/UTF-8 인코딩 계약을 확인하세요") from None
    return hashlib.sha256(encoded).hexdigest()

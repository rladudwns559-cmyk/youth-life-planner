"""저장소의 합성 데이터만 실행하는 M1 예제."""

import argparse
import json
from datetime import date
from pathlib import Path

from . import EvaluationContext, evaluate_policies, load_policy_set, load_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="실제 자격 판정이 아닌 합성 정책 M1 예제")
    parser.add_argument("--summary", action="store_true", help="상태와 누락 필드만 출력")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    policies = load_policy_set(root / "data/synthetic/policies.json")
    profile = load_profile(root / "data/synthetic/profile.json")
    context = EvaluationContext(as_of=date(2026, 10, 20), dataset_version=policies.dataset_version)
    results = evaluate_policies(profile, policies, context)
    output = [result.to_dict() for result in results]
    if args.summary:
        output = [{key: item[key] for key in ("policy_id", "overall_status", "display_status", "missing_fields")} for item in output]
    print(json.dumps({"synthetic": True, "test_only": True, "results": output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

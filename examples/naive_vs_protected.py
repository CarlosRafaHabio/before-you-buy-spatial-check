"""Demonstrate an unsafe anti-pattern versus Spatial Check's admission boundary.

This file is intentionally an example, not library code. The naive function below is
deliberately unsafe: it treats model-supplied metadata as authority. Do not copy it
into a real integration.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spatial_check import evaluate
from spatial_check.json_io import load


def intentionally_unsafe_naive_decision(candidate: dict) -> str:
    """ANTI-PATTERN: model-supplied source/status labels are not trustworthy."""
    facts = candidate.get("facts")
    if not isinstance(facts, list) or not facts:
        return "REVIEW"
    trusted_labels = {"user_measurement", "user_confirmation", "document_dimension"}
    if all(
        isinstance(fact, dict)
        and fact.get("status") == "PROVIDED"
        and isinstance(fact.get("source"), dict)
        and fact["source"].get("kind") in trusted_labels
        for fact in facts
    ):
        return "APPROVED_BY_NAIVE_PIPELINE"
    return "REVIEW"


def main() -> int:
    request = load(ROOT / "examples" / "fits.request.json")
    candidate = load(ROOT / "examples" / "fits.evidence.json")

    naive = intentionally_unsafe_naive_decision(candidate)
    protected = evaluate(request, candidate)
    blocker_codes = [item["code"] for item in protected["blockers"]]

    print("INTENTIONALLY_UNSAFE_ANTI_PATTERN")
    print(f"NAIVE_DECISION={naive}")
    print("The same candidate is then passed to Spatial Check WITHOUT host admission.")
    print(f"SPATIAL_CHECK_STATUS={protected['status']}")
    print(f"SPATIAL_CHECK_EXECUTION_MODE={protected['execution_mode']}")
    print(f"SPATIAL_CHECK_BLOCKERS={','.join(blocker_codes)}")
    print("Reason: source/status labels inside model data do not create authority.")

    if naive != "APPROVED_BY_NAIVE_PIPELINE":
        return 3
    if protected["status"] != "UNVERIFIED":
        return 4
    if protected["execution_mode"] != "UNTRUSTED" or "TRUST_REQUIRED" not in blocker_codes:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Minimal interactive reference host for the fixed synthetic fits fixture.

The reviewer sees the exact canonical EvidenceClaim bytes and must type CONFIRM before
HostIntake.confirm() is called. This demonstrates host-controlled admission; it does
not authenticate the reviewer, source, manufacturer, measurement, or physical truth.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spatial_check import evaluate
from spatial_check.json_io import load
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data

HOST_SCOPE = {
    "case_id": "case-1",
    "revision": "r1",
    "room_identity": "room-1",
    "item_identity": "product-1",
}


def run_review(*, input_fn=input, output_fn=print) -> int:
    request = load(ROOT / "examples" / "fits.request.json")
    candidate = load(ROOT / "examples" / "fits.evidence.json")

    authority = LifecycleRegistry()
    host = HostIntake(authority)
    claim = claim_from_data(candidate)

    output_fn("SYNTHETIC_REFERENCE_HOST")
    output_fn("Review the exact canonical claim below.")
    output_fn("This review controls admission only; it does not authenticate real-world facts.")
    output_fn(f"CLAIM_SHA256={hashlib.sha256(claim.payload.encode()).hexdigest()}")
    output_fn("BEGIN_CANONICAL_CLAIM")
    output_fn(claim.payload)
    output_fn("END_CANONICAL_CLAIM")

    answer = input_fn("Type CONFIRM to admit this exact claim, or anything else to cancel: ")
    if answer != "CONFIRM":
        output_fn("REVIEW_CANCELLED")
        output_fn("No trusted receipt was issued.")
        return 2

    receipt = host.confirm(
        claim,
        **HOST_SCOPE,
        confirmation_ref="interactive-reference-review",
    )
    result = evaluate(request, receipt)

    output_fn("REVIEW_CONFIRMED")
    output_fn(f"SPATIAL_CHECK_STATUS={result['status']}")
    output_fn(f"SPATIAL_CHECK_EXECUTION_MODE={result['execution_mode']}")
    output_fn(f"ADMISSION_RECEIPT_ID={result['admission']['receipt_id']}")
    output_fn("This is a geometric result over admitted synthetic data, not purchase approval.")
    output_fn(json.dumps(result, ensure_ascii=False, sort_keys=True))

    if result["execution_mode"] != "HOST_CONFIRMED_INPUT":
        return 3
    if result["status"] == "UNVERIFIED":
        return 4
    return 0 if result["status"] == "NO CONFLICT DETECTED IN PROVIDED DATA" else 1


def main() -> int:
    return run_review()


if __name__ == "__main__":
    raise SystemExit(main())

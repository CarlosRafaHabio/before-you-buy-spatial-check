"""TEST ONLY: consume a serialized public result, never an intake/receipt object.

Schema/consistency checks cannot authenticate a JSON report or establish currency.
The caller must obtain a fresh result from the trusted host. This is not an adapter.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from spatial_check.contracts import validate
from spatial_check.json_io import loads

SUPPORTED_VERSION = "0.3.0"  # Deliberately pinned independently of the schema file.
SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schemas/result.schema.json").read_text())
DECISIONS = {
    "CONFLICT DETECTED": "CONFLICT DETECTED",
    "NO CONFLICT DETECTED IN PROVIDED DATA": "NO CONFLICT DETECTED IN PROVIDED DATA",
    "UNVERIFIED": "UNVERIFIED",
}


class ConsumerContractError(ValueError):
    """Test consumer refuses an incompatible or internally inconsistent report."""


@dataclass
class ConsumedResult:
    decision: str
    result: dict

    @property
    def purchase_approved(self) -> bool:
        # None of the three spatial outcomes grants purchase approval/certification.
        return False

    @property
    def currentness(self) -> str:
        return "NOT_ESTABLISHED_FROM_SERIALIZED_RESULT"

    @property
    def reported_receipt_identity(self) -> tuple[str, str] | None:
        admission = self.result["admission"]
        if admission is None:
            return None
        # Process-local only; never use an event ref or a content digest as identity.
        return admission["domain_id"], admission["receipt_id"]

    def same_report_as(self, other: "ConsumedResult") -> bool:
        # Retain ALL public fields, including digest/event changes, without rebuilding them.
        # Equality of reports is neither authentication nor a currency check.
        return self.result == other.result


def consume(serialized_result: str) -> ConsumedResult:
    """Check the public 0.3.0 envelope and preserve its exact spatial decision.

    receipt_id: admission identity in a live process-local domain.
    confirmation_ref: repeatable host event reference, not receipt identity.
    evidence_digest: admitted snapshot content, not receipt identity.
    input_digest: request + snapshot content, not receipt identity.
    Text/locator/diagnostics are retained as data and never dispatched as commands.
    """
    try:
        result = loads(serialized_result)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ConsumerContractError("Invalid serialized public result.") from exc
    if type(result) is not dict or result.get("engine_version") != SUPPORTED_VERSION:
        raise ConsumerContractError("Unsupported result version.")
    errors = validate(result, SCHEMA)
    if errors:
        raise ConsumerContractError("Public result schema rejected: " + "; ".join(errors[:5]))
    status = result["status"]
    if status not in DECISIONS:
        raise ConsumerContractError("Unsupported spatial decision.")
    if status != "UNVERIFIED":
        admission = result["admission"]
        # The structural schema is not a cross-field semantic/authentication proof.
        if (admission is None or result["execution_mode"] == "UNTRUSTED"
                or result["input_digest"] is None or result["blockers"]):
            raise ConsumerContractError("Resolved outcome lacks admitted, unblocked inputs.")
        if any(result[key] != admission[key] for key in ("case_id", "revision", "item_identity")):
            raise ConsumerContractError("Result/admission scope mismatch.")
        if not result["checks"] or any(c["outcome"] == "BLOCKED" for c in result["checks"]):
            raise ConsumerContractError("Resolved outcome has missing/blocked checks.")
        has_conflict = any(c["outcome"] == "CONFLICT" for c in result["checks"])
        if status == "NO CONFLICT DETECTED IN PROVIDED DATA":
            if result["findings"] or has_conflict:
                raise ConsumerContractError("No-conflict status contradicts findings/checks.")
        elif not result["findings"] or not has_conflict:
            raise ConsumerContractError("Conflict status lacks findings/checks.")
    return ConsumedResult(DECISIONS[status], result)

"""Host-only intake capability. JSON claims do not confer authority.

This is a library boundary, NOT authentication or a Python execution sandbox.
Never expose HostIntake.confirm, HostIntake, or Python execution as model tools.
"""
from dataclasses import dataclass
import hashlib
import json
from itertools import count
from threading import RLock
from weakref import WeakKeyDictionary

from .contracts import EVIDENCE_SCHEMA, ID, validate
from .units import InputError, reject_ambiguous_number


class TrustError(ValueError):
    """Untrusted, malformed, stale or incorrectly bound evidence."""


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """Immutable candidate bytes; ANYONE may create a claim. Never trusted."""
    payload: str


def claim_from_data(value: object) -> EvidenceClaim:
    """Syntactic/structural validation only. This does not confirm any fact."""
    try:
        payload = json.dumps(value, sort_keys=True, ensure_ascii=True,
                             allow_nan=False, separators=(",", ":"))
        if len(payload) > 1_000_000:
            raise ValueError("Claim exceeds input limit.")
        snapshot = json.loads(payload)
        errors = validate(snapshot, EVIDENCE_SCHEMA, "claim")
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise TrustError("Claim must be bounded JSON conforming to evidence schema.") from exc
    if errors:
        raise TrustError("Claim schema invalid: " + "; ".join(errors[:10]))
    return EvidenceClaim(payload)


class TrustedEvidence:
    """Opaque process-local receipt, without serializable evidence attributes."""
    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("Only HostIntake.confirm can issue TrustedEvidence.")

    def __init_subclass__(cls, **kwargs):
        raise TypeError("TrustedEvidence cannot be subclassed.")

    def __reduce__(self):
        raise TypeError("TrustedEvidence cannot be serialized or copied.")


_domain_sequence = count(1)  # Labels only, NOT a shared lifecycle authority.


class _IssuerState:
    def __init__(self):
        self.domain_id = f"domain-{next(_domain_sequence)}"
        self.receipt_sequence = 0
        self.current: dict[str, tuple[str, str]] = {}
        self.history: dict[str, dict[str, str]] = {}
        self.lock = RLock()


class LifecycleRegistry:
    """One volatile lifecycle authority/domain, identified only within this process.

    Hosts for the same domain MUST share this exact object. Constructing another
    registry creates an independent domain, even when case/revision labels match.
    There is no restart continuity or cross-process identity/replay guarantee.
    """
    def __init__(self):
        self._state = _IssuerState()

    @property
    def domain_id(self) -> str:
        return self._state.domain_id

    def __reduce__(self):
        raise TypeError("LifecycleRegistry cannot be copied or serialized; share the live object.")


@dataclass(frozen=True, slots=True)
class _IssuedRecord:
    payload: str
    state: _IssuerState
    case_id: str
    revision: str
    digest: str
    confirmation_ref: str
    receipt_id: str


_records: WeakKeyDictionary = WeakKeyDictionary()
_records_lock = RLock()


class HostIntake:
    """Capability retained only by trusted application/bootstrap code.

    Calling confirm is the explicit admission act after external review. The
    library cannot determine who clicked or authored a message. The host must
    bind the expected case/product/revision independently of model claims.
    """
    def __init__(self, registry: LifecycleRegistry | None = None):
        if registry is None:
            registry = LifecycleRegistry()
        if type(registry) is not LifecycleRegistry:
            raise TypeError("HostIntake requires a live LifecycleRegistry authority.")
        self._registry = registry  # Retain authority; deepcopy/pickle cannot clone its state.
        self._state = registry._state

    @property
    def domain_id(self) -> str:
        """Process-local authority label, never a persistent identity."""
        return self._state.domain_id

    def confirm(self, claim: EvidenceClaim, *, case_id: str, revision: str,
                room_identity: str, item_identity: str,
                confirmation_ref: str) -> TrustedEvidence:
        if type(claim) is not EvidenceClaim or type(claim.payload) is not str:
            raise TrustError("Confirmation requires an EvidenceClaim, never a JSON trust flag.")
        # Revalidate even when a caller manually constructed EvidenceClaim.
        try:
            if len(claim.payload) > 1_000_000:
                raise ValueError("Claim exceeds input limit.")
            from .json_io import loads
            canonical = claim_from_data(loads(claim.payload))
        except (ValueError, TypeError, RecursionError) as exc:
            raise TrustError("Malformed claim at confirmation boundary.") from exc
        snapshot = json.loads(canonical.payload)
        expected = {"case_id": case_id, "revision": revision,
                    "room_identity": room_identity, "item_identity": item_identity}
        for key, value in expected.items():
            if validate(value, ID) or snapshot[key] != value:
                raise TrustError("Claim does not match independently selected host scope.")
        if validate(confirmation_ref, ID):
            raise TrustError("A host confirmation event reference is required.")
        # Admission must not turn a locale-ambiguous token into trusted geometry.
        # Keep the original claim bytes; clarification requires a new claim.
        for fact in snapshot["facts"]:
            try:
                reject_ambiguous_number(fact["value"])
            except InputError as exc:
                raise TrustError(f"Fact {fact['id']}: {exc}") from exc
        digest = hashlib.sha256(canonical.payload.encode()).hexdigest()
        state = self._state
        with state.lock:
            history = state.history.setdefault(case_id, {})
            previous_digest = history.get(revision)
            current = state.current.get(case_id)
            if previous_digest is not None:
                if previous_digest != digest:
                    raise TrustError("Changed evidence requires a new revision.")
                if current != (revision, digest):
                    raise TrustError("A stale/revoked revision cannot be reactivated.")
            history[revision] = digest
            state.current[case_id] = (revision, digest)
            state.receipt_sequence += 1
            receipt_id = f"{state.domain_id}/receipt-{state.receipt_sequence}"
            handle = object.__new__(TrustedEvidence)
            with _records_lock:
                _records[handle] = _IssuedRecord(canonical.payload, state, case_id,
                                                revision, digest, confirmation_ref, receipt_id)
        return handle

    def revoke(self, case_id: str) -> None:
        """Host may revoke a case; any subsequent confirmation needs new revision."""
        with self._state.lock:
            self._state.current.pop(case_id, None)


def _read_trusted(handle: object) -> tuple[dict, dict]:
    if type(handle) is not TrustedEvidence:
        raise TrustError("Raw JSON/text/claims are not trusted evidence; host confirmation required.")
    with _records_lock:
        record = _records.get(handle)
    if record is None:
        raise TrustError("Unissued or forged evidence object.")
    with record.state.lock:
        if record.state.current.get(record.case_id) != (record.revision, record.digest):
            raise TrustError("Evidence revision is stale or revoked.")
        snapshot = json.loads(record.payload)
        admission = {"domain_id": record.state.domain_id, "receipt_id": record.receipt_id,
                     "confirmation_ref": record.confirmation_ref, "evidence_digest": record.digest,
                     "case_id": record.case_id, "revision": record.revision,
                     "room_identity": snapshot["room_identity"],
                     "item_identity": snapshot["item_identity"]}
        return snapshot, admission

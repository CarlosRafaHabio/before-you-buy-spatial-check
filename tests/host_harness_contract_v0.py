"""TEST ONLY: external embedded-host fixture for Host Contract V0.1.

Uses public library APIs. No core internals, adapter, transport, persistence,
authentication, signatures, real review UI, or arbitrary-code sandbox.
Operational UUIDs/times/sequences live only outside the engine result.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from spatial_check import evaluate
from spatial_check.contracts import INPUT_SCHEMA, validate
from spatial_check.json_io import loads
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data
from tests.consumer_contract_v0 import ConsumerContractError, consume

CONFLICT = "CONFLICT DETECTED"
NO_CONFLICT = "NO CONFLICT DETECTED IN PROVIDED DATA"
UNVERIFIED = "UNVERIFIED"


class HostContractError(ValueError):
    """Host refuses an operation; never a manufactured engine verdict."""


@dataclass(frozen=True)
class Context:
    case_id: str
    revision: str
    item_identity: str
    room_identity: str


@dataclass(frozen=True)
class Review:
    context: Context
    claim: object
    evidence_digest: str
    confirmation_ref: str


@dataclass(frozen=True)
class Admission:
    review: Review
    receipt: object


@dataclass
class Case:
    context: Context
    admission: Admission | None = None
    review: Review | None = None
    pending: bool = False
    generation: int = 0


@dataclass(frozen=True)
class Delivery:
    """An immutable host-owned delivery; its JSON alone has no authority."""
    serialized_envelope: str
    serialized_request: str


@dataclass
class Presentation:
    result: dict
    context_state: str
    envelope: dict | None = None

    @property
    def decision(self):
        return self.result["status"]

    @property
    def purchase_approved(self):
        return False

    @property
    def physically_verified(self):
        return False

    @property
    def source_authenticated(self):
        return False

    @property
    def authoritative_block(self):
        # Preserve the whole engine result including limitations and free text.
        return deepcopy(self.result)


def check_result(serialized, expected_context=None):
    """Public schema/consistency checks, NEVER authentication or freshness."""
    result = consume(serialized).result
    if result["status"] == UNVERIFIED and not result["blockers"]:
        raise ConsumerContractError("UNVERIFIED requires blockers.")
    if result["status"] == CONFLICT:
        conflicts = [c for c in result["checks"] if c["outcome"] == "CONFLICT"]
        for finding in result["findings"]:
            if not any(finding["field"] == c["id"]
                       and finding["code"] == c["kind"].upper() + "_CONFLICT"
                       and set(finding["evidence_ids"]) == set(c["evidence_ids"])
                       for c in conflicts):
                raise ConsumerContractError("Finding/check mismatch.")
        if any(not any(f["field"] == c["id"] for f in result["findings"])
               for c in conflicts):
            raise ConsumerContractError("Conflict check lacks a finding.")
    admission = result["admission"]
    if admission is not None:
        if expected_context is not None:
            expected = asdict(expected_context)
            if any(admission[k] != value for k, value in expected.items()):
                raise ConsumerContractError("Admission differs from selected context.")
        if any(result[k] is not None and result[k] != admission[k]
               for k in ("case_id", "revision", "item_identity")):
            raise ConsumerContractError("Result differs from admission scope.")
    return result


def historical(serialized):
    """External JSON stays historical even when its live_evaluation flag is true."""
    data = loads(serialized)
    if type(data) is dict and "result" in data:
        result = check_result(json.dumps(data["result"]))
        return Presentation(result, "HISTORICAL_NOT_AUTHENTICATED", data)
    return Presentation(check_result(serialized), "HISTORICAL_NOT_AUTHENTICATED")


def project_for_llm(presentation):
    """Allowlist projection only. No prompt filter, dispatch, or instruction parser."""
    r = presentation.result
    return {"status": r["status"],
            "findings": [{"code": f["code"], "field": f["field"],
                          "evidence_ids": list(f["evidence_ids"])} for f in r["findings"]],
            "blockers": [{"code": b["code"], "field": b["field"],
                          "evidence_ids": list(b["evidence_ids"])} for b in r["blockers"]],
            "normalized": deepcopy(r["normalized"]),
            "limitations": list(r["limitations"])}


def qualify_deployment(*, embedded_python=True, case_affinity=True,
                       remote_api=False, local_service=False, persistence=False):
    """Configuration premise only, not a probe/certification of any platform."""
    if not embedded_python or not case_affinity or remote_api or local_service or persistence:
        raise HostContractError("Unsupported V0 deployment profile.")
    return {"profile": "EMBEDDED_PYTHON", "case_affinity": True,
            "restart": "NEW_DOMAIN", "serverless_continuity": False}


class HostHarness:
    """One trusted, sequential test host/domain. Never expose this to a model.

    Review/clock/evaluator substitutions are test seams, not production facilities.
    The review event is synthetic and does not authenticate an actual human.
    """
    def __init__(self, *, evaluator=evaluate, case_id_factory=None, clock=None):
        self.registry = LifecycleRegistry()
        self.issuers = [HostIntake(self.registry), HostIntake(self.registry)]
        self.authority_instance_id = str(uuid4())
        self.case_id_factory = case_id_factory or (lambda: str(uuid4()))
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        self.evaluator = evaluator
        self.cases = {}
        self.sequences = {}
        self.deliveries = {}
        self.review_records = {}
        self.evaluation_history = []
        self.active = True

    def key(self, case_id):
        return self.authority_instance_id, case_id

    def require_case(self, case_id):
        if not self.active or self.key(case_id) not in self.cases:
            raise HostContractError("Unknown case or closed authority.")
        return self.cases[self.key(case_id)]

    def create_case(self, *, item_identity, room_identity, revision="r1"):
        if not self.active:
            raise HostContractError("Closed authority.")
        case_id = self.case_id_factory()
        if self.key(case_id) in self.cases:
            raise HostContractError("Case identity cannot be reused.")
        self.cases[self.key(case_id)] = Case(Context(case_id, revision, item_identity, room_identity))
        return case_id

    def prepare_review(self, case_id, candidate, *, revision, confirmation_ref,
                       item_identity=None, room_identity=None):
        case = self.require_case(case_id)
        case.pending = True
        case.generation += 1
        case.review = None
        self.deliveries.pop(self.key(case_id), None)
        claim = claim_from_data(candidate)  # No trust promotion and no numeric rewrite.
        context = Context(case_id, revision, item_identity or case.context.item_identity,
                          room_identity or case.context.room_identity)
        review = Review(context, claim, hashlib.sha256(claim.payload.encode()).hexdigest(),
                        confirmation_ref)
        case.review = review
        return review

    def admit(self, review, *, claim=None, issuer_index=0):
        case = self.require_case(review.context.case_id)
        if not case.pending or case.review is not review:
            raise HostContractError("Review does not belong to this pending case.")
        selected_claim = review.claim if claim is None else claim
        if selected_claim is not review.claim:
            raise HostContractError("Admission requires the exact reviewed claim.")
        # On TrustError, this assignment is never reached: prior receipt survives,
        # pending edits remain blocked, no message/substring classification occurs.
        receipt = self.issuers[issuer_index].confirm(
            selected_claim, **asdict(review.context), confirmation_ref=review.confirmation_ref)
        case.admission = Admission(review, receipt)
        review_key = (*self.key(review.context.case_id), review.context.revision)
        self.review_records.setdefault(review_key, []).append(case.admission)
        case.context = review.context
        case.pending = False
        case.generation += 1
        return case.admission

    def cancel_edit(self, case_id):
        case = self.require_case(case_id)
        case.pending = False
        case.review = None
        case.generation += 1
        self.deliveries.pop(self.key(case_id), None)

    def assess(self, case_id, request):
        case = self.require_case(case_id)
        receipt = None if case.admission is None else case.admission.receipt
        return self.assess_with_receipt(case_id, request, receipt)

    def assess_with_receipt(self, case_id, request, receipt):
        case = self.require_case(case_id)
        self.deliveries.pop(self.key(case_id), None)
        if case.pending:
            raise HostContractError("Pending edit: no fallback to previous admission.")
        own_receipt = None if case.admission is None else case.admission.receipt
        if receipt is not own_receipt:
            raise HostContractError("Receipt does not belong to selected authority/case.")
        if validate(request, INPUT_SCHEMA):
            raise HostContractError("Malformed request.")
        context = case.context
        if (request["case_id"], request["revision"], request["item"]["identity"],
                request["room"]["identity"]) != tuple(asdict(context).values()):
            raise HostContractError("Request differs from host-selected scope.")
        # Unexpected exceptions propagate: no synthetic engine result or old cache.
        generation = case.generation
        result = check_result(json.dumps(self.evaluator(request, receipt)), context)
        if not self.active or case.pending or case.generation != generation:
            raise HostContractError("Case changed during evaluation.")
        if result["status"] != UNVERIFIED and result["execution_mode"] != "HOST_CONFIRMED_INPUT":
            raise ConsumerContractError("Demo/untrusted outcome cannot be a real host decision.")
        if case.admission is not None and result["admission"] is not None:
            review = case.admission.review
            if (result["admission"]["domain_id"] != self.issuers[0].domain_id
                    or result["admission"]["confirmation_ref"] != review.confirmation_ref):
                raise HostContractError("Admission differs from local issuer/review event.")
            if result["admission"]["evidence_digest"] != review.evidence_digest:
                raise HostContractError("Admission does not match reviewed payload.")
            combined = json.dumps([request, json.loads(review.claim.payload)], sort_keys=True,
                                  ensure_ascii=True, allow_nan=False, separators=(",", ":"))
            if result["input_digest"] != hashlib.sha256(combined.encode()).hexdigest():
                raise HostContractError("Decision does not match evaluated request/snapshot.")
        self.sequences[self.key(case_id)] = self.sequences.get(self.key(case_id), 0) + 1
        live = (result["admission"] is not None
                and result["execution_mode"] == "HOST_CONFIRMED_INPUT"
                and not any(b["code"] == "TRUST_REQUIRED" for b in result["blockers"]))
        envelope = {"authority_instance_id": self.authority_instance_id,
                    "case_id": case_id, "revision": context.revision,
                    "case_sequence": self.sequences[self.key(case_id)],
                    "evaluated_at": self.clock(), "expected_context": asdict(context),
                    "live_evaluation": live, "result": result}
        delivery = Delivery(json.dumps(envelope, ensure_ascii=True), json.dumps(request))
        self.deliveries[self.key(case_id)] = delivery
        self.evaluation_history.append((case.admission, delivery))
        return delivery

    def assess_key(self, operational_key, request):
        authority_id, case_id = operational_key
        if authority_id != self.authority_instance_id:
            raise HostContractError("Wrong affinity/authority for this case.")
        return self.assess(case_id, request)

    def present(self, delivery, *, before_handoff=None):
        envelope = loads(delivery.serialized_envelope)
        case_id = envelope["case_id"]
        case = self.require_case(case_id)
        if (case.pending or envelope["authority_instance_id"] != self.authority_instance_id
                or self.deliveries.get(self.key(case_id)) is not delivery):
            raise HostContractError("Delivery not owned/current in this host.")
        receipt = None if case.admission is None else case.admission.receipt
        generation = case.generation
        fresh = check_result(json.dumps(self.evaluator(loads(delivery.serialized_request), receipt)),
                             case.context)
        if case.generation != generation or fresh != envelope["result"]:
            raise HostContractError("Delivery changed since evaluation; reevaluation required.")
        if before_handoff is not None:
            before_handoff()  # Controlled fixture interleaving, never a model hook.
        if not self.active or case.pending or self.deliveries.get(self.key(case_id)) is not delivery:
            raise HostContractError("Case changed before handoff.")
        state = "LIVE_OBSERVED_DURING_HANDOFF" if envelope["live_evaluation"] else "NO_CURRENT_ADMISSION"
        return Presentation(fresh, state, envelope)

    def revoke(self, case_id, *, issuer_index=0):
        case = self.require_case(case_id)
        self.issuers[issuer_index].revoke(case_id)
        case.pending = False
        case.review = None
        case.generation += 1
        self.deliveries.pop(self.key(case_id), None)

    def close(self):
        # Closing this fixture does not claim global revocation of other objects.
        self.active = False
        self.deliveries.clear()

"""TEST ONLY: executable model for HOST_SERVICE_SINGLE_INVOCATION draft.

This is not a production adapter and does not qualify a deployment platform.
It uses only public Spatial Check APIs. Cross-invocation lifecycle/currentness is
synthetically modeled as an external authority so the proposed profile can be
attacked without weakening Host Contract V0.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from threading import RLock
from uuid import uuid4

from spatial_check import evaluate
from spatial_check.contracts import INPUT_SCHEMA, RESULT_SCHEMA, validate
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data


PROFILE = "HOST_SERVICE_SINGLE_INVOCATION"
AUTHORITY_SCOPE = "TRANSIENT_SNAPSHOT_ONLY"
REVIEWED_STATE = "REVIEWED"
REVIEW_ACTION = "use_values_for_spatial_check_v1"
CANONICAL_STATUSES = {
    "CONFLICT DETECTED",
    "NO CONFLICT DETECTED IN PROVIDED DATA",
    "UNVERIFIED",
}


class ProfileContractError(ValueError):
    """The draft host profile refuses an operation. Never an engine verdict."""


class SyntheticProcessCrash(RuntimeError):
    """Fault-injection seam representing loss of the one-shot host process."""


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExternalReview:
    review_event_id: str
    project_incarnation_id: str
    case_sequence: int
    review_generation: int
    review_state: str
    review_action: str
    evidence_payload: str
    evidence_digest: str
    effective_request_canonical: str
    case_id: str
    revision: str
    room_identity: str
    item_identity: str
    confirmation_ref: str
    review_binding_digest: str


@dataclass(frozen=True)
class ExternalSnapshot:
    principal_id: str
    project_id: str
    project_incarnation_id: str
    case_sequence: int
    currentness_version: int
    review: ExternalReview
    state_token: str


class SyntheticExternalAuthority:
    """Atomic, in-memory currentness authority used only by draft-profile tests."""

    def __init__(
        self,
        evidence,
        request,
        *,
        principal_id="user-1",
        project_id="project-1",
        review_event_id="review-1",
        project_incarnation_id=None,
    ):
        self._lock = RLock()
        self.principal_id = principal_id
        self.project_id = project_id
        self.project_incarnation_id = project_incarnation_id or str(uuid4())
        self.case_sequence = 1
        self.currentness_version = 1
        self.active = True
        self._reviews = {}
        self._current_review_event_id = None
        self._latest_review_event_id = None
        self._install_review(
            evidence,
            request,
            review_event_id=review_event_id,
            review_generation=1,
        )

    @staticmethod
    def _binding_data(
        *,
        project_id,
        project_incarnation_id,
        case_sequence,
        review_generation,
        review_event_id,
        review_state,
        review_action,
        evidence_payload,
        evidence_digest,
        effective_request_canonical,
        case_id,
        revision,
        room_identity,
        item_identity,
        confirmation_ref,
    ):
        return {
            "project_id": project_id,
            "project_incarnation_id": project_incarnation_id,
            "case_sequence": case_sequence,
            "review_generation": review_generation,
            "review_event_id": review_event_id,
            "review_state": review_state,
            "review_action": review_action,
            "evidence_payload_sha256": _sha256(evidence_payload),
            "evidence_digest": evidence_digest,
            "effective_request_sha256": _sha256(effective_request_canonical),
            "case_id": case_id,
            "revision": revision,
            "room_identity": room_identity,
            "item_identity": item_identity,
            "confirmation_ref": confirmation_ref,
        }

    def _build_review(self, evidence, request, *, review_event_id, review_generation):
        claim = claim_from_data(deepcopy(evidence))
        evidence_payload = claim.payload
        evidence_digest = _sha256(evidence_payload)
        effective_request_canonical = _canonical(request)
        confirmation_ref = "external-review:" + review_event_id
        fields = dict(
            project_id=self.project_id,
            project_incarnation_id=self.project_incarnation_id,
            case_sequence=self.case_sequence,
            review_generation=review_generation,
            review_event_id=review_event_id,
            review_state=REVIEWED_STATE,
            review_action=REVIEW_ACTION,
            evidence_payload=evidence_payload,
            evidence_digest=evidence_digest,
            effective_request_canonical=effective_request_canonical,
            case_id=evidence["case_id"],
            revision=evidence["revision"],
            room_identity=evidence["room_identity"],
            item_identity=evidence["item_identity"],
            confirmation_ref=confirmation_ref,
        )
        binding = _sha256(_canonical(self._binding_data(**fields)))
        return ExternalReview(review_binding_digest=binding, **{
            key: fields[key] for key in (
                "review_event_id",
                "project_incarnation_id",
                "case_sequence",
                "review_generation",
                "review_state",
                "review_action",
                "evidence_payload",
                "evidence_digest",
                "effective_request_canonical",
                "case_id",
                "revision",
                "room_identity",
                "item_identity",
                "confirmation_ref",
            )
        })

    def _install_review(self, evidence, request, *, review_event_id, review_generation):
        review = self._build_review(
            evidence,
            request,
            review_event_id=review_event_id,
            review_generation=review_generation,
        )
        self._reviews[review_event_id] = review
        self._current_review_event_id = review_event_id
        self._latest_review_event_id = review_event_id
        return review

    def _verify_review_binding(self, review):
        binding_data = self._binding_data(
            project_id=self.project_id,
            project_incarnation_id=review.project_incarnation_id,
            case_sequence=review.case_sequence,
            review_generation=review.review_generation,
            review_event_id=review.review_event_id,
            review_state=review.review_state,
            review_action=review.review_action,
            evidence_payload=review.evidence_payload,
            evidence_digest=review.evidence_digest,
            effective_request_canonical=review.effective_request_canonical,
            case_id=review.case_id,
            revision=review.revision,
            room_identity=review.room_identity,
            item_identity=review.item_identity,
            confirmation_ref=review.confirmation_ref,
        )
        if _sha256(_canonical(binding_data)) != review.review_binding_digest:
            raise ProfileContractError("External review binding mismatch.")
        if _sha256(review.evidence_payload) != review.evidence_digest:
            raise ProfileContractError("Reviewed evidence digest mismatch.")

    def _state_token(self, review):
        token_data = {
            "principal_id": self.principal_id,
            "project_id": self.project_id,
            "project_incarnation_id": self.project_incarnation_id,
            "case_sequence": self.case_sequence,
            "currentness_version": self.currentness_version,
            "active": self.active,
            "current_review_event_id": self._current_review_event_id,
            "review_binding_digest": review.review_binding_digest,
        }
        return _sha256(_canonical(token_data))

    def preflight(self, *, principal_id, review_event_id, evidence_digest):
        with self._lock:
            if principal_id != self.principal_id:
                raise ProfileContractError("Caller is not authorized for this project.")
            review = self._reviews.get(review_event_id)
            if review is None:
                raise ProfileContractError("Review does not exist.")
            self._verify_review_binding(review)
            if not self.active:
                raise ProfileContractError("Project is not active.")
            if self._current_review_event_id != review_event_id:
                raise ProfileContractError("Review is historical, not current.")
            if review.review_state != REVIEWED_STATE or review.review_action != REVIEW_ACTION:
                raise ProfileContractError("Review state/action is not admissible.")
            if review.project_incarnation_id != self.project_incarnation_id:
                raise ProfileContractError("Project incarnation changed.")
            if review.case_sequence != self.case_sequence:
                raise ProfileContractError("Case sequence changed.")
            if evidence_digest != review.evidence_digest:
                raise ProfileContractError("Evidence digest selector mismatch.")
            return ExternalSnapshot(
                principal_id=self.principal_id,
                project_id=self.project_id,
                project_incarnation_id=self.project_incarnation_id,
                case_sequence=self.case_sequence,
                currentness_version=self.currentness_version,
                review=deepcopy(review),
                state_token=self._state_token(review),
            )

    def postflight(self, snapshot):
        current = self.preflight(
            principal_id=snapshot.principal_id,
            review_event_id=snapshot.review.review_event_id,
            evidence_digest=snapshot.review.evidence_digest,
        )
        if current.state_token != snapshot.state_token:
            raise ProfileContractError("External state changed during evaluation.")
        return current

    def point_of_use_current(self, snapshot):
        try:
            return self.postflight(snapshot).state_token == snapshot.state_token
        except ProfileContractError:
            return False

    def transition_review(
        self,
        *,
        evidence=None,
        request=None,
        revision=None,
        review_event_id=None,
    ):
        with self._lock:
            if self._latest_review_event_id is None:
                raise ProfileContractError("No reviewed state exists.")
            current = self._reviews[self._latest_review_event_id]
            next_evidence = json.loads(current.evidence_payload) if evidence is None else deepcopy(evidence)
            next_request = (
                json.loads(current.effective_request_canonical)
                if request is None
                else deepcopy(request)
            )
            self.case_sequence += 1
            self.currentness_version += 1
            next_revision = revision or ("r" + str(self.case_sequence))
            next_evidence["revision"] = next_revision
            next_request["revision"] = next_revision
            next_id = review_event_id or ("review-" + str(self.case_sequence))
            return self._install_review(
                next_evidence,
                next_request,
                review_event_id=next_id,
                review_generation=current.review_generation + 1,
            )

    def revoke_current_review(self):
        with self._lock:
            if self._current_review_event_id is None:
                return
            self.currentness_version += 1
            self._current_review_event_id = None

    def reactivate_historical_review(self, review_event_id):
        raise ProfileContractError(
            "Silent revival is forbidden; create a new authority transition/review."
        )

    def delete_and_recreate(self, evidence, request, *, review_event_id="review-recreated"):
        with self._lock:
            self.project_incarnation_id = str(uuid4())
            self.case_sequence = 1
            self.currentness_version += 1
            self.active = True
            self._current_review_event_id = None
            return self._install_review(
                deepcopy(evidence),
                deepcopy(request),
                review_event_id=review_event_id,
                review_generation=self.currentness_version,
            )

    def deactivate_project(self):
        with self._lock:
            self.active = False
            self.currentness_version += 1

    def unsafe_corrupt_current_review_for_test(self, **changes):
        """Fault injection: mutate immutable review bytes without rebinding them."""
        with self._lock:
            if self._current_review_event_id is None:
                raise ProfileContractError("No current review to corrupt.")
            review = self._reviews[self._current_review_event_id]
            self._reviews[self._current_review_event_id] = replace(review, **changes)

    @property
    def current_review(self):
        with self._lock:
            if self._current_review_event_id is None:
                return None
            return deepcopy(self._reviews[self._current_review_event_id])


class SingleInvocationHost:
    """One-shot host for the draft profile. New call = new Spatial Check domain."""

    def __init__(self, authority, *, evaluator=evaluate, clock=None):
        self.authority = authority
        self.evaluator = evaluator
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat())

    @staticmethod
    def _check_result(result, snapshot):
        if validate(result, RESULT_SCHEMA):
            raise ProfileContractError("Malformed Spatial Check result.")
        if result["status"] not in CANONICAL_STATUSES:
            raise ProfileContractError("Non-canonical Spatial Check status.")
        admission = result.get("admission")
        if result["status"] != "UNVERIFIED" and result["execution_mode"] != "HOST_CONFIRMED_INPUT":
            raise ProfileContractError("Resolved result is not host-confirmed.")
        if admission is None:
            if result["status"] != "UNVERIFIED":
                raise ProfileContractError("Resolved result lacks admission.")
            return
        expected = snapshot.review
        for field, value in (
            ("case_id", expected.case_id),
            ("revision", expected.revision),
            ("room_identity", expected.room_identity),
            ("item_identity", expected.item_identity),
            ("confirmation_ref", expected.confirmation_ref),
            ("evidence_digest", expected.evidence_digest),
        ):
            if admission[field] != value:
                raise ProfileContractError("Admission differs from external review.")
        for field in ("case_id", "revision", "item_identity"):
            if result[field] is not None and result[field] != admission[field]:
                raise ProfileContractError("Result scope differs from admission.")

    def evaluate_review(
        self,
        *,
        principal_id,
        review_event_id,
        evidence_digest,
        after_confirm=None,
        after_evaluate=None,
    ):
        preflight = self.authority.preflight(
            principal_id=principal_id,
            review_event_id=review_event_id,
            evidence_digest=evidence_digest,
        )
        reviewed = preflight.review

        evidence = json.loads(reviewed.evidence_payload)
        claim = claim_from_data(evidence)
        if claim.payload != reviewed.evidence_payload:
            raise ProfileContractError("Canonical claim differs from reviewed payload.")
        if _sha256(claim.payload) != reviewed.evidence_digest:
            raise ProfileContractError("Canonical claim digest differs from reviewed digest.")

        request = json.loads(reviewed.effective_request_canonical)
        if validate(request, INPUT_SCHEMA):
            raise ProfileContractError("Reviewed effective request is malformed.")
        if (
            request["case_id"] != reviewed.case_id
            or request["revision"] != reviewed.revision
            or request["room"]["identity"] != reviewed.room_identity
            or request["item"]["identity"] != reviewed.item_identity
        ):
            raise ProfileContractError(
                "Effective request scope differs from reviewed authority."
            )

        registry = LifecycleRegistry()
        intake = HostIntake(registry)
        receipt = intake.confirm(
            claim,
            case_id=reviewed.case_id,
            revision=reviewed.revision,
            room_identity=reviewed.room_identity,
            item_identity=reviewed.item_identity,
            confirmation_ref=reviewed.confirmation_ref,
        )

        if after_confirm is not None:
            after_confirm()

        result = self.evaluator(request, receipt)

        if after_evaluate is not None:
            after_evaluate()

        self._check_result(result, preflight)
        self.authority.postflight(preflight)

        return {
            "profile": PROFILE,
            "evaluation_id": str(uuid4()),
            "engine_version": result["engine_version"],
            "generated_at": self.clock(),
            "state_token": preflight.state_token,
            "project_id": preflight.project_id,
            "project_incarnation_id": preflight.project_incarnation_id,
            "case_sequence": preflight.case_sequence,
            "review_event_id": reviewed.review_event_id,
            "evidence_digest": reviewed.evidence_digest,
            "case_id": reviewed.case_id,
            "revision": reviewed.revision,
            "room_identity": reviewed.room_identity,
            "item_identity": reviewed.item_identity,
            "confirmation_ref": reviewed.confirmation_ref,
            "result": deepcopy(result),
            "current_as_of_postflight": True,
            "authority_scope": AUTHORITY_SCOPE,
        }

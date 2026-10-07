"""TEST ONLY: Morable PostgreSQL Snapshot V2 conformance fixture.

The payloads below were captured from a real Morable staging lifecycle on
2026-10-07. They are historical test evidence, not live authority and not a
production Supabase adapter.

This module adapts the recorded external-authority contract to the generic
HOST_SERVICE_SINGLE_INVOCATION draft harness without importing Supabase or
weakening Host Contract V0.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from uuid import UUID

from spatial_check.contracts import INPUT_SCHEMA, validate
from spatial_check.trust import claim_from_data
from tests.host_service_single_invocation_profile_draft import (
    AUTHORITY_SCOPE,
    REVIEW_ACTION,
    REVIEWED_STATE,
    ExternalReview,
    ExternalSnapshot,
    ProfileContractError,
)


SNAPSHOT_CONTRACT = "spatial_check_external_authority_snapshot_v2"
STAGING_PRINCIPAL_ID = "97595dcb-3cb4-4f36-adb9-99f1aaeea569"
STAGING_PROJECT_ID = "spatial-profile-v04-conformance-20261007"
STAGING_PROJECT_INCARNATION_ID = "ba2290e6-0e96-4f14-bc13-3f943ba25e8a"
STAGING_REVIEW_EVENT_ID = (
    "mreview-v2-e8e189cd3468beac782bc40e19366077025418f424aefa93"
)
STAGING_EVIDENCE_DIGEST = (
    "86db9f16f80844a0c2a2c6ebfeee46aa0a1ebd4578889fe5412f83c1f8f13a26"
)
STAGING_REVIEW_SUBJECT_KEY = (
    "a28c041478df3f394983e7c76536a611821bde83e743f17024786b4ee37fa42d"
)
STAGING_REVIEW_BINDING_DIGEST = (
    "06e910949351935b4c5452bccebfbe5ba8f53c9f08a8ae1e11d44bd770987de7"
)
STAGING_STATE_TOKEN = (
    "254cdc7626d1ccff2a0f05e61dea0f3ef3c23547f939af2e1a07ddd26a9f9047"
)
STAGING_REVOCATION_EVENT_ID = "807c40d8-7ab1-4010-9217-168a258fb832"

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_EVENT = re.compile(r"^mreview-v2-[0-9a-f]{48}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")


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


def _positive_int(value):
    return type(value) is int and value > 0


def _utc_z(value):
    if type(value) is not str or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _uuid(value):
    if type(value) is not str:
        return False
    try:
        UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


def _safe_id(value):
    return (
        type(value) is str
        and 1 <= len(value) <= 256
        and value == value.strip()
        and _SAFE_ID.fullmatch(value) is not None
    )


def staging_current_snapshot_v2():
    """Exact successful Snapshot V2 payload captured from Morable staging."""
    confirmation_ref = "morable-review:" + STAGING_REVIEW_EVENT_ID
    claim_payload = (
        '{"case_id":"case-1","declarations":{"explicit_exclusions":[],"openings":[],'
        '"required_clearances":[]},"facts":[{"field":"room.width","id":"room-width",'
        '"meaning":"usable_width","source":{"id":"room-width-source","kind":"user_measurement",'
        '"locator":"morable:project:spatial-profile-v04-conformance-20261007:room.width"},'
        '"status":"PROVIDED","unit":"cm","value":"400"},{"field":"room.depth",'
        '"id":"room-depth","meaning":"usable_depth","source":{"id":"room-depth-source",'
        '"kind":"user_measurement","locator":"morable:project:spatial-profile-v04-conformance-'
        '20261007:room.depth"},"status":"PROVIDED","unit":"cm","value":"500"},'
        '{"field":"item.width","id":"item-width","meaning":"assembled_width","source":'
        '{"id":"item-width-source","kind":"user_confirmation","locator":"morable:project:'
        'spatial-profile-v04-conformance-20261007:budget-item:bed-1:product:mercado_livre:'
        'MLB-123:width"},"status":"PROVIDED","unit":"cm","value":"138"},'
        '{"field":"item.depth","id":"item-depth","meaning":"assembled_depth","source":'
        '{"id":"item-depth-source","kind":"user_measurement","locator":"morable:project:'
        'spatial-profile-v04-conformance-20261007:budget-item:bed-1:product:mercado_livre:'
        'MLB-123:depth"},"status":"PROVIDED","unit":"cm","value":"188"},'
        '{"field":"item.x","id":"item-x","meaning":"position_x","source":{"id":"item-x-source",'
        '"kind":"user_confirmation","locator":"' + confirmation_ref +
        ':item.x:origin:user_floor_plan_editor"},"status":"PROVIDED","unit":"cm","value":"35"},'
        '{"field":"item.y","id":"item-y","meaning":"position_y","source":{"id":"item-y-source",'
        '"kind":"user_confirmation","locator":"' + confirmation_ref +
        ':item.y:origin:user_floor_plan_editor"},"status":"PROVIDED","unit":"cm","value":"45"},'
        '{"field":"item.rotation","id":"item-rotation","meaning":"rotation","source":'
        '{"id":"item-rotation-source","kind":"user_confirmation","locator":"' + confirmation_ref +
        ':item.rotation:origin:user_floor_plan_editor"},"status":"PROVIDED","unit":"deg",'
        '"value":"90"}],"item_identity":"item-1","revision":"r1","room_identity":"room-1",'
        '"schema_version":"0.1"}'
    )
    effective_request = (
        '{"case_id":"case-1","explicit_exclusions":[],"item":{"depth":"item-depth",'
        '"identity":"item-1","position":{"x":"item-x","y":"item-y"},'
        '"rotation":"item-rotation","width":"item-width"},"openings":[],'
        '"required_clearances":[],"revision":"r1","room":{"depth":"room-depth",'
        '"identity":"room-1","width":"room-width"},"schema_version":"0.1"}'
    )
    review_context = (
        '{"budgetItemId":"bed-1","projectId":"'
        + STAGING_PROJECT_ID
        + '"}'
    )
    return {
        "ok": True,
        "contract_version": SNAPSHOT_CONTRACT,
        "current": True,
        "state_token": STAGING_STATE_TOKEN,
        "project_id": STAGING_PROJECT_ID,
        "project_incarnation_id": STAGING_PROJECT_INCARNATION_ID,
        "case_sequence": 1,
        "review_subject_key": STAGING_REVIEW_SUBJECT_KEY,
        "review_generation": 1,
        "authority_version": 3,
        "head_status": REVIEWED_STATE,
        "current_review_event_id": STAGING_REVIEW_EVENT_ID,
        "review_event_id": STAGING_REVIEW_EVENT_ID,
        "reviewed_authority_version": 3,
        "review_binding_digest": STAGING_REVIEW_BINDING_DIGEST,
        "revocation_state": "NONE",
        "revocation_event_id": None,
        "evidence_digest": STAGING_EVIDENCE_DIGEST,
        "confirmation_ref": confirmation_ref,
        "budget_item_id": "bed-1",
        "case_id": "case-1",
        "revision": "r1",
        "room_identity": "room-1",
        "item_identity": "item-1",
        "claim_payload": claim_payload,
        "effective_request_canonical": effective_request,
        "review_context_canonical": review_context,
        "reviewed_at": "2026-10-07T09:41:00.000Z",
        "authority_scope": AUTHORITY_SCOPE,
    }


def staging_revoked_snapshot_v2():
    """Exact fail-closed Snapshot V2 payload captured after explicit revocation."""
    return {
        "ok": False,
        "code": "REVIEW_REVOKED",
        "revoked_at": "2026-10-07T09:42:00.000Z",
        "reason_code": "USER_EXPLICIT_REVOKE",
        "review_event_id": STAGING_REVIEW_EVENT_ID,
        "review_generation": 1,
        "review_subject_key": STAGING_REVIEW_SUBJECT_KEY,
        "revocation_event_id": STAGING_REVOCATION_EVENT_ID,
        "revoked_authority_version": 4,
        "reviewed_authority_version": 3,
    }


def parse_morable_snapshot_v2(
    payload,
    *,
    principal_id,
    expected_review_event_id,
    expected_evidence_digest,
):
    """Parse one trusted-reader Snapshot V2 response into the draft profile model.

    A dict by itself is not authority. Production use would call this only on bytes
    obtained through a trusted/authenticated external-authority reader.
    """
    if type(payload) is not dict:
        raise ProfileContractError("Malformed external authority response.")

    if payload.get("ok") is False:
        if payload.get("code") != "REVIEW_REVOKED":
            raise ProfileContractError("External authority refused currentness.")
        forbidden = {
            "claim_payload",
            "effective_request_canonical",
            "review_context_canonical",
        }
        if forbidden.intersection(payload):
            raise ProfileContractError("Revoked response leaked evaluation bytes.")
        if payload.get("review_event_id") != expected_review_event_id:
            raise ProfileContractError("Revocation refers to another review.")
        reviewed_version = payload.get("reviewed_authority_version")
        revoked_version = payload.get("revoked_authority_version")
        if (
            not _positive_int(reviewed_version)
            or not _positive_int(revoked_version)
            or revoked_version != reviewed_version + 1
            or not _uuid(payload.get("revocation_event_id"))
            or not _utc_z(payload.get("revoked_at"))
        ):
            raise ProfileContractError("Invalid revocation authority.")
        raise ProfileContractError("External review is revoked.")

    if payload.get("ok") is not True:
        raise ProfileContractError("Malformed external authority response.")

    required_hex = (
        payload.get("state_token"),
        payload.get("review_subject_key"),
        payload.get("review_binding_digest"),
        payload.get("evidence_digest"),
    )
    if any(type(value) is not str or _HEX64.fullmatch(value) is None for value in required_hex):
        raise ProfileContractError("Invalid authority digest/token.")

    review_event_id = payload.get("review_event_id")
    authority_version = payload.get("authority_version")
    reviewed_authority_version = payload.get("reviewed_authority_version")
    if (
        payload.get("contract_version") != SNAPSHOT_CONTRACT
        or payload.get("current") is not True
        or payload.get("head_status") != REVIEWED_STATE
        or payload.get("current_review_event_id") != review_event_id
        or review_event_id != expected_review_event_id
        or _EVENT.fullmatch(review_event_id or "") is None
        or not _positive_int(payload.get("case_sequence"))
        or not _positive_int(payload.get("review_generation"))
        or not _positive_int(authority_version)
        or not _positive_int(reviewed_authority_version)
        or authority_version != reviewed_authority_version
        or payload.get("revocation_state") != "NONE"
        or payload.get("revocation_event_id") is not None
        or payload.get("authority_scope") != AUTHORITY_SCOPE
        or payload.get("evidence_digest") != expected_evidence_digest
    ):
        raise ProfileContractError("External authority is not current REVIEWED V2.")

    project_id = payload.get("project_id")
    project_incarnation_id = payload.get("project_incarnation_id")
    if (
        not _safe_id(project_id)
        or not _uuid(project_incarnation_id)
        or not _safe_id(payload.get("budget_item_id"))
        or not _safe_id(payload.get("case_id"))
        or not _safe_id(payload.get("revision"))
        or not _safe_id(payload.get("room_identity"))
        or not _safe_id(payload.get("item_identity"))
    ):
        raise ProfileContractError("Invalid external scope identity.")

    confirmation_ref = payload.get("confirmation_ref")
    if confirmation_ref != "morable-review:" + review_event_id:
        raise ProfileContractError("Confirmation reference is not event-bound.")

    claim_payload = payload.get("claim_payload")
    effective_request_canonical = payload.get("effective_request_canonical")
    review_context_canonical = payload.get("review_context_canonical")
    if not all(
        type(value) is str and value
        for value in (
            claim_payload,
            effective_request_canonical,
            review_context_canonical,
        )
    ):
        raise ProfileContractError("Missing reviewed evaluation bytes.")

    try:
        evidence = json.loads(claim_payload)
        request = json.loads(effective_request_canonical)
        review_context = json.loads(review_context_canonical)
    except (ValueError, TypeError):
        raise ProfileContractError("Invalid reviewed JSON.") from None

    if (
        _canonical(evidence) != claim_payload
        or _canonical(request) != effective_request_canonical
        or _canonical(review_context) != review_context_canonical
    ):
        raise ProfileContractError("Reviewed bytes are not canonical.")

    claim = claim_from_data(evidence)
    if (
        claim.payload != claim_payload
        or _sha256(claim_payload) != payload["evidence_digest"]
    ):
        raise ProfileContractError("Reviewed evidence digest/canonical payload mismatch.")

    if validate(request, INPUT_SCHEMA):
        raise ProfileContractError("Reviewed effective request is malformed.")

    if (
        evidence.get("case_id") != payload["case_id"]
        or evidence.get("revision") != payload["revision"]
        or evidence.get("room_identity") != payload["room_identity"]
        or evidence.get("item_identity") != payload["item_identity"]
        or request.get("case_id") != payload["case_id"]
        or request.get("revision") != payload["revision"]
        or request.get("room", {}).get("identity") != payload["room_identity"]
        or request.get("item", {}).get("identity") != payload["item_identity"]
        or review_context.get("projectId") != project_id
        or review_context.get("budgetItemId") != payload["budget_item_id"]
    ):
        raise ProfileContractError("Reviewed bytes differ from external scope.")

    pose_fields = {"item.x", "item.y", "item.rotation"}
    pose = {
        fact.get("field"): fact
        for fact in evidence.get("facts", [])
        if type(fact) is dict and fact.get("field") in pose_fields
    }
    if set(pose) != pose_fields:
        raise ProfileContractError("Pose review binding is incomplete.")
    for fact in pose.values():
        locator = fact.get("source", {}).get("locator")
        if type(locator) is not str or not locator.startswith(confirmation_ref + ":"):
            raise ProfileContractError("Pose source is bound to another review event.")

    if not _utc_z(payload.get("reviewed_at")):
        raise ProfileContractError("Invalid reviewed timestamp.")

    review = ExternalReview(
        review_event_id=review_event_id,
        project_incarnation_id=project_incarnation_id,
        case_sequence=payload["case_sequence"],
        review_generation=payload["review_generation"],
        review_state=REVIEWED_STATE,
        review_action=REVIEW_ACTION,
        evidence_payload=claim_payload,
        evidence_digest=payload["evidence_digest"],
        effective_request_canonical=effective_request_canonical,
        case_id=payload["case_id"],
        revision=payload["revision"],
        room_identity=payload["room_identity"],
        item_identity=payload["item_identity"],
        confirmation_ref=confirmation_ref,
        review_binding_digest=payload["review_binding_digest"],
    )
    return ExternalSnapshot(
        principal_id=principal_id,
        project_id=project_id,
        project_incarnation_id=project_incarnation_id,
        case_sequence=payload["case_sequence"],
        currentness_version=authority_version,
        review=review,
        state_token=payload["state_token"],
    )


class RecordedPostgresSnapshotV2Authority:
    """Trusted-reader seam backed by recorded current/postflight responses."""

    def __init__(
        self,
        *,
        preflight_payload=None,
        postflight_payload=None,
        principal_id=STAGING_PRINCIPAL_ID,
    ):
        self.principal_id = principal_id
        self._preflight_payload = deepcopy(
            staging_current_snapshot_v2()
            if preflight_payload is None
            else preflight_payload
        )
        self._postflight_payload = deepcopy(
            self._preflight_payload
            if postflight_payload is None
            else postflight_payload
        )

    def preflight(self, *, principal_id, review_event_id, evidence_digest):
        if principal_id != self.principal_id:
            raise ProfileContractError("Caller is not authorized for this snapshot.")
        return parse_morable_snapshot_v2(
            deepcopy(self._preflight_payload),
            principal_id=principal_id,
            expected_review_event_id=review_event_id,
            expected_evidence_digest=evidence_digest,
        )

    def postflight(self, snapshot):
        current = parse_morable_snapshot_v2(
            deepcopy(self._postflight_payload),
            principal_id=snapshot.principal_id,
            expected_review_event_id=snapshot.review.review_event_id,
            expected_evidence_digest=snapshot.review.evidence_digest,
        )
        if current.state_token != snapshot.state_token:
            raise ProfileContractError("External state changed during evaluation.")
        return current

    def point_of_use_current(self, snapshot):
        try:
            return self.postflight(snapshot).state_token == snapshot.state_token
        except ProfileContractError:
            return False

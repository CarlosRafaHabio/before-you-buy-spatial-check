"""TEST ONLY: external authority epoch for restore/PITR ABA resistance.

The epoch is intentionally outside the database restore domain. It is not a
Spatial Check trust capability, secret, receipt, signature, or authentication
mechanism. Its job is narrower: prevent a whole-database rollback/clone from
silently recreating an old HOST_SERVICE_SINGLE_INVOCATION state token.

Production storage/orchestration is deliberately unspecified here.
"""
from dataclasses import dataclass
import hashlib
import json
from threading import RLock
from uuid import UUID

from tests.host_service_single_invocation_profile_draft import (
    ExternalSnapshot,
    ProfileContractError,
)


EPOCH_TOKEN_DOMAIN = "spatial_check_host_service_authority_epoch_v1"
SNAPSHOT_CONTRACT = "spatial_check_external_authority_snapshot_v2"


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


def _valid_epoch(value):
    if type(value) is not str:
        return False
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        return False
    return str(parsed) == value.lower()


def bind_authority_epoch(*, authority_epoch, external_state_token):
    """Create the profile-level token from an external epoch + DB state token."""
    if not _valid_epoch(authority_epoch):
        raise ProfileContractError("Authority epoch is invalid.")
    if (
        type(external_state_token) is not str
        or len(external_state_token) != 64
        or any(ch not in "0123456789abcdef" for ch in external_state_token)
    ):
        raise ProfileContractError("External state token is invalid.")

    return _sha256(
        _canonical(
            {
                "domain": EPOCH_TOKEN_DOMAIN,
                "authority_epoch": authority_epoch,
                "external_snapshot_contract": SNAPSHOT_CONTRACT,
                "external_state_token": external_state_token,
            }
        )
    )


class AuthorityEpochSource:
    """Integrity-controlled external epoch seam used only by qualification tests."""

    def __init__(self, authority_epoch):
        if not _valid_epoch(authority_epoch):
            raise ProfileContractError("Authority epoch is invalid.")
        self._lock = RLock()
        self._authority_epoch = authority_epoch.lower()

    def read(self):
        with self._lock:
            return self._authority_epoch

    def rotate(self, next_epoch):
        """Explicit authority-lineage transition.

        Rotation to the same value is refused because a restore/clone procedure
        that claims to rotate but preserves the old epoch would leave ABA open.
        """
        if not _valid_epoch(next_epoch):
            raise ProfileContractError("Authority epoch is invalid.")
        next_epoch = next_epoch.lower()
        with self._lock:
            if next_epoch == self._authority_epoch:
                raise ProfileContractError("Authority epoch rotation must change value.")
            previous = self._authority_epoch
            self._authority_epoch = next_epoch
            return previous, next_epoch


@dataclass(frozen=True)
class EpochBoundSnapshot:
    """ExternalSnapshot plus non-database lineage used for profile currentness."""

    principal_id: str
    project_id: str
    project_incarnation_id: str
    case_sequence: int
    currentness_version: int
    review: object
    state_token: str

    authority_epoch: str
    external_state_token: str


def _bind_snapshot(snapshot, authority_epoch):
    return EpochBoundSnapshot(
        principal_id=snapshot.principal_id,
        project_id=snapshot.project_id,
        project_incarnation_id=snapshot.project_incarnation_id,
        case_sequence=snapshot.case_sequence,
        currentness_version=snapshot.currentness_version,
        review=snapshot.review,
        state_token=bind_authority_epoch(
            authority_epoch=authority_epoch,
            external_state_token=snapshot.state_token,
        ),
        authority_epoch=authority_epoch,
        external_state_token=snapshot.state_token,
    )


def _raw_snapshot(snapshot):
    """Recover only the historical external selector/token for postflight.

    This reconstructs no TrustedEvidence and no LifecycleRegistry. It is merely
    the external-authority observation needed by the wrapped reader's postflight.
    """
    return ExternalSnapshot(
        principal_id=snapshot.principal_id,
        project_id=snapshot.project_id,
        project_incarnation_id=snapshot.project_incarnation_id,
        case_sequence=snapshot.case_sequence,
        currentness_version=snapshot.currentness_version,
        review=snapshot.review,
        state_token=snapshot.external_state_token,
    )


class EpochBoundExternalAuthority:
    """Compose a trusted external Snapshot V2 reader with an external epoch."""

    def __init__(self, authority, epoch_source):
        self.authority = authority
        self.epoch_source = epoch_source

    def preflight(self, *, principal_id, review_event_id, evidence_digest):
        external = self.authority.preflight(
            principal_id=principal_id,
            review_event_id=review_event_id,
            evidence_digest=evidence_digest,
        )
        return _bind_snapshot(external, self.epoch_source.read())

    def postflight(self, snapshot):
        # The wrapped authority performs its own selector/currentness validation.
        external = self.authority.postflight(_raw_snapshot(snapshot))
        current = _bind_snapshot(external, self.epoch_source.read())
        if current.state_token != snapshot.state_token:
            raise ProfileContractError(
                "External database state or authority epoch changed during evaluation."
            )
        return current

    def point_of_use_current(self, snapshot):
        try:
            return self.postflight(snapshot).state_token == snapshot.state_token
        except ProfileContractError:
            return False


def require_restore_epoch_rotation(*, previous_epoch, resumed_epoch):
    """Operational qualification guard for restore/PITR/clone procedures.

    This function cannot detect a restore event by itself. Restore orchestration
    must call it (or enforce an equivalent invariant) before traffic resumes.
    """
    if not _valid_epoch(previous_epoch) or not _valid_epoch(resumed_epoch):
        raise ProfileContractError("Authority epoch is invalid.")
    if previous_epoch.lower() == resumed_epoch.lower():
        raise ProfileContractError(
            "Restore/clone authority epoch was not rotated before resuming traffic."
        )
    return True

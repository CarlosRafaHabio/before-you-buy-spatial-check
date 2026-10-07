"""Adversarial tests for the external authority epoch restore/PITR gate."""
import json
import unittest

from tests.host_harness_contract_v0 import HostContractError, qualify_deployment
from tests.host_service_authority_epoch_draft import (
    AuthorityEpochSource,
    EpochBoundExternalAuthority,
    bind_authority_epoch,
    require_restore_epoch_rotation,
)
from tests.host_service_single_invocation_profile_draft import (
    ProfileContractError,
    SingleInvocationHost,
)
from tests.morable_postgres_snapshot_v2_contract import (
    STAGING_EVIDENCE_DIGEST,
    STAGING_PRINCIPAL_ID,
    STAGING_REVIEW_EVENT_ID,
    STAGING_STATE_TOKEN,
    RecordedPostgresSnapshotV2Authority,
    staging_current_snapshot_v2,
)


EPOCH_1 = "11111111-1111-4111-8111-111111111111"
EPOCH_2 = "22222222-2222-4222-8222-222222222222"
EPOCH_CLONE = "33333333-3333-4333-8333-333333333333"
DB_TOKEN_B = "b" * 64


class AuthorityEpochDraftTests(unittest.TestCase):
    def authority(self, *, epoch=EPOCH_1, external=None):
        source = AuthorityEpochSource(epoch)
        wrapped = EpochBoundExternalAuthority(
            external or RecordedPostgresSnapshotV2Authority(),
            source,
        )
        return source, wrapped

    def evaluate_current(self, wrapped):
        return SingleInvocationHost(wrapped).evaluate_review(
            principal_id=STAGING_PRINCIPAL_ID,
            review_event_id=STAGING_REVIEW_EVENT_ID,
            evidence_digest=STAGING_EVIDENCE_DIGEST,
        )

    def test_EP01_same_db_snapshot_same_epoch_is_stable(self):
        one = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )
        two = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )
        self.assertEqual(one, two)
        self.assertEqual(len(one), 64)

    def test_EP02_whole_db_restore_without_epoch_rotation_recreates_old_token(self):
        """This is the attack being closed, not an accepted production state."""
        before_restore = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )
        during_normal_history = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=DB_TOKEN_B,
        )
        restored_without_rotation = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )

        self.assertNotEqual(before_restore, during_normal_history)
        self.assertEqual(before_restore, restored_without_rotation)
        with self.assertRaises(ProfileContractError):
            require_restore_epoch_rotation(
                previous_epoch=EPOCH_1,
                resumed_epoch=EPOCH_1,
            )

    def test_EP03_restore_plus_rotated_epoch_cannot_recreate_old_token(self):
        old = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )
        restored = bind_authority_epoch(
            authority_epoch=EPOCH_2,
            external_state_token=STAGING_STATE_TOKEN,
        )

        self.assertNotEqual(old, restored)
        self.assertTrue(
            require_restore_epoch_rotation(
                previous_epoch=EPOCH_1,
                resumed_epoch=EPOCH_2,
            )
        )

    def test_EP04_clone_with_identical_database_requires_distinct_environment_epoch(self):
        source_token = bind_authority_epoch(
            authority_epoch=EPOCH_1,
            external_state_token=STAGING_STATE_TOKEN,
        )
        clone_token = bind_authority_epoch(
            authority_epoch=EPOCH_CLONE,
            external_state_token=STAGING_STATE_TOKEN,
        )
        self.assertNotEqual(source_token, clone_token)

    def test_EP05_epoch_rotation_during_evaluation_blocks_current_handoff(self):
        source, wrapped = self.authority()

        def rotate_after_evaluate():
            source.rotate(EPOCH_2)

        with self.assertRaises(ProfileContractError):
            SingleInvocationHost(wrapped).evaluate_review(
                principal_id=STAGING_PRINCIPAL_ID,
                review_event_id=STAGING_REVIEW_EVENT_ID,
                evidence_digest=STAGING_EVIDENCE_DIGEST,
                after_evaluate=rotate_after_evaluate,
            )

    def test_EP06_old_point_of_use_snapshot_fails_after_epoch_rotation(self):
        source, wrapped = self.authority()
        snapshot = wrapped.preflight(
            principal_id=STAGING_PRINCIPAL_ID,
            review_event_id=STAGING_REVIEW_EVENT_ID,
            evidence_digest=STAGING_EVIDENCE_DIGEST,
        )
        envelope = self.evaluate_current(wrapped)

        self.assertEqual(snapshot.state_token, envelope["state_token"])
        self.assertTrue(wrapped.point_of_use_current(snapshot))

        source.rotate(EPOCH_2)

        self.assertFalse(wrapped.point_of_use_current(snapshot))

    def test_EP07_epoch_never_becomes_spatial_check_admission_or_public_capability(self):
        source, wrapped = self.authority()
        envelope = self.evaluate_current(wrapped)
        serialized = json.dumps(envelope, sort_keys=True)

        self.assertNotIn(EPOCH_1, serialized)
        self.assertNotIn('"authority_epoch"', serialized)
        self.assertNotEqual(envelope["state_token"], STAGING_STATE_TOKEN)
        self.assertEqual(
            envelope["result"]["admission"]["evidence_digest"],
            STAGING_EVIDENCE_DIGEST,
        )
        self.assertNotIn("authority_epoch", envelope["result"]["admission"])

    def test_EP08_rotation_must_change_epoch_and_invalid_values_fail_closed(self):
        source = AuthorityEpochSource(EPOCH_1)
        with self.assertRaises(ProfileContractError):
            source.rotate(EPOCH_1)
        with self.assertRaises(ProfileContractError):
            source.rotate("not-an-epoch")
        with self.assertRaises(ProfileContractError):
            AuthorityEpochSource("not-an-epoch")
        with self.assertRaises(ProfileContractError):
            bind_authority_epoch(
                authority_epoch=EPOCH_1,
                external_state_token="not-a-token",
            )

    def test_EP09_database_state_change_still_blocks_under_epoch_wrapper(self):
        changed = staging_current_snapshot_v2()
        changed["state_token"] = "f" * 64
        source, wrapped = self.authority(
            external=RecordedPostgresSnapshotV2Authority(
                postflight_payload=changed
            )
        )

        with self.assertRaises(ProfileContractError):
            self.evaluate_current(wrapped)

        # The epoch itself did not need to rotate for an ordinary DB mutation.
        self.assertEqual(source.read(), EPOCH_1)

    def test_EP10_v0_deployment_qualification_remains_unchanged(self):
        for config in (
            {"remote_api": True},
            {"local_service": True},
            {"persistence": True},
        ):
            with self.subTest(config=config), self.assertRaises(HostContractError):
                qualify_deployment(**config)


if __name__ == "__main__":
    unittest.main()

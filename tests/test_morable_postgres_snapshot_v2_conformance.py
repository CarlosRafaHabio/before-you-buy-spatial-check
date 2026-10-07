"""Conformance tests: real Morable staging Snapshot V2 -> draft host profile."""
from copy import deepcopy
import unittest

from spatial_check import evaluate
from tests.host_service_single_invocation_profile_draft import (
    AUTHORITY_SCOPE,
    ProfileContractError,
    SingleInvocationHost,
)
from tests.morable_postgres_snapshot_v2_contract import (
    STAGING_EVIDENCE_DIGEST,
    STAGING_PRINCIPAL_ID,
    STAGING_REVIEW_EVENT_ID,
    STAGING_STATE_TOKEN,
    RecordedPostgresSnapshotV2Authority,
    parse_morable_snapshot_v2,
    staging_current_snapshot_v2,
    staging_revoked_snapshot_v2,
)


class MorablePostgresSnapshotV2ConformanceTests(unittest.TestCase):
    def evaluate_current(self, authority=None):
        authority = authority or RecordedPostgresSnapshotV2Authority()
        host = SingleInvocationHost(authority)
        return host.evaluate_review(
            principal_id=STAGING_PRINCIPAL_ID,
            review_event_id=STAGING_REVIEW_EVENT_ID,
            evidence_digest=STAGING_EVIDENCE_DIGEST,
        )

    def test_PG01_recorded_staging_snapshot_runs_real_claim_confirm_evaluate(self):
        envelope = self.evaluate_current()

        self.assertEqual(envelope["state_token"], STAGING_STATE_TOKEN)
        self.assertEqual(envelope["authority_scope"], AUTHORITY_SCOPE)
        self.assertTrue(envelope["current_as_of_postflight"])
        self.assertEqual(
            envelope["result"]["status"],
            "NO CONFLICT DETECTED IN PROVIDED DATA",
        )
        self.assertEqual(
            envelope["result"]["execution_mode"],
            "HOST_CONFIRMED_INPUT",
        )
        self.assertEqual(
            envelope["result"]["admission"]["evidence_digest"],
            STAGING_EVIDENCE_DIGEST,
        )
        self.assertEqual(
            envelope["result"]["admission"]["confirmation_ref"],
            "morable-review:" + STAGING_REVIEW_EVENT_ID,
        )
        self.assertEqual(envelope["review_event_id"], STAGING_REVIEW_EVENT_ID)
        self.assertEqual(envelope["case_id"], "case-1")
        self.assertEqual(envelope["revision"], "r1")
        self.assertEqual(envelope["room_identity"], "room-1")
        self.assertEqual(envelope["item_identity"], "item-1")

    def test_PG02_same_real_snapshot_can_be_readmitted_only_as_fresh_local_domains(self):
        one = self.evaluate_current(RecordedPostgresSnapshotV2Authority())
        two = self.evaluate_current(RecordedPostgresSnapshotV2Authority())

        self.assertEqual(one["state_token"], two["state_token"])
        self.assertEqual(
            one["result"]["input_digest"],
            two["result"]["input_digest"],
        )
        self.assertEqual(one["result"]["status"], two["result"]["status"])
        self.assertNotEqual(one["evaluation_id"], two["evaluation_id"])
        self.assertNotEqual(
            one["result"]["admission"]["receipt_id"],
            two["result"]["admission"]["receipt_id"],
        )

    def test_PG03_real_current_to_revoked_postflight_blocks_handoff_after_evaluate(self):
        calls = {"evaluate": 0}

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        authority = RecordedPostgresSnapshotV2Authority(
            postflight_payload=staging_revoked_snapshot_v2()
        )
        host = SingleInvocationHost(authority, evaluator=counted)

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=STAGING_PRINCIPAL_ID,
                review_event_id=STAGING_REVIEW_EVENT_ID,
                evidence_digest=STAGING_EVIDENCE_DIGEST,
            )

        self.assertEqual(calls["evaluate"], 1)

    def test_PG04_real_revoked_snapshot_blocks_before_admission_and_evaluate(self):
        calls = {"evaluate": 0}

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        revoked = staging_revoked_snapshot_v2()
        authority = RecordedPostgresSnapshotV2Authority(
            preflight_payload=revoked,
            postflight_payload=revoked,
        )
        host = SingleInvocationHost(authority, evaluator=counted)

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=STAGING_PRINCIPAL_ID,
                review_event_id=STAGING_REVIEW_EVENT_ID,
                evidence_digest=STAGING_EVIDENCE_DIGEST,
            )

        self.assertEqual(calls["evaluate"], 0)

    def test_PG05_recorded_revocation_response_has_no_evaluation_bytes(self):
        revoked = staging_revoked_snapshot_v2()

        self.assertEqual(revoked["code"], "REVIEW_REVOKED")
        self.assertEqual(
            revoked["revoked_authority_version"],
            revoked["reviewed_authority_version"] + 1,
        )
        for forbidden in (
            "claim_payload",
            "effective_request_canonical",
            "review_context_canonical",
        ):
            self.assertNotIn(forbidden, revoked)

    def test_PG06_claim_request_and_scope_tamper_fail_before_real_evaluate(self):
        mutations = []

        claim_tamper = staging_current_snapshot_v2()
        claim_tamper["claim_payload"] = claim_tamper["claim_payload"].replace(
            '"value":"138"', '"value":"139"', 1
        )
        mutations.append(claim_tamper)

        request_tamper = staging_current_snapshot_v2()
        request_tamper["effective_request_canonical"] = (
            request_tamper["effective_request_canonical"]
            .replace('"identity":"item-1"', '"identity":"item-X"', 1)
        )
        mutations.append(request_tamper)

        noncanonical_context = staging_current_snapshot_v2()
        noncanonical_context["review_context_canonical"] = (
            '{"projectId":"spatial-profile-v04-conformance-20261007",'
            '"budgetItemId":"bed-1"}'
        )
        mutations.append(noncanonical_context)

        wrong_event = staging_current_snapshot_v2()
        wrong_event["current_review_event_id"] = "mreview-v2-" + "f" * 48
        mutations.append(wrong_event)

        for payload in mutations:
            calls = {"evaluate": 0}

            def counted(request, receipt):
                calls["evaluate"] += 1
                return evaluate(request, receipt)

            authority = RecordedPostgresSnapshotV2Authority(
                preflight_payload=payload
            )
            host = SingleInvocationHost(authority, evaluator=counted)
            with self.subTest(payload=payload.get("current_review_event_id")):
                with self.assertRaises(ProfileContractError):
                    host.evaluate_review(
                        principal_id=STAGING_PRINCIPAL_ID,
                        review_event_id=STAGING_REVIEW_EVENT_ID,
                        evidence_digest=STAGING_EVIDENCE_DIGEST,
                    )
                self.assertEqual(calls["evaluate"], 0)

    def test_PG07_token_change_between_real_shape_pre_and_postflight_blocks_handoff(self):
        postflight = staging_current_snapshot_v2()
        postflight["state_token"] = "f" * 64
        authority = RecordedPostgresSnapshotV2Authority(
            postflight_payload=postflight
        )

        with self.assertRaises(ProfileContractError):
            self.evaluate_current(authority)

    def test_PG08_wrong_principal_cannot_consume_recorded_project_authority(self):
        authority = RecordedPostgresSnapshotV2Authority()
        with self.assertRaises(ProfileContractError):
            SingleInvocationHost(authority).evaluate_review(
                principal_id="00000000-0000-4000-8000-000000000001",
                review_event_id=STAGING_REVIEW_EVENT_ID,
                evidence_digest=STAGING_EVIDENCE_DIGEST,
            )

    def test_PG09_parser_refuses_revoke_head_without_valid_revocation_contract(self):
        payload = staging_current_snapshot_v2()
        payload["head_status"] = "REVOKED"
        payload["revocation_state"] = "REVOKED"

        with self.assertRaises(ProfileContractError):
            parse_morable_snapshot_v2(
                payload,
                principal_id=STAGING_PRINCIPAL_ID,
                expected_review_event_id=STAGING_REVIEW_EVENT_ID,
                expected_evidence_digest=STAGING_EVIDENCE_DIGEST,
            )


if __name__ == "__main__":
    unittest.main()

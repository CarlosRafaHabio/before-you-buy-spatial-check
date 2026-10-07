"""Adversarial tests for HOST_SERVICE_SINGLE_INVOCATION draft profile."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import unittest

from spatial_check import evaluate
from spatial_check.trust import claim_from_data
from tests.helpers import base, change
from tests.host_harness_contract_v0 import HostContractError, qualify_deployment
from tests.host_service_single_invocation_profile_draft import (
    AUTHORITY_SCOPE,
    PROFILE,
    ProfileContractError,
    SingleInvocationHost,
    SyntheticExternalAuthority,
    SyntheticProcessCrash,
)


class SingleInvocationProfileDraftTests(unittest.TestCase):
    def fixture(self):
        request, evidence = base()
        authority = SyntheticExternalAuthority(evidence, request)
        review = authority.current_review
        host = SingleInvocationHost(authority)
        return authority, host, request, evidence, review

    def evaluate_current(self, authority, host):
        review = authority.current_review
        return host.evaluate_review(
            principal_id=authority.principal_id,
            review_event_id=review.review_event_id,
            evidence_digest=review.evidence_digest,
        )

    def test_S01_profile_does_not_weaken_v0_deployment_qualification(self):
        for config in (
            {"remote_api": True},
            {"local_service": True},
            {"persistence": True},
            {"embedded_python": False},
            {"case_affinity": False},
        ):
            with self.subTest(config=config), self.assertRaises(HostContractError):
                qualify_deployment(**config)

    def test_S02_one_shot_handoff_is_transient_and_contains_no_capability(self):
        authority, host, request, evidence, review = self.fixture()
        envelope = self.evaluate_current(authority, host)

        self.assertEqual(envelope["profile"], PROFILE)
        self.assertEqual(envelope["authority_scope"], AUTHORITY_SCOPE)
        self.assertTrue(envelope["current_as_of_postflight"])
        self.assertEqual(
            envelope["result"]["status"],
            "NO CONFLICT DETECTED IN PROVIDED DATA",
        )
        self.assertEqual(envelope["result"]["execution_mode"], "HOST_CONFIRMED_INPUT")
        self.assertEqual(
            envelope["result"]["admission"]["evidence_digest"],
            review.evidence_digest,
        )
        serialized = json.dumps(envelope)
        self.assertNotIn("TrustedEvidence", serialized)
        self.assertNotIn("LifecycleRegistry", serialized)
        self.assertNotIn('"receipt":', serialized)
        self.assertNotIn('"registry":', serialized)

    def test_S03_retry_creates_fresh_admission_but_same_state_attestation(self):
        authority, host, request, evidence, review = self.fixture()
        one = self.evaluate_current(authority, host)
        two = self.evaluate_current(authority, SingleInvocationHost(authority))

        self.assertNotEqual(one["evaluation_id"], two["evaluation_id"])
        self.assertNotEqual(
            one["result"]["admission"]["receipt_id"],
            two["result"]["admission"]["receipt_id"],
        )
        self.assertEqual(one["state_token"], two["state_token"])
        self.assertEqual(one["result"]["status"], two["result"]["status"])
        self.assertEqual(one["result"]["input_digest"], two["result"]["input_digest"])
        self.assertEqual(
            one["result"]["admission"]["confirmation_ref"],
            two["result"]["admission"]["confirmation_ref"],
        )

    def test_S04_a_to_b_to_a_never_restores_old_state_token(self):
        authority, host, request, evidence, old_review = self.fixture()
        first_snapshot = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id=old_review.review_event_id,
            evidence_digest=old_review.evidence_digest,
        )

        b_evidence = deepcopy(evidence)
        change(b_evidence, "iw", value=400)
        authority.transition_review(
            evidence=b_evidence,
            request=request,
            revision="r2",
            review_event_id="review-b",
        )
        b_token = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id="review-b",
            evidence_digest=authority.current_review.evidence_digest,
        ).state_token

        authority.transition_review(
            evidence=evidence,
            request=request,
            revision="r3",
            review_event_id="review-a-again",
        )
        final_snapshot = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id="review-a-again",
            evidence_digest=authority.current_review.evidence_digest,
        )

        self.assertNotEqual(first_snapshot.state_token, b_token)
        self.assertNotEqual(first_snapshot.state_token, final_snapshot.state_token)
        self.assertGreater(final_snapshot.case_sequence, first_snapshot.case_sequence)
        with self.assertRaises(ProfileContractError):
            authority.preflight(
                principal_id=authority.principal_id,
                review_event_id=old_review.review_event_id,
                evidence_digest=old_review.evidence_digest,
            )

    def test_S05_delete_recreate_same_project_id_rotates_incarnation(self):
        authority, host, request, evidence, old_review = self.fixture()
        old_snapshot = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id=old_review.review_event_id,
            evidence_digest=old_review.evidence_digest,
        )

        authority.delete_and_recreate(
            evidence,
            request,
            review_event_id="review-recreated",
        )
        new_review = authority.current_review
        new_snapshot = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id=new_review.review_event_id,
            evidence_digest=new_review.evidence_digest,
        )

        self.assertEqual(old_snapshot.project_id, new_snapshot.project_id)
        self.assertNotEqual(
            old_snapshot.project_incarnation_id,
            new_snapshot.project_incarnation_id,
        )
        self.assertNotEqual(old_snapshot.state_token, new_snapshot.state_token)
        with self.assertRaises(ProfileContractError):
            authority.preflight(
                principal_id=authority.principal_id,
                review_event_id=old_review.review_event_id,
                evidence_digest=old_review.evidence_digest,
            )

    def test_S06_revocation_blocks_old_review_but_allows_new_explicit_review(self):
        authority, host, request, evidence, review = self.fixture()
        authority.revoke_current_review()

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
            )
        with self.assertRaises(ProfileContractError):
            authority.reactivate_historical_review(review.review_event_id)

        authority.transition_review(
            evidence=evidence,
            request=request,
            revision="r2",
            review_event_id="review-after-revocation",
        )
        current = self.evaluate_current(authority, host)
        self.assertEqual(current["review_event_id"], "review-after-revocation")
        self.assertEqual(current["revision"], "r2")

    def test_S07_old_review_replay_fails_after_new_review(self):
        authority, host, request, evidence, old_review = self.fixture()
        authority.transition_review(
            evidence=evidence,
            request=request,
            revision="r2",
            review_event_id="review-new",
        )

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=old_review.review_event_id,
                evidence_digest=old_review.evidence_digest,
            )
        current = self.evaluate_current(authority, host)
        self.assertEqual(current["review_event_id"], "review-new")
        self.assertEqual(current["revision"], "r2")

    def test_S08_selector_digest_mismatch_fails_before_admission(self):
        authority, host, request, evidence, review = self.fixture()
        calls = {"evaluate": 0}

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        guarded = SingleInvocationHost(authority, evaluator=counted)
        with self.assertRaises(ProfileContractError):
            guarded.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest="0" * 64,
            )
        self.assertEqual(calls["evaluate"], 0)

    def test_S09_out_of_band_evidence_mutation_without_rebinding_is_detected(self):
        authority, host, request, evidence, review = self.fixture()
        corrupted = deepcopy(evidence)
        change(corrupted, "iw", value=201)
        corrupted_payload = claim_from_data(corrupted).payload
        authority.unsafe_corrupt_current_review_for_test(
            evidence_payload=corrupted_payload
        )

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
            )

    def test_S10_out_of_band_effective_request_mutation_is_detected(self):
        authority, host, request, evidence, review = self.fixture()
        corrupted_request = deepcopy(request)
        corrupted_request["item"]["position"]["x"] = "other-x"
        authority.unsafe_corrupt_current_review_for_test(
            effective_request_canonical=json.dumps(
                corrupted_request,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
            )
        )

        with self.assertRaises(ProfileContractError):
            self.evaluate_current(authority, host)


    def test_S10b_reviewed_request_scope_mismatch_is_refused_before_evaluate(self):
        authority, host, request, evidence, review = self.fixture()
        calls = {"evaluate": 0}
        mismatched_request = deepcopy(request)
        mismatched_request["item"]["identity"] = "other-item"

        authority.transition_review(
            evidence=evidence,
            request=mismatched_request,
            revision="r2",
            review_event_id="review-bad-request-scope",
        )

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        guarded = SingleInvocationHost(authority, evaluator=counted)
        with self.assertRaises(ProfileContractError):
            self.evaluate_current(authority, guarded)
        self.assertEqual(calls["evaluate"], 0)

    def test_S11_change_during_evaluation_blocks_current_handoff(self):
        authority, host, request, evidence, review = self.fixture()

        def mutate_after_evaluate():
            altered = deepcopy(evidence)
            change(altered, "iw", value=400)
            authority.transition_review(
                evidence=altered,
                request=request,
                revision="r2",
                review_event_id="review-during-evaluation",
            )

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
                after_evaluate=mutate_after_evaluate,
            )

    def test_S12_a_to_b_to_a_during_evaluation_still_blocks_handoff(self):
        authority, host, request, evidence, review = self.fixture()

        def aba_after_evaluate():
            altered = deepcopy(evidence)
            change(altered, "iw", value=400)
            authority.transition_review(
                evidence=altered,
                request=request,
                revision="r2",
                review_event_id="review-b",
            )
            authority.transition_review(
                evidence=evidence,
                request=request,
                revision="r3",
                review_event_id="review-a-again",
            )

        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
                after_evaluate=aba_after_evaluate,
            )

    def test_S13_crash_after_confirm_delivers_nothing_and_retry_is_fresh(self):
        authority, host, request, evidence, review = self.fixture()
        calls = {"evaluate": 0}

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        crashing = SingleInvocationHost(authority, evaluator=counted)

        def crash():
            raise SyntheticProcessCrash("after-confirm")

        with self.assertRaises(SyntheticProcessCrash):
            crashing.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
                after_confirm=crash,
            )
        self.assertEqual(calls["evaluate"], 0)

        retry = self.evaluate_current(authority, SingleInvocationHost(authority))
        self.assertTrue(retry["current_as_of_postflight"])

    def test_S14_crash_after_evaluate_delivers_nothing_and_retry_is_safe(self):
        authority, host, request, evidence, review = self.fixture()
        calls = {"evaluate": 0}

        def counted(request, receipt):
            calls["evaluate"] += 1
            return evaluate(request, receipt)

        crashing = SingleInvocationHost(authority, evaluator=counted)

        def crash():
            raise SyntheticProcessCrash("after-evaluate")

        with self.assertRaises(SyntheticProcessCrash):
            crashing.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
                after_evaluate=crash,
            )
        self.assertEqual(calls["evaluate"], 1)

        retry = self.evaluate_current(authority, SingleInvocationHost(authority))
        self.assertTrue(retry["current_as_of_postflight"])

    def test_S15_two_python_instances_can_evaluate_same_current_state_independently(self):
        authority, host, request, evidence, review = self.fixture()

        def run_one(_):
            instance = SingleInvocationHost(authority)
            return instance.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            one, two = list(pool.map(run_one, range(2)))

        self.assertEqual(one["state_token"], two["state_token"])
        self.assertEqual(one["result"]["status"], two["result"]["status"])
        self.assertNotEqual(one["evaluation_id"], two["evaluation_id"])
        self.assertNotEqual(
            one["result"]["admission"]["receipt_id"],
            two["result"]["admission"]["receipt_id"],
        )

    def test_S16_service_restart_has_no_receipt_continuity(self):
        authority, host, request, evidence, review = self.fixture()
        before = self.evaluate_current(authority, host)
        restarted = SingleInvocationHost(authority)
        after = self.evaluate_current(authority, restarted)

        self.assertEqual(before["state_token"], after["state_token"])
        self.assertNotEqual(
            before["result"]["admission"]["receipt_id"],
            after["result"]["admission"]["receipt_id"],
        )

    def test_S17_point_of_use_revalidation_detects_post_handoff_change(self):
        authority, host, request, evidence, review = self.fixture()
        snapshot = authority.preflight(
            principal_id=authority.principal_id,
            review_event_id=review.review_event_id,
            evidence_digest=review.evidence_digest,
        )
        envelope = self.evaluate_current(authority, host)
        self.assertEqual(snapshot.state_token, envelope["state_token"])
        self.assertTrue(authority.point_of_use_current(snapshot))

        authority.transition_review(
            evidence=evidence,
            request=request,
            revision="r2",
            review_event_id="review-after-handoff",
        )
        self.assertFalse(authority.point_of_use_current(snapshot))

    def test_S18_wrong_principal_cannot_use_another_users_review(self):
        authority, host, request, evidence, review = self.fixture()
        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id="other-user",
                review_event_id=review.review_event_id,
                evidence_digest=review.evidence_digest,
            )

    def test_S19_changed_content_same_revision_still_requires_new_authority_state(self):
        authority, host, request, evidence, old_review = self.fixture()
        altered = deepcopy(evidence)
        change(altered, "iw", value=201)
        authority.transition_review(
            evidence=altered,
            request=request,
            revision="r1",
            review_event_id="review-same-label-new-state",
        )
        new_review = authority.current_review

        self.assertEqual(new_review.revision, old_review.revision)
        self.assertGreater(new_review.case_sequence, old_review.case_sequence)
        self.assertNotEqual(new_review.evidence_digest, old_review.evidence_digest)
        with self.assertRaises(ProfileContractError):
            host.evaluate_review(
                principal_id=authority.principal_id,
                review_event_id=old_review.review_event_id,
                evidence_digest=old_review.evidence_digest,
            )
        self.assertTrue(self.evaluate_current(authority, host)["current_as_of_postflight"])


if __name__ == "__main__":
    unittest.main()

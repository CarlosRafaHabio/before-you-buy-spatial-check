"""H15 Ed25519 signed synthetic approvals + durable H14 dispatch.

New independent synthetic adversarial cases. Uses ephemeral generated keys
in memory; NEVER a real private key, human approval or actual external API.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prototypes.camel_selective_v0.durable_claim_v0 import DurableClaimV0, GrantScope
from prototypes.camel_selective_v0.signed_approval_v0 import (
    SignedApproval, PublicApprovalVerifier, canonical_payload,
    dispatch_with_signed_approval,
)

T = 2000000000
CTX = sha256(b"synthetic:folder=/a;intent=view").hexdigest()
OTHER_CTX = sha256(b"synthetic:folder=/b;intent=view").hexdigest()
EFFECT = b"SYNTHETIC_EFFECT_V0\n"
GR = "GR-0123456789abcdef"
EP = "EP-000042"
USER = "USR-0042"


def claims(**overrides):
    result = dict(
        v=1, key_id="ISS-0001", grant_id=GR, epoch=EP,
        user_id=USER, operation="directory.lookup_user",
        audience="spatial-check.h15.synthetic-broker",
        context_sha256=CTX, actor_claim="ACTOR-0001",
        issued_at=T - 10, expires_at=T + 60,
    )
    result.update(overrides)
    return result


def sign(private, **updates):
    raw = canonical_payload(claims(**updates))
    return SignedApproval(raw, private.sign(raw))


class H15SignedSyntheticAuthority(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="h15-synthetic-")
        self.root = Path(self.tmp.name)
        self.db = self.root / "grants.sqlite3"
        self.file = self.root / "effects.log"
        self.ledger = DurableClaimV0(self.db)
        self.private = Ed25519PrivateKey.generate()
        self.public_bytes = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.verifier = PublicApprovalVerifier({"ISS-0001": self.public_bytes})

    def tearDown(self):
        self.tmp.cleanup()

    def dispatch(self, signed, **kwargs):
        args = dict(
            verifier=self.verifier, signed=signed,
            expected_context_sha256=CTX, now_utc=T,
            ledger=self.ledger, raw_user_id=USER,
            trusted_broker_mode="write_return", scratch_log=self.file,
            timeout_secs=2,
        )
        args.update(kwargs)
        return dispatch_with_signed_approval(**args)

    def effects(self):
        return self.file.read_bytes() if self.file.exists() else b""

    def test_H15_01_correct_signed_approval_runs_one_synthetic_effect(self):
        r = self.dispatch(sign(self.private))
        self.assertEqual((r.code, r.state), ("DISPATCH_CONFIRMED", "CONFIRMED"))
        self.assertEqual(self.effects(), EFFECT)

    def test_H15_02_signed_approval_replay_denied_after_reopen(self):
        token = sign(self.private)
        self.assertEqual(self.dispatch(token).code, "DISPATCH_CONFIRMED")
        self.ledger = DurableClaimV0(self.db)
        r = self.dispatch(token)
        self.assertEqual((r.code, r.state),
                         ("DENY_ALREADY_CONSUMED", "CONFIRMED"))
        self.assertEqual(self.effects(), EFFECT)

    def test_H15_03_unsigned_payload_changes_rejected_no_registration(self):
        original = sign(self.private)
        fields = json.loads(original.payload)
        for change in (
            {"user_id": "USR-9999"},
            {"epoch": "EP-000043"},
            {"operation": "admin.delete"},
            {"actor_claim": "ACTOR-0002"},
            {"context_sha256": OTHER_CTX},
            {"expires_at": T+100},
        ):
            with self.subTest(change=change):
                changed = SignedApproval(
                    canonical_payload({**fields, **change}),
                    original.signature,
                )
                self.assertEqual(
                    self.dispatch(changed).code, "DENY_INVALID_SIGNATURE")
                self.assertIsNone(self.ledger.inspect(
                    GrantScope(GR, EP, USER)))
        self.assertEqual(self.effects(), b"")

    def test_H15_04_wrong_signer_does_not_pass(self):
        token = sign(Ed25519PrivateKey.generate())
        self.assertEqual(self.dispatch(token).code, "DENY_INVALID_SIGNATURE")
        self.assertEqual(self.effects(), b"")

    def test_H15_05_unknown_key_and_revocation_rejected(self):
        token = sign(self.private)
        second = PublicApprovalVerifier({"ISS-0002": self.public_bytes})
        self.assertEqual(self.dispatch(token, verifier=second).code,
                         "DENY_UNKNOWN_ISSUER")
        self.assertEqual(self.effects(), b"")

    def test_H15_06_expired_and_future_dated_rejected(self):
        for token,now in (
            (sign(self.private), T+60),
            (sign(self.private), T-11),
            (sign(self.private, issued_at=T-400, expires_at=T+1), T),
        ):
            with self.subTest(now=now, raw=token.payload):
                self.assertEqual(self.dispatch(token, now_utc=now).code,
                                 "DENY_APPROVAL_EXPIRED_OR_NOT_YET_VALID")
        self.assertEqual(self.effects(), b"")

    def test_H15_07_context_mismatch_with_valid_signature_rejected(self):
        token = sign(self.private)
        self.assertEqual(
            self.dispatch(token, expected_context_sha256=OTHER_CTX).code,
            "DENY_CONTEXT_MISMATCH")
        self.assertEqual(self.effects(), b"")

    def test_H15_08_signed_wrong_audience_or_operation_rejected(self):
        for changed in (
            {"audience":"spatial-check.habio.production"},
            {"operation":"directory.delete_user"},
        ):
            with self.subTest(fields=changed):
                self.assertEqual(self.dispatch(sign(self.private, **changed)).code,
                                 "DENY_APPROVAL_SCOPE")
        self.assertEqual(self.effects(), b"")

    def test_H15_09_canonical_duplicate_unknown_fields_and_boolean_rejected(self):
        fields = claims()
        raw = json.dumps(fields, separators=(",", ":")).encode()
        signed_noncanonical = SignedApproval(raw, self.private.sign(raw))
        self.assertEqual(self.dispatch(signed_noncanonical).code,
                         "DENY_MALFORMED_APPROVAL")
        raw_dup = b'{"v":1,"v":1}'
        self.assertEqual(
            self.dispatch(SignedApproval(raw_dup, self.private.sign(raw_dup))).code,
            "DENY_MALFORMED_APPROVAL")
        for variant in (
            {"v": True},
            {"extra": "unapproved"},
        ):
            token = sign(self.private, **variant)
            self.assertIn(self.dispatch(token).code,
                          ("DENY_MALFORMED_APPROVAL", "DENY_APPROVAL_SCOPE"))
        self.assertEqual(self.effects(), b"")

    def test_H15_10_signature_and_payload_length_enforced(self):
        for token in (
            SignedApproval(b"{}", b""),
            SignedApproval(b"{}" * 600, b"0"*64),
            SignedApproval(b"{}", b"0"*65),
            None, "signed", {"payload":"injected"}
        ):
            self.assertEqual(self.dispatch(token).code,
                             "DENY_MALFORMED_APPROVAL")
        self.assertEqual(self.effects(), b"")

    def test_H15_11_wrong_guest_user_does_not_consume_signed_grant(self):
        token = sign(self.private)
        bad = self.dispatch(token, raw_user_id="USR-9999")
        self.assertEqual(bad.code, "DENY_OUT_OF_SCOPE")
        self.assertEqual(self.effects(), b"")
        self.assertEqual(self.dispatch(token).code, "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), EFFECT)

    def test_H15_12_valid_signature_concurrent_host_threads_once_only(self):
        token = sign(self.private)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.dispatch(token), range(12)))
        self.assertEqual(sum(r.code=="DISPATCH_CONFIRMED" for r in results),1)
        self.assertEqual(sum(r.code=="DENY_ALREADY_CONSUMED" for r in results),11)
        self.assertEqual(self.effects(), EFFECT)

    def test_H15_13_signed_actor_claim_not_human_proof_negative_witness(self):
        # NEGATIVE: a trusted issuer may sign an unverified actor claim.
        forged_by_issuer = sign(self.private, actor_claim="ACTOR-9999")
        self.assertEqual(
            self.dispatch(forged_by_issuer).code, "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), EFFECT)

    def test_H15_14_local_ledger_deletion_allows_signed_token_replay_negative(self):
        # NEGATIVE: signed approval doesn't make the local DB tamper proof.
        ticket = sign(self.private)
        self.assertEqual(self.dispatch(ticket).code, "DISPATCH_CONFIRMED")
        self.db.unlink()
        self.ledger = DurableClaimV0(self.db)
        self.assertEqual(self.dispatch(ticket).code, "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), EFFECT * 2)

    def test_H15_15_valid_issuer_can_sign_an_unapproved_new_epoch_negative(self):
        # NEGATIVE: signer compromise/issuer policy error enables regrant.
        first = sign(self.private)
        second = sign(self.private, grant_id="GR-fedcba9876543210",
                      epoch="EP-000043")
        self.assertEqual(self.dispatch(first).code, "DISPATCH_CONFIRMED")
        self.assertEqual(self.dispatch(second).code, "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), EFFECT * 2)

    def test_H15_16_verifier_holds_only_public_key_snapshot(self):
        # Modifying original host dict does not alter the copied key set.
        mapping = {"ISS-0001": self.public_bytes}
        verifier = PublicApprovalVerifier(mapping)
        mapping["ISS-0001"] = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.assertEqual(self.dispatch(sign(self.private),verifier=verifier).code,
                         "DISPATCH_CONFIRMED")

    def test_H15_17_malformed_scopes_denied_after_verified_signature(self):
        for changed in (
            {"grant_id": "GR-../../"},
            {"epoch":"EP-000999/"},
            {"user_id": "USR-999X"},
        ):
            with self.subTest(fields=changed):
                self.assertEqual(
                    self.dispatch(sign(self.private, **changed)).code,
                    "DENY_APPROVAL_SCOPE")
        self.assertEqual(self.effects(), b"")

    def test_H15_18_synthetic_broker_unknown_stays_consumed(self):
        t = sign(self.private)
        r = self.dispatch(t,trusted_broker_mode="write_hang",timeout_secs=.8)
        self.assertEqual((r.code,r.state),
                         ("DISPATCH_OUTCOME_UNKNOWN","UNKNOWN"))
        self.assertEqual(self.effects(), EFFECT)
        self.assertEqual(self.dispatch(t).code, "DENY_ALREADY_CONSUMED")
        self.assertEqual(self.effects(), EFFECT)


if __name__ == "__main__":
    unittest.main()

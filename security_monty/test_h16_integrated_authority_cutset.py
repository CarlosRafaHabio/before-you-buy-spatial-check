"""H16: cross-module authority cut-set audit. Synthetic effects only.

IMPORTANT: Green NEGATIVE witnesses demonstrate multiple cooperating-host
routes around H15, not an exploitable prompt-only sandbox escape. This is
an architecture integration evaluation, not a new protection layer.
"""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prototypes.camel_selective_v0.closed_host_plan import (
    ClosedHostExecutor, ExternalSlot, HostPlan, Source,
)
from prototypes.camel_selective_v0.durable_claim_v0 import (
    DurableClaimV0, GrantScope, dispatch_synthetic_once,
)
from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, external_text,
)
from prototypes.camel_selective_v0.host_dispatch import BoundTool
from prototypes.camel_selective_v0.isolated_broker_v0 import run_synthetic_broker
from prototypes.camel_selective_v0.monty_host_bridge_v0 import MontyHostBridgeV0
from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup
from prototypes.camel_selective_v0.signed_approval_v0 import (
    PublicApprovalVerifier, SignedApproval, canonical_payload,
    dispatch_with_signed_approval,
)

_EPOCH = "EP-000042"
_USER = "USR-0042"
_GRANT = "GR-0123456789abcdef"
_TIME = 2_000_000_000
_CONTEXT = sha256(b"H16 independent synthetic host decision").hexdigest()
_EFFECT = b"SYNTHETIC_EFFECT_V0\n"


class H16AuthorityCompositionWitnesses(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="h16-")
        self.root = Path(self.temp.name)
        self.ledger = DurableClaimV0(self.root / "synthetic.sqlite3")
        self.scratch = self.root / "effect.log"
        self.scope = GrantScope(_GRANT, _EPOCH, _USER)
        self.key = Ed25519PrivateKey.generate()
        raw_public = self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.verifier = PublicApprovalVerifier({"ISS-0001": raw_public})

    def tearDown(self):
        self.temp.cleanup()

    def token(self, **overrides):
        fields = {
            "v": 1, "key_id": "ISS-0001", "grant_id": _GRANT,
            "epoch": _EPOCH, "user_id": _USER,
            "operation": "directory.lookup_user",
            "audience": "spatial-check.h15.synthetic-broker",
            "context_sha256": _CONTEXT, "actor_claim": "ACTOR-0001",
            "issued_at": _TIME - 10, "expires_at": _TIME + 60,
        }
        fields.update(overrides)
        payload = canonical_payload(fields)
        return SignedApproval(payload, self.key.sign(payload))

    def signed_dispatch(self, token, *, verifier=None):
        return dispatch_with_signed_approval(
            verifier=verifier or self.verifier,
            signed=token,
            expected_context_sha256=_CONTEXT,
            now_utc=_TIME,
            ledger=self.ledger,
            raw_user_id=_USER,
            trusted_broker_mode="write_return",
            scratch_log=self.scratch,
            timeout_secs=2,
        )

    def direct_dispatch(self):
        return dispatch_synthetic_once(
            self.ledger, self.scope,
            raw_user_id=_USER,
            broker_mode="write_return",
            scratch_log=self.scratch,
            timeout_secs=2,
        )

    def effects(self):
        return self.scratch.read_bytes() if self.scratch.exists() else b""

    def test_H16_01_positive_complete_H15_H14_H13_chain(self):
        outcome = self.signed_dispatch(self.token())
        self.assertEqual((outcome.code, outcome.state),
                         ("DISPATCH_CONFIRMED", "CONFIRMED"))
        self.assertEqual(self.effects(), _EFFECT)
        replay = self.signed_dispatch(self.token())
        self.assertEqual(replay.code, "DENY_ALREADY_CONSUMED")
        self.assertEqual(self.effects(), _EFFECT)

    def test_H16_02_INVALID_signature_denied_then_DIRECT_H14_effect(self):
        # NEGATIVE: trusted host deliberately bypasses optional verifier.
        ticket = self.token()
        forged = SignedApproval(
            ticket.payload.replace(b"USR-0042", b"USR-9999"),
            ticket.signature,
        )
        self.assertEqual(self.signed_dispatch(forged).code,
                         "DENY_INVALID_SIGNATURE")
        self.assertIsNone(self.ledger.inspect(self.scope))
        self.assertEqual(self.effects(), b"")
        self.assertEqual(self.ledger.grant(self.scope).code,
                         "GRANT_REGISTERED")
        self.assertEqual(self.direct_dispatch().code,
                         "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), _EFFECT)

    def test_H16_03_removed_issuer_denied_then_HOST_H14_effect(self):
        # NEGATIVE: H15 revocation does not revoke independent H14 authority.
        raw = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        revoked = PublicApprovalVerifier({"ISS-0002": raw})
        self.assertEqual(
            self.signed_dispatch(self.token(), verifier=revoked).code,
            "DENY_UNKNOWN_ISSUER",
        )
        self.assertEqual(self.ledger.grant(self.scope).code,
                         "GRANT_REGISTERED")
        self.assertEqual(self.direct_dispatch().code,
                         "DISPATCH_CONFIRMED")
        self.assertEqual(self.effects(), _EFFECT)

    def test_H16_04_DIRECT_H13_worker_not_subject_to_H15_or_H14(self):
        # NEGATIVE: a trusted host can invoke broker without ANY grant.
        result = run_synthetic_broker(
            mode="write_return",
            scratch_log=self.scratch,
            timeout_secs=2,
        )
        self.assertEqual(result.code, "BROKER_COMPLETED")
        self.assertEqual(self.effects(), _EFFECT)
        self.assertIsNone(self.ledger.inspect(self.scope))

    def test_H16_05_G2b_taint_denial_does_not_enforce_G5_bypass(self):
        # NEGATIVE composition: same synthetically registered effect sink
        # can have another, intentionally host-approved call path.
        effects = []
        dispatcher = ClosedHostExecutor(
            tool=BoundTool(
                "tool.send", "partner", lambda args: effects.append(args)
            ),
            slots=(ExternalSlot("page", "web.page"),),
            plan=HostPlan("tool.send", (Source("page"),)),
        )
        denied = dispatcher.invoke({"page": _USER})
        self.assertEqual(denied.code, "DENY_UNTRUSTED_INFLUENCE")
        self.assertEqual(effects, [])
        scoped = HostScopedUserLookup(
            approved_user_id=_USER,
            handler=lambda args: effects.append(args),
        )
        self.assertEqual(scoped.invoke(_USER).code, "HANDLER_RETURNED")
        self.assertEqual(effects, [(_USER,)])

    def test_H16_06_Monty_H12_tool_does_not_require_H15_ticket(self):
        # NEGATIVE: guest in a Monty sandbox can trigger a host-approved
        # operation with no H15 signed approval in this distinct path.
        effects = []
        scoped = HostScopedUserLookup(
            approved_user_id=_USER,
            handler=lambda args: effects.append(args),
        )
        bridge = MontyHostBridgeV0(scoped, wall_budget_secs=2)
        result = bridge.run("lookup_user('USR-0042')")
        self.assertEqual((result.status, result.value),
                         ("COMPLETED", "HANDLER_RETURNED"))
        self.assertEqual(effects, [(_USER,)])
        self.assertIsNone(self.ledger.inspect(self.scope))

    def test_H16_07_G1_policy_denies_untrusted_but_host_labels_forgeable(self):
        # NEGATIVE TCB-only witness: FlowText labels are not signed,
        # and host code can manufacture a trusted label for page bytes.
        from prototypes.camel_selective_v0.flow_guard import host_text
        page = external_text("SYNTHETIC_RAW_WEB", origin="web.page")
        guard = FlowGuard((Operation("tool.send", "external", "partner"),))
        self.assertEqual(
            guard.check("tool.send", arguments=(page,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )
        relabeled = host_text(page.text, origin="host.program")
        self.assertEqual(
            guard.check("tool.send", arguments=(relabeled,)).code,
            "ALLOW",
        )

    def test_H16_08_H15_valid_ticket_cannot_authorize_other_context(self):
        # Positive check: verified path has real contextual restriction,
        # even though other privileged routes remain separate.
        ticket = self.token()
        wrong_context = sha256(b"unrelated synthetic decision").hexdigest()
        result = dispatch_with_signed_approval(
            verifier=self.verifier,
            signed=ticket,
            expected_context_sha256=wrong_context,
            now_utc=_TIME,
            ledger=self.ledger, raw_user_id=_USER,
            trusted_broker_mode="write_return",
            scratch_log=self.scratch,
            timeout_secs=2,
        )
        self.assertEqual(result.code, "DENY_CONTEXT_MISMATCH")
        self.assertIsNone(self.ledger.inspect(self.scope))
        self.assertEqual(self.effects(), b"")

    def test_H16_09_same_sink_can_execute_without_any_signed_claim(self):
        # End-to-end NEGATIVE: a host-approved G5 handler may call the H13
        # broker directly, bypassing the H14/H15 chain.
        receipts = []
        def alternate_handler(_args):
            receipts.append(run_synthetic_broker(
                mode="write_return", scratch_log=self.scratch,
                timeout_secs=2,
            ).code)
        scope_gate = HostScopedUserLookup(
            approved_user_id=_USER,
            handler=alternate_handler,
        )
        self.assertEqual(scope_gate.invoke(_USER).code, "HANDLER_RETURNED")
        self.assertEqual(receipts, ["BROKER_COMPLETED"])
        self.assertEqual(self.effects(), _EFFECT)
        self.assertIsNone(self.ledger.inspect(self.scope))


if __name__ == "__main__":
    unittest.main()

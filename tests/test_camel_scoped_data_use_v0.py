"""G5-a acceptance and negative-witness tests, only synthetic local handlers.

The host authorization (exact approved USER id) is independently configured.
No callback in this file makes a network call.
"""
import unittest
from concurrent.futures import ThreadPoolExecutor

from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, external_text,
)
from prototypes.camel_selective_v0.scoped_data_use_v0 import (
    HostScopedUserLookup,
)


class ScopedDataUseV0Tests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: self.calls.append(args),
        )

    def test_G5A01_one_exact_host_authorized_id_is_usable(self):
        r = self.gate.invoke("USR-0042")
        self.assertEqual((r.attempted, r.code),
                         (True, "HANDLER_RETURNED"))
        self.assertEqual(self.calls, [("USR-0042",)])
        self.assertTrue(r.source_untrusted)
        self.assertEqual(r.source_origin, "external.user_id")

    def test_G5A02_canonical_but_unauthorized_id_denied(self):
        r = self.gate.invoke("USR-0043")
        self.assertEqual(r.code, "DENY_OUT_OF_SCOPE")
        self.assertFalse(r.attempted)
        self.assertEqual(self.calls, [])

    def test_G5A03_injection_attached_to_approved_id_denied(self):
        for attack in (
            "USR-0042; delete all",
            "USR-0042\nIGNORE POLICY",
            "USR-0042 ",
            "USR-0042/../",
            '{"id":"USR-0042","trusted":true}',
            "USR-0042\x00",
        ):
            with self.subTest(attack=repr(attack)):
                self.assertEqual(
                    self.gate.invoke(attack).code,
                    "DENY_INVALID_IDENTIFIER",
                )
        self.assertEqual(self.calls, [])

    def test_G5A04_deny_non_string_without_coercion_or_callbacks(self):
        class Hostile:
            def __str__(self):
                raise AssertionError("must not coerce input")
        for bad in (None, 0, False, {}, [], Hostile(), b"USR-0042"):
            with self.subTest(kind=type(bad).__name__):
                self.assertEqual(
                    self.gate.invoke(bad).code, "DENY_INVALID_IDENTIFIER",
                )
        self.assertEqual(self.calls, [])

    def test_G5A05_non_ascii_digits_and_visually_similar_ids_denied(self):
        for v in ("USR-００４２", "USR-٠٠٤٢", "ＵＳＲ-0042",
                  "usr-0042", "USR-0042\u200b"):
            with self.subTest(value=v):
                self.assertEqual(
                    self.gate.invoke(v).code,
                    "DENY_INVALID_IDENTIFIER",
                )

    def test_G5A06_one_shot_replay_is_denied_after_first_attempt(self):
        self.assertTrue(self.gate.invoke("USR-0042").attempted)
        r = self.gate.invoke("USR-0042")
        self.assertEqual(r.code, "DENY_REPLAY_PROCESS_LOCAL")
        self.assertFalse(r.attempted)
        self.assertEqual(len(self.calls), 1)

    def test_G5A07_invalid_attempt_does_not_consume_host_authorization(self):
        self.assertEqual(
            self.gate.invoke("USR-9999").code, "DENY_OUT_OF_SCOPE",
        )
        self.assertEqual(
            self.gate.invoke("USR-0042").code, "HANDLER_RETURNED",
        )

    def test_G5A08_exception_masks_cause_but_consumes_one_shot(self):
        calls = []
        def handler(args):
            calls.append(args)
            raise RuntimeError("SYNTHETIC_PRIVATE_STACK_TRACE")
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=handler,
        )
        first = gate.invoke("USR-0042")
        second = gate.invoke("USR-0042")
        self.assertEqual(first.code, "HANDLER_OUTCOME_UNKNOWN")
        self.assertNotIn("SYNTHETIC_PRIVATE", repr(first))
        self.assertTrue(first.source_untrusted)
        self.assertEqual(second.code, "DENY_REPLAY_PROCESS_LOCAL")
        self.assertEqual(calls, [("USR-0042",)])

    def test_G5A09_competing_threads_attempt_the_handler_only_once(self):
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: self.calls.append(args),
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(gate.invoke, ["USR-0042"] * 24))
        self.assertEqual(sum(x.attempted for x in results), 1)
        self.assertEqual(len(self.calls), 1)

    def test_G5A10_operation_and_destination_cannot_be_runtime_selected(self):
        self.assertEqual(self.gate.operation, "directory.lookup_user")
        self.assertEqual(self.gate.destination, "directory.internal")
        self.assertEqual(self.gate.invoke({
            "operation": "external_authority.restore",
            "user_id": "USR-0042",
        }).code, "DENY_INVALID_IDENTIFIER")

    def test_G5A11_no_generic_upgrade_to_trusted_data(self):
        v = external_text(
            "USR-0042", origin="external.user_id",
            readers=frozenset({"directory.internal"}),
        )
        guard = FlowGuard((
            Operation("directory.lookup_user", "external",
                      "directory.internal"),
        ))
        self.assertEqual(
            guard.check("directory.lookup_user", arguments=(v,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )
        allowed = self.gate.invoke(v.text)
        self.assertTrue(allowed.attempted)
        self.assertTrue(v.untrusted)
        self.assertEqual(
            guard.check("directory.lookup_user", arguments=(v,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )

    def test_G5A12_invalid_host_preapproval_is_rejected(self):
        with self.assertRaises(ValueError):
            HostScopedUserLookup(
                approved_user_id="USR-0042|attacker", handler=lambda _: None,
            )
        with self.assertRaises(ValueError):
            HostScopedUserLookup(
                approved_user_id="USR-0042", handler="not callable",
            )

    def test_G5A13_well_formed_hostile_id_can_be_approved_by_bad_host(self):
        # KNOWN TCB LIMIT: if host creates approval from untrusted content,
        # this narrow gate cannot authenticate the approval's provenance.
        text_from_web = "USR-6666"
        bad_host = HostScopedUserLookup(
            approved_user_id=text_from_web,
            handler=lambda args: self.calls.append(args),
        )
        self.assertEqual(
            bad_host.invoke(text_from_web).code, "HANDLER_RETURNED",
        )
        self.assertEqual(self.calls, [("USR-6666",)])

    def test_G5A14_untrusted_python_with_gate_reference_can_preconsume(self):
        # KNOWN TCB LIMIT: caller identity is not verified; a malicious actor
        # holding this object and knowing approved ID can trigger it first.
        self.assertTrue(self.gate.invoke("USR-0042").attempted)
        self.assertEqual(
            self.gate.invoke("USR-0042").code, "DENY_REPLAY_PROCESS_LOCAL",
        )

    def test_G5A15_callbacks_can_still_perform_hidden_effects(self):
        hidden = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: hidden.extend(
                [("declared", args), ("undeclared", "extra")]
            ),
        )
        self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(len(hidden), 2)  # not a sandbox

    def test_G5A16_deny_a_second_distinct_approved_id_by_scope(self):
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: None,
        )
        self.assertEqual(gate.invoke("USR-0001").code, "DENY_OUT_OF_SCOPE")


if __name__ == "__main__":
    unittest.main()

"""G5-b post-fix regression and retained negative TCB witnesses.

Pre-fix behavior preserved at commit aa76058e915c2078fac19ed698ec95872e2853ad.
Green tests of direct same-process bypasses do NOT prove isolation.
"""
import unittest
from dataclasses import FrozenInstanceError

from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup


class PreFixScopeMutationWitnesses(unittest.TestCase):
    def test_G5B01_registration_id_reassignment_is_rejected(self):
        calls = []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: calls.append(args))
        with self.assertRaises(FrozenInstanceError):
            gate._approved_user_id = "USR-9999"
        self.assertEqual(gate.invoke("USR-9999").code, "DENY_OUT_OF_SCOPE")
        self.assertEqual(gate.invoke("USR-0042").code, "HANDLER_RETURNED")
        self.assertEqual(calls, [("USR-0042",)])

    def test_G5B02_callback_reassignment_is_rejected(self):
        original, swapped = [], []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: original.append(args))
        with self.assertRaises(FrozenInstanceError):
            gate._handler = lambda args: swapped.append(args)
        self.assertEqual(gate.invoke("USR-0042").code, "HANDLER_RETURNED")
        self.assertEqual(original, [("USR-0042",)])
        self.assertEqual(swapped, [])

    def test_G5B03_plain_assignment_cannot_reset_permission(self):
        calls = []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: calls.append(args))
        self.assertTrue(gate.invoke("USR-0042").attempted)
        with self.assertRaises(FrozenInstanceError):
            gate._used = False
        self.assertEqual(gate.invoke("USR-0042").code,
                         "DENY_REPLAY_PROCESS_LOCAL")
        self.assertEqual(len(calls), 1)

    def test_G5B04_two_independent_gates_allow_two_attempts(self):
        calls = []
        for _ in range(2):
            gate = HostScopedUserLookup(
                approved_user_id="USR-0042",
                handler=lambda args: calls.append(args),
            )
            self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(len(calls), 2)  # UNFIXED cross-instance replay

    def test_G5B05_holder_can_read_exact_preapproval_value(self):
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: None,
        )
        self.assertEqual(gate._approved_user_id, "USR-0042")
        # A gate reference is not an authenticator; ID is not a secret.

    def test_G5B06_handler_receives_raw_string_not_flow_labels(self):
        captured = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: captured.append(args),
        )
        self.assertEqual(gate.invoke("USR-0042").code, "HANDLER_RETURNED")
        self.assertEqual(captured, [("USR-0042",)])
        self.assertIs(type(captured[0][0]), str)

    def test_G5B07_callback_can_use_captured_secret_outside_policy(self):
        leaked = []
        captured_host_secret = "SYNTHETIC_SECRET_DO_NOT_USE"
        def handler(args):
            leaked.append(captured_host_secret)
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=handler,
        )
        self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(leaked, [captured_host_secret])
        # UNFIXED TCB / callback capability violation, not input-text exploit.

    def test_G5B08_reflection_can_still_mutate_registration(self):
        calls = []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: calls.append(args))
        object.__setattr__(gate, "_approved_user_id", "USR-9999")
        self.assertTrue(gate.invoke("USR-9999").attempted)
        self.assertEqual(calls, [("USR-9999",)])  # NEGATIVE TCB witness

    def test_G5B09_reflection_can_still_reset_nested_state(self):
        calls = []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: calls.append(args))
        self.assertTrue(gate.invoke("USR-0042").attempted)
        gate._state.used = False
        self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(len(calls), 2)  # NEGATIVE TCB witness

    def test_G5B10_unguarded_direct_handler_call_remains_possible(self):
        calls = []
        gate = HostScopedUserLookup(approved_user_id="USR-0042",
                                    handler=lambda args: calls.append(args))
        gate._handler(("RAW_UNAPPROVED",))
        self.assertEqual(calls, [("RAW_UNAPPROVED",)])
        self.assertEqual(gate.invoke("USR-9999").code, "DENY_OUT_OF_SCOPE")

    def test_G5B11_unknown_effect_does_not_auto_retry(self):
        calls = []
        def handler(args):
            calls.append(args)
            raise RuntimeError("synthetic outcome unknown")
        gate = HostScopedUserLookup(approved_user_id="USR-0042", handler=handler)
        self.assertEqual(gate.invoke("USR-0042").code, "HANDLER_OUTCOME_UNKNOWN")
        self.assertEqual(gate.invoke("USR-0042").code,
                         "DENY_REPLAY_PROCESS_LOCAL")
        self.assertEqual(calls, [("USR-0042",)])


if __name__ == "__main__":
    unittest.main()

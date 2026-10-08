"""G5-b PRE-FIX negative witnesses. PASS means insecure behavior reproduced.

Do not interpret as proof of security. No real tool, private data or network
resource is involved. Fix the accidental ordinary-attribute mutation cases
in a subsequent commit; retain deliberate cross-instance and same-process
Python bypasses as documented TCB limitations.
"""
import unittest

from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup


class PreFixScopeMutationWitnesses(unittest.TestCase):
    def test_G5B01_caller_mutates_preapproved_id_by_plain_assignment(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: calls.append(args),
        )
        gate._approved_user_id = "USR-9999"
        result = gate.invoke("USR-9999")
        self.assertTrue(result.attempted)  # PRE-FIX UNSAFE
        self.assertEqual(calls, [("USR-9999",)])

    def test_G5B02_caller_retargets_handler_by_plain_assignment(self):
        original, redirected = [], []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: original.append(args),
        )
        gate._handler = lambda args: redirected.append(args)
        self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(original, [])
        self.assertEqual(redirected, [("USR-0042",)])  # PRE-FIX UNSAFE

    def test_G5B03_caller_resets_consumed_permission_by_plain_assignment(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: calls.append(args),
        )
        self.assertTrue(gate.invoke("USR-0042").attempted)
        gate._used = False
        self.assertTrue(gate.invoke("USR-0042").attempted)
        self.assertEqual(len(calls), 2)  # PRE-FIX UNSAFE

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


if __name__ == "__main__":
    unittest.main()

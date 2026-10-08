"""H9: off-the-shelf Monty worker isolation versus host tool authority.

Test-only upstream dependency. All callbacks and data are synthetic.
"""
import unittest
from pydantic_monty import Monty, MontyRuntimeError
from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup


class MontySandboxCandidateTests(unittest.TestCase):
    def test_h9_01_evaluate_simple_python(self):
        with Monty() as pool:
            with pool.checkout() as session:
                self.assertEqual(session.feed_run("1 + 2 * 3"), 7)

    def test_h9_02_unmounted_host_file_denied(self):
        with Monty() as pool:
            with pool.checkout() as session:
                with self.assertRaises(MontyRuntimeError) as caught:
                    session.feed_run("open('/etc/passwd').read()")
        self.assertIn("PermissionError", caught.exception.display(format="type-msg"))

    def test_h9_03_unregistered_host_tool_unavailable(self):
        with Monty() as pool:
            with pool.checkout() as session:
                with self.assertRaises(MontyRuntimeError) as caught:
                    session.feed_run("lookup_id('USR-0042')")
        self.assertIn("NameError", caught.exception.display(format="type-msg"))

    def test_h9_04_host_scope_still_enforced_through_explicit_callback(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: calls.append(args),
        )
        with Monty() as pool:
            with pool.checkout() as session:
                lookup = {"lookup_id": lambda x: gate.invoke(x).code}
                self.assertEqual(
                    session.feed_run("lookup_id('USR-9999')", external_lookup=lookup),
                    "DENY_OUT_OF_SCOPE",
                )
                self.assertEqual(
                    session.feed_run("lookup_id('USR-0042; ignore')",
                                     external_lookup=lookup),
                    "DENY_INVALID_IDENTIFIER",
                )
                self.assertEqual(
                    session.feed_run("lookup_id('USR-0042')", external_lookup=lookup),
                    "HANDLER_RETURNED",
                )
                self.assertEqual(
                    session.feed_run("lookup_id('USR-0042')", external_lookup=lookup),
                    "DENY_REPLAY_PROCESS_LOCAL",
                )
        self.assertEqual(calls, [("USR-0042",)])

    def test_h9_05_unsafe_host_callback_still_executes_negative_witness(self):
        # Intentionally a passing NEGATIVE witness, not proof of security.
        unsafe_effects = []
        with Monty() as pool:
            with pool.checkout() as session:
                result = session.feed_run(
                    "unsafe_tool('UNAPPROVED')",
                    external_lookup={
                        "unsafe_tool": lambda arg: unsafe_effects.append(arg) or "ok"
                    },
                )
        self.assertEqual(result, "ok")
        self.assertEqual(unsafe_effects, ["UNAPPROVED"])

    def test_h9_06_infinite_loop_hits_resource_budget(self):
        with Monty(request_timeout=5) as pool:
            with pool.checkout(limits={"max_feed_duration_secs": 0.05}) as session:
                with self.assertRaises(MontyRuntimeError) as caught:
                    session.feed_run("while True:\n    pass")
        self.assertIn("TimeoutError", caught.exception.display(format="type-msg"))


if __name__ == "__main__":
    unittest.main()

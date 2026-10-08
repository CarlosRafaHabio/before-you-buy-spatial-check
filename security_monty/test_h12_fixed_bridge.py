"""H12 — new, minimal Monty broker tests; no real tools, secrets or network.

Negative witnesses are intentionally green when TCB gaps are reproduced.
These tests are NOT independent assessments or sandbox escape attempts.
"""
import time
import unittest

from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup
from prototypes.camel_selective_v0.monty_host_bridge_v0 import MontyHostBridgeV0


def make_bridge(*, approved="USR-0042", handler=None, max_calls=4,
                wall_budget_secs=.5):
    effects = []
    callback = handler if handler is not None else lambda args: effects.append(args)
    gate = HostScopedUserLookup(approved_user_id=approved, handler=callback)
    return MontyHostBridgeV0(gate, max_calls=max_calls,
                             wall_budget_secs=wall_budget_secs), effects


class H12FixedMontyHostBridge(unittest.TestCase):
    def test_H12_01_benign_exact_preapproval_one_attempt(self):
        bridge, effects = make_bridge()
        outcome = bridge.run("lookup_user('USR-0042')")
        self.assertEqual((outcome.status, outcome.value),
                         ("COMPLETED", "HANDLER_RETURNED"))
        self.assertEqual((outcome.callback_calls, outcome.effect_attempts), (1, 1))
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_02_injection_and_wrong_scope_do_not_consume(self):
        bridge, effects = make_bridge()
        code = ("[lookup_user('USR-0042; restore all'), "
                "lookup_user('USR-0043'), "
                "lookup_user('USR-0042')]")
        result = bridge.run(code)
        self.assertEqual(result.value,
                         ["DENY_INVALID_IDENTIFIER", "DENY_OUT_OF_SCOPE",
                          "HANDLER_RETURNED"])
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_03_no_guest_supplied_operation_or_metadata(self):
        bridge, effects = make_bridge()
        result = bridge.run(
            "[lookup_user({'operation':'host.restore', 'user_id':'USR-0042'}),"
            "lookup_user('USR-0042', trusted=True),"
            "lookup_user(user_id='USR-0042'),"
            "lookup_user('USR-0042', 'extra')]"
        )
        self.assertEqual(result.value, ["DENY_INVALID_CALL_SHAPE"] * 4)
        self.assertEqual(effects, [])

    def test_H12_04_quota_bounds_repeat_calls_inside_one_guest_execution(self):
        bridge, effects = make_bridge(max_calls=2)
        outcome = bridge.run("[lookup_user('USR-0042') for _ in range(7)]")
        self.assertEqual(outcome.value,
                         ["HANDLER_RETURNED", "DENY_REPLAY_PROCESS_LOCAL"]
                         + ["DENY_HOST_CALL_QUOTA"] * 5)
        self.assertEqual(outcome.callback_calls, 2)
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_05_fresh_sessions_prevent_old_guest_function_reference(self):
        bridge, effects = make_bridge()
        result1 = bridge.run("cached = lookup_user\n'ok'")
        result2 = bridge.run("cached('USR-0042')")
        self.assertEqual(result1.status, "COMPLETED")
        self.assertEqual(result2.status, "GUEST_EXECUTION_REJECTED")
        self.assertEqual(effects, [])

    def test_H12_06_unregistered_privileged_names_not_exported(self):
        bridge, effects = make_bridge()
        for name in ("external_authority", "host_restore",
                     "fetch", "open", "unsafe_tool"):
            with self.subTest(name=name):
                outcome = bridge.run(name + "('USR-0042')")
                self.assertEqual(outcome.status, "GUEST_EXECUTION_REJECTED")
        self.assertEqual(effects, [])

    def test_H12_07_exception_details_are_not_returned_to_guest(self):
        synthetic_secret = "SYNTHETIC_PRIVATE_TRACE"
        def failed(_):
            raise RuntimeError(synthetic_secret)
        bridge, _ = make_bridge(handler=failed)
        result = bridge.run(
            "try:\n"
            "    code = lookup_user('USR-0042')\n"
            "except Exception as exc:\n"
            "    code = str(exc)\n"
            "code"
        )
        self.assertEqual(result.value, "HANDLER_OUTCOME_UNKNOWN")
        self.assertNotIn(synthetic_secret, repr(result))
        self.assertEqual(result.effect_attempts, 1)

    def test_H12_08_invalid_large_and_malformed_sources_denied(self):
        bridge, effects = make_bridge()
        for raw in ("", " " * 5000, "\ud800", 4, None, b"lookup_user('USR-0042')"):
            with self.subTest(value=repr(raw)[:20]):
                outcome = bridge.run(raw)
                self.assertEqual(outcome.status, "DENY_INVALID_PROGRAM")
        self.assertEqual(effects, [])

    def test_H12_09_same_gate_used_across_fresh_feeds_keeps_one_shot(self):
        bridge, effects = make_bridge()
        results = [bridge.run("lookup_user('USR-0042')") for _ in range(4)]
        self.assertEqual([x.value for x in results],
                         ["HANDLER_RETURNED"] + ["DENY_REPLAY_PROCESS_LOCAL"] * 3)
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_10_resource_infinite_loop_denied_without_effect(self):
        bridge, effects = make_bridge()
        result = bridge.run("while True:\n    pass")
        self.assertEqual(result.status, "GUEST_EXECUTION_REJECTED")
        self.assertEqual(effects, [])

    def test_H12_11_host_callback_delay_is_not_preempted_negative_witness(self):
        # NEGATIVE: the host Python callback still runs to completion despite
        # a smaller wall budget. We only avoid claiming a successful result.
        effects = []
        def slow(args):
            time.sleep(.08)
            effects.append(args)
        bridge, _ = make_bridge(handler=slow, wall_budget_secs=.03)
        out = bridge.run("lookup_user('USR-0042')")
        self.assertEqual(out.status, "HOST_WALL_BUDGET_EXCEEDED_UNKNOWN")
        self.assertEqual(out.effect_attempts, 1)
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_12_wrong_scope_does_not_create_authority_from_valid_syntax(self):
        bridge, effects = make_bridge()
        self.assertEqual(bridge.run("lookup_user('USR-9000')").value,
                         "DENY_OUT_OF_SCOPE")
        self.assertEqual(effects, [])

    def test_H12_13_even_fixed_bridge_exposes_approved_operation_negative(self):
        # NEGATIVE: if host exposes action, guest can spontaneously invoke it.
        bridge, effects = make_bridge()
        out = bridge.run("lookup_user('USR-' + '0042')")
        self.assertEqual(out.value, "HANDLER_RETURNED")
        self.assertEqual(effects, [("USR-0042",)])

    def test_H12_14_invalid_host_configuration_rejected(self):
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda _: None)
        for bad in (0, True, 999):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    MontyHostBridgeV0(gate, max_calls=bad)
        with self.assertRaises(ValueError):
            MontyHostBridgeV0(gate, wall_budget_secs=0)


if __name__ == "__main__":
    unittest.main()

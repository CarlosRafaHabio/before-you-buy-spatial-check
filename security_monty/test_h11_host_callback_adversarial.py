"""H11: fresh (non-G3) Monty v1.1.0 host callback adversarial cases.

All negative witness assertions demonstrate UNSAFE TCB behavior, not
mitigation; no actual credentials, network, file effects or live tools.
A passing suite is a narrow verified semantics record, not security proof.
"""
import time
import unittest

from pydantic_monty import Monty, MontyRuntimeError

from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup


def _restricted_lookup(gate):
    """One explicit capability: no guest-supplied operation/kwargs/objects.

    This handles shape and sanitizes all errors before returning a status
    string to Monty, but cannot authenticate host bootstrap or constrain
    arbitrary Python actions by the callback inside the trusted process.
    """
    def use(*args, **kwargs):
        if kwargs or len(args) != 1 or type(args[0]) is not str:
            return "DENY_INVALID_CALL_SHAPE"
        try:
            return gate.invoke(args[0]).code
        except Exception:
            return "DENY_INTERNAL_ERROR"
    return use


class H11HostCallbackAdversarial(unittest.TestCase):
    def test_H11_01_host_exception_string_enters_untrusted_guest(self):
        # NEGATIVE evidence: Monty documents catchable host exceptions.
        secret = "SYNTHETIC_HOST_PRIVATE_MESSAGE"
        def leaky(_):
            raise ValueError(secret)
        with Monty() as pool:
            with pool.checkout() as session:
                seen = session.feed_run(
                    "try:\n    tool('anything')\nexcept ValueError as e:\n    value = str(e)\nvalue",
                    external_lookup={"tool": leaky},
                )
        self.assertEqual(seen, secret)

    def test_H11_02_unsafe_host_function_return_leaks_synthetic_secret(self):
        secret = "SYNTHETIC_HOST_ONLY_VALUE"
        with Monty() as pool:
            with pool.checkout() as session:
                seen = session.feed_run(
                    "tool('dummy')",
                    external_lookup={"tool": lambda _: secret},
                )
        self.assertEqual(seen, secret)  # NEGATIVE TCB witness

    def test_H11_03_host_object_and_kwarg_attempts_do_not_consume_scope(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: calls.append(args)
        )
        safe = _restricted_lookup(gate)
        script = (
            "results = ["
            "tool(user_id='USR-0042'),"
            "tool('USR-0042', approved=True),"
            "tool({'value':'USR-0042'}),"
            "tool(['USR-0042']),"
            "tool(True),"
            "tool(42),"
            "tool(None),"
            "tool('USR-0042','USR-0042')"
            "]\nresults"
        )
        with Monty() as pool:
            with pool.checkout() as session:
                seen = session.feed_run(script, external_lookup={"tool": safe})
                self.assertEqual(seen, ["DENY_INVALID_CALL_SHAPE"] * 8)
                self.assertEqual(calls, [])
                result = session.feed_run(
                    "tool('USR-0042')", external_lookup={"tool": safe}
                )
                self.assertEqual(result, "HANDLER_RETURNED")
        self.assertEqual(calls, [("USR-0042",)])

    def test_H11_04_unexpected_callback_exception_is_sanitized(self):
        synthetic = "SYNTHETIC_INTERNAL_STACK_SECRET"
        def unsafe_callback(_):
            raise RuntimeError(synthetic)
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=unsafe_callback
        )
        with Monty() as pool:
            with pool.checkout() as session:
                first = session.feed_run(
                    "tool('USR-0042')",
                    external_lookup={"tool": _restricted_lookup(gate)},
                )
                second = session.feed_run(
                    "tool('USR-0042')",
                    external_lookup={"tool": _restricted_lookup(gate)},
                )
        self.assertEqual(first, "HANDLER_OUTCOME_UNKNOWN")
        self.assertEqual(second, "DENY_REPLAY_PROCESS_LOCAL")
        self.assertNotIn(synthetic, first + second)

    def test_H11_05_cached_guest_host_function_name_rebinds(self):
        # Negative capability hazard if host reassigns same alias to a more
        # privileged tool. A guest-retained function proxy is resolved by
        # NAME on each feed, per Monty upstream documentation.
        calls = []
        with Monty() as pool:
            with pool.checkout() as session:
                session.feed_run(
                    "cached = host_action\n'cached'",
                    external_lookup={"host_action": lambda x: calls.append(("low",x))},
                )
                result = session.feed_run(
                    "cached('SYNTHETIC')",
                    external_lookup={"host_action": lambda x: calls.append(("high",x)) or "ok"},
                )
        self.assertEqual(result, "ok")
        self.assertEqual(calls, [("high", "SYNTHETIC")])  # NEGATIVE witness

    def test_H11_06_omitted_host_action_does_not_keep_prior_callback(self):
        # Closing explicit lookup must not leave a live callable in guest.
        with Monty() as pool:
            with pool.checkout() as session:
                session.feed_run(
                    "cached = host_action\n'cached'",
                    external_lookup={"host_action": lambda x: "SECRET"},
                )
                with self.assertRaises(MontyRuntimeError) as caught:
                    session.feed_run("cached('anything')", external_lookup={})
        self.assertIn("NameError", caught.exception.display(format="type-msg"))

    def test_H11_07_interpreter_timeout_does_not_bound_host_callback_walltime(self):
        # NEGATIVE: deliberately delay a synthetic host callback very briefly.
        # The worker's bytecode clock is paused during host round trips.
        def slow(_):
            time.sleep(0.075)
            return "ok"
        with Monty(request_timeout=5) as pool:
            with pool.checkout(limits={"max_feed_duration_secs": 0.025}) as session:
                before = time.monotonic()
                result = session.feed_run(
                    "tool('data')", external_lookup={"tool": slow}
                )
                elapsed = time.monotonic() - before
        self.assertEqual(result, "ok")
        self.assertGreater(elapsed, 0.06)

    def test_H11_08_guest_knowing_id_can_preconsume_if_host_exposes_gate(self):
        # Another negative TCB witness: knowledge of a host-approved string
        # and access to the callback can trigger it even without model consent.
        received = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: received.append(args)
        )
        with Monty() as pool:
            with pool.checkout() as session:
                code = "tool('USR-' + '0042')"
                first = session.feed_run(
                    code, external_lookup={"tool": _restricted_lookup(gate)}
                )
        self.assertEqual(first, "HANDLER_RETURNED")
        self.assertEqual(received, [("USR-0042",)])

    def test_H11_09_call_shape_validation_rejects_spoofed_metadata(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: calls.append(args)
        )
        with Monty() as pool:
            with pool.checkout() as session:
                code = ("tool({'user_id':'USR-0042','trusted':True,"
                        "'operation':'host.confirm_evidence'})")
                self.assertEqual(
                    session.feed_run(code, external_lookup={
                        "tool": _restricted_lookup(gate)
                    }), "DENY_INVALID_CALL_SHAPE"
                )
        self.assertEqual(calls, [])

    def test_H11_10_scope_permission_remains_one_shot_across_monty_feeds(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=lambda args: calls.append(args)
        )
        with Monty() as pool:
            with pool.checkout() as session:
                bridge = _restricted_lookup(gate)
                codes = [
                    session.feed_run("tool('USR-0042')",
                                     external_lookup={"tool": bridge})
                    for _ in range(5)
                ]
        self.assertEqual(codes, ["HANDLER_RETURNED"] +
                         ["DENY_REPLAY_PROCESS_LOCAL"] * 4)
        self.assertEqual(calls, [("USR-0042",)])


if __name__ == "__main__":
    unittest.main()

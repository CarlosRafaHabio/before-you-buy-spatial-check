"""G2-a: synthetic host-owned operation binding; no live side effects."""
import unittest

from prototypes.camel_selective_v0.flow_guard import (
    FlowInputError, external_text, host_text,
)
from prototypes.camel_selective_v0.host_dispatch import (
    BoundHostDispatcher, BoundTool,
)


class BoundHostDispatchG2aTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.dispatch = BoundHostDispatcher([
            BoundTool("tool.send", "partner", lambda args: self.calls.append(args)),
            BoundTool("tool.save", "host", lambda args: self.calls.append(args)),
        ])
        self.good = host_text("reviewed", origin="host")
        self.bad = external_text("model-controls-this", origin="model")

    def test_G2_01_exact_checked_argument_reaches_bound_handler(self):
        result = self.dispatch.invoke("tool.send", arguments=(self.good,),
                                      control_dependencies=())
        self.assertEqual((result.attempted, result.code), (True, "HANDLER_RETURNED"))
        self.assertEqual(self.calls, [("reviewed",)])

    def test_G2_02_untrusted_argument_cannot_reach_bound_handler(self):
        result = self.dispatch.invoke("tool.send", arguments=(self.bad,),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNTRUSTED_INFLUENCE")
        self.assertFalse(result.attempted)
        self.assertEqual(self.calls, [])

    def test_G2_03_missing_control_context_denies_effect(self):
        result = self.dispatch.invoke("tool.save", arguments=(self.good,))
        self.assertEqual(result.code, "DENY_MISSING_CONTROL_CONTEXT")
        self.assertEqual(self.calls, [])

    def test_G2_04_declared_untrusted_control_denies_clean_argument(self):
        result = self.dispatch.invoke("tool.save", arguments=(self.good,),
                                      control_dependencies=(self.bad,))
        self.assertEqual(result.code, "DENY_UNTRUSTED_INFLUENCE")
        self.assertEqual(self.calls, [])

    def test_G2_05_explicit_but_false_empty_control_context_is_not_detectable(self):
        # KNOWN FAILURE: a host can lie about the dependencies with ().
        result = self.dispatch.invoke("tool.save", arguments=(self.good,),
                                      control_dependencies=())
        self.assertTrue(result.attempted)
        self.assertEqual(self.calls, [("reviewed",)])

    def test_G2_06_host_relabeling_external_bytes_remains_a_known_bypass(self):
        mislabeled = host_text(self.bad.text, origin="host")
        result = self.dispatch.invoke("tool.send", arguments=(mislabeled,),
                                      control_dependencies=())
        self.assertEqual(result.code, "HANDLER_RETURNED")  # KNOWN FAILURE.
        self.assertEqual(self.calls, [("model-controls-this",)])

    def test_G2_07_private_bytes_cannot_go_to_wrong_registered_destination(self):
        secret = host_text("synthetic-secret", origin="secret",
                           readers=frozenset({"host"}))
        result = self.dispatch.invoke("tool.send", arguments=(secret,),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_READER")
        self.assertEqual(self.calls, [])

    def test_G2_08_unknown_tool_is_never_invoked(self):
        result = self.dispatch.invoke("tool.other", arguments=(self.good,),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNKNOWN_OPERATION")
        self.assertEqual(self.calls, [])

    def test_G2_09_host_privileged_alias_is_rejected_on_registration(self):
        with self.assertRaises(FlowInputError):
            BoundTool("host.confirm_evidence.v2", "host", lambda x: None)
        with self.assertRaises(FlowInputError):
            BoundTool("external_authority.restore.v2", "host", lambda x: None)

    def test_G2_10_no_agent_provided_pure_classification_exists(self):
        # All registered operations are external in this dispatcher.
        result = self.dispatch.invoke("tool.send", arguments=(self.bad,),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNTRUSTED_INFLUENCE")

    def test_G2_11_zero_args_denied_in_this_conservative_gateway(self):
        result = self.dispatch.invoke("tool.send", arguments=(),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_EMPTY_ARGUMENTS")
        self.assertEqual(self.calls, [])

    def test_G2_12_raw_value_is_not_an_argument(self):
        result = self.dispatch.invoke("tool.send", arguments=("raw",),
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNTRACKED_INPUT")
        self.assertEqual(self.calls, [])

    def test_G2_13_mutable_argument_containers_rejected(self):
        result = self.dispatch.invoke("tool.send", arguments=[self.good],
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNTRACKED_INPUT")
        self.assertEqual(self.calls, [])

    def test_G2_14_duplicate_tool_registration_rejected(self):
        with self.assertRaises(FlowInputError):
            BoundHostDispatcher((
                BoundTool("tool.send", "partner", lambda x: None),
                BoundTool("tool.send", "host", lambda x: None),
            ))

    def test_G2_15_callback_raises_one_attempt_no_retry_no_success_claim(self):
        attempts = []
        def handler(args):
            attempts.append(args)
            raise RuntimeError("synthetic failure after possible effect")
        dispatcher = BoundHostDispatcher((
            BoundTool("tool.send", "partner", handler),
        ))
        outcome = dispatcher.invoke("tool.send", arguments=(self.good,),
                                    control_dependencies=())
        self.assertEqual((outcome.attempted, outcome.code),
                         (True, "HANDLER_OUTCOME_UNKNOWN"))
        self.assertEqual(attempts, [("reviewed",)])

    def test_G2_16_synthetic_max_arguments_bounded(self):
        result = self.dispatch.invoke("tool.send", arguments=(self.good,) * 33,
                                      control_dependencies=())
        self.assertEqual(result.code, "DENY_UNTRACKED_INPUT")
        self.assertEqual(self.calls, [])

    def test_G2_17_untracked_control_dependency_denied(self):
        result = self.dispatch.invoke("tool.send", arguments=(self.good,),
                                      control_dependencies=("unknown",))
        self.assertEqual(result.code, "DENY_UNTRACKED_INPUT")
        self.assertEqual(self.calls, [])

    def test_G2_18_handler_cannot_be_registered_as_non_callable(self):
        with self.assertRaises(FlowInputError):
            BoundTool("tool.send", "partner", "not callable")


if __name__ == "__main__":
    unittest.main()

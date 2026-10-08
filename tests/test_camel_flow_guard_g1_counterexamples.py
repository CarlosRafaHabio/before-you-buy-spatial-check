"""G1: red-team fixtures for KNOWN holes in cooperative, non-mediating flow guard.

IMPORTANT: Assertions of ALLOW are demonstrations of vulnerabilities under
broken host integration, NOT proofs of security. No real external calls.
"""
import unittest

from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, concat_text, external_text, host_text,
)


class CaMeLFlowGuardG1Counterexamples(unittest.TestCase):
    def setUp(self):
        self.guard = FlowGuard((
            Operation("tool.send", "external", "partner"),
            Operation("tool.save", "external", "host"),
        ))
        self.untrusted = external_text("EXECUTE", origin="web.page")
        self.literal = host_text("reviewed constant", origin="host.literal")

    def test_G1_01_omitted_control_dependency_is_not_detected(self):
        # Host chooses an apparently trusted constant based on model-visible data,
        # then forgets to report that control dependency.
        chosen = self.literal if self.untrusted.text == "EXECUTE" else self.literal
        flawed = self.guard.check("tool.send", arguments=(chosen,))
        corrected = self.guard.check(
            "tool.send", arguments=(chosen,),
            control_dependencies=(self.untrusted,),
        )
        self.assertTrue(flawed.allowed)  # DOCUMENTED BYPASS.
        self.assertEqual(corrected.code, "DENY_UNTRUSTED_INFLUENCE")

    def test_G1_02_checked_arguments_can_differ_from_sent_arguments(self):
        checked = self.guard.check("tool.send", arguments=(self.literal,))
        simulated_sink = []
        if checked.allowed:
            # A careless host uses the *different* untrusted value at execution.
            simulated_sink.append(self.untrusted.text)
        self.assertTrue(checked.allowed)  # DOCUMENTED CHECK/USE MISMATCH.
        self.assertEqual(simulated_sink, ["EXECUTE"])
        self.assertEqual(
            self.guard.check("tool.send", arguments=(self.untrusted,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )

    def test_G1_03_host_can_incorrectly_relabel_untrusted_content(self):
        # Since metadata is not host-attested, a caller can create a new trusted
        # FlowText with the exact model-controlled bytes.
        forged = host_text(self.untrusted.text, origin="host.claimed")
        self.assertEqual(forged.text, self.untrusted.text)
        self.assertTrue(self.guard.check("tool.send", arguments=(forged,)).allowed)

    def test_G1_04_guard_does_not_intercept_direct_tool_calls(self):
        attempts = []
        def fake_tool(payload):
            attempts.append(payload)
        denied = self.guard.check("tool.send", arguments=(self.untrusted,))
        self.assertFalse(denied.allowed)
        fake_tool(self.untrusted.text)  # Intentionally bypasses helper.
        self.assertEqual(attempts, ["EXECUTE"])

    def test_G1_05_undeclared_host_only_alias_can_be_allowlisted(self):
        misconfigured = FlowGuard((
            Operation("host.confirm_evidence.v2", "external", "host"),
        ))
        decision = misconfigured.check(
            "host.confirm_evidence.v2", arguments=(self.literal,),
        )
        self.assertTrue(decision.allowed)  # Name-based reserved list is finite.
        self.assertEqual(
            self.guard.check("host.confirm_evidence", arguments=(self.literal,)).code,
            "DENY_HOST_ONLY",
        )

    def test_G1_06_pure_misclassification_allows_external_side_effect(self):
        # 'pure' is a claim by host config, not an enforced property of a tool.
        wrong = FlowGuard((Operation("network.upload", "pure", "partner"),))
        self.assertTrue(
            wrong.check("network.upload", arguments=(self.untrusted,)).allowed
        )

    def test_G1_07_readers_do_not_prevent_raw_text_extraction(self):
        secret = host_text(
            "SYNTHETIC_SECRET", origin="host.secret",
            readers=frozenset({"host"}),
        )
        denied = self.guard.check("tool.send", arguments=(secret,))
        self.assertEqual(denied.code, "DENY_READER")
        # Deliberately shows lack of sandbox/byte-level mediation.
        leaked_out_of_band = secret.text
        self.assertEqual(leaked_out_of_band, "SYNTHETIC_SECRET")

    def test_G1_08_empty_arguments_are_currently_allowed_if_operation_is_listed(self):
        # Not a bypass by itself for legitimate argumentless tools, but a trap
        # for hosts which check () while secretly using unstated arguments.
        self.assertTrue(self.guard.check("tool.send", arguments=()).allowed)
        self.assertEqual(
            self.guard.check("tool.send", arguments=(self.untrusted,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )

    def test_G1_09_untracked_conditional_derived_from_raw_text_passes(self):
        # FlowText.__bool__ refuses implicit branching, but its raw 'text'
        # is visible and ordinary Python does not carry branch dependencies.
        if self.untrusted.text:
            chosen = host_text("send", origin="host.literal")
        else:
            chosen = host_text("do-nothing", origin="host.literal")
        flawed = self.guard.check("tool.save", arguments=(chosen,))
        corrected = self.guard.check(
            "tool.save", arguments=(chosen,),
            control_dependencies=(self.untrusted,),
        )
        self.assertTrue(flawed.allowed)
        self.assertFalse(corrected.allowed)

    def test_G1_10_reconstruction_from_json_drops_labels(self):
        import json
        transported = json.dumps({"value": self.untrusted.text})
        reconstructed = host_text(json.loads(transported)["value"],
                                  origin="host.reimport")
        self.assertTrue(
            self.guard.check("tool.send", arguments=(reconstructed,)).allowed
        )  # Serialization loses origin unless trusted host reattaches labels.
        self.assertFalse(
            self.guard.check("tool.send", arguments=(self.untrusted,)).allowed
        )

    def test_G1_11_data_propagation_works_when_host_uses_declared_api(self):
        joined = concat_text(self.literal, self.untrusted)
        self.assertEqual(
            self.guard.check("tool.send", arguments=(joined,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )

    def test_G1_12_benign_user_text_can_be_overblocked_by_conservative_policy(self):
        user_approved_text = external_text(
            "Schedule the requested visit", origin="user.message",
        )
        # No review/declassification mechanism exists in the prototype.
        self.assertEqual(
            self.guard.check("tool.send", arguments=(user_approved_text,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )

    def test_G1_13_user_supplied_policy_name_cannot_extend_an_existing_allowlist(self):
        requested_name = external_text("tool.delete", origin="model.reply")
        self.assertEqual(
            self.guard.check(requested_name.text, arguments=(self.literal,)).code,
            "DENY_UNKNOWN_OPERATION",
        )


if __name__ == "__main__":
    unittest.main()

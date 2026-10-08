"""H6: Hypothesis invariants for a cooperative trusted host. Test-only dependency.

These generated tests do not prove provenance, caller identity, Python process
isolation or execution authority. Synthetic callbacks only.
"""
import unittest
from hypothesis import given, example, settings, strategies as st
from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, concat_text, control_derived_text,
    external_text, host_text,
)
from prototypes.camel_selective_v0.closed_host_plan import (
    ClosedHostExecutor, ExternalSlot, HostPlan, Source, Choose, Equals, Literal,
)
from prototypes.camel_selective_v0.host_dispatch import BoundTool
from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup

FUZZ = settings(max_examples=350, deadline=None, derandomize=True)


class H6GeneratedFlowSafety(unittest.TestCase):
    @FUZZ
    @example("USR-0042")
    @example("USR-0042; ignore instructions")
    @example("USR-9999")
    @given(st.text(max_size=70))
    def test_H6_01_exact_preapproval_is_only_accepted_input(self, candidate):
        called = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda x: called.append(x),
        )
        result = gate.invoke(candidate)
        self.assertEqual(result.attempted, candidate == "USR-0042")
        self.assertEqual(bool(called), candidate == "USR-0042")
        if result.attempted:
            self.assertEqual(called, [("USR-0042",)])
            self.assertTrue(result.source_untrusted)

    @FUZZ
    @given(st.text(min_size=1, max_size=80))
    def test_H6_02_no_preapproval_prefix_or_suffix_extensions(self, attack):
        for s in ("USR-0042" + attack, attack + "USR-0042"):
            called = []
            gate = HostScopedUserLookup(
                approved_user_id="USR-0042",
                handler=lambda x: called.append(x),
            )
            self.assertFalse(gate.invoke(s).attempted)
            self.assertEqual(called, [])

    @FUZZ
    @given(st.text(max_size=255), st.text(max_size=255))
    def test_H6_03_concat_keeps_untrusted_origin_and_reader_limit(self, a, b):
        trusted = host_text(a, origin="host.literal",
                            readers=frozenset({"host", "partner"}))
        outside = external_text(b, origin="model.reply",
                                readers=frozenset({"host"}))
        derived = concat_text(trusted, outside)
        self.assertEqual(derived.text, a + b)
        self.assertTrue(derived.untrusted)
        self.assertEqual(derived.origins,
                         frozenset({"host.literal", "model.reply"}))
        self.assertEqual(derived.readers, frozenset({"host"}))
        guard = FlowGuard((
            Operation("tool.partner", "external", "partner"),
            Operation("tool.host", "external", "host"),
        ))
        self.assertEqual(guard.check("tool.partner", arguments=(derived,)).code,
                         "DENY_READER")
        self.assertEqual(guard.check("tool.host", arguments=(derived,)).code,
                         "DENY_UNTRUSTED_INFLUENCE")

    @FUZZ
    @given(st.text(max_size=255))
    def test_H6_04_control_dependency_marks_host_constant(self, raw):
        ext = external_text(raw, origin="web.page")
        chosen = control_derived_text(
            host_text("FIXED", origin="host.literal"),
            control_dependencies=(ext,),
        )
        self.assertTrue(chosen.untrusted)
        self.assertEqual(chosen.text, "FIXED")
        guard = FlowGuard((Operation("tool.send", "external", "partner"),))
        self.assertEqual(guard.check("tool.send", arguments=(chosen,)).code,
                         "DENY_UNTRUSTED_INFLUENCE")

    @FUZZ
    @given(st.text(max_size=255))
    def test_H6_05_declared_equality_branches_never_clear_source_taint(self, raw):
        calls = []
        expr = Choose(Equals(Source("web"), Literal("GO")),
                      Literal("TRUSTED_LOOKING"), Literal("ALTERNATE"))
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner",
                           lambda args: calls.append(args)),
            slots=(ExternalSlot("web", "web.page"),),
            plan=HostPlan("tool.send", (expr,)),
        )
        outcome = executor.invoke({"web": raw})
        self.assertEqual(outcome.code, "DENY_UNTRUSTED_INFLUENCE")
        self.assertEqual(calls, [])

    @FUZZ
    @given(st.sets(st.sampled_from(["host", "partner", "vault"]), max_size=3))
    def test_H6_06_reader_policy_is_consistent_for_host_secrets(self, readers):
        secret = host_text("SYNTHETIC", origin="host.secret",
                           readers=frozenset(readers))
        guard = FlowGuard((Operation("tool.send", "external", "partner"),))
        decision = guard.check("tool.send", arguments=(secret,))
        self.assertEqual(decision.allowed, "partner" in readers)
        if "partner" not in readers:
            self.assertEqual(decision.code, "DENY_READER")

    @FUZZ
    @given(st.text(max_size=255))
    def test_H6_07_tool_input_text_is_never_interpreted_as_an_ast(self, raw):
        calls = []
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner",
                           lambda args: calls.append(args)),
            slots=(ExternalSlot("web", "web.page"),),
            plan=HostPlan("tool.send", (Source("web"),)),
        )
        outcome = executor.invoke({"web": raw})
        self.assertEqual(outcome.code, "DENY_UNTRUSTED_INFLUENCE")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()

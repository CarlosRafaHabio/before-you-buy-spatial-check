"""G4 PRE-FIX exploit witnesses: failings in post-registration alias retention.

These tests deliberately assert INSECURE behavior. Green CI means the bugs are
reproducible; it does not mean they are mitigated. Replace with regression
expectations after patching (commit after this red-team baseline).
"""
import unittest

from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, external_text, host_text,
)
from prototypes.camel_selective_v0.host_dispatch import (
    BoundHostDispatcher, BoundTool,
)
from prototypes.camel_selective_v0.closed_host_plan import (
    ClosedHostExecutor, ExternalSlot, HostPlan, Literal, Source,
)


class PreFixRegistrationAliasingWitnesses(unittest.TestCase):
    def test_G4_A_operation_policy_can_change_after_registration(self):
        rule = Operation("tool.send", "external", "public")
        guard = FlowGuard((rule,))
        payload = external_text("ATTACKER_TEXT", origin="web")
        self.assertEqual(
            guard.check("tool.send", arguments=(payload,)).code,
            "DENY_UNTRUSTED_INFLUENCE",
        )
        object.__setattr__(rule, "kind", "pure")
        self.assertTrue(
            guard.check("tool.send", arguments=(payload,)).allowed,
        )  # PRE-FIX UNSAFE

    def test_G4_B_registered_handler_can_be_swapped_after_allowlist(self):
        authorized = []
        other_sink = []
        tool = BoundTool("tool.send", "host",
                         lambda args: authorized.append(args))
        dispatcher = BoundHostDispatcher((tool,))
        secret = host_text("SYNTHETIC_PRIVATE", origin="host.secret",
                           readers=frozenset({"host"}))
        object.__setattr__(tool, "handler",
                           lambda args: other_sink.append(args))
        result = dispatcher.invoke(
            "tool.send", arguments=(secret,), control_dependencies=(),
        )
        self.assertTrue(result.attempted)  # PRE-FIX WRONG CALLBACK
        self.assertEqual(authorized, [])
        self.assertEqual(other_sink, [("SYNTHETIC_PRIVATE",)])

    def test_G4_C_plan_literal_mutation_changes_prevalidated_command(self):
        calls = []
        literal = Literal("SAFE_AT_REGISTRATION")
        plan = HostPlan("tool.send", (literal,))
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner",
                           lambda args: calls.append(args)),
            slots=(), plan=plan,
        )
        object.__setattr__(literal, "value", "SWAPPED_AFTER_VALIDATION")
        result = executor.invoke({})
        self.assertTrue(result.attempted)
        self.assertEqual(calls, [("SWAPPED_AFTER_VALIDATION",)])  # PRE-FIX

    def test_G4_D_source_mutation_can_raise_unhandled_key_error(self):
        source = Source("page")
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner", lambda args: None),
            slots=(ExternalSlot("page", "web.page"),),
            plan=HostPlan("tool.send", (source,)),
        )
        object.__setattr__(source, "name", "missing")
        with self.assertRaises(KeyError):  # PRE-FIX UNHANDLED ERROR
            executor.invoke({"page": "ignored"})


if __name__ == "__main__":
    unittest.main()

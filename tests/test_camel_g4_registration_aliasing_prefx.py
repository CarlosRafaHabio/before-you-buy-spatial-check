"""G4 post-fix regression of four PRE-FIX aliasing vulnerabilities.

The previous, red-team baseline on commit 72abf2ec7c52ea554fcfa2f99491c8c974dda61c
demonstrated these issues by intentionally asserting insecure behavior.
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


class G4RegisteredObjectSnapshots(unittest.TestCase):
    def test_G4_A_operation_kind_mutation_no_longer_flips_policy(self):
        original = Operation("tool.send", "external", "public")
        guard = FlowGuard((original,))
        payload = external_text("ATTACKER_TEXT", origin="web")
        object.__setattr__(original, "kind", "pure")
        decision = guard.check("tool.send", arguments=(payload,))
        self.assertEqual(decision.code, "DENY_UNTRUSTED_INFLUENCE")

    def test_G4_B_substituted_callback_no_longer_receives_allowed_bytes(self):
        authorized, unauthorized = [], []
        original = BoundTool("tool.send", "host",
                             lambda args: authorized.append(args))
        dispatcher = BoundHostDispatcher((original,))
        secret = host_text("SYNTHETIC_PRIVATE", origin="host.secret",
                           readers=frozenset({"host"}))
        object.__setattr__(
            original, "handler", lambda args: unauthorized.append(args),
        )
        result = dispatcher.invoke(
            "tool.send", arguments=(secret,), control_dependencies=(),
        )
        self.assertEqual(result.code, "HANDLER_RETURNED")
        self.assertEqual(authorized, [("SYNTHETIC_PRIVATE",)])
        self.assertEqual(unauthorized, [])

    def test_G4_C_post_registration_literal_mutation_is_ineffective(self):
        calls = []
        original = Literal("SAFE_AT_REGISTRATION")
        plan = HostPlan("tool.send", (original,))
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner",
                           lambda args: calls.append(args)),
            slots=(), plan=plan,
        )
        object.__setattr__(original, "value", "SWAPPED_AFTER_VALIDATION")
        result = executor.invoke({})
        self.assertEqual(result.code, "HANDLER_RETURNED")
        self.assertEqual(calls, [("SAFE_AT_REGISTRATION",)])

    def test_G4_D_post_registration_source_mutation_no_longer_raises(self):
        source = Source("page")
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner", lambda args: None),
            slots=(ExternalSlot("page", "web.page"),),
            plan=HostPlan("tool.send", (source,)),
        )
        object.__setattr__(source, "name", "missing")
        result = executor.invoke({"page": "ignored"})
        self.assertEqual(result.code, "DENY_UNTRUSTED_INFLUENCE")

    def test_G4_E_slot_reader_restrictions_cannot_be_downgraded(self):
        slot = ExternalSlot("page", "web.page", frozenset({"host"}))
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner", lambda args: None),
            slots=(slot,), plan=HostPlan("tool.send", (Source("page"),)),
        )
        object.__setattr__(slot, "readers", None)
        result = executor.invoke({"page": "SYNTHETIC_PRIVATE"})
        self.assertEqual(result.code, "DENY_READER")

    def test_G4_F_host_plan_arguments_cannot_change_after_binding(self):
        calls = []
        plan = HostPlan("tool.send", (Literal("REGISTERED"),))
        executor = ClosedHostExecutor(
            tool=BoundTool("tool.send", "partner",
                           lambda args: calls.append(args)),
            slots=(), plan=plan,
        )
        object.__setattr__(plan, "arguments", (Literal("REPLACED"),))
        result = executor.invoke({})
        self.assertEqual(result.code, "HANDLER_RETURNED")
        self.assertEqual(calls, [("REGISTERED",)])

    def test_G4_G_operation_destination_mutation_cannot_bypass_reader(self):
        op = Operation("tool.send", "external", "partner")
        guard = FlowGuard((op,))
        secret = host_text(
            "SYNTHETIC_PRIVATE", origin="host.secret",
            readers=frozenset({"host"}),
        )
        object.__setattr__(op, "destination", "host")
        self.assertEqual(
            guard.check("tool.send", arguments=(secret,)).code,
            "DENY_READER",
        )

    def test_G4_H_tool_destination_mutation_does_not_change_policy(self):
        tool = BoundTool("tool.send", "partner", lambda args: None)
        dispatcher = BoundHostDispatcher((tool,))
        secret = host_text(
            "SYNTHETIC_PRIVATE", origin="host.secret",
            readers=frozenset({"host"}),
        )
        object.__setattr__(tool, "destination", "host")
        self.assertEqual(
            dispatcher.invoke(
                "tool.send", arguments=(secret,),
                control_dependencies=(),
            ).code,
            "DENY_READER",
        )


if __name__ == "__main__":
    unittest.main()

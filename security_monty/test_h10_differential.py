"""H10: fixed G3 corpus, closed G2-b policy vs stock Monty v1.1.0.

Passing "naive" and "broken host" cases are explicitly NEGATIVE evidence.
No LLM, live credentials, provider effects, prod APIs or runtime promotion.
"""
import unittest

from pydantic_monty import Monty

from prototypes.camel_selective_v0.closed_host_plan import (
    Choose, ClosedHostExecutor, Equals, ExternalSlot,
    HostPlan, Join, Literal, Source,
)
from prototypes.camel_selective_v0.flow_guard import (
    FlowGuard, Operation, concat_text, control_derived_text,
    external_text, host_text,
)
from prototypes.camel_selective_v0.host_dispatch import BoundHostDispatcher, BoundTool
from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup
from tests.camel_g3_corpus_v0_1 import CASES


def _g2b_fixture(case, calls):
    """Use unaltered G3 policy semantics for all 21 frozen examples."""
    if case.mode == "literal":
        plan, slots, incoming = Literal(case.value), (), {}
    else:
        slots = (ExternalSlot("page", "web.page"),)
        incoming = {"page": case.value}
        if case.mode == "source":
            plan = Source("page")
        elif case.mode == "join":
            plan = Join((Literal("prefix: "), Source("page")))
        elif case.mode == "choose":
            plan = Choose(
                Equals(Source("page"), Literal("GO")),
                Literal("trusted-looking choice"),
                Literal("trusted-looking fallback"),
            )
        elif case.mode == "ambient_if":
            plan = Literal("trusted-looking host command")
        else:
            raise AssertionError("Unknown frozen G3 mode.")
    executor = ClosedHostExecutor(
        tool=BoundTool("tool.send", "partner", lambda args: calls.append(args)),
        slots=slots,
        plan=HostPlan("tool.send", (plan,)),
    )
    # Deliberate broken-TCB branch is outside the AST, just as in G3.
    if case.mode == "ambient_if":
        assert incoming["page"]
    return executor.invoke(incoming)


def _host_labeled_arg(case):
    """ATTENTION: the HOST provides these labels, Monty does NOT compute them."""
    if case.mode in ("literal", "ambient_if"):
        literal = (case.value if case.mode == "literal"
                   else "trusted-looking host command")
        return host_text(literal, origin="host.program")
    from_external = external_text(case.value, origin="web.page")
    if case.mode == "source":
        return from_external
    if case.mode == "join":
        return concat_text(host_text("prefix: ", origin="host.program"),
                           from_external)
    if case.mode == "choose":
        chosen = ("trusted-looking choice" if case.value == "GO"
                  else "trusted-looking fallback")
        return control_derived_text(
            host_text(chosen, origin="host.program"),
            control_dependencies=(from_external, host_text("GO", origin="host.program")),
        )
    raise AssertionError("Unknown frozen G3 mode.")


class H10MontyG2bDifferential(unittest.TestCase):
    def test_H10_01_existing_G3_reference_is_unchanged(self):
        self.assertEqual(len(CASES), 21)
        calls_by_category = {}
        for case in CASES:
            calls = []
            with self.subTest(case=case.ident):
                result = _g2b_fixture(case, calls)
                self.assertEqual(result.attempted, case.expected_attempt)
                self.assertEqual(bool(calls), case.expected_attempt)
                calls_by_category.setdefault(case.category, []).append(
                    result.attempted)
        self.assertEqual(sum(calls_by_category["hostile_input"]), 0)
        self.assertEqual(sum(calls_by_category["benign"]), 6)
        self.assertEqual(sum(calls_by_category["broken_tcb"]), 2)

    def test_H10_02_unmediated_Monty_calls_registered_effect_all_21_times(self):
        # NEGATIVE evidence: Monty VM isolation alone is NOT IFC/effect policy.
        received = []
        with Monty() as pool:
            with pool.checkout() as session:
                for case in CASES:
                    result = session.feed_run(
                        "tool_send(payload)",
                        inputs={"payload": case.value},
                        external_lookup={
                            "tool_send": lambda value: received.append(value) or "called"
                        },
                    )
                    self.assertEqual(result, "called")
        self.assertEqual(received, [x.value for x in CASES])
        self.assertEqual(len(received), 21)
        self.assertEqual(sum(x.category == "hostile_input" for x in CASES), 9)

    def test_H10_03_Monty_with_host_mediation_matches_G3_outcomes(self):
        # The only reason this matches G2-b is EXPLICIT trusted host labeling.
        outcome_pairs = []
        callbacks = []
        with Monty() as pool:
            with pool.checkout() as session:
                for case in CASES:
                    mediated_calls = []
                    dispatcher = BoundHostDispatcher((
                        BoundTool("tool.send", "partner",
                                  lambda args: mediated_calls.append(args)),
                    ))
                    expected_arg = _host_labeled_arg(case)
                    def mediated(value, *, _case=case, _expected=expected_arg,
                                 _dispatcher=dispatcher):
                        # Host-owned fixture already knows exact input/meaning;
                        # never interpret a model-supplied "trusted" flag.
                        if value != _case.value:
                            return "DENY_ARGUMENT_MISMATCH"
                        decision = _dispatcher.invoke(
                            "tool.send", arguments=(_expected,),
                            control_dependencies=(),
                        )
                        return decision.code
                    code = session.feed_run(
                        "tool_send(payload)",
                        inputs={"payload": case.value},
                        external_lookup={"tool_send": mediated},
                    )
                    attempted = bool(mediated_calls)
                    self.assertEqual(attempted, case.expected_attempt,
                                     case.ident)
                    self.assertEqual(
                        code, "HANDLER_RETURNED" if attempted
                        else "DENY_UNTRUSTED_INFLUENCE",
                        case.ident,
                    )
                    callbacks.append((case.category, attempted))
                    outcome_pairs.append((case.ident, attempted))
        self.assertEqual(len(outcome_pairs), 21)
        self.assertEqual(sum(b for _, b in callbacks), 8)

    def test_H10_04_guest_branch_taints_not_automatically_reported_to_host(self):
        # NEGATIVE witness: a guest Python branch derives a host-looking text,
        # yet the callback cannot deduce the control dependency from raw bytes.
        for raw in ("GO", "STOP"):
            with self.subTest(raw=raw):
                calls = []
                dispatcher = BoundHostDispatcher((
                    BoundTool("tool.send", "partner",
                              lambda args: calls.append(args)),
                ))
                def wrong_host_callback(text):
                    return dispatcher.invoke(
                        "tool.send",
                        arguments=(host_text(text, origin="host.program"),),
                        control_dependencies=(),
                    ).code
                code = (
                    "if payload == 'GO':\n"
                    "    chosen = 'trusted-looking choice'\n"
                    "else:\n"
                    "    chosen = 'trusted-looking fallback'\n"
                    "tool_send(chosen)"
                )
                with Monty() as pool:
                    with pool.checkout() as session:
                        result = session.feed_run(
                            code, inputs={"payload": raw},
                            external_lookup={"tool_send": wrong_host_callback},
                        )
                self.assertEqual(result, "HANDLER_RETURNED")
                self.assertEqual(len(calls), 1)  # unsafe host lost implicit flow
                safe = ClosedHostExecutor(
                    tool=BoundTool("tool.send", "partner",
                                   lambda args: self.fail("G2b should deny")),
                    slots=(ExternalSlot("page", "web.page"),),
                    plan=HostPlan("tool.send", (Choose(
                        Equals(Source("page"), Literal("GO")),
                        Literal("trusted-looking choice"),
                        Literal("trusted-looking fallback")),)),
                )
                self.assertEqual(
                    safe.invoke({"page": raw}).code, "DENY_UNTRUSTED_INFLUENCE"
                )

    def test_H10_05_guest_can_repeat_unsafe_callbacks_without_host_quota(self):
        # NEGATIVE witness: the sandbox does not enforce effect idempotency.
        unguarded = []
        with Monty() as pool:
            with pool.checkout() as session:
                session.feed_run(
                    "for _ in range(4):\n    send('USR-0042')",
                    external_lookup={
                        "send": lambda user: unguarded.append(user) or "ok"
                    },
                )
        self.assertEqual(unguarded, ["USR-0042"] * 4)

    def test_H10_06_one_shot_policy_still_prevents_duplicate_host_effects(self):
        calls = []
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042",
            handler=lambda args: calls.append(args),
        )
        results = []
        def guarded(user):
            code = gate.invoke(user).code
            results.append(code)
            return code
        with Monty() as pool:
            with pool.checkout() as session:
                session.feed_run(
                    "for _ in range(4):\n    send('USR-0042')",
                    external_lookup={"send": guarded},
                )
        self.assertEqual(results,
                         ["HANDLER_RETURNED"] + ["DENY_REPLAY_PROCESS_LOCAL"] * 3)
        self.assertEqual(calls, [("USR-0042",)])


if __name__ == "__main__":
    unittest.main()

"""G3 offline paired naive/guarded fixed corpus; no actual LLM or remote tools."""
import unittest

from prototypes.camel_selective_v0.closed_host_plan import (
    Choose, ClosedHostExecutor, Equals, ExternalSlot,
    HostPlan, Join, Literal, Source,
)
from prototypes.camel_selective_v0.flow_guard import FlowInputError
from prototypes.camel_selective_v0.host_dispatch import BoundTool
from tests.camel_g3_corpus_v0_1 import CASES


class DifferentialCorpusTests(unittest.TestCase):
    def test_G3_01_corpus_taxonomy_and_expected_total_are_frozen(self):
        self.assertEqual(len(CASES), 21)
        self.assertEqual(len({c.ident for c in CASES}), len(CASES))
        counts = {label: sum(c.category == label for c in CASES)
                  for label in ("hostile_input", "benign", "broken_tcb")}
        self.assertEqual(counts, {"hostile_input": 9, "benign": 10,
                                  "broken_tcb": 2})
        self.assertEqual(
            sum(c.category == "benign" and not c.expected_attempt
                for c in CASES), 4,
        )

    def test_G3_02_paired_naive_and_closed_host_outcomes(self):
        # Naive baseline: it dispatches once per request with no policy check.
        # This comparator does NOT simulate a full LLM agent.
        outcomes = {"hostile_input": [], "benign": [], "broken_tcb": []}
        for case in CASES:
            with self.subTest(case.ident):
                naive_calls = [case.value]  # synthetic always-dispatch baseline
                guarded_calls = []
                tool = BoundTool(
                    "tool.send", "partner",
                    lambda args: guarded_calls.append(args),
                )
                if case.mode == "literal":
                    expr, slots, raw = Literal(case.value), (), {}
                else:
                    slots, raw = (ExternalSlot("page", "web.page"),), {
                        "page": case.value
                    }
                    if case.mode == "source":
                        expr = Source("page")
                    elif case.mode == "join":
                        expr = Join((Literal("prefix: "), Source("page")))
                    elif case.mode == "choose":
                        expr = Choose(
                            Equals(Source("page"), Literal("GO")),
                            Literal("trusted-looking choice"),
                            Literal("trusted-looking fallback"),
                        )
                    elif case.mode == "ambient_if":
                        expr = Literal("trusted-looking host command")
                    else:
                        self.fail("Unknown fixed corpus mode")
                executor = ClosedHostExecutor(
                    tool=tool, slots=slots,
                    plan=HostPlan("tool.send", (expr,)),
                )
                if case.mode == "ambient_if":
                    # Deliberate WRONG host: untrusted raw condition outside AST.
                    result = executor.invoke(raw) if raw["page"] else None
                else:
                    result = executor.invoke(raw)
                self.assertIsNotNone(result)
                self.assertTrue(naive_calls)
                self.assertEqual(result.attempted, case.expected_attempt)
                self.assertEqual(bool(guarded_calls), case.expected_attempt)
                outcomes[case.category].append(case.expected_attempt)

        # These fractions are exact FOR THIS ARTIFICIAL FIXTURE ONLY.
        self.assertEqual(outcomes["hostile_input"], [False] * 9)
        self.assertEqual(outcomes["benign"].count(False), 4)
        self.assertEqual(outcomes["benign"].count(True), 6)
        self.assertEqual(outcomes["broken_tcb"], [True, True])

    def test_G3_03_malformed_manifest_ref_is_rejected_not_uncaught(self):
        with self.assertRaises(FlowInputError):
            ClosedHostExecutor(
                tool=BoundTool("tool.send", "partner", lambda args: None),
                slots=(ExternalSlot("page", "web"),),
                plan=HostPlan("tool.send", (Source([]),)),
            )


if __name__ == "__main__":
    unittest.main()

"""Executable example contract tests.

These tests exercise only public APIs and the example scripts. They do not turn the
examples into supported library surfaces.
"""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from spatial_check.json_io import load
from spatial_check.trust import claim_from_data

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load_example_module(name):
    path = EXAMPLES / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_example_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceExampleTests(unittest.TestCase):
    def test_naive_vs_protected_same_candidate_fails_closed(self):
        run = subprocess.run(
            [sys.executable, str(EXAMPLES / "naive_vs_protected.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("NAIVE_DECISION=APPROVED_BY_NAIVE_PIPELINE", run.stdout)
        self.assertIn("SPATIAL_CHECK_STATUS=UNVERIFIED", run.stdout)
        self.assertIn("SPATIAL_CHECK_EXECUTION_MODE=UNTRUSTED", run.stdout)
        self.assertIn("TRUST_REQUIRED", run.stdout)

    def test_reference_host_cancel_never_calls_confirm(self):
        module = load_example_module("reference_host")
        output = []
        with patch.object(module.HostIntake, "confirm", side_effect=AssertionError("confirm called")):
            code = module.run_review(input_fn=lambda _prompt: "CANCEL", output_fn=output.append)
        self.assertEqual(code, 2)
        self.assertIn("REVIEW_CANCELLED", output)
        self.assertIn("No trusted receipt was issued.", output)

    def test_reference_host_shows_exact_claim_before_confirmation(self):
        module = load_example_module("reference_host")
        candidate = load(EXAMPLES / "fits.evidence.json")
        claim = claim_from_data(candidate)
        expected_digest = hashlib.sha256(claim.payload.encode()).hexdigest()
        output = []
        code = module.run_review(input_fn=lambda _prompt: "CANCEL", output_fn=output.append)
        self.assertEqual(code, 2)
        self.assertIn(claim.payload, output)
        self.assertIn(f"CLAIM_SHA256={expected_digest}", output)

    def test_reference_host_confirm_uses_host_confirmed_input(self):
        module = load_example_module("reference_host")
        output = []
        code = module.run_review(input_fn=lambda _prompt: "CONFIRM", output_fn=output.append)
        self.assertEqual(code, 0)
        self.assertIn("REVIEW_CONFIRMED", output)
        self.assertIn(
            "SPATIAL_CHECK_STATUS=NO CONFLICT DETECTED IN PROVIDED DATA",
            output,
        )
        self.assertIn("SPATIAL_CHECK_EXECUTION_MODE=HOST_CONFIRMED_INPUT", output)


if __name__ == "__main__":
    unittest.main()

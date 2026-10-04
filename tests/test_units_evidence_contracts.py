from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from spatial_check.units import normalize, InputError
from tests.helpers import evaluate_confirmed_fixture as evaluate
from spatial_check.contracts import INPUT_SCHEMA, EVIDENCE_SCHEMA, RESULT_SCHEMA, validate
from spatial_check.engine import NO_CONFLICT, UNVERIFIED
from tests.helpers import base, fact, change, required, reservation

ROOT = Path(__file__).resolve().parents[1]


class UnitEvidenceContractTests(unittest.TestCase):
    def test_exact_normalization(self):
        self.assertEqual(normalize("3.20", "m", "usable_width"), Decimal("320"))
        self.assertEqual(normalize(2800, "mm", "usable_width"), Decimal("280"))
        self.assertEqual(normalize("0.000001", "mm", "position_x"), Decimal("0.0000001"))

    def test_numeric_domain_boundary(self):
        self.assertEqual(normalize(1000000, "cm", "usable_width"), Decimal(1000000))
        with self.assertRaises(InputError):
            normalize("1000000.000001", "cm", "usable_width")

    def test_engine_isolated_from_caller_decimal_exponent(self):
        q, e = base()
        change(e, "rw", value=3000)
        with localcontext() as ctx:
            ctx.Emax = 2
            self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_missing_derived_parent(self):
        q, e = base()
        change(e, "rw", status="DERIVED", derivation={"operation": "unit_conversion", "input": "absent"})
        fact(e, "rw")["source"]["kind"] = "engine"
        self.assertEqual(evaluate(q, e)["status"], UNVERIFIED)

    def test_provided_cannot_smuggle_derivation(self):
        q, e = base()
        change(e, "rw", derivation={"operation": "unit_conversion", "input": "rd"})
        self.assertEqual(evaluate(q, e)["status"], UNVERIFIED)

    def test_same_value_unknown_source_still_blocks(self):
        q, e = base()
        duplicate = dict(fact(e, "rw"), id="rw-unknown", status="UNKNOWN")
        e["facts"].append(duplicate)
        self.assertEqual(evaluate(q, e)["status"], UNVERIFIED)

    def test_duplicate_reservation_and_requirement_ids(self):
        q, e = base()
        reservation(q, e, ident="same")
        required(q, e, ident="same")
        self.assertEqual(evaluate(q, e)["status"], UNVERIFIED)

    def test_schema_files_match_runtime_contracts(self):
        for name, schema in [("input", INPUT_SCHEMA), ("evidence", EVIDENCE_SCHEMA), ("result", RESULT_SCHEMA)]:
            saved = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
            saved.pop("$schema")
            saved.pop("title")
            self.assertEqual(saved, schema)

    def test_result_contract_for_adversarial_variants(self):
        for value in (None, -1, 0, "2,00", {}, [], True, 10**20):
            q, e = base()
            change(e, "iw", value=value)
            self.assertEqual(validate(evaluate(q, e), RESULT_SCHEMA), [])

    def test_examples_cli_exit_codes_and_public_status(self):
        for name, exit_code, status in [("fits", 0, NO_CONFLICT), ("clearance_conflict", 1, "CONFLICT DETECTED"),
                                         ("unverified", 2, UNVERIFIED)]:
            run = subprocess.run([sys.executable, "-m", "spatial_check",
                                  "--demo", name],
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, exit_code, run.stderr)
            self.assertEqual(json.loads(run.stdout)["status"], status)

    def test_cli_duplicate_json_keys_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"room": {}, "room": {}}')
            run = subprocess.run([sys.executable, "-m", "spatial_check", str(path),
                                  "examples/fits.evidence.json"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout)["status"], UNVERIFIED)

    def test_cli_text_keeps_status(self):
        run = subprocess.run([sys.executable, "-m", "spatial_check", "examples/unverified.request.json",
                              "examples/unverified.evidence.json", "--text"],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertTrue(run.stdout.startswith(UNVERIFIED))

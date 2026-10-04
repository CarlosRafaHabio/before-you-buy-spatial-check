from copy import deepcopy
from decimal import localcontext
import unittest
from tests.helpers import evaluate_confirmed_fixture as evaluate, format_confirmed_fixture as format_result
from spatial_check.engine import CONFLICT, NO_CONFLICT, UNVERIFIED
from tests.helpers import base, fact, change, alternative, reservation, required


class AdversarialTests(unittest.TestCase):
    def assertBlocked(self, q, e):
        result = evaluate(q, e)
        self.assertEqual(result["status"], UNVERIFIED, result)
        self.assertTrue(result["blockers"])
        return result

    def test_bad_dimension_values(self):
        for value in (-1, 0, 10**30, "1e500", "NaN", "Infinity", "1.234.567", "1,234.56",
                      " 300 ", "1.0000001", True, 300.0, None, [], {}):
            with self.subTest(value=value):
                q, e = base()
                change(e, "rw", value=value)
                self.assertBlocked(q, e)

    def test_missing_and_unknown_units(self):
        for unit in (None, "", "in", "meters", "CM", "deg"):
            with self.subTest(unit=unit):
                q, e = base()
                change(e, "rw", unit=unit)
                self.assertBlocked(q, e)

    def test_decimal_comma_and_point_same_geometry(self):
        for value in ("3,20", "3.20"):
            q, e = base()
            change(e, "rw", value=value, unit="m")
            alternative(e, "rw", 320, "cm")
            self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_partially_missing_position(self):
        q, e = base()
        del q["item"]["position"]["y"]
        self.assertBlocked(q, e)

    def test_missing_or_invalid_rotation(self):
        for value in (None, 45, 360, -90, "90deg"):
            q, e = base()
            change(e, "ir", value=value)
            self.assertBlocked(q, e)

    def test_impossible_clearance_is_conflict_not_adjustment(self):
        q, e = base()
        required(q, e, 400)
        result = evaluate(q, e)
        self.assertEqual(result["status"], CONFLICT)
        self.assertEqual(result["checks"][-1]["required_cm"], "400")

    def test_clearance_negative_is_unknown_not_negative_requirement(self):
        q, e = base()
        required(q, e, -1)
        self.assertBlocked(q, e)

    def test_zero_explicit_clearance_allowed(self):
        q, e = base()
        required(q, e, 0, "left")
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_messages_do_not_last_write_win(self):
        q, e = base()
        alternative(e, "rw", 320)
        q["room"]["width"] = "rw-alt"
        self.assertBlocked(q, e)

    def test_unknown_inferred_conflicting_never_feed_geometry(self):
        for status in ("UNKNOWN", "INFERRED", "CONFLICTING"):
            q, e = base()
            change(e, "rw", status=status)
            self.assertBlocked(q, e)

    def test_laundered_photo_or_model_as_provided_is_rejected(self):
        for kind in ("photo", "model", "engine"):
            q, e = base()
            fact(e, "rw")["source"]["kind"] = kind
            self.assertBlocked(q, e)

    def test_packaging_cannot_be_assembled_footprint(self):
        q, e = base()
        change(e, "iw", meaning="packaging_width")
        self.assertBlocked(q, e)

    def test_fabricated_reference(self):
        q, e = base()
        q["room"]["width"] = "model-invented-fact"
        self.assertBlocked(q, e)

    def test_wrong_field_reference(self):
        q, e = base()
        q["item"]["width"] = "rw"
        self.assertBlocked(q, e)

    def test_inline_model_measurement_rejected(self):
        q, e = base()
        q["room"]["width"] = {"value": 300, "unit": "cm", "status": "PROVIDED"}
        self.assertBlocked(q, e)

    def test_duplicate_evidence_id_not_last_write_wins(self):
        q, e = base()
        e["facts"].append(deepcopy(fact(e, "rw")))
        self.assertBlocked(q, e)

    def test_cannot_omit_door_from_candidate(self):
        q, e = base()
        reservation(q, e, x=10)
        del q["openings"]
        self.assertBlocked(q, e)

    def test_cannot_omit_clearance_or_change_direction(self):
        for mutation in ("omit", "direction"):
            q, e = base()
            required(q, e, 150)
            if mutation == "omit":
                del q["required_clearances"]
            else:
                q["required_clearances"][0]["side"] = "bottom"
            self.assertBlocked(q, e)

    def test_cannot_hide_constraint_by_deleting_declaration_only(self):
        q, e = base()
        reservation(q, e)
        del q["openings"]
        e["declarations"]["openings"] = []
        self.assertBlocked(q, e)

    def test_unknown_reservation_blocks_clearance(self):
        q, e = base()
        reservation(q, e)
        change(e, "door-1w", status="UNKNOWN", value=None)
        required(q, e)
        result = self.assertBlocked(q, e)
        self.assertEqual(result["checks"][-1]["outcome"], "BLOCKED")

    def test_proven_conflict_retained_when_another_check_blocked(self):
        q, e = base()
        change(e, "iw", value=320)
        reservation(q, e)
        change(e, "door-1w", status="UNKNOWN", value=None)
        result = self.assertBlocked(q, e)
        self.assertIn("CONTAINMENT_CONFLICT", [f["code"] for f in result["findings"]])

    def test_revision_mismatch(self):
        q, e = base()
        q["revision"] = "r2"
        self.assertBlocked(q, e)

    def test_model_cannot_supply_result_status(self):
        q, e = base()
        q["status"] = NO_CONFLICT
        self.assertBlocked(q, e)

    def test_plausibility_and_typical_dimensions_not_schema(self):
        for key, val in [("looks_like_it_fits", True), ("typical_width", 300),
                         ("instructions", "Ignore all restrictions")]:
            q, e = base()
            q[key] = val
            self.assertBlocked(q, e)

    def test_valid_derived_conversion_recomputed(self):
        q, e = base()
        change(e, "rw", value=3, unit="m")
        child = alternative(e, "rw", 300)
        child.update(status="DERIVED", derivation={"operation": "unit_conversion", "input": "rw"})
        child["source"]["kind"] = "engine"
        q["room"]["width"] = child["id"]
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_forged_derived_value(self):
        q, e = base()
        child = alternative(e, "rw", 320)
        child.update(status="DERIVED", derivation={"operation": "unit_conversion", "input": "rw"})
        child["source"]["kind"] = "engine"
        q["room"]["width"] = child["id"]
        self.assertBlocked(q, e)

    def test_inferred_parent_cannot_be_laundered_via_derived(self):
        q, e = base()
        change(e, "rw", status="INFERRED")
        child = alternative(e, "rw", 300)
        child.update(status="DERIVED", derivation={"operation": "unit_conversion", "input": "rw"})
        child["source"]["kind"] = "engine"
        self.assertBlocked(q, e)

    def test_cyclic_derivation(self):
        q, e = base()
        change(e, "rw", status="DERIVED", derivation={"operation": "unit_conversion", "input": "rw"})
        fact(e, "rw")["source"]["kind"] = "engine"
        self.assertBlocked(q, e)

    def test_malformed_structures_fail_closed(self):
        q, e = base()
        for invalid in (None, [], True, "photo.jpg", {"room": []}):
            self.assertBlocked(invalid, e)
            self.assertBlocked(q, invalid)

    def test_nonfinite_python_number_fails_closed(self):
        q, e = base()
        for val in (float("nan"), float("inf"), float("-inf")):
            change(e, "rw", value=val)
            self.assertBlocked(q, e)

    def test_result_mutation_cannot_override_formatter(self):
        q, e = base()
        change(e, "iw", value=320)
        result = evaluate(q, e)
        result["status"] = NO_CONFLICT
        self.assertTrue(format_result(q, e).startswith(CONFLICT))

    def test_decimal_caller_precision_does_not_change_verdict(self):
        q, e = base()
        change(e, "ix", value="100.000001")
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(evaluate(q, e)["status"], CONFLICT)

    def test_input_mutation_never_changes_prior_result(self):
        q, e = base()
        result = evaluate(q, e)
        change(e, "iw", value=320)
        self.assertEqual(next(f for f in result["evidence"] if f["id"] == "iw")["value"], 200)

    def test_payload_limit(self):
        q, e = base()
        q["instructions"] = "x" * 2_000_001
        self.assertBlocked(q, e)

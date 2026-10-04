from decimal import Decimal as D
import unittest
from tests.helpers import evaluate_confirmed_fixture as evaluate
from spatial_check.geometry import Rectangle, intersects, contained
from spatial_check.engine import CONFLICT, NO_CONFLICT
from tests.helpers import base, change, required, reservation


class GeometryTests(unittest.TestCase):
    def test_rotation_all_four_explicit(self):
        for angle, expected in [(0, CONFLICT), (90, NO_CONFLICT), (180, CONFLICT), (270, NO_CONFLICT)]:
            with self.subTest(angle=angle):
                q, e = base()
                change(e, "rw", value=100)
                change(e, "ir", value=angle)
                self.assertEqual(evaluate(q, e)["status"], expected)

    def test_negative_position_is_demonstrable_conflict(self):
        q, e = base()
        change(e, "ix", value=-1)
        self.assertEqual(evaluate(q, e)["status"], CONFLICT)

    def test_touching_boundary_passes_without_assumed_gap(self):
        q, e = base()
        change(e, "ix", value=100)
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_exact_small_excess_is_not_rounded_away(self):
        q, e = base()
        change(e, "ix", value="100.000001")
        self.assertEqual(evaluate(q, e)["status"], CONFLICT)

    def test_coincident_rectangles_conflict(self):
        q, e = base()
        reservation(q, e, group="explicit_exclusions", x=0, y=0, w=200, d=60)
        self.assertEqual(evaluate(q, e)["status"], CONFLICT)

    def test_touching_opening_no_area_overlap(self):
        q, e = base()
        reservation(q, e, x=200)
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_no_clearance_default_for_opening(self):
        q, e = base()
        reservation(q, e, x=200)
        result = evaluate(q, e)
        self.assertEqual([c["kind"] for c in result["checks"]], ["containment", "intersection"])

    def test_each_direction_and_exact_equality(self):
        for side, expected in [("left", "40"), ("right", "60"), ("top", "70"), ("bottom", "120")]:
            with self.subTest(side=side):
                q, e = base()
                change(e, "ix", value=40)
                change(e, "iy", value=70)
                required(q, e, amount=expected, side=side)
                result = evaluate(q, e)
                self.assertEqual(result["status"], NO_CONFLICT)
                self.assertEqual(result["checks"][-1]["actual_cm"], expected)

    def test_forward_obstacle_limits_clearance(self):
        q, e = base()
        reservation(q, e, x=248)
        required(q, e, 60)
        result = evaluate(q, e)
        self.assertEqual(result["status"], CONFLICT)
        self.assertEqual(result["checks"][-1]["actual_cm"], "48")

    def test_obstacle_outside_transverse_span_not_invented_as_blocker(self):
        q, e = base()
        reservation(q, e, x=210, y=60)
        required(q, e, 100)
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_contained_obstacle_has_zero_free_clearance(self):
        q, e = base()
        reservation(q, e, x=10, y=10, w=20, d=20)
        required(q, e, 60)
        result = evaluate(q, e)
        self.assertEqual(result["status"], CONFLICT)
        self.assertEqual(result["checks"][-1]["actual_cm"], "0")

    def test_overlapping_reservations_are_not_two_physical_items(self):
        q, e = base()
        reservation(q, e, ident="a", x=240)
        reservation(q, e, ident="b", x=240)
        self.assertEqual(evaluate(q, e)["status"], NO_CONFLICT)

    def test_intersection_matches_integer_cell_oracle(self):
        # Independent occupied-cell oracle over a bounded exhaustive grid.
        base_rect = Rectangle(D(0), D(0), D(2), D(3))
        base_cells = {(x, y) for x in range(2) for y in range(3)}
        for x in range(-3, 4):
            for y in range(-3, 4):
                for w in (1, 2):
                    for d in (1, 3):
                        rect = Rectangle(D(x), D(y), D(w), D(d))
                        cells = {(i, j) for i in range(x, x+w) for j in range(y, y+d)}
                        self.assertEqual(intersects(base_rect, rect), bool(base_cells & cells))
                        self.assertEqual(intersects(rect, base_rect), bool(base_cells & cells))
                        self.assertEqual(contained(rect, base_rect), cells <= base_cells)

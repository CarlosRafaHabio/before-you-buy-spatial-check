import hashlib
import json
import unittest

from spatial_check import evaluate
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data


EXPECTED_DIGEST = "8288a35799519bb2cb2a816da6467a3ae7895116824ca26ad0760686a26c0272"


def morable_evidence():
    return {
        "schema_version": "0.1",
        "case_id": "case-1",
        "revision": "r1",
        "room_identity": "room-1",
        "item_identity": "item-1",
        "declarations": {
            "openings": [],
            "explicit_exclusions": [],
            "required_clearances": [],
        },
        "facts": [
            {
                "id": "room-width",
                "field": "room.width",
                "value": "400",
                "unit": "cm",
                "meaning": "usable_width",
                "source": {
                    "id": "room-width-source",
                    "kind": "user_measurement",
                    "locator": "morable:project:project-1:room.width",
                },
                "status": "PROVIDED",
            },
            {
                "id": "room-depth",
                "field": "room.depth",
                "value": "500",
                "unit": "cm",
                "meaning": "usable_depth",
                "source": {
                    "id": "room-depth-source",
                    "kind": "user_measurement",
                    "locator": "morable:project:project-1:room.depth",
                },
                "status": "PROVIDED",
            },
            {
                "id": "item-width",
                "field": "item.width",
                "value": "138",
                "unit": "cm",
                "meaning": "assembled_width",
                "source": {
                    "id": "item-width-source",
                    "kind": "user_confirmation",
                    "locator": "morable:project:project-1:budget-item:bed-1:product:mercado_livre:MLB-123:width",
                },
                "status": "PROVIDED",
            },
            {
                "id": "item-depth",
                "field": "item.depth",
                "value": "188",
                "unit": "cm",
                "meaning": "assembled_depth",
                "source": {
                    "id": "item-depth-source",
                    "kind": "user_measurement",
                    "locator": "morable:project:project-1:budget-item:bed-1:product:mercado_livre:MLB-123:depth",
                },
                "status": "PROVIDED",
            },
            {
                "id": "item-x",
                "field": "item.x",
                "value": "35",
                "unit": "cm",
                "meaning": "position_x",
                "source": {
                    "id": "item-x-source",
                    "kind": "user_confirmation",
                    "locator": "morable-review:review-1:item.x:origin:user_floor_plan_editor",
                },
                "status": "PROVIDED",
            },
            {
                "id": "item-y",
                "field": "item.y",
                "value": "45",
                "unit": "cm",
                "meaning": "position_y",
                "source": {
                    "id": "item-y-source",
                    "kind": "user_confirmation",
                    "locator": "morable-review:review-1:item.y:origin:user_floor_plan_editor",
                },
                "status": "PROVIDED",
            },
            {
                "id": "item-rotation",
                "field": "item.rotation",
                "value": "90",
                "unit": "deg",
                "meaning": "rotation",
                "source": {
                    "id": "item-rotation-source",
                    "kind": "user_confirmation",
                    "locator": "morable-review:review-1:item.rotation:origin:user_floor_plan_editor",
                },
                "status": "PROVIDED",
            },
        ],
    }


def morable_request():
    return {
        "schema_version": "0.1",
        "case_id": "case-1",
        "revision": "r1",
        "room": {
            "identity": "room-1",
            "width": "room-width",
            "depth": "room-depth",
        },
        "item": {
            "identity": "item-1",
            "width": "item-width",
            "depth": "item-depth",
            "rotation": "item-rotation",
            "position": {
                "x": "item-x",
                "y": "item-y",
            },
        },
        "openings": [],
        "explicit_exclusions": [],
        "required_clearances": [],
    }


class MorableInteropTests(unittest.TestCase):
    def test_real_claim_confirm_evaluate_matches_morable_golden(self):
        evidence = morable_evidence()
        claim = claim_from_data(evidence)

        expected_payload = json.dumps(
            evidence,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        self.assertEqual(claim.payload, expected_payload)

        digest = hashlib.sha256(claim.payload.encode("utf-8")).hexdigest()
        self.assertEqual(digest, EXPECTED_DIGEST)

        registry = LifecycleRegistry()
        intake = HostIntake(registry)
        receipt = intake.confirm(
            claim,
            case_id="case-1",
            revision="r1",
            room_identity="room-1",
            item_identity="item-1",
            confirmation_ref="morable-review:review-1",
        )

        result = evaluate(morable_request(), receipt)

        self.assertEqual(result["status"], "NO CONFLICT DETECTED IN PROVIDED DATA")
        self.assertEqual(result["execution_mode"], "HOST_CONFIRMED_INPUT")
        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["revision"], "r1")
        self.assertEqual(result["item_identity"], "item-1")
        self.assertIsNotNone(result["admission"])
        self.assertEqual(result["admission"]["evidence_digest"], EXPECTED_DIGEST)
        self.assertEqual(
            result["admission"]["confirmation_ref"],
            "morable-review:review-1",
        )
        self.assertEqual(result["admission"]["case_id"], "case-1")
        self.assertEqual(result["admission"]["revision"], "r1")
        self.assertEqual(result["admission"]["room_identity"], "room-1")
        self.assertEqual(result["admission"]["item_identity"], "item-1")


if __name__ == "__main__":
    unittest.main()

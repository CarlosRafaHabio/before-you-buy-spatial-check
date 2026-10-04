"""Closed synthetic examples. No arbitrary-file or arbitrary-claim admission."""
from .trust import HostIntake, claim_from_data
from .engine import evaluate


def run_demo(name: str) -> dict:
    if name not in ("fits", "clearance_conflict", "unverified"):
        raise ValueError("Unknown fixed demo.")
    request = {"schema_version": "0.1", "case_id": "demo", "revision": "r1",
               "room": {"identity": "room", "width": "rw", "depth": "rd"},
               "item": {"identity": "product", "width": "iw", "depth": "id",
                        "position": {"x": "ix", "y": "iy"}, "rotation": "ir"}}
    facts = []
    for ident, field, value, meaning in [
        ("rw", "room.width", 300, "usable_width"), ("rd", "room.depth", 250, "usable_depth"),
        ("iw", "item.width", 252 if name == "clearance_conflict" else 200, "assembled_width"),
        ("id", "item.depth", 60, "assembled_depth"), ("ix", "item.x", 0, "position_x"),
        ("iy", "item.y", 0, "position_y"), ("ir", "item.rotation", 0, "rotation")]:
        facts.append({"id": ident, "field": field, "value": value,
                      "meaning": meaning, "unit": "deg" if ident == "ir" else "cm",
                      "status": "PROVIDED", "source": {"id": "synthetic-example",
                      "kind": "user_measurement", "locator": "Synthetic example, not a real measurement"}})
    declarations = {"openings": [], "explicit_exclusions": [], "required_clearances": []}
    if name == "clearance_conflict":
        request["required_clearances"] = [{"id": "right", "side": "right", "required": "cr"}]
        declarations["required_clearances"] = [{"id": "right", "side": "right"}]
        facts.append({"id": "cr", "field": "required_clearances.right.required", "value": 60,
                      "meaning": "required_clearance", "unit": "cm", "status": "PROVIDED",
                      "source": {"id": "synthetic-example", "kind": "user_measurement",
                                 "locator": "Synthetic explicit clearance"}})
    if name == "unverified":
        facts[0].update(value=None, status="UNKNOWN")
    evidence = {"schema_version": "0.1", "case_id": "demo", "revision": "r1",
                "room_identity": "room", "item_identity": "product", "declarations": declarations,
                "facts": facts}
    host = HostIntake()
    receipt = host.confirm(claim_from_data(evidence), case_id="demo", revision="r1",
                           room_identity="room", item_identity="product", confirmation_ref="synthetic-demo")
    result = evaluate(request, receipt)
    result["execution_mode"] = "DEMO_ONLY"
    result["limitations"].insert(0, "DEMO ONLY: fixed synthetic data; no real user or manufacturer confirmation.")
    return result

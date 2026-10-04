from copy import deepcopy


def confirm_fixture(evidence):
    """TEST ONLY: admit synthetic fixtures as a host, never a production adapter.

    A fresh issuer keeps original geometry regressions independent. New trust
    tests exercise real raw-input rejection and same-host revision lifecycle.
    """
    from spatial_check.trust import HostIntake, TrustError, claim_from_data
    try:
        claim = claim_from_data(evidence)
        return HostIntake().confirm(claim, case_id=evidence["case_id"],
                                    revision=evidence["revision"], room_identity=evidence["room_identity"],
                                    item_identity=evidence["item_identity"], confirmation_ref="synthetic-test")
    except (TrustError, KeyError, TypeError):
        return evidence  # Invalid fixtures still go through real fail-closed API.


def evaluate_confirmed_fixture(request, evidence):
    from spatial_check import evaluate
    return evaluate(request, confirm_fixture(evidence))


def format_confirmed_fixture(request, evidence):
    from spatial_check import format_result
    return format_result(request, confirm_fixture(evidence))


def base():
    request = {"schema_version": "0.1", "case_id": "case-1", "revision": "r1",
               "room": {"identity": "room-1", "width": "rw", "depth": "rd"},
               "item": {"identity": "product-1", "width": "iw", "depth": "id",
                        "position": {"x": "ix", "y": "iy"}, "rotation": "ir"}}
    evidence = {"schema_version": "0.1", "case_id": "case-1", "revision": "r1",
                "room_identity": "room-1", "item_identity": "product-1",
                "declarations": {"openings": [], "explicit_exclusions": [], "required_clearances": []},
                "facts": []}
    for ident, field, value, meaning in [
        ("rw", "room.width", 300, "usable_width"), ("rd", "room.depth", 250, "usable_depth"),
        ("iw", "item.width", 200, "assembled_width"), ("id", "item.depth", 60, "assembled_depth"),
        ("ix", "item.x", 0, "position_x"), ("iy", "item.y", 0, "position_y"),
        ("ir", "item.rotation", 0, "rotation")]:
        add_fact(evidence, ident, field, value, meaning, "deg" if ident == "ir" else "cm")
    return request, evidence


def add_fact(evidence, ident, field, value, meaning, unit="cm", **extra):
    record = {"id": ident, "field": field, "value": value, "unit": unit, "meaning": meaning,
              "source": {"id": "message-1", "kind": "user_measurement", "locator": field},
              "status": "PROVIDED", **extra}
    evidence["facts"].append(record)
    return record


def fact(evidence, ident):
    return next(f for f in evidence["facts"] if f["id"] == ident)


def change(evidence, ident, **values):
    fact(evidence, ident).update(values)


def reservation(request, evidence, ident="door-1", group="openings", x=250, y=0, w=50, d=60):
    record = {"id": ident, "width": ident + "w", "depth": ident + "d",
              "position": {"x": ident + "x", "y": ident + "y"}}
    request.setdefault(group, []).append(record)
    evidence["declarations"][group].append(ident)
    for key, val, meaning in [("x", x, "position_x"), ("y", y, "position_y"),
                              ("w", w, "reserved_width"), ("d", d, "reserved_depth")]:
        field = "width" if key == "w" else "depth" if key == "d" else key
        add_fact(evidence, ident + key, f"{group}.{ident}.{field}", val, meaning)
    return record


def required(request, evidence, amount=60, side="right", ident="clear-1"):
    request.setdefault("required_clearances", []).append({"id": ident, "side": side, "required": ident})
    evidence["declarations"]["required_clearances"].append({"id": ident, "side": side})
    add_fact(evidence, ident, f"required_clearances.{ident}.required", amount, "required_clearance")


def alternative(evidence, ident, value, unit="cm"):
    entry = deepcopy(fact(evidence, ident))
    entry.update(id=ident + "-alt", value=value, unit=unit)
    entry["source"]["id"] = "message-2"
    evidence["facts"].append(entry)
    return entry

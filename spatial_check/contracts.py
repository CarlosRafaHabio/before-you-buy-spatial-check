"""JSON Schema contracts plus a small validator for the exact subset we use.

    Generated JSON schemas are deliverables; this module is the source of truth.
"""
from typing import Any

ID = {"type": "string", "minLength": 1, "maxLength": 128,
      "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$"}
TEXT = {"type": "string", "maxLength": 4096}
REF = {"anyOf": [ID, {"type": "null"}]}


def obj(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}


def array(items: dict, limit: int = 100) -> dict:
    return {"type": "array", "items": items, "maxItems": limit}


RECT = obj({"id": ID, "width": REF, "depth": REF,
            "position": obj({"x": REF, "y": REF}, [])}, ["id"])
SIDES = {"enum": ["left", "right", "top", "bottom"]}
CLEARANCE = obj({"id": ID, "side": SIDES, "required": REF}, ["id", "side"])
INPUT_SCHEMA = obj({
    "schema_version": {"const": "0.1"}, "case_id": ID, "revision": ID,
    "room": obj({"identity": ID, "width": REF, "depth": REF}, ["identity"]),
    "item": obj({"identity": ID, "width": REF, "depth": REF, "rotation": REF,
                 "position": obj({"x": REF, "y": REF}, [])}, ["identity"]),
    "openings": array(RECT), "explicit_exclusions": array(RECT),
    "required_clearances": array(CLEARANCE),
}, ["schema_version", "case_id", "revision", "room", "item"])

SOURCE = obj({"id": ID, "kind": {"enum": ["user_measurement", "user_confirmation",
                "document_dimension", "photo", "model", "engine"]},
              "locator": {"type": "string", "minLength": 1, "maxLength": 4096}},
             ["id", "kind", "locator"])
FACT = obj({
    "id": ID, "field": ID,
    "value": {"anyOf": [{"type": "integer"}, {"type": "string", "maxLength": 64},
                        {"type": "null"}]},
    "unit": {"anyOf": [{"type": "string", "maxLength": 16}, {"type": "null"}]},
    "meaning": {"type": "string", "minLength": 1, "maxLength": 128},
    "source": SOURCE,
    "status": {"enum": ["PROVIDED", "DERIVED", "INFERRED", "UNKNOWN", "CONFLICTING"]},
    "derivation": obj({"operation": {"const": "unit_conversion"}, "input": ID},
                      ["operation", "input"]),
}, ["id", "field", "value", "unit", "meaning", "source", "status"])
EVIDENCE_SCHEMA = obj({
    "schema_version": {"const": "0.1"}, "case_id": ID, "revision": ID,
    "room_identity": ID, "item_identity": ID,
    "declarations": obj({"openings": array(ID), "explicit_exclusions": array(ID),
                         "required_clearances": array(obj({"id": ID, "side": SIDES},
                                                           ["id", "side"]))},
                        ["openings", "explicit_exclusions", "required_clearances"]),
    "facts": array(FACT, 1000),
}, ["schema_version", "case_id", "revision", "room_identity", "item_identity",
    "declarations", "facts"])

STATUSES = ["CONFLICT DETECTED", "NO CONFLICT DETECTED IN PROVIDED DATA", "UNVERIFIED"]
ISSUE = obj({"code": ID, "field": TEXT, "message": TEXT, "evidence_ids": array(ID, 1000)},
            ["code", "field", "message", "evidence_ids"])
CHECK = obj({"id": {"type": "string", "minLength": 1, "maxLength": 512},
             "kind": {"enum": ["containment", "intersection", "clearance"]},
             "outcome": {"enum": ["PASS", "CONFLICT", "BLOCKED"]},
             "evidence_ids": array(ID, 1000),
             "actual_cm": {"type": "string"}, "required_cm": {"type": "string"}},
            ["id", "kind", "outcome", "evidence_ids"])
NORMALIZED = obj({"field": TEXT, "value": {"type": "string"},
                  "unit": {"enum": ["cm", "deg"]}, "evidence_ids": array(ID, 1000)},
                 ["field", "value", "unit", "evidence_ids"])
DIGEST = {"type": "string", "pattern": r"^[a-f0-9]{64}$"}
ADMISSION = obj({"domain_id": ID, "receipt_id": ID, "confirmation_ref": ID,
                 "evidence_digest": DIGEST, "case_id": ID, "revision": ID,
                 "room_identity": ID, "item_identity": ID},
                ["domain_id", "receipt_id", "confirmation_ref", "evidence_digest",
                 "case_id", "revision", "room_identity", "item_identity"])
RESULT_SCHEMA = obj({
    "engine_version": {"const": "0.3.0"}, "status": {"enum": STATUSES},
    "admission": {"anyOf": [ADMISSION, {"type": "null"}]},
    "execution_mode": {"enum": ["UNTRUSTED", "HOST_CONFIRMED_INPUT", "DEMO_ONLY"]},
    "case_id": {"anyOf": [ID, {"type": "null"}]},
    "revision": {"anyOf": [ID, {"type": "null"}]},
    "item_identity": {"anyOf": [ID, {"type": "null"}]},
    "input_digest": {"anyOf": [{"type": "string", "pattern": r"^[a-f0-9]{64}$"},
                              {"type": "null"}]},
    "findings": array(ISSUE, 5000), "blockers": array(ISSUE, 5000),
    "checks": array(CHECK, 5000), "evidence": array(FACT, 1000),
    "normalized": array(NORMALIZED, 1000), "limitations": array(TEXT),
}, ["engine_version", "status", "execution_mode", "admission", "case_id", "revision", "item_identity", "input_digest",
    "findings", "blockers", "checks", "evidence", "normalized", "limitations"])


def validate(value: Any, schema: dict, path: str = "$") -> list[str]:
    """Reject unknown properties, booleans as numbers, and wrong container types."""
    import re
    if "anyOf" in schema:
        if any(not validate(value, s, path) for s in schema["anyOf"]):
            return []
        return [f"{path}: wrong value type/shape"]
    if "const" in schema and value != schema["const"]:
        return [f"{path}: unexpected constant"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: unsupported value"]
    expected = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "null": type(None)}
    if expected and type(value) is not types[expected]:
        return [f"{path}: expected {expected}"]
    errors = []
    if expected == "object":
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: missing")
        for key, val in value.items():
            if key not in schema["properties"]:
                errors.append(f"{path}: unsupported field")
            else:
                errors.extend(validate(val, schema["properties"][key], f"{path}.{key}"))
    elif expected == "array":
        if len(value) > schema["maxItems"]:
            return [f"{path}: too many entries"]
        for i, val in enumerate(value):
            errors.extend(validate(val, schema["items"], f"{path}[{i}]"))
    elif expected == "string":
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1_000_000):
            errors.append(f"{path}: invalid length")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value, re.ASCII) is None:
            errors.append(f"{path}: invalid identifier")
    return errors

"""Deterministic, stateless, fail-closed evaluation. No model or network calls."""
import copy
from decimal import Context, Decimal, localcontext
import hashlib
import json

from .contracts import INPUT_SCHEMA, EVIDENCE_SCHEMA, validate
from .evidence import EvidenceResolver
from .geometry import Rectangle, rotated, contained, intersects, clearance
from .units import number_text
from .trust import _read_trusted, TrustError

VERSION = "0.3.0"
CONFLICT = "CONFLICT DETECTED"
NO_CONFLICT = "NO CONFLICT DETECTED IN PROVIDED DATA"
UNVERIFIED = "UNVERIFIED"
LIMITATIONS = [
    "Only the supplied rectangular 2D footprint and explicit reservations were tested.",
    "Measurements are supplied evidence, not independently measured physical truth.",
    "No height, delivery path, assembly, door swing inference or automatic positioning.",
    "No certification of circulation, accessibility, safety, standards or purchase suitability.",
    "No unspecified clearance was assumed. Touching edges is not positive-area intersection.",
]


def _issue(code: str, field: str, message: str, refs: list[str] | None = None) -> dict:
    return {"code": code, "field": field, "message": message, "evidence_ids": refs or []}


def evaluate(request: object, trusted_evidence: object) -> dict:
    """Evaluate a JSON request against a HostIntake-issued opaque receipt.

    A raw dictionary, even with a perfect schema, cannot establish trust.
    Geometry has no cache, input mutation, repairs, model calls or I/O.
    """
    result = {"engine_version": VERSION, "status": UNVERIFIED, "case_id": None,
              "revision": None, "item_identity": None, "input_digest": None,
              "findings": [], "blockers": [], "checks": [], "evidence": [],
              "normalized": [], "limitations": list(LIMITATIONS),
              "execution_mode": "UNTRUSTED"}
    result["admission"] = None
    handle = trusted_evidence
    try:
        trusted_evidence, result["admission"] = _read_trusted(handle)
    except TrustError as exc:
        result["blockers"].append(_issue("TRUST_REQUIRED", "evidence", str(exc)))
        return result
    result["execution_mode"] = "HOST_CONFIRMED_INPUT"
    try:
        # A size/depth boundary also protects callers passing Python objects.
        serialized = json.dumps([request, trusted_evidence], sort_keys=True,
                                ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(serialized) > 2_000_000:
            raise ValueError("Payload too large.")
        request, trusted_evidence = json.loads(serialized)
    except (TypeError, ValueError, RecursionError, OverflowError):
        result["blockers"].append(_issue("INVALID_INPUT", "$", "Inputs must be bounded JSON data."))
        return result
    result["input_digest"] = hashlib.sha256(serialized.encode()).hexdigest()
    try:
        errors = (validate(request, INPUT_SCHEMA, "request")
                  + validate(trusted_evidence, EVIDENCE_SCHEMA, "evidence"))
    except (TypeError, RecursionError):
        errors = ["Invalid or excessively nested data."]
    if errors:
        result["blockers"] = [_issue("SCHEMA_ERROR", "$", error) for error in errors[:100]]
        return result
    result.update(case_id=request["case_id"], revision=request["revision"],
                  item_identity=request["item"]["identity"])
    result["evidence"] = copy.deepcopy(trusted_evidence["facts"])
    _check_scope(request, trusted_evidence, result["blockers"])
    if result["blockers"]:
        return result
    with localcontext(Context(prec=50, Emax=999999, Emin=-999999)):
        # Explicitly isolate caller precision/rounding/traps for our exact domain.
        _geometry(request, trusted_evidence, result)
    result["status"] = (UNVERIFIED if result["blockers"] else
                        CONFLICT if result["findings"] else NO_CONFLICT)
    # A concurrent host revision must not silently leave an old positive verdict.
    try:
        _read_trusted(handle)
    except TrustError as exc:
        result["status"] = UNVERIFIED
        result["blockers"].append(_issue("TRUST_REQUIRED", "evidence", str(exc)))
    return result


def _check_scope(request: dict, evidence: dict, blockers: list[dict]) -> None:
    for field, actual in (("case_id", request["case_id"]), ("revision", request["revision"]),
                          ("room_identity", request["room"]["identity"]),
                          ("item_identity", request["item"]["identity"])):
        if evidence[field] != actual:
            blockers.append(_issue("SCOPE_MISMATCH", field, "Identity/case/revision differs from trusted intake."))
    seen: set[str] = set()
    for group in ("openings", "explicit_exclusions", "required_clearances"):
        actual = request.get(group, [])
        declared = evidence["declarations"][group]
        actual_ids = [r["id"] for r in actual]
        declared_ids = [r["id"] for r in declared] if group == "required_clearances" else declared
        if (len(set(actual_ids)) != len(actual_ids)
                or len(set(declared_ids)) != len(declared_ids)
                or set(actual_ids) != set(declared_ids)):
            blockers.append(_issue("SCOPE_MISMATCH", group, "Missing, extra or duplicate declared constraint."))
        for ident in actual_ids:
            if ident in seen:
                blockers.append(_issue("DUPLICATE_ID", group, "Spatial constraint IDs must be globally unique."))
            seen.add(ident)
        if group == "required_clearances":
            sides = {d["id"]: d["side"] for d in declared}
            if any(sides.get(d["id"]) != d["side"] for d in actual):
                blockers.append(_issue("SCOPE_MISMATCH", group, "Clearance direction changed."))
    ids = [f["id"] for f in evidence["facts"]]
    if len(ids) != len(set(ids)):
        blockers.append(_issue("DUPLICATE_EVIDENCE_ID", "facts", "Evidence IDs must be unique."))
    fields = {"room.width", "room.depth", "item.width", "item.depth", "item.x", "item.y", "item.rotation"}
    for group in ("openings", "explicit_exclusions"):
        for record in request.get(group, []):
            fields.update(f"{group}.{record['id']}.{key}" for key in ("width", "depth", "x", "y"))
    fields.update(f"required_clearances.{r['id']}.required" for r in request.get("required_clearances", []))
    for fact in evidence["facts"]:
        if fact["field"] not in fields:
            blockers.append(_issue("UNDECLARED_EVIDENCE", fact["field"],
                                   "Evidence references an undeclared field/constraint.", [fact["id"]]))


def _geometry(request: dict, evidence: dict, result: dict) -> None:
    resolver = EvidenceResolver(evidence["facts"])
    room_fields = ["room.width", "room.depth"]
    rw = resolver.resolve(request["room"].get("width"), "room.width", "usable_width")
    rd = resolver.resolve(request["room"].get("depth"), "room.depth", "usable_depth")
    room = None if rw is None or rd is None else Rectangle(Decimal(0), Decimal(0), rw, rd)
    item_data = request["item"]
    item_fields = ["item.width", "item.depth", "item.x", "item.y", "item.rotation"]
    width = resolver.resolve(item_data.get("width"), "item.width", "assembled_width")
    depth = resolver.resolve(item_data.get("depth"), "item.depth", "assembled_depth")
    x = resolver.resolve(item_data.get("position", {}).get("x"), "item.x", "position_x")
    y = resolver.resolve(item_data.get("position", {}).get("y"), "item.y", "position_y")
    angle = resolver.resolve(item_data.get("rotation"), "item.rotation", "rotation")
    item = None if any(v is None for v in (width, depth, x, y, angle)) else rotated(x, y, width, depth, angle)

    def check(ident: str, kind: str, ok: bool | None, refs: list[str], **extra) -> None:
        outcome = "BLOCKED" if ok is None else "PASS" if ok else "CONFLICT"
        result["checks"].append({"id": ident, "kind": kind, "outcome": outcome,
                                 "evidence_ids": refs, **extra})
        if ok is False:
            result["findings"].append(_issue(f"{kind.upper()}_CONFLICT", ident,
                                            f"Explicit {kind} condition violated.", refs))

    check("item_containment", "containment", contained(item, room) if item and room else None,
          resolver.refs(*(room_fields + item_fields)))
    reservations: list[tuple[str, Rectangle | None, list[str]]] = []
    for group in ("openings", "explicit_exclusions"):
        for data in request.get(group, []):
            prefix = f"{group}.{data['id']}"
            fields = [f"{prefix}.{key}" for key in ("x", "y", "width", "depth")]
            vals = [resolver.resolve(data.get("position", {}).get("x"), fields[0], "position_x"),
                    resolver.resolve(data.get("position", {}).get("y"), fields[1], "position_y"),
                    resolver.resolve(data.get("width"), fields[2], "reserved_width"),
                    resolver.resolve(data.get("depth"), fields[3], "reserved_depth")]
            rect = None if any(v is None for v in vals) else Rectangle(*vals)
            reservations.append((prefix, rect, fields))
            check(f"item_vs_{prefix}", "intersection", not intersects(item, rect) if item and rect else None,
                  resolver.refs(*(item_fields + fields)))
    # Reserved zones may overlap each other intentionally. They are not two
    # physical items: only item-vs-reservation intersection is a V0 constraint.
    obstacles = [r for _, r, _ in reservations if r is not None]
    obstacle_fields = [field for _, _, fields in reservations for field in fields]
    complete = item is not None and room is not None and len(obstacles) == len(reservations)
    for data in request.get("required_clearances", []):
        field = f"required_clearances.{data['id']}.required"
        required = resolver.resolve(data.get("required"), field, "required_clearance")
        refs = resolver.refs(*(room_fields + item_fields + obstacle_fields + [field]))
        if not complete or required is None:
            check(data["id"], "clearance", None, refs)
        else:
            actual = clearance(item, room, obstacles, data["side"])
            check(data["id"], "clearance", actual >= required, refs,
                  actual_cm=number_text(actual), required_cm=number_text(required))
    result["blockers"].extend(resolver.blockers)
    result["normalized"] = resolver.normalized

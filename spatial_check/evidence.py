"""Resolve references against independently supplied intake, never LLM assertions."""
from decimal import Decimal
from .units import InputError, normalize, number_text


class EvidenceResolver:
    def __init__(self, facts: list[dict]):
        self.facts = {fact["id"]: fact for fact in facts}
        self.groups: dict[str, list[dict]] = {}
        for fact in facts:
            self.groups.setdefault(fact["field"], []).append(fact)
        self.blockers: list[dict] = []
        self.normalized: list[dict] = []
        self.used: dict[str, list[str]] = {}

    def block(self, code: str, field: str, message: str, ids: list[str]) -> None:
        self.blockers.append({"code": code, "field": field, "message": message,
                              "evidence_ids": ids})

    def _value(self, fact: dict, field: str, meaning: str,
               visiting: frozenset[str] = frozenset()) -> Decimal:
        if fact["id"] in visiting or len(visiting) >= 32:
            raise InputError("Cyclic/overlong derivation.")
        if fact["field"] != field or fact["meaning"] != meaning:
            raise InputError("Evidence field/meaning mismatch; packaging is not assembled size.")
        if fact["status"] not in ("PROVIDED", "DERIVED"):
            raise InputError(f"Evidence status {fact['status']} cannot establish geometry.")
        value = normalize(fact["value"], fact["unit"], meaning)
        if fact["status"] == "PROVIDED":
            if fact["source"]["kind"] not in ("user_measurement", "user_confirmation", "document_dimension"):
                raise InputError("Photo/model/engine assertion is not a provided measurement.")
            if "derivation" in fact:
                raise InputError("PROVIDED must not carry a derivation.")
        else:
            derivation = fact.get("derivation")
            if not derivation or fact["source"]["kind"] != "engine":
                raise InputError("DERIVED requires an explicit engine unit-conversion lineage.")
            parent = self.facts.get(derivation["input"])
            if parent is None:
                raise InputError("Missing derivation parent.")
            original = self._value(parent, field, meaning, visiting | {fact["id"]})
            if original != value:
                raise InputError("Claimed derivation differs from recomputed unit conversion.")
        return value

    def resolve(self, ref: object, field: str, meaning: str) -> Decimal | None:
        group = self.groups.get(field, [])
        ids = [fact["id"] for fact in group]
        self.used[field] = ids
        if type(ref) is not str or ref not in self.facts:
            self.block("MISSING_EVIDENCE", field, "Missing position/dimension/rotation or evidence reference.", ids)
            return None
        if self.facts[ref]["field"] != field:
            self.block("REFERENCE_MISMATCH", field, "Reference belongs to another field.", [ref])
            return None
        values = []
        invalid = False
        # Evaluate ALL sources for this field, not just the one the LLM selects.
        for fact in group:
            try:
                values.append(self._value(fact, field, meaning))
            except InputError as exc:
                invalid = True
                self.block("UNUSABLE_EVIDENCE", field, str(exc), [fact["id"]])
        if len(set(values)) > 1:
            invalid = True
            self.block("CONFLICTING_EVIDENCE", field, "Sources disagree after unit normalization.", ids)
        if invalid or not values:
            return None
        value = values[0]
        self.normalized.append({"field": field, "value": number_text(value),
                                "unit": "deg" if meaning == "rotation" else "cm",
                                "evidence_ids": ids})
        return value

    def refs(self, *fields: str) -> list[str]:
        return sorted({ref for field in fields for ref in self.used.get(field, [])})

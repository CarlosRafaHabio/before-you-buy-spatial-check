"""Exact decimal parsing; no geometric epsilon, rounding or guessed units."""
from decimal import Decimal
import re

FACTORS = {"mm": Decimal("0.1"), "cm": Decimal(1), "m": Decimal(100)}
MAX_CM = Decimal("1000000")  # Computational domain, NOT an architectural rule.
MAX_DECIMAL_PLACES = 6
NUMBER = re.compile(r"-?\d{1,12}(?:[.,]\d{1,6})?\Z", re.ASCII)


class InputError(ValueError):
    pass


def reject_ambiguous_number(value: object) -> None:
    """Refuse one conventional thousands group; never infer the intended locale.

    Other invalid syntax is left to decimal_value. A zero integer part is not
    a conventional thousands prefix, so explicit small decimals remain usable.
    """
    if type(value) is not str or not NUMBER.fullmatch(value):
        return
    parts = re.split(r"[.,]", value.lstrip("-"))
    if (len(parts) == 2 and 1 <= len(parts[0]) <= 3
            and int(parts[0]) != 0 and len(parts[1]) == 3):
        raise InputError(f"Ambiguous numeric representation {value!r}; explicitly clarify "
                         "the value and submit an unambiguous decimal or ungrouped integer.")


def decimal_value(value: object) -> Decimal:
    # JSON integers or decimal strings only: do not import float uncertainty.
    if type(value) is int:
        text = str(value)
    elif type(value) is str:
        text = value
    else:
        raise InputError("Use an integer or decimal string, not float/bool/null.")
    if not NUMBER.fullmatch(text):
        raise InputError("Invalid decimal; no grouping separators/exponents; max 6 decimals.")
    reject_ambiguous_number(value)
    return Decimal(text.replace(",", "."))


def normalize(value: object, unit: object, meaning: str) -> Decimal:
    n = decimal_value(value)
    if meaning == "rotation":
        if unit != "deg" or n not in (0, 90, 180, 270):
            raise InputError("Rotation must explicitly be 0, 90, 180 or 270 deg.")
        return n
    if type(unit) is not str or unit not in FACTORS:
        raise InputError("Missing/unsupported length unit; supported: mm, cm, m.")
    # Scaling by a power of ten is exact and independent of caller decimal context.
    exponent = {"mm": -1, "cm": 0, "m": 2}[unit]
    tup = n.as_tuple()
    n = Decimal((tup.sign, tup.digits, tup.exponent + exponent))
    if n.copy_abs() > MAX_CM:
        raise InputError("Outside V0 numeric domain: absolute length > 1000000 cm.")
    if meaning in ("usable_width", "usable_depth", "assembled_width", "assembled_depth",
                   "reserved_width", "reserved_depth") and n <= 0:
        raise InputError("A dimension must be strictly positive.")
    if meaning == "required_clearance" and n < 0:
        raise InputError("Required clearance must be nonnegative.")
    return n


def number_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if value == 0 else text

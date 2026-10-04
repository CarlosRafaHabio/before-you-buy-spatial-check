"""Strict untrusted JSON parsing. Parsing never emits trusted evidence."""
import json
from pathlib import Path


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key.")
        result[key] = value
    return result


def loads(raw: str | bytes):
    if len(raw) > 2_000_000:
        raise ValueError("Payload too large.")
    def invalid_constant(_):
        raise ValueError("Non-finite JSON number.")
    return json.loads(raw, object_pairs_hook=unique_keys, parse_constant=invalid_constant)


def load(path):
    with Path(path).open("rb") as file:
        raw = file.read(2_000_001)
    return loads(raw)

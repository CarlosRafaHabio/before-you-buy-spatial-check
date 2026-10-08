"""Offline, cooperative information-flow experiment inspired by CaMeL.

NOT a sandbox, authentication system, data provenance attestation, tool router,
or replacement for HostIntake. This module is deliberately NOT wheel-packaged.
Only the trusted host may construct the policy and label input origins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Iterable
import re

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z", re.ASCII)
_MAX_TEXT = 16384
_MAX_ORIGINS = 64
_HOST_ONLY_OPERATIONS = frozenset({
    "host.confirm_evidence",
    "host.revoke_evidence",
    "host.issue_receipt",
    "external_authority.restore",
    "external_authority.write",
})


class FlowInputError(ValueError):
    """Untracked, unbounded, or malformed flow metadata."""


def _identifier(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _readers(value: frozenset[str] | None) -> bool:
    return value is None or (
        type(value) is frozenset and all(_identifier(x) for x in value)
    )


@dataclass(frozen=True, slots=True)
class FlowText:
    """A snapshot of text plus conservative labels; labels are NOT credentials.

    readers=None means unrestricted disclosure at the *policy* level.
    A finite set limits destinations. An empty set prohibits every destination.
    untrusted is sticky under derive operations and can never be cleared here.
    """

    text: str = field(repr=False)
    origins: frozenset[str]
    untrusted: bool
    readers: frozenset[str] | None

    def __post_init__(self) -> None:
        if (type(self.text) is not str or len(self.text) > _MAX_TEXT
                or type(self.origins) is not frozenset
                or len(self.origins) == 0 or len(self.origins) > _MAX_ORIGINS
                or any(not _identifier(x) for x in self.origins)
                or type(self.untrusted) is not bool or not _readers(self.readers)):
            raise FlowInputError("Invalid tracked text/label.")

    def __bool__(self) -> bool:
        raise TypeError(
            "A FlowText cannot decide control flow implicitly; pass explicit "
            "control_dependencies to the selected output and to policy checks."
        )


def external_text(text: str, *, origin: str,
                  readers: frozenset[str] | None = None) -> FlowText:
    """Trusted intake labels external material; an LLM cannot assign trust."""
    return FlowText(text, frozenset({origin}), True, readers)


def host_text(text: str, *, origin: str,
              readers: frozenset[str] | None = None) -> FlowText:
    """Trusted host literal; never expose this constructor as an agent tool."""
    return FlowText(text, frozenset({origin}), False, readers)


def _tracked(values: Iterable[FlowText]) -> tuple[FlowText, ...]:
    try:
        snapshot = tuple(values)
    except TypeError as exc:
        raise FlowInputError("Expected iterable of tracked values.") from exc
    if any(type(x) is not FlowText for x in snapshot):
        raise FlowInputError("Untracked data cannot participate in derivation.")
    return snapshot


def _combine_labels(values: tuple[FlowText, ...]) -> tuple[frozenset[str], bool, frozenset[str] | None]:
    if not values:
        raise FlowInputError("Derivation requires tracked dependencies.")
    origins: frozenset[str] = frozenset()
    untrusted = False
    readers: frozenset[str] | None = None
    for item in values:
        origins = origins.union(item.origins)
        if len(origins) > _MAX_ORIGINS:
            raise FlowInputError("Too many provenance origins.")
        untrusted = untrusted or item.untrusted
        if item.readers is not None:
            readers = item.readers if readers is None else readers.intersection(item.readers)
    return origins, untrusted, readers


def concat_text(*parts: FlowText,
                control_dependencies: Iterable[FlowText] = ()) -> FlowText:
    """Join text and BOTH data/control labels. Only declared controls are tracked."""
    operands = _tracked(parts)
    controls = _tracked(control_dependencies)
    if not operands:
        raise FlowInputError("No text operands.")
    text = "".join(part.text for part in operands)
    origins, untrusted, readers = _combine_labels(operands + controls)
    return FlowText(text, origins, untrusted, readers)


def control_derived_text(selected: FlowText, *,
                         control_dependencies: Iterable[FlowText]) -> FlowText:
    """Mark even an unchanged/literal branch output as control-dependent."""
    item = _tracked((selected,))
    controls = _tracked(control_dependencies)
    if not controls:
        raise FlowInputError("Explicit control dependencies are mandatory.")
    origins, untrusted, readers = _combine_labels(item + controls)
    return FlowText(selected.text, origins, untrusted, readers)


@dataclass(frozen=True, slots=True)
class Operation:
    name: str
    kind: str   # "pure" or "external" (reads, writes, network, or other effects)
    destination: str

    def __post_init__(self) -> None:
        if (not _identifier(self.name)
                or self.kind not in ("pure", "external")
                or not _identifier(self.destination)):
            raise FlowInputError("Invalid trusted host operation policy.")


@dataclass(frozen=True, slots=True)
class Decision:
    allowed: bool
    code: str


class FlowGuard:
    """Allowlist-only, fail-closed, side-effect-free policy decision helper.

    All actual operation arguments AND all control dependencies must be supplied.
    Pure means truly local and side-effect-free, not merely an HTTP GET.
    No trust endorsement, downgrade or declassification path exists in V0.
    """

    def __init__(self, operations: Iterable[Operation]):
        rules: dict[str, Operation] = {}
        for rule in operations:
            if type(rule) is not Operation or rule.name in rules:
                raise FlowInputError("Invalid or duplicate operation.")
            # Copy the validated policy: no retained caller-owned Operation alias.
            rules[rule.name] = Operation(rule.name, rule.kind, rule.destination)
        self._rules = MappingProxyType(rules)

    def check(self, operation: str, *,
              arguments: Iterable[FlowText],
              control_dependencies: Iterable[FlowText] = ()) -> Decision:
        if not _identifier(operation):
            return Decision(False, "DENY_INVALID_OPERATION")
        if operation in _HOST_ONLY_OPERATIONS:
            return Decision(False, "DENY_HOST_ONLY")
        rule = self._rules.get(operation)
        if rule is None:
            return Decision(False, "DENY_UNKNOWN_OPERATION")
        try:
            tracked = _tracked(arguments) + _tracked(control_dependencies)
        except FlowInputError:
            return Decision(False, "DENY_UNTRACKED_INPUT")
        # Confidentiality is orthogonal to integrity. A trusted secret is not public.
        if any(x.readers is not None and rule.destination not in x.readers
               for x in tracked):
            return Decision(False, "DENY_READER")
        if rule.kind == "external" and any(x.untrusted for x in tracked):
            return Decision(False, "DENY_UNTRUSTED_INFLUENCE")
        return Decision(True, "ALLOW")

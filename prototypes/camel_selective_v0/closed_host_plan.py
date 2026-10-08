"""G2-b: a closed, host-owned expression plan for synthetic external effects.

The trusted host constructs the plan, source slots, handler and destination.
At run-time, callers provide ONLY raw strings for predetermined untrusted slots.
Unlike G2-a, neither trusted FlowText labels nor control dependency lists can
be supplied through run(). Branch labels are calculated inside this tiny AST.

This is NOT an arbitrary-Python monitor, a secure sandbox, source authentication,
a general CaMeL implementation, or a substitute for HostIntake.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .flow_guard import (
    FlowInputError, FlowText, concat_text, control_derived_text,
    external_text, host_text,
)
from .host_dispatch import (
    BoundHostDispatcher, BoundTool, DispatchOutcome,
)


_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z", re.ASCII)
_MAX_NODES = 96
_MAX_DEPTH = 16
_MAX_SLOTS = 32
_MAX_ARGUMENTS = 16


def _name(value: object) -> bool:
    return type(value) is str and _NAME.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class ExternalSlot:
    """A trusted-host manifest entry. Every runtime-provided slot is untrusted."""
    name: str
    origin: str
    readers: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if (not _name(self.name) or not _name(self.origin)
                or (self.readers is not None and
                    (type(self.readers) is not frozenset or
                     any(not _name(x) for x in self.readers)))):
            raise FlowInputError("Invalid trusted source manifest.")


@dataclass(frozen=True, slots=True)
class Literal:
    """A trusted host-authored literal, never built from a model response."""
    value: str


@dataclass(frozen=True, slots=True)
class Source:
    """Reference to a host-manifested untrusted input slot."""
    name: str


@dataclass(frozen=True, slots=True)
class Join:
    parts: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class Equals:
    """Explicit predicate whose operands become control dependencies."""
    left: object
    right: object


@dataclass(frozen=True, slots=True)
class Choose:
    condition: Equals
    when_true: object
    when_false: object


@dataclass(frozen=True, slots=True)
class HostPlan:
    """The host chooses one fixed registered operation and all its arguments."""
    operation: str
    arguments: tuple[object, ...]


class ClosedHostExecutor:
    """Narrow, cooperative executor; no caller-provided labels or Python code.

    This records explicit conditions within a closed AST, but cannot detect
    branches elsewhere in the host, untrusted plan construction, or direct tool
    calls outside the dispatcher. It cannot prove physical source authenticity.
    """
    def __init__(self, *, tool: BoundTool, slots: tuple[ExternalSlot, ...],
                 plan: HostPlan):
        if (type(tool) is not BoundTool or type(slots) is not tuple
                or len(slots) > _MAX_SLOTS or
                any(type(s) is not ExternalSlot for s in slots)
                or type(plan) is not HostPlan
                or plan.operation != tool.name
                or type(plan.arguments) is not tuple
                or not (1 <= len(plan.arguments) <= _MAX_ARGUMENTS)):
            raise FlowInputError("Invalid closed-host registration.")
        slot_names = {s.name for s in slots}
        if len(slot_names) != len(slots):
            raise FlowInputError("Duplicate untrusted source slot.")
        nodes = [0]
        for expr in plan.arguments:
            self._validate_expr(expr, slot_names, nodes, 0)
        self._slots = {s.name: s for s in slots}
        self._plan = plan
        self._dispatcher = BoundHostDispatcher((tool,))

    @classmethod
    def _validate_expr(cls, expr: object, names: set[str],
                       nodes: list[int], depth: int) -> None:
        nodes[0] += 1
        if nodes[0] > _MAX_NODES or depth > _MAX_DEPTH:
            raise FlowInputError("Host plan exceeds safe structural limits.")
        if type(expr) is Literal:
            host_text(expr.value, origin="host.program")
        elif type(expr) is Source:
            if not _name(expr.name) or expr.name not in names:
                raise FlowInputError("Source absent from host manifest.")
        elif type(expr) is Join:
            if (type(expr.parts) is not tuple or
                    not (1 <= len(expr.parts) <= _MAX_ARGUMENTS)):
                raise FlowInputError("Invalid host-plan join.")
            for value in expr.parts:
                cls._validate_expr(value, names, nodes, depth + 1)
        elif type(expr) is Choose:
            if type(expr.condition) is not Equals:
                raise FlowInputError("Only declared equality predicates supported.")
            nodes[0] += 1
            cls._validate_expr(expr.condition.left, names, nodes, depth + 1)
            cls._validate_expr(expr.condition.right, names, nodes, depth + 1)
            cls._validate_expr(expr.when_true, names, nodes, depth + 1)
            cls._validate_expr(expr.when_false, names, nodes, depth + 1)
        else:
            raise FlowInputError("No arbitrary calls, code or expressions allowed.")

    @classmethod
    def _evaluate(cls, expr: object, inputs: dict[str, FlowText]) -> FlowText:
        if type(expr) is Literal:
            return host_text(expr.value, origin="host.program")
        if type(expr) is Source:
            return inputs[expr.name]
        if type(expr) is Join:
            return concat_text(*(cls._evaluate(x, inputs) for x in expr.parts))
        if type(expr) is Choose:
            left = cls._evaluate(expr.condition.left, inputs)
            right = cls._evaluate(expr.condition.right, inputs)
            branch = expr.when_true if left.text == right.text else expr.when_false
            chosen = cls._evaluate(branch, inputs)
            return control_derived_text(chosen, control_dependencies=(left, right))
        raise FlowInputError("Unexpected closed-plan expression.")

    def invoke(self, raw_inputs: dict[str, str]) -> DispatchOutcome:
        """Execute trusted, pre-registered plan with raw UNTRUSTED slot values."""
        if (type(raw_inputs) is not dict or
                raw_inputs.keys() != self._slots.keys() or
                any(type(s) is not str for s in raw_inputs.values())):
            return DispatchOutcome(False, "DENY_INPUT_MANIFEST_MISMATCH")
        try:
            inputs = {
                key: external_text(value, origin=slot.origin, readers=slot.readers)
                for key, slot in self._slots.items()
                for value in (raw_inputs[key],)
            }
            arguments = tuple(
                self._evaluate(expr, inputs) for expr in self._plan.arguments
            )
        except (FlowInputError, TypeError, ValueError, RecursionError):
            return DispatchOutcome(False, "DENY_INVALID_PLAN_VALUE")
        # The AST interpreter incorporated every internal Choose predicate in
        # the corresponding output argument. Other host Python control flow
        # is not tracked and MUST NOT control whether invoke() is called.
        return self._dispatcher.invoke(
            self._plan.operation, arguments=arguments, control_dependencies=()
        )

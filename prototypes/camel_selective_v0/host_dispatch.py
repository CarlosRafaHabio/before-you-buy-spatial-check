"""G2-a: host-owned synthetic dispatch. NOT a hostile-Python security sandbox.

Runs policy and the registered callback in one host-controlled code path,
with a private exact snapshot of the arguments. Control dependencies and
provenance still depend on the genuine trusted host. This helper cannot stop
direct calls to other Python libraries or malicious callbacks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Iterable

from .flow_guard import (
    FlowGuard, FlowInputError, FlowText, Operation,
)


_MAX_ARGS = 32
_MAX_CONTROLS = 64


@dataclass(frozen=True, slots=True)
class BoundTool:
    """Tool/handler registration performed exclusively by trusted host bootstrap."""
    name: str
    destination: str
    handler: Callable[[tuple[str, ...]], None] = field(repr=False)

    def __post_init__(self) -> None:
        # No host authority operation can be mediated as an ordinary agent tool,
        # even under a newly suffixed name.
        if (type(self.name) is not str or
                self.name.startswith(("host.", "external_authority.")) or
                not callable(self.handler)):
            raise FlowInputError("Privileged or invalid handler registration.")
        Operation(self.name, "external", self.destination)


@dataclass(frozen=True, slots=True)
class DispatchOutcome:
    attempted: bool
    code: str


class BoundHostDispatcher:
    """Synthetic external-tool reference monitor for a cooperative trusted host.

    Handles only the tools supplied at trusted initialization. The host must not
    expose these callbacks or any parallel direct tool access to untrusted code.
    No user/source authentication, implicit control tainting, or side-effect
    rollback is implemented.
    """

    def __init__(self, tools: Iterable[BoundTool]):
        registered: dict[str, BoundTool] = {}
        for tool in tools:
            if type(tool) is not BoundTool or tool.name in registered:
                raise FlowInputError("Invalid or duplicate tool registration.")
            # Snapshot registration; caller may retain/mutate their BoundTool.
            registered[tool.name] = BoundTool(
                tool.name, tool.destination, tool.handler,
            )
        self._tools = MappingProxyType(registered)
        self._guard = FlowGuard(
            Operation(x.name, "external", x.destination)
            for x in registered.values()
        )

    @staticmethod
    def _snapshot(values: object, *, max_count: int) -> tuple[FlowText, ...] | None:
        # Tuple only: reject generators/side effects and mutable sequences.
        if type(values) is not tuple or len(values) > max_count:
            return None
        if any(type(x) is not FlowText for x in values):
            return None
        try:
            # Independent snapshots make policy checks and invoked bytes agree.
            return tuple(
                FlowText(x.text, x.origins, x.untrusted, x.readers)
                for x in values
            )
        except (FlowInputError, TypeError, ValueError):
            return None

    def invoke(
        self,
        operation: str,
        *,
        arguments: tuple[FlowText, ...],
        control_dependencies: tuple[FlowText, ...] | None = None,
    ) -> DispatchOutcome:
        if type(operation) is not str or operation not in self._tools:
            return DispatchOutcome(False, "DENY_UNKNOWN_OPERATION")
        if control_dependencies is None:
            return DispatchOutcome(False, "DENY_MISSING_CONTROL_CONTEXT")
        args = self._snapshot(arguments, max_count=_MAX_ARGS)
        controls = self._snapshot(control_dependencies, max_count=_MAX_CONTROLS)
        if args is None or controls is None:
            return DispatchOutcome(False, "DENY_UNTRACKED_INPUT")
        if not args:
            return DispatchOutcome(False, "DENY_EMPTY_ARGUMENTS")

        decision = self._guard.check(
            operation, arguments=args, control_dependencies=controls,
        )
        if not decision.allowed:
            return DispatchOutcome(False, decision.code)

        # An invocation can have an ambiguous effect if the callback raises.
        # NEVER automatically retry or claim transactional completion.
        try:
            self._tools[operation].handler(tuple(v.text for v in args))
        except Exception:
            return DispatchOutcome(True, "HANDLER_OUTCOME_UNKNOWN")
        return DispatchOutcome(True, "HANDLER_RETURNED")

"""H12 — minimal, fixed host-side Monty bridge (RESEARCH / TEST ONLY).

The guest can call only "lookup_user"; host policy and the registered callback
remain outside the Monty VM. Every run gets a NEW guest session and a FIXED
lookup binding, so a cached function proxy cannot be rebound across feeds.

This is cooperative trusted-host hardening, NOT authenticated agent intent,
signed human authorization, a real OS sandbox, or a deadline that can
interrupt an arbitrary blocking host callback. Production engine untouched.

Optional pydantic-monty is only imported during run(), not a wheel dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sysconfig
from time import monotonic

from .scoped_data_use_v0 import HostScopedUserLookup

_TOOL_NAME = "lookup_user"
_MAX_SOURCE_BYTES = 4096
_ALLOWED_MAX_CALLS = 8
_MAX_MEMORY = 4_000_000
_MAX_FEED_SECS = 0.25
_MAX_SUSPENSIONS = 32


@dataclass(frozen=True, slots=True)
class GuestRunResult:
    status: str
    value: object = None
    callback_calls: int = 0
    effect_attempts: int = 0


@dataclass(frozen=True, slots=True, init=False)
class MontyHostBridgeV0:
    """One trusted host-scoped gate + one fixed exported callback name.

    The gate MUST be created from a real host authorization independently of
    untrusted model/prompt content. Passing it to this bridge cannot make its
    provenance trusted. All effects are synthetic in our test harness.
    """
    _gate: HostScopedUserLookup
    _max_calls: int
    _wall_budget_secs: float

    def __init__(self, gate: HostScopedUserLookup, *,
                 max_calls: int = 4, wall_budget_secs: float = 0.5) -> None:
        if type(gate) is not HostScopedUserLookup:
            raise ValueError("Trusted host gate is required.")
        if type(max_calls) is not int or not 1 <= max_calls <= _ALLOWED_MAX_CALLS:
            raise ValueError("Invalid callback call budget.")
        if (type(wall_budget_secs) not in (int, float)
                or not 0.01 <= wall_budget_secs <= 5.0):
            raise ValueError("Invalid wall budget.")
        object.__setattr__(self, "_gate", gate)
        object.__setattr__(self, "_max_calls", max_calls)
        object.__setattr__(self, "_wall_budget_secs", float(wall_budget_secs))

    def run(self, source: object) -> GuestRunResult:
        if type(source) is not str:
            return GuestRunResult("DENY_INVALID_PROGRAM")
        try:
            encoded = source.encode("utf-8", errors="strict")
        except UnicodeError:
            return GuestRunResult("DENY_INVALID_PROGRAM")
        if not encoded or len(encoded) > _MAX_SOURCE_BYTES:
            return GuestRunResult("DENY_INVALID_PROGRAM")

        # Do not resolve Monty worker binary through PATH or MONTY_BIN:
        # upstream explicitly recommends a trusted explicit binary_path.
        binary_path = Path(sysconfig.get_path("scripts")) / "monty"
        if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
            return GuestRunResult("DENY_MONTY_BINARY_UNAVAILABLE")

        # Effects are host-scoped and counted even if callback times out or
        # fails ambiguously. These counters are observational, not receipts.
        calls = 0
        attempts = 0
        post_effect_deadline = False
        deadline = monotonic() + self._wall_budget_secs

        def lookup_user(*args: object, **kwargs: object) -> str:
            nonlocal calls, attempts, post_effect_deadline
            if monotonic() >= deadline:
                return "DENY_HOST_WALL_BUDGET"
            if calls >= self._max_calls:
                return "DENY_HOST_CALL_QUOTA"
            calls += 1
            if kwargs or len(args) != 1 or type(args[0]) is not str:
                return "DENY_INVALID_CALL_SHAPE"
            try:
                decision = self._gate.invoke(args[0])
                if decision.attempted:
                    attempts += 1
                result = decision.code
            except Exception:
                result = "DENY_INTERNAL_ERROR"
            if monotonic() >= deadline:
                post_effect_deadline = True
            return result

        try:
            # Import remains opt-in/test-only; host code passes no model
            # supplied callback maps, objects, mounts, or OS handler.
            from pydantic_monty import Monty
            with Monty(binary_path=str(binary_path), request_timeout=3) as pool:
                with pool.checkout(limits={
                    "max_memory": _MAX_MEMORY,
                    "max_feed_duration_secs": _MAX_FEED_SECS,
                    "max_suspensions": _MAX_SUSPENSIONS,
                }) as session:
                    result = session.feed_run(
                        source,
                        external_lookup={_TOOL_NAME: lookup_user},
                    )
        except Exception:
            # No raw worker or trusted host exception to caller/guest.
            if post_effect_deadline or monotonic() >= deadline:
                return GuestRunResult("HOST_WALL_BUDGET_EXCEEDED_UNKNOWN",
                                      None, calls, attempts)
            return GuestRunResult("GUEST_EXECUTION_REJECTED",
                                  None, calls, attempts)

        if post_effect_deadline or monotonic() >= deadline:
            # This is an OBSERVATION after return, not preemption. The agent
            # may already have observed a status before this check.
            return GuestRunResult("HOST_WALL_BUDGET_EXCEEDED_UNKNOWN",
                                  None, calls, attempts)
        return GuestRunResult("COMPLETED", result, calls, attempts)

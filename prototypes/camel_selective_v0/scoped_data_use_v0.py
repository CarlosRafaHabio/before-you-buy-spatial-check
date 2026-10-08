"""G5-a: a *narrow* syntactically valid, host-scoped external data-use experiment.

No generic taint clearing, declassification, trust endorsement, arbitrary
operation selection, or public Spatial Check runtime integration is provided.

Only trusted bootstrap code may construct this object and hold its callback.
A caller supplies just one raw string. The host already independently chose
the exact approved USER id, fixed operation and fixed destination.
This is NOT caller authentication, durable replay protection, or a sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from threading import Lock
from typing import Callable

from .flow_guard import external_text


_USER_ID = re.compile(r"USR-[0-9]{4}\Z", re.ASCII)
_OPERATION = "directory.lookup_user"
_DESTINATION = "directory.internal"
_ORIGIN = "external.user_id"


@dataclass(frozen=True, slots=True)
class LookupOutcome:
    attempted: bool
    code: str
    source_origin: str | None = None
    source_untrusted: bool = False


class HostScopedUserLookup:
    """Exactly one permitted lookup of an independently host-approved USER id.

    No agent-provided policy, destination, operation, callback or trusted label.
    The caller MAY choose whether to invoke and is not authenticated: the
    embedding host MUST make this private to an authorized, trusted call path.
    The callback is entirely inside the TCB and is NOT isolated by this object.
    """

    __slots__ = ("_approved_user_id", "_handler", "_used", "_lock")

    def __init__(
        self,
        *,
        approved_user_id: str,
        handler: Callable[[tuple[str, ...]], None],
    ) -> None:
        if (type(approved_user_id) is not str
                or _USER_ID.fullmatch(approved_user_id) is None):
            raise ValueError("Host scope requires one exact canonical user id.")
        if not callable(handler):
            raise ValueError("Host scope requires a trusted callback.")
        # These bytes come only from independently trusted host bootstrap, never
        # from text extracted from a page, a model response, or user-provided JSON.
        self._approved_user_id = approved_user_id
        self._handler = handler
        self._used = False
        self._lock = Lock()

    @property
    def operation(self) -> str:
        return _OPERATION

    @property
    def destination(self) -> str:
        return _DESTINATION

    def invoke(self, raw_external_id: object) -> LookupOutcome:
        if (type(raw_external_id) is not str
                or len(raw_external_id) != 8
                or _USER_ID.fullmatch(raw_external_id) is None):
            return LookupOutcome(False, "DENY_INVALID_IDENTIFIER")
        # A correct shape is NOT authorization, and does not upgrade the text.
        if raw_external_id != self._approved_user_id:
            return LookupOutcome(False, "DENY_OUT_OF_SCOPE")

        # Consume before attempting a potentially irrevocable external effect.
        # A failed callback may have acted; never retry automatically.
        with self._lock:
            if self._used:
                return LookupOutcome(False, "DENY_REPLAY_PROCESS_LOCAL")
            self._used = True

        # This snapshot remains untrusted. We authorize ONE parameter use,
        # not a change of integrity or a reusable host capability.
        value = external_text(
            raw_external_id,
            origin=_ORIGIN,
            readers=frozenset({_DESTINATION}),
        )
        try:
            self._handler((value.text,))
        except Exception:
            return LookupOutcome(True, "HANDLER_OUTCOME_UNKNOWN",
                                 _ORIGIN, True)
        return LookupOutcome(True, "HANDLER_RETURNED", _ORIGIN, True)

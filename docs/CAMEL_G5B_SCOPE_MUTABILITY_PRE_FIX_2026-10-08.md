# G5-b pre-fix negative evidence — scope/handler/replay mutation

**EXPERIMENTAL / OFFLINE ONLY — NOT AN AGENT SECURITY BOUNDARY**

The G5-a class HostScopedUserLookup has __slots__ but no frozen
registration. A caller retaining its live reference can use *ordinary Python
assignment* to replace the registered approved ID or callback, or reset the
one-shot boolean after it was consumed. This is weaker than G4-a's protective
registration snapshots and is a correctable accidental-mutation issue.

The seven tests intentionally PASS before the fix:

- G5B01: mutate _approved_user_id -> different ID allowed.
- G5B02: swap _handler -> different callback receives argument.
- G5B03: reset _used -> repeated effect in same instance.
- G5B04: new instance with same scope -> cross-instance replay allowed.
- G5B05: holder reads approved ID. The ID is not secret/authentication.
- G5B06: callback receives raw string; provenance label is not enforced by sink.
- G5B07: callback closure can emit unrelated synthetic secret.

**The first three are a narrow engineering bug, not an externally proven exploit.**
G5B04-07 depend on stronger architectural/TCB assumptions and remain
unresolved even with frozen facade.

Next commit: freeze public registration facade and move mutable one-shot state
behind a private state object; invert first three assertions to prevent ordinary
attribute reconfiguration. Python reflection/object.__setattr__, access to
private state or direct callback calls STILL defeats same-process isolation.
Only process separation / privileged adapter can address that threat class.

No main merge, runtime publication, AWS, SQL, Habio integration or real effects.

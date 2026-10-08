# H11 — new adversarial host callback boundary audit (Monty 1.1.0)

PR #14 DRAFT, TEST ONLY. Cases are independent of the 21-case G3 corpus,
though they reuse the already implemented HostScopedUserLookup synthetic gate.
Monty v1.1.0 installed only in branch CI, no public wheel dependency.

Prior art inspected in pydantic/monty GitHub documentation, specifically:
- docs/host-functions.md: keyword argument pass-through and host exception
  messages that cross back into guest and are catchable;
- docs/limitations/host-values.md: retained host-function proxies dispatch
  by NAME against the *current* feed's external_lookup, not a fixed callback;
- docs/resource-limits.md: interpreter execution clock is paused during host
  callbacks; feed budget does not bound callback wall time or side effects;
- docs/security.md: guest has no ambient host authority, but every exposed
  host callback, host object and mount is a privileged capability.

H11 separately checks, with no real secrets or tools:
1. NEGATIVE: a host callback ValueError carrying a SYNTHETIC private string
   reaches model-controlled guest code unchanged.
2. NEGATIVE: unsafe host callback returns a SYNTHETIC secret directly.
3. POSITIVE: minimal strict host bridge refuses kwargs, extra arguments,
   non-string, dict/list/bool/null/int values *without consuming permission*.
4. POSITIVE: existing G5 gate sanitizes callback internal exception into
   HANDLER_OUTCOME_UNKNOWN and consumes one attempt, blocking automatic replay.
5. NEGATIVE: old guest-cached alias automatically resolves to a NEW, more
   privileged host callback if the host reuses the same external_lookup name
   during a later feed; no guest sandbox compromise needed, but trusted host
   misconfiguration is a prerequisite.
6. POSITIVE: removing that alias from external_lookup denies a stale proxy.
7. NEGATIVE: a worker bytecode execution timeout does NOT cap the duration
   of an external host callback. Explicit host-side deadlines must be separate.
8. NEGATIVE: a guest that learns/guesses a correct approved ID can call the
   host-exposed gate and consume its one-shot permission. Host intention and
   agent identity are not authenticated by the value alone.
9. POSITIVE: spoofed authority metadata is not accepted as a legitimate
   single user-id argument.
10. POSITIVE: one-shot gate survives repeated Monty feed_run calls within
    same host gate instance.

Only three host restrictions were coded in an **in-test static adapter**:
exact positional argument count, exact str type, no kwargs; exceptions
sanitized into constant status strings. A successful test does not
authenticate intent, human approval or literal origin. No general-purpose
policy engine is being added.

Decision GATE: verify original 360 tests and optional H9/H10/H11 on CI,
including CodeQL Python/Actions and separate PR security check. Record
novel negative findings and next minimal mitigation if verified; do not
declare Monty itself vulnerable to sandbox escape, since hostile-host
callbacks are a distinct TCB violation.

No main change, package release, AWS, Supabase, SQL, Vercel, Habio PR #43/#44
or paid resource. HOLD_SECURITY_PROMOTION.

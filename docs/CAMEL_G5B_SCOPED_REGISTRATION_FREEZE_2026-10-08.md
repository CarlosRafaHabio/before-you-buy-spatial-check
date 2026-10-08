# G5-b — scoped registration hardening, bounded acceptance

PR #14 remains DRAFT; this is offline experimental evidence only.

PRE-FIX witness commit: aa76058e915c2078fac19ed698ec95872e2853ad.
That commit deliberately reproduced 3 weak registrations by ordinary assignment:
changing the preapproved user ID, replacing callback and resetting a used bit.

POST-FIX: HostScopedUserLookup now uses a frozen dataclass facade and a
process-local mutable lock/attempt state. Ordinary reassignment of registered
ID, callback or used state fails; G5B01-03 verify safety under this *limited*
attacker model. G5B04-07 and G5B08-11 preserve unresolved witness cases:
independent gate instances can duplicate effects, gate holder reads ID,
callback receives raw string and may inspect globals, reflection still edits
internals or used state, callback is directly callable. They intentionally
PASS despite absence of a full trust boundary.

A dataclass is NOT tamper-proof against arbitrary Python in the same process.
No user authentication, origin attestation, tenant separation, durable replay
protection, provider idempotency, isolated handler or real API integration
has been added. Do not present this as a security boundary.

HOLD promotion until third external evaluation and an independently reviewed
host isolation design. Main, spatial_check/, Habio PR #43/#44, SQL, AWS and
production remain unmodified.

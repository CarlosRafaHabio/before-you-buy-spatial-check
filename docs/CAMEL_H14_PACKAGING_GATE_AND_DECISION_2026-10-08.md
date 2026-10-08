# H14 packaging/readback addendum (2026-10-08)

Final protocol evidence: H14_01 through H14_20 (20 fresh tests)
and 47 retained H9-H13 tests were executed in pinned Monty 1.1.0
CI: 67/67 PASS. Explicit second-wave negative witness:
H14_20 host deletes local SQLite and reissues same grant -> second
SYNTHETIC_EFFECT_V0 is observed; this is NOT a production security
boundary. H14_18 independent processes (12 concurrent real broker
dispatches, one ledger) produce exactly one effect and 11 denial codes.
Initial CI detected world-readable 0644 SQLite DB; fixed with explicit
os.open(mode 0600, O_NOFOLLOW) and host-private parent validation.

This final packaging-only commit makes the standard build assert H14
source and tests exist in extracted sdist and continues excluding
prototypes/security_monty from the installed wheel. Do not accept H14
until all HEAD checks finish SUCCESS, including the separate CodeQL
PR check, CodeQL Python/Actions, H8, Bandit/Hypothesis and zizmor.

Decision: ACCEPT_H14_BOUNDED_SYNTHETIC_DURABLE_CLAIM_EVIDENCE +
HOLD_AUTHENTICATED_AUTHORITY + HOLD_PROVIDER_IDEMPOTENCY +
HOLD_SECURITY_PROMOTION. No merges, paid cloud or production changes.

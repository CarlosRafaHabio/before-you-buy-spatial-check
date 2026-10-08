# H15 signed-approval test matrix and packaging closure (2026-10-08)

Research-only PR #14; the public Spatial Check geometry motor is
unchanged. Test-only PyCA cryptography==50.0.2 and Monty==1.1.0
installed only in the experimental Github Actions workflow.

Ed25519 is used as documented by official PyCA cryptography. No
private-key fixtures or static secrets are committed; a fresh ephemeral
key pair is generated in memory per test. The host verifier holds only
a trusted public-key mapping snapshot, with NO signing endpoint.

Initial H15 HEAD bab5254ad256d117df523b8e5b0d5a5d5b798417:
- Existing full source/sdist baseline test suite was 360/360 PASS.
- H15 new suite ran 18 tests and ONE assertion failed: a mutated
  operation was rejected with DENY_APPROVAL_SCOPE before signature
  verification rather than the expected DENY_INVALID_SIGNATURE.
  The untrusted operation was NOT executed.
- Fixed in f97547d673afe3d3768de525c2ac900f0a018f9f:
  issuer key ID selects a pretrusted public key; Ed25519 must verify
  exact canonical payload bytes BEFORE validating the signed operation,
  audience, actor_claim or context. No security assertion was weakened
  or test disabled.
- Follow-up H15 ALL 18/18 PASS, total H9-H15 85/85 PASS.

Positive tests: correct signature/fixed operation executes once; scope
replay across new ledger instance denied; fields altered after signing,
unknown issuer, different signing key, invalid format, duplicate JSON
keys, bool schema injection, oversized token, wrong audience or
operation, context mismatch, stale/future timestamps, unsigned/forged
scopes and wrong USER ID fail closed; concurrent threads with one
valid signed approval cause one synthetic effect; UNKNOWN broker effect
is not automatically retried.

NEGATIVE (tests PASS because risk is reproduced):
- Signer with private key can assert any ACTOR-NNNN without a real
  identity proof; issuer-signed actor_claim is not human approval.
- Same-UID trusted/malicious host can delete and recreate SQLite,
  replay still-valid signed grant and trigger a second synthetic effect.
- Trusted issuer can mint a new synthetic epoch for same USER id.
- H14 direct grant() route and all privileged host callbacks remain
  available to trusted host code. This H15 path does not enforce all
  effects globally.

This final packaging commit adds exact sdist assertions for H15
source and test; prototype and test remain excluded from public wheel.
Final HEAD CI must be verified across CodeQL PR security check,
CodeQL Python/Actions, tests push/PR, Hypothesis/Bandit, zizmor,
H8 isolation and optional Monty. If any failed, do not call H15 promoted.

Verdict: ACCEPT_H15_SIGNATURE_INTEGRITY_EVIDENCE +
HOLD_ACTUAL_HUMAN_APPROVAL + HOLD_TAMPER_RESISTANT_AUTHORITY +
HOLD_PROVIDER_IDEMPOTENCY + HOLD_SECURITY_PROMOTION. No merge,
production cloud/service, Habio changes, spending or real effects.

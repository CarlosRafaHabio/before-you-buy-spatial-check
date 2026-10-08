# H15 pre-signature scope-oracle regression and correction

Initial H15 CI on bab5254ad256d117df523b8e5b0d5a5d5b798417 ran
85 optional H9–H15 tests: 84 passed; H15_03 failed because the
tampered operation `admin.delete` was classified as
DENY_APPROVAL_SCOPE before the signature was verified, whereas the
expected authentication-first outcome was DENY_INVALID_SIGNATURE.
No real effect was allowed. All standard 360 tests and CodeQL/H8/Bandit/
zizmor succeeded on the initial implementation.

Bounded correction: require only canonical payload and well-formed trusted
issuer key ID to choose trusted public key, verify Ed25519 signature over
the exact entire canonical payload bytes, THEN evaluate signed
operation/audience/context/types/expiry/scope. Thus unsigned mutations
of an otherwise well-formed issuer payload report INVALID_SIGNATURE.
Validly signed wrong-scope grants are still denied by APPROVAL_SCOPE.

No tests suppressed or rewritten to mask a mismatch. Re-run complete H15
and all other CI before promotion; remains DRAFT and security HOLD.

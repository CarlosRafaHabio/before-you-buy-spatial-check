# H15 -- Asymmetric issuer-signature / synthetic approval scope

2026-10-08 · Before You Buy -- Spatial Check, PR #14 DRAFT / TEST ONLY.

H14 proved at-most-one dispatch in cooperative processes using local SQLite
but no authenticated approval. H15 introduces a tiny Ed25519 *verification*
step that receives only trusted issuer PUBLIC keys, using the mature PyCA
cryptography package (pinned in the optional test-only workflow; no public
wheel dependency). Public-key signature verification follows published PyCA
Ed25519 usage, NOT self-written cryptographic primitives:
https://github.com/pyca/cryptography/blob/main/docs/hazmat/primitives/asymmetric/ed25519.rst

The signer (PRIVATE key) exists only as an ephemeral in-memory synthetic
fixture inside security_monty/test_h15_signed_approval.py. The verifier
module contains NO private key, sign method, signature minting endpoint or
model-accessible issuer configuration.

A signed, strictly canonical JSON byte payload includes:
- v=1 schema, issuer key ID, grant ID and host-selected epoch;
- one canonical USER ID, fixed directory.lookup_user operation;
- exact audience spatial-check.h15.synthetic-broker;
- SHA-256 of an independently host-selected synthetic task context;
- a **claimed** actor reference (ACTOR-...), not verified human identity;
- issued-at / expiry integer UTC seconds, max five-minute lifetime.
Unknown fields, duplicate keys, wrong types, noncanonical JSON, oversized
input, wrong audience/operation, invalid signature, stale/unknown issuer,
expired/future claims and context mismatch fail closed before any H14 grant.

If signature validates, a new host-owned restricted dispatch path creates
(or checks) the exact H14 scoped grant, atomically CLAIMED before H13 broker
worker effect, and denies repeats, UNKNOWNs and cross-process contention.
A signature is NOT sufficient to invoke the broker outside trusted host
control: code must not expose the verifier, ledger or trusted broker mode
as model-callable functions.

CRITICAL NEGATIVE witnesses intentionally pass:
- Trusted issuer may sign a false actor_claim; nothing in Ed25519 checks
  that a HUMAN ACTUALLY APPROVED.
- A compromised trusted issuer can sign a second epoch for same user and
  cause a second effect.
- The same-UID privileged host can DELETE the local H14 SQLite file and
  replay the original, still-valid signed grant for a second effect.
- Existing H14 direct grant()/dispatch() paths remain callable by
  privileged host code, so this is not a global enforcement boundary.

Signed grant integrity is verifiable relative to trusted publisher key
material. It is NOT authenticated human approval, host identity, PKI key
management, access revocation beyond host key removal, reliable wall-clock
trust, secure private-key hardware, tamper-proof ledger, distributed
idempotency or external provider receipt/authorization.

No real identity, actual user PII, secrets, network providers, new cloud
services, paid resources, deployment or public package. Independently
review signer issuance and binding to real human evidence before any
security promotion. H15 must pass all optional tests and GitHub CodeQL,
Hypothesis/Bandit/zizmor/H8 and source/sdist/wheel parity checks.

Decision GATE: ACCEPT_H15_SIGNATURE_INTEGRITY_PROOF (conditional CI) +
HOLD_HUMAN_APPROVAL_LINKAGE + HOLD_PROVIDER_IDEMPOTENCY +
HOLD_SECURITY_PROMOTION + HOLD_G2B_REPLACEMENT.

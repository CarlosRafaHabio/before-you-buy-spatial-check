# H16 — adversarial architecture consolidation / authority cut-set

**Date:** 2026-10-08
**Scope:** before-you-buy-spatial-check, experimental PR #14 only.
**Purpose:** try to REFUTE the notion that H1–H15 compose into a single
mandatory security boundary. Retain existing tests, decisions, versions,
GitHub Actions; do not add a new sandbox, auth layer, provider integration
or any code to the publicly distributed spatial_check/ engine.

## Audited source, not inferred architecture

Modules were read at commit e8a23e7f12ae0af9c37cdbbbc30a6b5fc550c58b:

- G1 flow_guard.py: cooperative text labels and flow decisions. It has no
  trusted origin attestation, and same-process host code can forge labels.
- G2-a host_dispatch.py: optional registered callback wrapper, performs
  policy check then invokes trusted Python callback; no all-path control.
- G2-b closed_host_plan.py: host-authored, closed mini AST that propagates
  explicit data and branch dependencies inside that AST only.
- G5 scoped_data_use_v0.py: independent host-preapproved ID and one-shot,
  BUT callback and synthetic scope are not cryptographically authenticated.
- H7 process_boundary_v0.py: Linux SO_PEERCRED synthetic IPC; H7-b shows
  preconnected FD delegation can defeat simple peer PID authorization.
- H8 separate container CI: confirms OS properties on a Docker runner,
  not general untrusted-code or privileged-broker confinement.
- H9 Monty via test-only upstream package: sandboxed restricted guest
  interpreter, NOT automatic information-flow tracking.
- H12 monty_host_bridge_v0.py: trusted host exports fixed lookup_user
  callback to a new VM session; it invokes G5 directly and does not
  import or require H15 approval verification.
- H13 isolated_broker_v0.py: direct callable synthetic subprocess
  launcher. It does not require H14 or H15 and cannot roll back effects.
- H14 durable_claim_v0.py: SQLite claim-before-effect; direct grant()
  and dispatch_synthetic_once() methods exist without H15 verification.
- H15 signed_approval_v0.py: verifies issuer signature + scope then calls
  H14. This is ONE OPTIONAL dispatch route, not the unique gate.
- All variants are in prototypes/ and excluded from the public wheel.

## Dependency DAG (IMPLEMENTED, not desired)

A. G2-b -> G2-a -> G1 -> host callback (optional route).
B. H12 Monty guest -> G5 (host-approved raw ID) -> arbitrary trusted
   handler (can directly invoke H13 broker).
C. H15 signed ticket -> H14 local SQLite -> H13 synthetic broker.
D. Direct H14 grant + dispatch -> H13 synthetic broker, no H15.
E. Direct trusted Python host -> H13 synthetic broker, no H14 or H15.
F. Host-controlled G1 labels/G2-b plan authoring -> callback; not an
   independent trusted issuer or mandatory policy enforcement.

The component intersection (cut-set) is EMPTY for the stated *all
privileged synthetic effects require H15 verification* property.
No single gateway is forced onto every actual host callback route.
These are trusted-host / TCB bypasses: the tests do NOT demonstrate an
arbitrary malicious prompt can import a privileged host module from the
Monty guest. The trust assumptions must be stated.

## New concrete end-to-end adversarial witnesses (H16_01–09)

1. POSITIVE: H15 valid ticket uses H14/H13 and denies replay.
2. NEGATIVE: forged signed ticket correctly rejected by H15, while same
   privileged host can bypass verifier by calling H14 directly and effect
   proceeds without any signature.
3. NEGATIVE: trust-key removal blocks H15 but not a host-initiated H14
   dispatch via the bypass route (revocation not universal).
4. NEGATIVE: H13 direct worker dispatch produces effect, no H14 claim.
5. NEGATIVE: G2-b rejects external taint on same sink, while separate
   host-approved G5 route can call a handler with untrusted raw ID.
6. NEGATIVE: H12 guest asks for host-approved ID via fixed Monty callback;
   no H15 cryptographic signed proof is checked in that alternate route.
7. NEGATIVE: host can relabel raw external bytes using host_text and
   G1 allows; this is a HOST TRUST violation, not string-only exploit.
8. POSITIVE: valid H15 signed ticket for wrong independently host-selected
   context is correctly denied before effect or grant.
9. NEGATIVE: alternative G5 host handler invokes H13 directly for one
   synthetic effect, with no matching H14/H15 ledger entry.

**Interpretation:** the H15 signature layer successfully protects its
OWN explicit call path, but cannot be presented as end-to-end enforcement.
CI GREEN on the nine H16 cases means negative boundary evidence is
reproduced, not mitigated.

## Simpler defensible architecture (PROPOSAL, NOT IMPLEMENTED)

Only AFTER a real application requirement exists:
1. **Untrusted computation:** Monty for a constrained Python subset, with
   no exposed privileged objects, file mounts, unrestricted callbacks or
   default host authority. Keep G2-b as an explicit flow-control policy
   where data/control provenance must be shown; DO NOT replace it with
   Monty, which doesn't track taint automatically.
2. **Trusted ingress/consent:** authenticate a real reviewer via an
   independently verifiable mechanism and bind the actual approval event,
   context, scope, expiry, human identity and epoch to an issuer decision.
   H15 signatures alone assert facts, they do not verify these events.
3. **ONE privileged effect gateway:** consolidate every reachable
   tool/handler into a single server/adapter *outside* the guest's
   execution domain. All effect routes MUST reference this gateway and
   check host-approved operation, provenance, consent, signature, quota,
   scope, epoch and immutable replay status BEFORE each actual effect.
4. **True isolated effect executor:** H13 is killable, but same-UID and
   not a security sandbox. Put provider operations behind OS/process
   credentials unavailable to the guest; restrict FD transfer and
   direct endpoints; do not confuse PID identity with authenticated
   authority.
5. **Durable external trust domain / provider receipts:** H14 SQLite is
   useful for local cooperative CAS but is tamperable by privileged host
   and cannot deduplicate an already committed remote effect. Require
   independently controlled state and real provider idempotency, only
   when real provider and consent workflow are specified.

To simplify research rather than proliferating components:
- KEEP Monty as a test-only reusable interpreter, H10–H16 tests, core
  source/sdist/wheel isolation and a minimal research facade.
- KEEP H15/H14/H13 as independent proof-of-concepts, NOT mandatory
  operating authority.
- RETAIN G1/G2-b as documented information-flow experiments; Monty
  cannot replace their semantics. Avoid implementing another custom AST.
- ARCHIVE H7/H8 as environment/perimeter experiments. Do not add a
  second IPC protocol without a clear provider and OS trust model.
- Do NOT merge PR #14, harden public production flows, call a prototype
  sandbox production ready or claim general prompt injection resistance.

## Gate / priority

P0 correctness blocker to a future security boundary: there is not ONE
forced privileged tool path. H15 is optional; H14 and H13 can be called
directly. Closely related blockers: authentic human approval, isolation of
trusted host from guest, enforceable provider-level idempotency, and
genuine labeled influence into tool calls.

HOLD_SECURITY_PROMOTION and HOLD_G2B_REPLACEMENT.
Next action: independent blind adversarial reviewer, plus a minimum
**implementation-free** tool-route inventory for a REAL integration if
and only if one is proposed. No more speculative security primitives.
No AWS, SQL cloud, paid resources, main merge, Habio #43/#44 changes.

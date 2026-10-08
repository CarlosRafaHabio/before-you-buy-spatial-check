# H16 — INDEPENDENT adversarial review brief: entire G1–H16 authority

**Project:** CarlosRafaHabio/before-you-buy-spatial-check
**Scope:** experimental PR #14 only, NOT Habio/Morable commercial app.
**Status:** DRAFT, not merged, no production effects, no security promotion.
**Preferred subject:** what is actually enforced by the executable code,
not whether individual unit tests have green badges.

## Reviewer instructions

Read the public PR branch and main independently. Confirm HEAD, changed
files, current CI/check-run status and Python packaging exclusions.
Assume documentation and positive tests may overstate guarantees. Do not
use the author's prior score or any preset maturity grade. Ask what a
malicious guest can really influence vs what requires malicious or
misconfigured trusted host access. Identify any newly practical, reachable
counterexample the author has missed.

### Must-read sources

- G1 flow_guard.py and G2-a host_dispatch.py
- G2-b closed_host_plan.py and frozen 21-case G3 benchmark
- G4-b host TCB negative test witnesses and H7 FD delegation witness
- G5 scoped_data_use_v0.py (one-shot in-process approved ID)
- H12 monty_host_bridge_v0.py and H10–H12 Monty tests
- H13 isolated_broker_v0.py and worker; H13 timeout tests
- H14 durable_claim_v0.py and H14 concurrency tests
- H15 signed_approval_v0.py and H15 signature tests
- H16 security_monty/test_h16_integrated_authority_cutset.py
- H16 integrated cut-set report in docs/
- MANIFEST.in, packaging workflow, CodeQL and H8 experimental workflow.

All of these are on
https://github.com/CarlosRafaHabio/before-you-buy-spatial-check/pull/14

## Questions the reviewer must answer adversarially

1. List every REAL entrypoint to a privileged synthetic effect in the code.
   Can a guest use it through an offered callback, or only privileged host?
2. Is a verified Ed25519 signature MANDATORY for every host-side effect?
   Demonstrate yes/no with a test or precise code path, and classify scope.
3. Are a claimed actor string and a trusted public key sufficient evidence
   of actual human consent? What separate issuance assumptions are necessary?
4. Could H14's shared local SQLite DB be deleted, reissued or bypassed?
   What does it really guarantee on a single filesystem versus provider side?
5. Does Monty automatically track *control* dependence and provenance
   through a Python guest? Does G2-b cover non-AST host decisions?
6. What do H7/Linux peer-PID and H8 Docker prove, and how can a trusted
   host incorrectly delegate a privileged socket FD?
7. Does H13 SIGKILL cancel remote effects or prove idempotency?
8. Find a novel relevant abuse not covered by G4-b/H10/H16, reproduce it
   in a minimal offline test if feasible, and avoid manufacturing a
   vulnerability from host-only code as if prompt text were enough.
9. Propose a MINIMAL number of components to retain for the actual
   spatial-engine use case. Identify redundant demonstration layers,
   danger of in-house interpreter/sandbox growth and cost/resource impact.
10. Render an independently calibrated verdict for (a) experiment/test
    engineering maturity, (b) security boundary maturity, and (c) utility
    for a publicly maintainable open-source repo. Do not combine them in
    one flattering overall grade.

## Deliberately independent baseline

Do not assume a success merely because the integration harness reports
94/94 optional tests. Several of those are PASSING NEGATIVE witnesses,
meaning the current architecture still permits known paths around H15.
A broken trusted host is not the same attack class as untrusted text.

Do not merge or deploy. No AWS, Supabase, production API, credentials,
Habio PR #43/#44, payment, real privileged effect or non-synthetic user data.
The final adjudication remains HOLD_SECURITY_PROMOTION.

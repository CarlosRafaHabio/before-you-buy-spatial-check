# Blind independent G4 reviewer packet — Spatial Check × CaMeL

Date: 2026-10-08. **Review request only; no external verdict yet.**

Repository: https://github.com/CarlosRafaHabio/before-you-buy-spatial-check
Main baseline: a676a573bac8c240292bf6ba4197566cefb731ee
Experimental PR: https://github.com/CarlosRafaHabio/before-you-buy-spatial-check/pull/14

## Scope

Audit **only the experimental information-flow and host-execution safety
layer of PR #14**, not the commercial Habio/Morable product. Avoid grading
the main Spatial Check engine as if it provided general prompt-injection
defense. Do not adopt prior self-assessed scores.

Review:
- prototypes/camel_selective_v0/flow_guard.py
- prototypes/camel_selective_v0/host_dispatch.py
- prototypes/camel_selective_v0/closed_host_plan.py
- tests/test_camel_flow_guard_g1_counterexamples.py
- tests/test_camel_bound_host_dispatch_g2a.py
- tests/test_camel_closed_host_plan_g2b.py
- tests/test_camel_g3_differential_v0_1.py
- tests/test_camel_g4_registration_aliasing_prefx.py
- tests/test_camel_g4b_host_authority_witnesses.py
- docs/CAMEL_G4A_REGISTRATION_ALIASING_PRE_FIX_2026-10-08.md
- docs/CAMEL_G4A_REGISTRATION_SNAPSHOT_HARDENING_2026-10-08.md
- docs/CAMEL_G4B_TRUSTED_HOST_AND_ISOLATION_FINDINGS_2026-10-08.md

## Questions / required deliverable

1. Establish what threat model the current policy actually enforces, what
   attacker capabilities invalidate it, and whether the label-propagation
   semantics and reader intersection are implemented correctly.
2. Verify actual GitHub HEAD, CI, baseline-vs-branch diff and package boundary;
   do not infer success from previous messages.
3. Find at least one novel counterexample or explain why none emerged after
   tracing program and handler behavior. Categorize findings by prerequisites.
4. Re-test the G4-a post-registration snapshots against original caller aliases
   versus malicious same-process introspection; distinguish scopes.
5. Evaluate risk of unused source slots, constant plans, arbitrary callback
   side effects, callback retry/replay and secret escape from closures.
6. Challenge the self-reported G3 figures as synthetic fixtures, not a real
   AgentDojo, LLM or production benchmark.
7. Give one of three conclusions with precise conditions: (A) policy-only
   utility suitable for experimental sharing, (B) isolate as a new optional
   agent-security component pending real host integration, or (C) reject
   publication as misleading or unsafe.
8. Recommend the smallest next technical proof, an explicit STOP/HOLD list and
   severity-ranked counterexamples. If scoring, score **PR #14 independently**
   without carrying over an earlier Spatial Check/Habio score.

Security restrictions: no merge, deployment, paid resources, live secrets,
AWS changes, Supabase migrations or modifications to Habio PR #43/#44.

## Evidence handling

Green CI means tests run as authored. Many G1 and G4-b tests intentionally
pass on unsafe synthetic behavior. A security claim requires examining the
assertions and trust boundary, not counting green tests.

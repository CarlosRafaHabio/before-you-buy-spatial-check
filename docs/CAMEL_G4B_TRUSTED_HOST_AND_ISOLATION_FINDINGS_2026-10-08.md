# G4-b — trusted host and isolation: adversarial evidence

**8 October 2026. Experimental PR #14 — NOT INDEPENDENT EXTERNAL REVIEW.**
**Decision: ACCEPT_NEGATIVE_EVIDENCE; HOLD_SECURITY_PROMOTION.**

## What this tranche does

Conservatively reproduces twelve **synthetic host/TCB failures or structural
limitations**, without touching the deterministic spatial core or any deployed
service. Each witness is a passing unit test **because the current prototype
still allows the simulated behavior**, not because the prototype blocked it.

- G4B01: caller with executor reference repeats a fixed side effect five times;
  no caller identity, once-only authorization or durable replay fence exists.
- G4B02–03: unused external slots do not taint fixed host literals.
  If a host uses those values in Python control flow outside the AST to decide
  whether to invoke, the true decision dependency is lost.
- G4B04: host program author can launder web bytes into an approved Literal.
- G4B05–07: bound callbacks may perform undisclosed extra effects, use global
  confidential bytes, or amplify a single dispatch into multiple effects;
  the guard checks declared arguments but cannot constrain callback behavior.
- G4B08–09: malicious *same-process* Python can mutate the internal registry
  by reflection, beyond G4-a's caller-owned-object-copy hardening. This is
  not a vulnerability requiring only hostile input text.
- G4B10: host Python conditional performed *outside* the closed AST is
  untracked even when program AST itself is deterministic.
- G4B11: FlowText provides labels, not confidentiality in Python memory.
- G4B12: a handler with unknown outcome can be invoked again and duplicate
  its effect; the prototype deliberately does not implement idempotency.

These are not claims of real, remotely exploitable attacks. They identify
where the TRUSTED COMPUTING BASE is currently large or insufficiently modeled.

## Adversarial adjudication

G4-a snapshotting fixed the narrower post-registration alias problem.
G4-b demonstrates that G4-a is **not** a proof of runtime isolation or a
complete operation reference monitor:

1. Without isolating the agent from Python internals and direct tool endpoints,
   malicious agent code can reach private registries and perform effects.
2. Without host-authenticated/one-shot request authority, a constant plan can
   be called repeatedly by an untrusted principal with a reference.
3. Without restricting registered handler implementations, arbitrary callback
   behavior may undermine reader restrictions or side-effect counts.
4. Without an interpreter/host-bounded plan that encompasses *all* decisions,
   out-of-AST branches produce untracked control dependencies.
5. Without idempotency keys/fences at the real effect provider, ambiguous
   callbacks can produce duplicate effects after retries.
6. Without signed/reviewed provenance, external-to-Literal promotion by a
   privileged but confused host remains possible.

**Do not solve these by adding ad hoc booleans, string-based "trusted" flags
or in-process hiding of private attributes.**

## Recommendation (design only)

The next boundary is not another unverified label class. It is a **host-owned
isolated adapter contract**: closed set of privileged handlers, out-of-band
host authentication and per-request authorization; information labels
assigned by a trusted intake adapter; policy check and callback in the same
trusted process; explicit scope/rate/replay policy for real effects; and no
agent-controlled Python access to that process or its credentials.

Even such a design remains an **untested proposal** until separately deployed
and adversarially verified. It is deliberately NOT connected to
HostIntake, DynamoDB, Supabase, PR #43/#44, or public main.

## G4 independent blind review handoff

Ask a separate reviewer/model to inspect PR #14 without being provided a prior
maturity score or an assertion of safety. Reviewer should:
- review the precise original/main and branch commits;
- classify whether each reported weakness is a real exploit, a TCB-assumption
  violation, an unimplemented optional feature, or a mere policy choice;
- search for new counterexamples and try to disprove each G4-a claimed fix;
- assess the risk of Python reflection, handler side effects and raw data
  escape, including the impossibility of sandboxing a malicious Python caller
  with dataclasses;
- independently evaluate whether the experimental guard is worth publishing
  as a security primitive, merely as a policy utility, or not publishing;
- specify the minimal indispensable runtime boundaries to preserve a
  truthful, domain-specific engine rather than inventing a competing project.

**Do not call this report independent:** it was produced by the same
assistant/development workflow. Independent G4 is still pending.

No merges, costs, SQL, AWS, production integration, or version promotion.

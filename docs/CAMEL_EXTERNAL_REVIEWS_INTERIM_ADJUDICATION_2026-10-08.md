# Spatial Check × CaMeL — Interim external review adjudication (2 of 3)

**DRAFT · October 8, 2026 · PR #14 TEST ONLY · No canonical promotion.**

Two independent-model texts were supplied; a third is expected later and was
not part of this adjudication. Their source-code inspection/test claims are
not assumed verified merely from narrative. The current repo was inspected
and verified against PR #14 HEAD (before this tranche):
\`4f07a4e2b0e647b6ddd66889641efc1ed097c5c7\`, main
\`a676a573bac8c240292bf6ba4197566cefb731ee\`.

## Preliminary comparison

| Topic | Review 1 / 3.5 | Review 2 / 6.5 | Technical adjudication |
|---|---|---|---|
| Publishing as security sandbox | REJECT | NOT production; optional utility | ADOPT HOLD: do not claim security boundary |
| Integrating into geometric engine | Decouple | Keep outside core | ADOPT, already true (prototypes only) |
| Strict input validation | Strongly recommends | Recommends typed approval | ADOPT for narrow field-use experiment, NOT generic endorsement |
| Error leakage | Asserts engine leaks tracebacks | Not emphasized | NEEDS PROOF: do not infer real production exfil without trace/transport |
| CaMeL-grade interpreter/host separation | Advocates separate runtime | Advocates isolated callback | ADOPT concept, defer real isolated adapter until host design |
| One-shot/replay | Not discussed | Recommends tokens/counters | PARTIAL: in-process one-shot reduces repeat attempts only; NOT durable idempotency |
| Zero dependency | Proposes Pydantic or Rust/PyO3 | Prefers small stdlib-only | REJECT replacement without measured requirement |
| Declassification on regex | N/A | Raw FlowText untrusted->False on schema match | REJECT generic trust laundering; allow exact purpose-scoped data use |
| Independent empirical metrics | Questions biased tests | Notes G3 tautology & 40% fixture denial | ADOPT: G3 synthetic rates NOT general performance |

## Inaccurate / unsupported claims in review 1

- The report describes loss of Flow Guard taint during spatial-core float
  processing. It cannot be a current finding: nothing under
  \`spatial_check/engine.py\` depends on the \`prototypes/\` Flow Guard and
  no such taint tracking exists within geometry.
- The report suggests reflective Python expression evaluation via dunders
  from a plan. Current \`closed_host_plan.py\` accepts only
  \`Literal/Source/Join/Choose/Equals\` nodes; it does not eval/exec Python
  code found in model data. Arbitrary hostile Python *already executing in
  process* has broader privileges, a different precondition.
- It refers to non-coplanar vertices/singular matrices not shown in the
  narrow rectangular 2D engine, without a specific executable repro.
- Strict schema should **reject unrecognized fields** at privileged
  boundaries, not silently ignore them. Source 1's suggestion to ignore
  extras is not automatically safer.
- Since the reviewer offers mostly general attack sketches without precise
  code lines/reproductions, severity ratings are provisional, not accepted
  as demonstrated vulnerabilities.

## Review 2: accepted findings and necessary modifications

- Accurate that \`host_text\` / \`Literal\` trust comes from host bootstrap,
  not from checking a payload's syntactic shape.
- Accurate that callbacks can read globals and escape the declared sink.
- Accurate that process-local identity and replay control are insufficient
  for distributed effects.
- Accurate that nine hostile G3 cases blocked and four benign cases denied
  is an artificial fixed-fixture measurement only.
- However requiring any generic \`schema_validator: Callable\` and then
  setting \`FlowText.untrusted=False\` would itself create an open-ended trust
  laundering primitive. Regex shape does not attest authority, identity,
  consent or expected destination.

## G5-a authorized *data-use*, not declassification

The narrow \`HostScopedUserLookup\` experiment demonstrates a safer limited
exception to an otherwise blanket denial of external data in external calls:

- Host bootstrap alone selects one canonical \`USR-NNNN\` and fixed
  \`directory.lookup_user\` / \`directory.internal\` target.
- Runtime input must be exactly that ASCII id, with zero extra tokens or
  object-supplied metadata, before callback executes.
- An independently approved exact ID must be host-originated: do not derive
  it from the same untrusted model input. This is a TCB precondition.
- The external input provenance is still marked untrusted; no general
  FlowGuard trusted-conversion or API-wide declassification is added.
- One process-local concurrent-safe single-use fence is consumed **before**
  the effect attempt; unknown callback results are not retried.
- This is only a demonstration of a purpose-scoped lookup parameter and is
  not caller authentication or durable, across-process exactly-once effect.
- Two tests intentionally prove the unresolved TCB problems: host can still
  approve untrusted bytes if poorly implemented; any untrusted Python with
  object reference and approved id can preconsume the permission.
- Callback side effects remain unconfined. No agent isolation was added.
- No metric here replaces the G3 baseline or proves improvement in
  real-world false denial rates.

## Plan / HOLD

G5-a tests MUST pass on both CI triggers, including sdist/rebuilt wheel.
The prototype MUST remain outside the wheel and public \`spatial_check/\`.
Upon receiving the third review, reconcile conflicts before doing bigger
architecture work. Do not merge to main, add dependencies, modify Habio
PR #43/#44, SQL, Supabase, AWS, production, or spend paid credits.

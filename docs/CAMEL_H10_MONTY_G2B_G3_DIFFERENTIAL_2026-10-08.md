# H10 — G2-b × Pydantic Monty v1.1.0 on the SAME frozen G3 corpus

**Experimental branch PR #14 DRAFT. Security promotion HOLD.**
H10 reuses the 21 G3 fixed synthetic fixtures with their original mode and
expected attempts, *not* a new curated or independent test corpus.
The source G3 baseline remains untouched.

## Comparison definition

Three deliberately distinct regimes must not be conflated:
(A) Existing G2-b closed host interpreter, host-authored AST & trusted source
manifest; no arbitrary Python guest interpreter.
(B) Monty VM with a registered host callback and **no host policy**. Monty
isolates execution but does not intrinsically decide tool/data provenance.
(C) Monty VM with explicit host callback mediation / manually host-authored
FlowText labels (from the same case definition). This tests policy
compatibility, NOT automated information-flow tracking by Monty.

Expected frozen outcomes under this fixture:
- G2-b (A): hostile 0/9 allowed; benign 6/10 allowed, 4/10 denied; broken
  trusted host 2/2 allowed.
- Monty unmediated (B): 21/21 callback invocations, including hostile 9/9
  and bad-host 2/2. This is NEGATIVE evidence of no IFC policy built in.
- Monty explicitly mediated (C): matches G2-b only because policy code on
  the trusted host reconstructs input and control provenance.
- A guest branch conditioned on an untrusted input can produce a fixed
  literal; a host that relabels that observed literal as trusted executes
  it. Monty alone does not carry the implicit flow to the callback.
- A guest can request repeated effects without host quota; existing G5
  one-shot policy can stop repeats. This is not provider idempotency.

## Interpretation

Monty already addresses a materially different problem: bounded execution of
model-supplied Python without ambient filesystem, network or host process
access. G2-b addresses closed expressions/flows with sticky provenance
from trusted host sources. Monty is **not a drop-in substitution** for IFC,
and G2-b is **not** a general Python sandbox. Genuine simplification may be
obtained by retaining Monty as optional executor and keeping one deliberately
small host-owned effect authorization/taint mediation layer; do not delete
G2-b until it is proven redundant in an authenticated tool setting.

No security metrics from a live agent, human approval, actual external
provider, or unknown attacks are implied. No external package is added to
the public wheel; Monty v1.1.0 is pinned in experimental CI only.

## Decision gate

ACCEPT_DIFFERENTIAL_EVIDENCE if all H10 tests pass and repository CI stays
green. HOLD_G2B_REPLACEMENT, HOLD_SECURITY_PROMOTION and no merge.
Critical open risk: malicious/incorrect trusted host callback can undo
the intended boundary even though guest Python runs in a separate worker.
Next technical change should only target authority at callback/API boundary
and independent sample utility; not more generic bespoke interpreters.

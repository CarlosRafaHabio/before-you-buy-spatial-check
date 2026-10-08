# G4-a: Alias retention reproduced and bounded hardening applied

**2026-10-08 · PR #14 · DRAFT / TEST ONLY / NO MERGE**

## Adversarial proof, BEFORE remediation

The exact pre-fix commit
\`72abf2ec7c52ea554fcfa2f99491c8c974dda61c\`
added four test witnesses demonstrating:

- G4-A: caller-owned Operation mutated from external to pure changes policy.
- G4-B: caller-owned BoundTool handler mutation redirects allowed synthetic secret.
- G4-C: caller-owned Literal mutation after plan validation changes outgoing bytes.
- G4-D: caller-owned Source mutation after plan validation causes an uncaught KeyError.

The four tests on that commit *intentionally passed while behavior was
insecure*. Their filenames and documentation preserve the before-state.

## Remediation

- FlowGuard copies each validated Operation into an internally owned instance.
- BoundHostDispatcher copies each registered BoundTool, capturing its original
  handler, name and destination instead of retaining caller's object reference.
- ClosedHostExecutor compiles supported AST nodes (Literal, Source, Join,
  Equals/Choose) into fresh, bounded/validated nodes and clones the external
  slot manifest. The operation/arguments are copied into a new internal HostPlan.
- Invoke snapshots the raw-input dictionary before comparing manifest and
  evaluating it.
- 8 post-fix assertions test that original caller-held objects mutated
  via object.__setattr__ no longer change registry policy, handler,
  sources, manifest, or approved outgoing bytes.

## Qualified security impact

This fixes **caller-reference aliasing for ordinary after-registration
mutations of the provided original objects**, a real correctness/security
defect in the experimental code. It does **not** provide immutable process
memory or protection from malicious same-process Python. If an adversary can
access \`dispatcher._tools\`, \`guard._rules\`, \`executor._plan\`, callback
globals, or directly call effectful libraries, the attacker remains inside
the trusted computing base and can bypass this cooperative prototype.

Remaining blockers: sealed host source/plan authority in a real integration,
taint control outside the AST, direct tool effects and exfiltration prevention,
authenticated review/endorsement, adversarial real-agent evaluation, and
independent third-party review.

No code changes to spatial_check/, no persistent cross-process authority,
no AWS or SQL, no main merge. G4 remains HOLD for external independent review.

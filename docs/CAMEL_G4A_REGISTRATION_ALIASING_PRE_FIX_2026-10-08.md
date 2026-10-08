# G4-a registration aliasing — red-team baseline (UNFIXED)

PR #14 · Branch experiment/camel-selective-flow-guard-v0 · 2026-10-08

Four offline **PRE-FIX vulnerability witnesses** in
\`tests/test_camel_g4_registration_aliasing_prefx.py\`:

- G4-A: \`FlowGuard\` retains caller's \`Operation\` reference; later field
  mutation changes external to pure classification, allowing untrusted text.
- G4-B: \`BoundHostDispatcher\` retains caller's \`BoundTool\` object; later
  handler mutation invokes a substituted sink after check. Test uses a
  synthetic secret, not live private data.
- G4-C: \`ClosedHostExecutor\` retains caller's \`HostPlan\` graph. Mutation of
  an originally approved \`Literal\` after construction changes later
  permitted outbound bytes.
- G4-D: Mutation of a registered \`Source\` name after validation raises an
  uncaught \`KeyError\` in invoke, instead of returning a denied outcome.

\`@dataclass(frozen=True, slots=True)\` does **not** prevent deliberate
\`object.__setattr__\`; and \`MappingProxyType\` only freezes mapping keys,
not the referenced objects. This is a concrete limitation in the supposed
"host-owned, immutable plan" contract.

This attack requires an adversary or misconfigured host component to retain
references to registry objects *inside the same Python process*, and have the
ability to mutate those objects. It does **not** demonstrate a remotely
reachable vulnerability in Spatial Check or a malicious-input-only exploit.

These tests intentionally **pass when the prototype is vulnerable**.
DO NOT MISREPRESENT green CI as successful mitigation. The next commit
should snapshot validated operation, handler, slot metadata and compiled AST
into fresh internally owned objects at registration; then invert test assertions
to verify the mutation no longer alters behavior.

G4 external independent review is NOT completed. NO MERGE / TEST ONLY /
AWS FREE / NO SQL MIGRATION / no change to spatial_check/.

# Spatial Check × selective CaMeL — G2-b closed host plan

**DRAFT / OFFLINE / TEST ONLY — NOT A SECURITY CERTIFICATION**  
Branch: experiment/camel-selective-flow-guard-v0 · PR #14  
Dependency: G1 counterexamples and G2-a bound dispatcher.

## Objective

Remove two avoidable classes of misuse *within a host-owned, closed plan*:

1. A runtime untrusted caller may no longer pass a preconstructed trust-labeled FlowText directly to the new host executor. It supplies **only raw strings** for a previously sealed slot manifest; the executor labels all runtime slots untrusted.
2. A runtime untrusted caller may no longer supply an explicitly empty \`control_dependencies=()\` when the host plan itself chooses a value under a predicate. The executor evaluates a tiny declarative AST (Source, Literal, Join, Equals, Choose) and automatically tracks the selected expression's equality-condition dependencies.

An immutable plan binds a **single predetermined external operation**, its destination and callback via the G2-a dispatcher. No model-supplied plan, dynamic tool routing, arbitrary callable nodes, or declarations of a \`pure\` network effect are accepted through \`invoke(raw_inputs)\`.

## Scope of protection

Given a **trusted host** which privately constructs the plan, slot manifest and bound tool, uses \`invoke()\` as the only reachable effect path, and does not branch outside that plan based on untrusted content:

- model/document/web text cannot self-declare \`trusted:true\` in a runtime input;
- conditional choice inside the AST carries taint to a constant branch result;
- the exact resolved argument snapshot is checked and passed to the same bound handler;
- unknown keys, omitted required keys, malformed values, unsupported AST nodes, overlong data, excessive tree depth and unregistered source references fail closed;
- the destination-specific reader restriction is propagated through branches and joins.

The executor requires bounded raw values and has no network, LLM, database, credentials, or persistent control.

## Critical unresolved limits / counterexamples

- **Plan authorship is TCB, not attested.** A malicious host or another Python actor with the ability to construct a new executor can create \`Literal(external_bytes)\` and mislabel external input as trusted. Demonstration G2b-22 intentionally returns ALLOW. The caller must not be permitted to supply or replace the HostPlan.
- **External control flow is untracked.** A Python \`if external_string\` outside the declarative AST can determine whether the host even calls \`invoke()\`. G2b-23 documents this limit. Neither G2-a nor G2-b is a general Python interpreter or sandbox.
- Handler code can perform additional unregistered effects and inspect global variables; this helper is not a proof of tool authority. Direct tool access, unauthorized imports, reflection and byte leakage remain outside scope.
- All runtime input slots are untrusted; benign inputs intended for effects (including user-approved document text) will be overblocked. There is no versioned, authenticated human approval or declassification contract.
- Not connected to \`spatial_check.trust.HostIntake\` and must never generate \`TrustedEvidence\` automatically.
- The expressions support equality tests and string concatenation only. This is a deliberate constrained prototype, not a general agent programming language.

## Acceptance gates

G2-b **engineering feasibility** is complete only after CI and source-package parity. G2 security acceptance stays **HOLD** until a separate independently evaluated trusted-host integration proves that the host owns all program decisions/handlers and the data/permission/flow registry cannot be forged from model-controlled inputs.

Next: fixed differential attack/benign corpus and measured denied-safe/allowed-unsafe rates (G3); adversarial G4 review of TCB and inability to track external flow. Do not claim CaMeL-equivalent guarantees.

No changes to \`spatial_check/\`, engine 0.3.0, HostIntake, result schemas, PYPI, AWS, SQL, Habio PR #43/#44 or main. Experimental PR #14 stays Draft.

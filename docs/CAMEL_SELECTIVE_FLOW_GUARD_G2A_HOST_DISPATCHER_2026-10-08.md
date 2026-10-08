# CaMeL-inspired Selective Flow Guard — G2-a synthetic host-bound dispatch

**DRAFT · OFFLINE ONLY · NO PRODUCTION SECURITY CLAIMS**  
Branch: `experiment/camel-selective-flow-guard-v0` / PR #14  
Dependency: G1 adversarial findings, `CAMEL_FLOW_GUARD_G1_ADVERSARIAL_FINDINGS_2026-10-08.md`.

## Why G2-a exists

G1 showed check/use divergence: a cooperating host can call `FlowGuard.check()` on trusted text and then invoke a tool with entirely different model-controlled bytes. This G2-a prototype puts both **policy evaluation and callback invocation in one synthetic trusted-host codepath**:

1. Trusted bootstrap registers exact named handler and destination (external-effect class is mandatory).
2. Caller sends exact immutable `tuple[FlowText,...]` of arguments and an **explicit** control-dependency context.
3. Dispatcher makes its own private frozen snapshots of bytes and labels, checks the operation policy, then passes the SAME snapshotted raw bytes to the bound registered handler.
4. No callback runs on policy denial; ambiguous callback exceptions return `HANDLER_OUTCOME_UNKNOWN` and are not automatically retried.

This removes check/use byte mismatch **within the dispatcher invocation** given an honest, isolated host, but is NOT a control-flow tracking interpreter, standalone capability authority, or hostile in-process Python sandbox.

## Tight gates

- No arbitrary `pure` operation registrations: G2-a is exclusively for external-effect handlers.
- Unknown operation, invalid args, omitted control context and zero-argument invocations are denied.
- Host privilege namespaces `host.*` and `external_authority.*` are explicitly denied during registration. This is **not a complete privilege namespace taxonomy**.
- Destination restrictions and tainted controls/arguments are applied before callback.
- No argument snapshot can mutate between policy and dispatch through caller-owned mutable containers.
- Handler outcomes are not evidence of persisted success or human approval; this module returns only status metadata.

## Residual high-priority attacks: STILL OPEN

1. **Omitted but explicitly-empty dependencies:** caller submits `control_dependencies=()` after branching on untrusted raw text. The dispatcher has no way to discover it (test G2-05).
2. **Forged host labels:** caller re-labels bytes from `external_text` as `host_text`, with no trusted provenance attestation (test G2-06).
3. **Alternative tool path:** a Python process that can import/call the callback directly can still bypass the dispatcher. Real isolation and a closed tool registry are host responsibilities.
4. **Discretionary handler behavior:** registered handler can access globals, alternative arguments or other side effects outside its declared input. This prototype cannot enforce callback purity or permitted effects.
5. **Raw restricted bytes remain readable in-process:** true confidentiality requires trusted transport and isolation.
6. **No reviewer identity/consent:** a host label is not a human review and cannot grant `TrustedEvidence`.
7. **No atomic distributed recovery:** does not alter Postgres/AWS authority, replay, PITR or V3.

## Promotion decision

`G2_A_PARTIAL_ENGINEERING + HOLD_G2_SECURITY_ACCEPTANCE`.

The check/use mismatch is reduced in a **cooperative synthetic host**. The two most material adversarial counterexamples remain observable and unmitigated. The follow-up should prioritize a trusted host label-origin contract and a small, auditable control-dependency DSL/profile, then compare to the naive host on a fixed adversarial+benign corpus. Full CaMeL-strength protection is not claimed.

No PR merge, no main changes, no imports from `spatial_check/`, no AWS or SQL changes.

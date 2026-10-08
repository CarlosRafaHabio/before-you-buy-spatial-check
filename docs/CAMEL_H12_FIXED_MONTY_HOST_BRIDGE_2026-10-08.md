# H12 — fixed callback boundary for Monty 1.1.0 (EXPERIMENT ONLY)

**2026-10-08 · PR #14 DRAFT · no production promotion**

## Scope

The host initializes an existing, independently preapproved
\`HostScopedUserLookup\` with synthetic side effects. The \`MontyHostBridgeV0\`
exposes only \`lookup_user\` to one new Monty worker checkout per call to
\`run(source)\` and never accepts arbitrary guest-supplied tool maps,
privileged operation names, filesystem mounts, OS callbacks or class wrappers.

The host code snapshots only one gate; no general-purpose capability
framework is introduced. All guest-originated Python/values remain
untrusted. Authorization still depends on a real independent trusted host
bootstrap, and knowing the approved ID may be enough to trigger the exposed
callback. No machine-checked CaMeL information-flow tracking was added.

Controls:
- One fixed callback name, strict positional single-string input, no kwargs,
  extra parameters, dicts, lists or attacker-supplied trusted metadata.
- Existing G5 exact approved USER ID, once-only process-local effect.
- A small per-run invocation quota (up to 8), pre-dispatch monotonic wall
  deadline check, explicit Monty VM max_memory/max_feed_duration_secs/
  max_suspensions limits.
- Monty VM binary pinned by trusted Python environment scripts path via
  \`Monty(binary_path=...)\`, not user-controlled PATH or MONTY_BIN.
- Hard 4096 UTF-8 byte input cap and strict code-string type.
- Guest and trusted callback errors returned as fixed codes without raw
  stack frames/secret exception messages.
- A fresh Monty pool+checkout for each run, preventing cached guest
  function references from surviving to a new feed with a different
  privileged binding.
- No new import in public spatial_check wheel; \`pydantic-monty==1.1.0\`
  remains a test-only CI dependency.

## Critical negative witnesses / limitations

- An agent that knows the host-approved identifier can call the offered
  function without separately authenticated intent; this is NOT an
  authorization protocol or proof of a real human approval.
- The host callback can perform unregistered effects, access ambient host
  globals or directly bypass this bridge. Malicious trusted Python beats
  any in-process reference monitor.
- The wall budget is checked before dispatch and *observed* after callback.
  It cannot preempt an in-process blocking callback. A slow synthetic effect
  can complete after deadline and be reported as UNKNOWN; that is a
  deliberately PASSING NEGATIVE witness, NOT deadline enforcement.
- Host function results can be read by the guest. Our registered bridge
  returns only fixed status strings but does not stop other tool routes.
- Per-run quotas and process-local one-shot do not create real durable
  provider idempotency, approval epochs or tenant isolation.
- Monty is a Python-subset language-level VM, not complete OS sandboxing.
  It has host-function, host-object and filesystem-mount capabilities which
  are DISABLED here, except the one intentionally offered host function.
- Cached proxies are mitigated by fresh guest session per run, not by
  forbidding the underlying Monty capability.
- This adds no proof of general agent prompt-injection resistance.

## Pass criteria

Fourteen explicit synthetic H12 tests (including two negative witnesses)
plus unchanged H9–H11 suites, standard 360/360 tests twice (source and
extracted sdist), H8 OS synthetic boundary, H6 Hypothesis/Bandit, zizmor,
CodeQL Python+Actions+separate PR security check all PASS.
No exceptions suppressed to manufacture green CI. No runtime promotion,
main merge, Habio PR #43/#44, cloud services or paid resources.

Decision proposed for technical adjudication after CI:
\`ACCEPT_H12_MINIMAL_BRIDGE_WITH_LIMITS + HOLD_SECURITY_PROMOTION\`.
Do NOT claim HOST_WALL_BUDGET_EXCEEDED_UNKNOWN means a slow host effect was
stopped or rolled back. A real hard callback deadline would require a
separate killable broker process and provider-side deduplication.

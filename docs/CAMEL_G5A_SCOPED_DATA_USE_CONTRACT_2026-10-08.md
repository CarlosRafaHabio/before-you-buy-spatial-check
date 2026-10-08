# G5-a: one host-approved external identifier as data, not authority

**OFFLINE ONLY / TEST ONLY / NOT A TOOL SECURITY BOUNDARY**

Question: can benign external data participate in an external effect without
claiming it was inherently trustworthy or allowing arbitrary exfiltration?

## Contract

A trusted host creates an ephemeral \`HostScopedUserLookup\` with:
- a pre-approved canonical user ID \`USR-NNNN\`, chosen **independently of the
  candidate external/model input**;
- fixed method \`directory.lookup_user\` and fixed target \`directory.internal\`;
- one trusted callback, not exposed to model tools.

The only runtime input is one raw external string. The gate allows a single
attempt ONLY if it exactly matches canonical ASCII syntax *and* the independently
pre-approved host ID. It neither accepts a user-controlled operation name nor
turns the FlowText into untrusted=False. It consumes its single-use fence before
the callback, so an ambiguous effect is not automatically retried.

This is deliberately not a general schema-driven trust endorsement.
Schema conformance is data validity; permission to use it is a separate,
narrow, purpose-and-target-scoped host decision.

## Positive and negative fixtures

- Pre-approved exact ID can be used once; a well-formed but different ID,
  prompt text, JSON trust flags, control characters and visually confusable
  Unicode strings are rejected.
- Missing/wrong types are rejected without string coercion.
- No arbitrary operation/destination/tool names accepted at invocation.
- Concurrent attempts may reach the callback at most once inside this one
  Python process, and callback errors result in UNKNOWN (no automatic retry).
- The same external text remains untrusted to the ordinary FlowGuard.
- Negative witnesses intentionally show (a) approvals derived from
  model-supplied text, (b) preemptive calls by any process-local holder and
  (c) callback arbitrary secondary effects still defeat the trust assumptions.

## Threat model, exclusions and design tradeoffs

This is an isolated **synthetic** lookup into a callback stub, with no actual
directory provider, user data, API network call, authorization server or
secret. Hardcoding one allowed operation and destination limits what the
experiment demonstrates and does not create a general-purpose framework.

One-shot here is PROCESS LOCAL, not persistent and not tied to an authenticated
caller identity. Two separately created gates or a process restart permit
another attempt; this is NOT exactly-once execution. It has no real CAS,
database, tenant validation, request signature, purpose-bound token or provider
idempotency key.

The callback has ambient Python privileges and can violate the declared effect.
The same process can access object internals; this class does not isolate it.
Neither geometry nor TrustedEvidence is touched.

### Decision

\`ADOPT_SCOPED_DATA_USE_POC + HOLD_GENERAL_ENDORSEMENT + HOLD_G5_PROMOTION\`

Before operationalizing: obtain independent hostile-host and real-agent
assessment, authenticated source and human/tenant scope, an actual isolated
provider adapter and effect idempotency outside Python, with utility/attack
measurement on independently sampled tasks. Preserve all negative tests.

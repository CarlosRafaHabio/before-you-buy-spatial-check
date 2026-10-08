# H7 — isolated adapter experiment with real Linux process boundary

**PR #14 DRAFT, Linux-only / offline / synthetic / not a security sandbox**

## Research grounding
- CaMeL / google-research/camel-prompt-injection separates untrusted
  model-influenced instructions from a trusted tool policy/interpreter.
- AgentDojo / ethz-spylab/agentdojo is a realistic agent/attack test
  environment; its examples require LLM providers and do not directly
  prove the guarantees of an offline engine.
- H7 is *not* an AgentDojo benchmark nor a reproduction of CaMeL's
  security guarantee. No CaMeL or AgentDojo source was copied.

## Boundary tested
A trusted parent starts a new Python interpreter as a synthetic tool adapter
using subprocess.Popen (no shared interpreter objects). The trusted adapter
owns HostScopedUserLookup, the callback and its single-use state. The only
communication is a local Linux AF_UNIX stream socket, with 0600 permissions,
in a temporary directory created with restrictive mode.

The adapter obtains peer PID from Linux SO_PEERCRED, not from client JSON.
It permits only connections from its still-live parent PID. The parent can
check the adapter process's kernel-reported PID before sending its request.
One fixed synthetic USER id and operation are host-bootstrapped; requester
data cannot choose tools or create a trusted label.

Wire format is bounded, strict UTF-8 JSON with exactly one 'user_id'
string. Duplicate object keys, oversized frames, added authority metadata,
arbitrary commands and non-string ids are denied. Response exposes only
attempted boolean and a fixed status code, never Python exceptions.

The experiment should show:
1. Parent invokes once, replay denied.
2. A different untrusted *separate subprocess* that knows the socket path
   and approved ID is denied before parsing and cannot consume the one use.
3. Forged operation fields, malformed JSON, oversized frames, duplicate
   fields, injected strings and wrong-scope ID fail closed.
4. Concurrent calls from the parent allow one and only one local handler
   attempt.
5. Client-side expected server PID check blocks accidental socket
   endpoint substitution **when expected_server_pid is supplied by host**.

## Threat prerequisites / remaining critical limitations
- **NOT a process sandbox:** both processes can run under the same OS UID.
  A malicious local user/code actor with filesystem, /proc, ptrace or
  inherited/SCM_RIGHTS file descriptors may evade this demonstration.
- PID identity is not cryptographic identity, can be recycled, can be
  influenced by how the host spawns subprocesses, and is NOT an authorization
  record tied to tenant/human approval.
- The trusted parent itself can choose an invalid authorization from untrusted
  inputs, spawn a fake adapter, call directly with ambient privileges, or
  leak sensitive data. A compromised parent defeats this TCB.
- A compromised adapter also defeats the boundary. No OS UID isolation,
  seccomp, namespace isolation, signed policy, supply-chain attestation,
  hardened IPC authentication or real capability sandbox is supplied.
- The synthetic handler is an append-only in-process list; no external
  network, email, filesystem effect or credential is used.
- The process-local once flag does not provide cross-process/durable
  idempotency. Restarting the adapter resets it. NO exactly-once claim.
- Linux-only on CI; Windows/other OS tests must be skipped with an explicit
  reason, not reported as passed.
- Real model/LLM attacks, approval bypasses and usable benign outcomes remain
  unmeasured. H7 does not alter G3's synthetic benchmark figures.

## Acceptance gate
Prove a separate interpreter and kernel peer-PID check against an actual
different process. Keep tests+demo stdlib-only, in sources/sdist but not
wheel. Green CI is engineering feasibility, NOT an end-to-end security
barrier. Retain HOLD_SECURITY_PROMOTION until threat model and genuinely
independent external G4 audit/third AI report are reconciled.
No AWS, SQL, Habio PR #43/#44, cloud, production release or paid tool calls.

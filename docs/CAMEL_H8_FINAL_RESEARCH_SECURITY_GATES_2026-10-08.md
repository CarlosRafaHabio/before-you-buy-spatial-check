# H8 — final GitHub research and real OS-boundary evidence

**2026-10-08 · PR #14 DRAFT · OFFLINE TEST ONLY · HOLD SECURITY PROMOTION**

## Source-backed GitHub research

Eight projects were checked directly: google-research/camel-prompt-injection,
ethz-spylab/agentdojo, google/nsjail, containers/bubblewrap, google/gvisor,
openai/codex, NVIDIA/garak and microsoft/pyrit.

Codex source beyond its top-level README:
- codex-rs/linux-sandbox/src/lib.rs documents no_new_privs + seccomp
  and bubblewrap for filesystem isolation.
- codex-rs/linux-sandbox/README.md documents bwrap startup/fallback,
  user/PID/network namespace behavior, read-only filesystem roots and
  related limitations.

nsjail provides Linux namespaces/seccomp/cgroups/rlimits; bubblewrap is
a low-level sandbox builder, not a turnkey secure policy; gVisor adds an
OCI runtime application kernel for stronger container boundaries but
requires integration. AgentDojo/garak require a real agent/model evaluation
target to measure prompt-injection attack and benign-task success.
CaMeL is a research interpreter, not identical to our flow-label prototype.
These are comparisons; no third-party sandbox code was imported.

## H8 real GitHub hosted runner evidence

A public standard ubuntu-24.04 runner, with no paid resource, executed
a disposable Docker Python guest using an immutable digest:

python@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4

The four H8 tests assert and OBSERVED:
- UID/GID 65534, effective capabilities zero, no_new_privs enabled,
  isolated PID namespace (PID 1);
- --network=none shows only loopback; read-only root filesystem and
  a limited isolated writable tmpfs /tmp;
- no host private synthetic canary, host checkout or Docker daemon socket;
- host's synthetic H7 Unix IPC socket appears through a restricted read-only
  bind-mount, but guest cannot connect, because kernel discretionary file
  access rejects it with EACCES (errno 13) on a PRIVATE 0600 socket.
  Trusted parent subsequently performs its single synthetic effect.

Separate, pre-existing H7 tests prove an unrelated same-UID Python
process with a reachable socket receives DENY_PEER_PID via SO_PEERCRED.
H7-b proves trusted-parent delegation of an already-connected FD can
bypass that peer-PID check. Never conflate H7 and H8 protections.

No LLM execution, secrets, external network tool effects or trusted
evidence changes were involved.

## Two high CodeQL alerts corrected without suppression

First H8 job passed tests but PR CodeQL check exposed two HIGH findings in
the synthetic test fixture:
- chmod 0755 on a temporary host directory (world readable);
- chmod 0666 on a Unix socket (world writable).

A temporary read-only GitHub Actions job fetched exact annotations via
the check-runs API. Initial fix kept temp directory private (0700),
but switching socket to 0660 and adding a guest supplementary group
was also flagged HIGH for group-writable socket. That alert was found
through another explicitly inspected CodeQL annotation and NOT dismissed.

Final fix keeps socket mode 0600 and removes all guest group access.
H8 now tests DAC denial EACCES rather than allowing a reachable socket
and relying on peer-PID authorization. The temporary diagnostic workflow
was deleted, not carried as an unnecessary permission-bearing task.

Do NOT claim CodeQL has zero active alerts until final PR CodeQL check
and both scanner jobs have completed with SUCCESS.

## Packaging and governance

- Main unchanged and production spatial_check/ untouched.
- Source distribution now explicitly includes security_isolation/ and
  security_fuzz/ test source; public wheel remains spatial_check only.
- Existing main suite: 360 tests, H8 optional: 4 explicit OS tests,
  Hypothesis: 7 generated-property groups, Bandit and zizmor.
- No paid cloud, SQL, AWS, Supabase, Vercel, real effects, production
  deployment or Habio PR #43/#44 changes.
- Rootful Docker daemon and shared Linux kernel remain trusted;
  no protection from kernel escape, compromised trusted host, delegated
  descriptors, provider replay or real-world prompt injection is proven.
- Third genuinely independent review still pending. No automatic release.

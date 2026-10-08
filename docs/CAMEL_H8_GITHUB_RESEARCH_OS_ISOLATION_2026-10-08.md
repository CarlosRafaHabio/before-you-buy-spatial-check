# H8 — GitHub prior-art research and OS isolation proof

Date: 2026-10-08. Before You Buy — Spatial Check PR #14, DRAFT / TEST ONLY.

## GitHub research, not just tool name drops

- google-research/camel-prompt-injection: controlled interpreter and agent/tool
  policy; the README explicitly warns the released research implementation
  could contain bugs and is not necessarily fully secure. A label-only
  in-process implementation cannot claim equivalence.
- ethz-spylab/agentdojo: real task/attack benchmarks with LLM execution.
  Useful in a later evaluation, but currently there is no agent/LLM runtime
  integrated with this isolated geometry engine.
- google/nsjail: Linux namespaces, seccomp-bpf, cgroups and resource limits;
  requires real host/kernel setup, not a Python library drop-in.
- containers/bubblewrap: unprivileged namespace sandbox builder; its README
  says it is not a complete policy/sandbox and requires careful setup.
- google/gvisor: OCI runsc application kernel for stronger container isolation;
  gVisor explicitly says standard containers alone are NOT a full sandbox.
  Runtime integration and tests would be needed before adoption.
- openai/codex: agent client repository useful for architecture comparison;
  no source or security promise was transplanted into Spatial Check.
- NVIDIA/garak and microsoft/pyrit: LLM red-team tools, more relevant when
  an agent, tasks and an affordable inference provider exist.

GitHub repo references:
https://github.com/google-research/camel-prompt-injection
https://github.com/ethz-spylab/agentdojo
https://github.com/google/nsjail
https://github.com/containers/bubblewrap
https://github.com/google/gvisor
https://github.com/openai/codex
https://github.com/NVIDIA/garak
https://github.com/microsoft/pyrit

## Explicit H8 Linux experiment

Run only on ubuntu-24.04 STANDARD GitHub hosted runner in the public repo.
Docker daemon is part of TRUSTED CI; a compromised daemon/host breaks boundary.
No paid runner, external APIs, real secret or privileged deployment.

Guest is a disposable official Python image with:
- --network none, --read-only, --cap-drop ALL
- --security-opt no-new-privileges
- --pids-limit 32, --memory 192m, --cpus 1
- --user 65534:65534 and writable noexec/nosuid ephemeral /tmp
- separate PID namespace, no host workspace, no host private canary and no
  Docker daemon socket mounted
- one synthetic H7 Unix socket bind-mount read-only.

The trusted host retains a synthetic H7 subprocess adapter. The synthetic
socket is deliberately chmod 0666 ONLY during this test to distinguish peer-PID
denial from simple filesystem permission denial. A separate guest process
sends exact approved USER ID and must receive DENY_PEER_PID; the trusted
parent must still be able to invoke the same synthetic operation once.

Tests verify kernel-reported UID/GID, capability set, no_new_privileges,
read-only root mount, loopback-only interfaces, PID namespace, lack of host
secret/daemon socket and direct synthetic tool denial.

The *first* run resolves the official image digest and prints it in the
workflow log. Pin the verified immutable OCI digest immediately after
a successful first experiment; mutable tags are not production-safe.

## Threat model limits and HOLD

A standard Docker container shares the host kernel. These checks do NOT
prove protection from a kernel escape, unsafe host Docker daemon, inherited
privileged FDs, malicious code in the trusted host, host approval laundering,
cross-process exactly-once effects or real LLM prompt injection.

Previous H7-b proves that passing a pre-connected privileged FD to
untrusted process defeats SO_PEERCRED. H8 does not claim to eliminate such
host compromise/delegation.

No new production dependency, release, core geometry edit, main merge,
AWS, SQL, Supabase, Vercel, Habio PR #43/#44 or paid resources.
Independent third review remains pending. SECURITY_PROMOTION HOLD.

# H8 GitHub security gates — completed evidence and removed diagnostic scaffolding

Date: 8 October 2026. This is a TEST ONLY branch change, not a production
security acceptance or a change to the public deterministic geometry core.

## Prior art researched and retained

- OpenAI Codex: codex-rs/linux-sandbox/README.md and src/lib.rs, not merely
  the top-level readme. On Linux it uses bubblewrap for filesystem isolation
  plus no_new_privs/seccomp, separate namespaces, configurable network rules;
  it documents fallback behavior. This is RESEARCH, not inherited security.
- google/nsjail: namespaces/seccomp/resource limits, requires host policies.
- containers/bubblewrap: low-level namespace tool, not a ready-made sandbox.
- google/gvisor: OCI application kernel for isolation; runtime setup required.
- google-research/camel-prompt-injection: controlled interpreter, not
  interchangeable with a plain label-only Python library.
- ethz-spylab/agentdojo and NVIDIA/garak: agent/LLM adversarial evaluation,
  deferred until there is a genuine measurable agent runtime.
- Official GitHub Actions Docs: standard hosted Linux runners in public repos
  free. No paid cloud or separate VMs provisioned.

See docs/CAMEL_H8_GITHUB_RESEARCH_OS_ISOLATION_2026-10-08.md.

## H8 proof on a real Github runner

Four independent container tests PASSED on ubuntu-24.04:
UID/GID 65534, CapEff zero, no_new_privs enabled, isolated PID,
only loopback network interface, read-only root plus isolated tmpfs,
no host workspace/private canary/Docker daemon socket available, and
Linux SO_PEERCRED DENY_PEER_PID on synthetic adapter direct access while
trusted parent can still execute once.

Python image digest pinned: python@sha256:
1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4.
Successful explicit digest-pinned CI run:
https://github.com/CarlosRafaHabio/before-you-buy-spatial-check/actions/runs/37816190688

## Two high CodeQL alerts diagnosed and corrected

Python and Actions CodeQL scanner jobs had SUCCESS, but the separate
GitHub Advanced Security CodeQL check initially returned FAILURE with
two HIGH annotations:
1. security_isolation/test_h8_container_boundary.py:31 — chmod 0755
   made a temporary test directory world-readable.
2. security_isolation/test_h8_container_boundary.py:48 — chmod 0666
   made the disposable synthetic socket world-writable.

The review used a temporary experimental branch-only read-only
GitHub Actions job, with checks:read only, querying the exact check-run
annotations API. Fix committed: f2b49931260212c4e1d2c07e418aab2fb0dba101.
The temporary directory is now 0700 and the socket 0660. The Docker
guest retains UID/GID 65534 and uses an explicit additional group matching
the socket inode, so it can still reach the socket without world access.
The kernel SO_PEERCRED policy remains the actual source of DENY_PEER_PID.

On fix HEAD, H8 PASSED again and independent CodeQL PR security gate
reported SUCCESS without new security alert count. The temporary
diagnostics workflow is now REMOVED so it does not keep receiving
an elevated checks:read permission and consuming further CI runs.

H8 and H6 optional-only test source directories are retained in the
*source distribution* for reproducibility. Existing wheel package list
continues to contain only spatial_check; no runtime dependencies added.

## Critical limitations

This is neither a sandbox for arbitrary model-generated code nor a guarantee
against a malicious privileged parent, Linux kernel/container escape, Docker
daemon compromise, FD delegation, provider-side replay or authority laundering.
H7-b intentionally proved preconnected FD transfer defeats pure PID guards.

Independent third-model audit is still pending; G3 has a synthetic
fixture corpus only. Never infer "zero exploitable vulnerabilities" from
green SAST. Keep PR #14 DRAFT and no merge / no deployment / no paid
resources / no Habio PR #43/#44 changes. SECURITY_PROMOTION HOLD.

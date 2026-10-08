# H8 immutable OCI image digest and first OS proof

Run on public GitHub ubuntu-24.04, first HEAD 607e425dafb86cadcbbc74a7a700d6883e1e3ce3:
https://github.com/CarlosRafaHabio/before-you-buy-spatial-check/actions/runs/37816024665

H8 all four isolated Docker tests PASS:
- UID=GID 65534, CapEff=0, no-new-privileges enabled, private PID=1
- root filesystem read-only, /tmp ephemeral and writable, only loopback
- no host private-canary file, no Docker daemon socket, no host checkout
- intentionally accessible Unix socket DENIED to container (DENY_PEER_PID);
  the trusted parent subsequently dispatched one synthetic lookup.

CI logged Docker engine v28.0.4, builtin seccomp, AppArmor and cgroup namespace.
OCI digest actually resolved from official Python image:
python@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4

The new workflow pins this EXACT digest instead of python:3.12-alpine tag.
Re-run required to prove digest-based image pulls and full test parity.

**Limitations:** a container is not a host security proof. Rootful Docker daemon,
host kernel, host-approved policy, FD delegation, process memory access and
container/kernel vulnerabilities remain relevant. No real agent was executed,
no real private credential or external effect was used, and this does not
establish CaMeL-equivalent guarantees.

DO NOT merge, deploy, enable paid cloud, or promote security status.

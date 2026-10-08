# H8 final CodeQL correction — private Unix socket and OS DAC denial

2026-10-08 / PR #14 Draft / Security Promotion HOLD.

Initial H8 deliberately chmodded test socket 0666 to verify SO_PEERCRED
denial even with an accessible endpoint. CodeQL PR check flagged two
HIGH security alerts for broad chmod permissions. First correction
removed directory world access and switched socket to 0660, but CodeQL
subsequently (asynchronously) reported ONE remaining HIGH:
"Overly permissive mask in chmod sets file to group writable"
at security_isolation/test_h8_container_boundary.py line 48.

No alert is suppressed or dismissed to force a green gate.

Final H8 deliberately does NOT broaden host socket mode or the container
group. The H7 adapter creates its synthetic IPC socket at 0600, owned by
the trusted runner user. Docker guest remains uid/gid 65534, all
capabilities dropped, no_new_privileges=1, network none, private PID
namespace, read-only root, bounded RAM/PIDs. Guest can observe the socket
path via one read-only bind-mounted synthetic IPC directory but its
attempt to connect must fail with EACCES (errno 13) due to kernel
discretionary access control. The trusted parent can subsequently
connect and execute one synthetic effect.

This is defense-in-depth separation of guarantees:
- H7 test H7_02: peer PID mismatch triggers DENY_PEER_PID even when
  same-UID process can independently connect to a socket.
- H7-b test H7_12: host delegation of an already-connected FD bypasses
  SO_PEERCRED: intentionally passing counterexample (UNFIXED TCB risk).
- H8 final: a different unprivileged UID in an isolated Docker container
  cannot even connect because of file permissions; H8 no longer claims
  it reached the kernel peer-PID check.

The temporary read-only GitHub diagnostics workflow was removed again.
No privileged sudo, OS kernel changes, cloud service, real secret or
effect. The Docker Python OCI image remains pinned by digest.

Gate: Only call final H8 good after 4/4 executed tests and full CodeQL
PR security check SUCCESS, full 360/360 source/sdist test parity and
clean zizmor. No changes to spatial_check/ core/main, no merges.

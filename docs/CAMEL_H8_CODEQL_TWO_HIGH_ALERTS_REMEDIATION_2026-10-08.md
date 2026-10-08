# H8 security scan findings and correction: two high CodeQL alerts

Date 2026-10-08. First H8 pinned-image HEAD:
a3ae459efeeea0e0e25c16a575ea0af62cf05701.

GitHub CodeQL successfully analyzed source but its PR security check FAILED:
"2 new alerts including 2 high severity security vulnerabilities".
The exact check annotations were extracted from GitHub's authenticated
check-runs annotations API via the branch-only, read-only diagnostics job:

1. security_isolation/test_h8_container_boundary.py:31 —
   "Overly permissive mask in chmod sets file to world readable."
2. security_isolation/test_h8_container_boundary.py:48 —
   "Overly permissive mask in chmod sets file to world writable."

Both were deliberately broadened *in a synthetic Docker test* so that the
guest could reach the test IPC socket, but global permissions were
unnecessary and unsafe even in a test fixture.

Bounded correction:
- Leave TemporaryDirectory root in mode 0700 (no chmod to 0755).
- Use mode 0660 (owner/group only) for the disposable synthetic socket.
- Docker guest remains UID:GID=65534:65534, CapEff zero, no_new_privs=1,
  but receives exactly one additional group from the synthetic socket
  inode via Docker --group-add (no workspace or other host mounts).
- The guest's POSIX permission is sufficient to connect to that one socket
  through the bind mount, while the independent kernel peer-PID filter
  must still deny an unauthorized separate process.
- Denied socket call must NOT consume the host's one approved effect.

This is a least-privilege test correction, NOT production security.
The guest deliberately shares that specific host file group, and this
is not a generally safe authorization model for arbitrary endpoints.

Acceptance requires H8 4/4 pass *and* original 360/360 source/sdist tests,
plus CodeQL Python/Actions and PR CodeQL security check no new alerts.
Do not mark CodeQL green based only on successful scanner execution.

No modification to public geometry package, AWS, SQL, Habio, paid services
or PR readiness. PR #14 stays Draft.

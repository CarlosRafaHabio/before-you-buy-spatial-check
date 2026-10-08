# H14 SQLite permission regression — fail-closed repair

The first H14 CI on commit c1e2f4e9cc74eafa35a0ffc72ee548533cd40b1a
ran 64 total Monty/H14 tests and failed exactly H14_14:
observed SQLite DB mode 0644 (420 decimal) versus required 0600
(384 decimal). The expected POSIX umask was NOT inherited as 0077;
sqlite3.connect initially created a world-readable authority DB despite
the enclosing fixture directory being private 0700.

Correction in DurableClaimV0:
- Require a host-private directory (0700, or at least no group/other bits)
  before initialization.
- Explicitly precreate DB path using POSIX os.open(O_RDWR | O_CREAT |
  O_NOFOLLOW, 0600) prior to sqlite3.connect.
- Require a regular file and reject any existing DB whose mode includes
  group/other access; NEVER silently chmod an externally controlled
  pre-existing file or symlink. Existing file must already be 0600.
- Close precreation descriptor, then open with sqlite3 for synchronous FULL
  and BEGIN IMMEDIATE atomic claims.

This is a narrow improvement in DATA-AT-REST file permissions. It does
NOT authenticate host-granted approvals; same-UID Python can modify the
file, and a compromised trusted host or a new epoch can bypass the
cooperative policy. Re-run full CI before accepting H14; no security
gate suppression, new dependency or production change.

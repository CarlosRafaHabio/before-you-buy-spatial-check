# Independent audit F05 — H14 SQLite connection lifecycle fix

**2026-10-08 / PR #14 Draft / offline and synthetic only.**

An independent adversarial review of the pre-H16 commit and H16 HEAD
reported a novel, concrete operational defect **F05**: SQLite connections
created by DurableClaimV0._connect() relied on garbage collection for
closure. In particular, the audit's own P09 script temporarily disabled
GC and observed process open FDs increase from 4 to 104 after 100
ledger.inspect() calls, returning to 4 only after gc.collect().
This confirms a real lifecycle issue but not default production failure,
nor an externally exploitable vulnerability in this research branch.

Root cause: \`with sqlite3.Connection as db:\` performs transaction
commit/rollback, **not** Connection.close(). Python's documented semantics:
https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager

Correction is intentionally small and local:
- Convert private _connect() into a contextlib.contextmanager.
- On success, yield under \`with conn:\` to preserve transaction semantics.
- Always close in \`finally\`, including exceptions while executing PRAGMAs
  or before/after returning from a short ledger operation.
- Preserve the earlier private-mode 0600 and NOFOLLOW checks, FULL
  durability setting, BEGIN IMMEDIATE, claim transitions and synthetic
  worker interfaces. No application, public wheel or API change.

Regression tests added as H14_21, H14_22 and H14_23:
(a) 100 inspect calls with GC disabled cause no material increase in
    /proc/self/fd on Linux;
(b) failed PRAGMA closes underlying connection (explicit mock); and
(c) a raised exception inside a transaction rolls back before closing.

Other audit results are preserved as findings, not patch camouflage.
The optional H14 direct privileged route still bypasses H15; no live
human authorization, tamper-resistant storage, process/tenant identity,
provider deduplication or privileged endpoint is implemented. No claim
of CaMeL-level security or unconditional runtime promotion.

Require full H9–H16 optional tests, core source + extracted sdist
tests, wheel exclusion gate, H8 synthetic tests, CodeQL PR gate and
Python/Actions, Hypothesis/Bandit and zizmor before final adjudication.

Decision proposal: ADOPT_F05_LIFECYCLE_FIX + KEEP_F01/F02/F03/F04/F06/
F07/F08_SCOPE_NOT_PROMOTED + HOLD_SECURITY_PROMOTION.

# H14 — persistent local claim before synthetic external effect

**Before You Buy — Spatial Check / PR #14 DRAFT / OFFLINE ONLY**
Date: 2026-10-08. Main, public geometry engine and wheel unchanged.

## Goal / narrow meaning

H13 makes a single callback worker killable, but proved a killed process can
leave a committed effect and separate G5 gate instances can execute duplicate
effects. H14 uses SQLite transactions to *persist one dispatch claim before
the worker*, and to reject duplicate claims by cooperating Python processes
after restarts. NO external service, cloud, paid API, tenant auth or real
human review is involved.

Stdlib SQLite DB is created inside a trusted private temporary test
directory, with synchronous FULL, busy timeout and BEGIN IMMEDIATE. One
row records (host grant ID, host epoch, exact canonical USER ID,
fixed operation = directory.lookup_user, state). UNIQUE(epoch,user_id,
operation) rejects a second grant for the same declared scope/epoch;
PRIMARY KEY(grant_id) protects ID collisions. All SQL uses parameterized
queries. Invalid values and scope collisions fail closed.

HOST registers a synthetic grant in GRANTED. When a tool is requested
from a model, the trusted host checks correct origin/authorization
**outside this primitive** and calls claim with exact host-approved scope.
Atomic compare-and-set GRANTED -> CLAIMED is COMMITTED before H13 worker
launch. Only one cooperating process wins per grant/scope/epoch.
After broker result, host writes CONFIRMED only for BROKER_COMPLETED,
otherwise UNKNOWN. A crash between claim and finalize leaves CLAIMED,
which is a terminal no-retry state; recovery marks it UNKNOWN, not GRANTED.

## Crucial limits

- Host can forge authority, generate a new epoch and bypass ledger with
  another direct callback; grant IDs/epochs are just host-supplied strings,
  NOT crypto-authenticated, independently witnessed human approval or
  secret tokens. The SQLite file does not isolate same-UID malicious
  Python or direct access to its storage: a privileged attacker could
  rewrite/delete/replace the DB, and an owner of the object could
  bypass this reference monitor altogether.
- Only cooperating processes sharing ONE local filesystem SQLite DB
  are coordinated. This is not distributed consensus, provider
  idempotency, remote exactly-once delivery or recovery.
- In UNKNOWN/CLAIMED, no automatic retry. This prioritizes preventing
  duplicate *dispatch* over liveness; a grant can become stuck even if
  the worker never started.
- Trusted host may crash after an external effect actually completed but
  before a receipt is written. Recovery marks UNKNOWN, not CONFIRMED.
- SQLite durability assumes the host OS/filesystem and disk honor fsync/
  synchronous; catastrophic storage loss/corruption is not covered.
  The database is a synthetic test fixture, not a production secure store.
- A new epoch (host-controlled) may issue another grant for same USER ID,
  and no real-world identity or approval semantics are established.
- All broker effects append only SYNTHETIC_EFFECT_V0 to a test temp file.
  No network, secrets, real database, AWS, Supabase, SQL production,
  or Habio PR #43/#44 change.

## Required tests (H14_01–17)

Reopens; schema, scope and grant identity; duplicate registration;
grant collision; separate host epochs (negative); 24 competing
actual Python processes with exactly one CLAIM_ACQUIRED; claimant OS crash
after claim; broker normal completion; broker timeout AFTER append/fync;
broker crash AFTER append/fsync; UNKNOWN cannot be promoted to success;
forged scope; fail-closed invalid dispatch; private 0600 DB;
invalid identifiers; trusted host OS crash *after broker completion but
before durable finish*; DB deletion does not silently create authority.

Passing concurrency tests prove ONLY one atomic claim for cooperating
processes sharing the same DB. They do not prove any privileged tool
is forced to use the broker or that a forged caller cannot manipulate
the source of the host approval.

**Provisional verdict:** ACCEPT_H14_DURABLE_CLAIM_POC +
HOLD_AUTHENTICATED_APPROVAL + HOLD_PROVIDER_IDEMPOTENCY +
HOLD_SECURITY_PROMOTION. All CI gates must pass before closing.

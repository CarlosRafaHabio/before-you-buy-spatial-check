"""H14: SQLite-backed, host-granted synthetic once-only DISPATCH lease.

This records ONE *cooperating host dispatch attempt* across processes and
restarts. It cannot prove an effect actually happened/was rolled back, nor
authenticate a model, caller, tenant, or human. TRUSTED bootstrap only.

NEVER promote this experimental SQLite file as production external authority.
All effects are test-only, no network, no real identities or secrets.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import stat
import re
import sqlite3
from typing import Literal

from .isolated_broker_v0 import BrokerOutcome, run_synthetic_broker

_USER = re.compile(r"USR-[0-9]{4}\Z", re.ASCII)
_EPOCH = re.compile(r"EP-[0-9]{6}\Z", re.ASCII)
_GRANT = re.compile(r"GR-[0-9a-f]{16}\Z", re.ASCII)
_OPERATION = "directory.lookup_user"


@dataclass(frozen=True, slots=True)
class GrantScope:
    """Chosen by trusted host, NOT by a guest tool request."""
    grant_id: str
    epoch: str
    user_id: str

    def __post_init__(self) -> None:
        for key, pattern in ((self.grant_id, _GRANT),
                             (self.epoch, _EPOCH),
                             (self.user_id, _USER)):
            if type(key) is not str or pattern.fullmatch(key) is None:
                raise ValueError("Invalid host authority identity.")


@dataclass(frozen=True, slots=True)
class ClaimResult:
    code: str
    attempted: bool = False
    state: str | None = None


class DurableClaimV0:
    """Single-file SQLite compare-and-set; no cross-host shared service.

    All methods trust local host code with access to this object/DB. A model
    must never receive this object, a DB filename, or ability to call grant().
    """
    __slots__ = ("_path",)

    def __init__(self, path: Path):
        if (not isinstance(path, Path) or not path.is_absolute()
                or path.suffix != ".sqlite3"
                or not path.parent.is_dir()):
            raise ValueError("Trusted host must select an absolute SQLite file.")
        # The caller must allocate a PRIVATE trusted directory. Do not
        # create an authority database in a world-readable path.
        if os.name == "posix" and path.parent.stat().st_mode & 0o077:
            raise ValueError("Host ledger directory must be owner-private.")
        self._path = path
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS dispatch_claims("
                "grant_id TEXT PRIMARY KEY,"
                "epoch TEXT NOT NULL, user_id TEXT NOT NULL,"
                "operation TEXT NOT NULL,"
                "state TEXT NOT NULL CHECK(state IN "
                "('GRANTED','CLAIMED','CONFIRMED','UNKNOWN')),"
                "UNIQUE(epoch,user_id,operation))"
            )

    def _connect(self) -> sqlite3.Connection:
        # SQLite's default O_CREAT respects umask but often produces 0644.
        # Create with explicit mode 0600 BEFORE SQLite opens the path.
        # O_NOFOLLOW excludes symlink substitution of the authority file.
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self._path, flags, 0o600)
        try:
            mode = os.fstat(fd).st_mode
            if not stat.S_ISREG(mode):
                raise ValueError("Authority DB must be a regular file.")
            if os.name == "posix" and mode & 0o077:
                raise ValueError("Authority DB has excessive permissions.")
        finally:
            os.close(fd)
        conn = sqlite3.connect(str(self._path), timeout=10.0,
                               isolation_level=None)
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn

    def grant(self, scope: GrantScope) -> ClaimResult:
        """Trusted host registration; prevent second grant for same epoch/id."""
        if type(scope) is not GrantScope:
            return ClaimResult("DENY_INVALID_GRANT")
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT grant_id,epoch,user_id,state FROM dispatch_claims "
                    "WHERE grant_id=? OR (epoch=? AND user_id=? AND operation=?)",
                    (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
                ).fetchall()
                if row:
                    # A repeated identical registration is NOT a fresh grant.
                    # Never turn CLAIMED, CONFIRMED or UNKNOWN back to GRANTED.
                    if len(row) == 1 and row[0][:3] == (
                        scope.grant_id, scope.epoch, scope.user_id
                    ):
                        db.execute("COMMIT")
                        return ClaimResult("GRANT_ALREADY_EXISTS",
                                           False, row[0][3])
                    db.execute("ROLLBACK")
                    return ClaimResult("DENY_GRANT_SCOPE_COLLISION")
                db.execute(
                    "INSERT INTO dispatch_claims "
                    "(grant_id,epoch,user_id,operation,state)"
                    " VALUES (?,?,?,?,?)",
                    (scope.grant_id, scope.epoch, scope.user_id,
                     _OPERATION, "GRANTED"),
                )
                db.execute("COMMIT")
                return ClaimResult("GRANT_REGISTERED", False, "GRANTED")
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise

    def claim(self, scope: GrantScope, *, raw_user_id: object) -> ClaimResult:
        """Atomic claim durable before external callback is attempted.

        The host must have validated model-to-host call origin/intent elsewhere.
        Possession of a valid scope/ID is NOT a caller identity proof.
        """
        if type(scope) is not GrantScope:
            return ClaimResult("DENY_INVALID_GRANT")
        if (type(raw_user_id) is not str
                or _USER.fullmatch(raw_user_id) is None):
            return ClaimResult("DENY_INVALID_IDENTIFIER")
        if raw_user_id != scope.user_id:
            return ClaimResult("DENY_OUT_OF_SCOPE")
        with self._connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                cur = db.execute(
                    "UPDATE dispatch_claims SET state='CLAIMED' "
                    "WHERE grant_id=? AND epoch=? AND user_id=? "
                    "AND operation=? AND state='GRANTED'",
                    (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
                )
                if cur.rowcount == 1:
                    db.execute("COMMIT")
                    return ClaimResult("CLAIM_ACQUIRED", True, "CLAIMED")
                row = db.execute(
                    "SELECT state FROM dispatch_claims "
                    "WHERE grant_id=? AND epoch=? AND user_id=? "
                    "AND operation=?",
                    (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
                ).fetchone()
                db.execute("COMMIT")
                if row is None:
                    return ClaimResult("DENY_GRANT_NOT_FOUND")
                return ClaimResult("DENY_ALREADY_CONSUMED", False, row[0])
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise

    def finish(self, scope: GrantScope, outcome: BrokerOutcome) -> ClaimResult:
        """Trusted host records outcome; UNKNOWN is terminal, not retryable.

        A forged BrokerOutcome created by malicious host Python is still
        possible. This is NOT an authenticated effect receipt.
        """
        if type(scope) is not GrantScope or type(outcome) is not BrokerOutcome:
            return ClaimResult("DENY_INVALID_FINISH")
        state = "CONFIRMED" if outcome.code == "BROKER_COMPLETED" else "UNKNOWN"
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Do not convert UNKNOWN back to CONFIRMED, or invert an old
            # CONFIRMED result, if the process called finish again.
            changed = db.execute(
                "UPDATE dispatch_claims SET state=? WHERE grant_id=? "
                "AND epoch=? AND user_id=? AND operation=? AND state='CLAIMED'",
                (state, scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
            )
            row = db.execute(
                "SELECT state FROM dispatch_claims WHERE grant_id=? "
                "AND epoch=? AND user_id=? AND operation=?",
                (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
            ).fetchone()
            db.execute("COMMIT")
        return ClaimResult(
            "FINISH_RECORDED" if changed.rowcount == 1 else "FINISH_NOT_APPLIED",
            False, row[0] if row else None
        )

    def recover_in_doubt(self, scope: GrantScope) -> ClaimResult:
        """A crashed owner left CLAIMED; record UNKNOWN, NEVER reissue."""
        if type(scope) is not GrantScope:
            return ClaimResult("DENY_INVALID_GRANT")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute(
                "UPDATE dispatch_claims SET state='UNKNOWN' "
                "WHERE grant_id=? AND epoch=? AND user_id=? "
                "AND operation=? AND state='CLAIMED'",
                (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
            )
            row = db.execute(
                "SELECT state FROM dispatch_claims WHERE grant_id=? "
                "AND epoch=? AND user_id=? AND operation=?",
                (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
            ).fetchone()
            db.execute("COMMIT")
        return ClaimResult(
            "RECOVERED_UNKNOWN" if changed.rowcount == 1
            else "RECOVERY_NO_CHANGE",
            False, row[0] if row else None,
        )

    def inspect(self, scope: GrantScope) -> str | None:
        if type(scope) is not GrantScope:
            raise ValueError("Invalid trusted host grant")
        with self._connect() as db:
            row = db.execute(
                "SELECT state FROM dispatch_claims WHERE grant_id=? "
                "AND epoch=? AND user_id=? AND operation=?",
                (scope.grant_id, scope.epoch, scope.user_id, _OPERATION),
            ).fetchone()
            return row[0] if row else None


def dispatch_synthetic_once(
    ledger: DurableClaimV0, scope: GrantScope, *, raw_user_id: object,
    broker_mode: Literal["write_return", "sleep_before", "write_hang",
                         "write_crash", "spawn_writer_then_hang"],
    scratch_log: Path, timeout_secs: float = 1.0,
) -> ClaimResult:
    """One trusted host call path. Exact grant claim committed BEFORE worker.

    If the host dies after claim, the record is CLAIMED, which is terminal
    for further dispatch. It can later be marked UNKNOWN for investigation.
    """
    if type(ledger) is not DurableClaimV0:
        return ClaimResult("DENY_INVALID_LEDGER")
    # All config is TRUSTED bootstrap. Validate before burning the claim.
    if (type(broker_mode) is not str
            or broker_mode not in ("write_return", "sleep_before",
                                   "write_hang", "write_crash",
                                   "spawn_writer_then_hang")
            or not isinstance(scratch_log, Path)
            or not scratch_log.is_absolute()
            or not scratch_log.parent.is_dir()
            or type(timeout_secs) not in (float, int)
            or not .05 <= timeout_secs <= 5.0):
        return ClaimResult("DENY_INVALID_DISPATCH")
    claimed = ledger.claim(scope, raw_user_id=raw_user_id)
    if not claimed.attempted:
        return claimed
    try:
        outcome = run_synthetic_broker(
            mode=broker_mode, scratch_log=scratch_log,
            timeout_secs=timeout_secs
        )
    except BaseException:
        # No automatic retry; durable CLAIMED remains in doubt.
        raise
    finalized = ledger.finish(scope, outcome)
    if outcome.code == "BROKER_COMPLETED" and finalized.state == "CONFIRMED":
        return ClaimResult("DISPATCH_CONFIRMED", True, "CONFIRMED")
    return ClaimResult("DISPATCH_OUTCOME_UNKNOWN", True,
                       finalized.state)

"""H14: SQLite atomic claims across processes, restart, crash & effects.

All grants are synthetic HOST-CHOSEN. Green negative witnesses expose
missing authentication and provider idempotency, not guarantees.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest

from prototypes.camel_selective_v0.durable_claim_v0 import (
    DurableClaimV0, GrantScope, dispatch_synthetic_once,
)
from prototypes.camel_selective_v0.isolated_broker_v0 import BrokerOutcome


SCOPE = GrantScope("GR-0123456789abcdef", "EP-000042", "USR-0042")
OTHER = GrantScope("GR-fedcba9876543210", "EP-000042", "USR-0042")
NEW_EPOCH = GrantScope("GR-fedcba9876543210", "EP-000043", "USR-0042")
EFFECT = b"SYNTHETIC_EFFECT_V0\n"


class H14DurableLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="h14-private-")
        self.dir = Path(self.tmp.name)
        self.db_path = self.dir / "authority.sqlite3"
        self.effect_path = self.dir / "synthetic.log"
        self.ledger = DurableClaimV0(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def effects(self):
        return self.effect_path.read_bytes() if self.effect_path.exists() else b""

    def grant(self):
        result = self.ledger.grant(SCOPE)
        self.assertEqual(result.code, "GRANT_REGISTERED")
        return result

    def test_H14_01_claim_survives_fresh_ledger_instance(self):
        self.grant()
        self.assertEqual(self.ledger.claim(SCOPE, raw_user_id="USR-0042").code,
                         "CLAIM_ACQUIRED")
        reopened = DurableClaimV0(self.db_path)
        out = reopened.claim(SCOPE, raw_user_id="USR-0042")
        self.assertEqual((out.code, out.state),
                         ("DENY_ALREADY_CONSUMED", "CLAIMED"))
        self.assertEqual(self.effects(), b"")

    def test_H14_02_invalid_or_wrong_scope_does_not_consume(self):
        self.grant()
        for value, code in (({"user_id":"USR-0042"}, "DENY_INVALID_IDENTIFIER"),
                            ("USR-9999", "DENY_OUT_OF_SCOPE"),
                            ("USR-0042;DO", "DENY_INVALID_IDENTIFIER"),
                            (True, "DENY_INVALID_IDENTIFIER")):
            self.assertEqual(self.ledger.claim(SCOPE, raw_user_id=value).code,
                             code)
        self.assertEqual(self.ledger.inspect(SCOPE), "GRANTED")

    def test_H14_03_duplicate_registration_cannot_reset_state(self):
        self.grant()
        self.assertEqual(self.ledger.claim(SCOPE, raw_user_id=SCOPE.user_id).code,
                         "CLAIM_ACQUIRED")
        result = DurableClaimV0(self.db_path).grant(SCOPE)
        self.assertEqual((result.code, result.state),
                         ("GRANT_ALREADY_EXISTS", "CLAIMED"))
        self.assertEqual(self.ledger.inspect(SCOPE), "CLAIMED")

    def test_H14_04_same_epoch_scope_cannot_issue_fresh_grant_id(self):
        self.grant()
        self.assertEqual(self.ledger.grant(OTHER).code,
                         "DENY_GRANT_SCOPE_COLLISION")
        self.assertEqual(self.ledger.inspect(SCOPE), "GRANTED")
        self.assertIsNone(self.ledger.inspect(OTHER))

    def test_H14_05_different_epoch_can_issue_new_grant_negative(self):
        # NEGATIVE: host can choose a new epoch. The ledger does not verify
        # actual human/authority epoch ownership or authentication.
        self.grant()
        self.assertEqual(self.ledger.grant(NEW_EPOCH).code, "GRANT_REGISTERED")
        self.assertEqual(self.ledger.claim(SCOPE, raw_user_id=SCOPE.user_id).code,
                         "CLAIM_ACQUIRED")
        self.assertEqual(self.ledger.claim(
            NEW_EPOCH, raw_user_id=NEW_EPOCH.user_id).code, "CLAIM_ACQUIRED")

    def test_H14_06_multiple_PYTHON_PROCESSES_only_one_atomic_claim(self):
        self.grant()
        root = str(Path(__file__).resolve().parents[1])
        script = (
            "from pathlib import Path;"
            "from prototypes.camel_selective_v0.durable_claim_v0 "
            "import DurableClaimV0,GrantScope;"
            "import sys;"
            "s=GrantScope('GR-0123456789abcdef','EP-000042','USR-0042');"
            "r=DurableClaimV0(Path(sys.argv[1])).claim(s,raw_user_id='USR-0042');"
            "print(r.code)"
        )
        def run(_):
            proc = subprocess.run(
                [sys.executable, "-c", script, str(self.db_path)],
                cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=12, check=True
            )
            return proc.stdout.strip()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(run, range(24)))
        self.assertEqual(results.count("CLAIM_ACQUIRED"), 1)
        self.assertEqual(results.count("DENY_ALREADY_CONSUMED"), 23)
        self.assertEqual(self.ledger.inspect(SCOPE), "CLAIMED")

    def test_H14_07_crashed_claimant_never_reissued(self):
        self.grant()
        root = str(Path(__file__).resolve().parents[1])
        script = (
            "from pathlib import Path;"
            "from prototypes.camel_selective_v0.durable_claim_v0 "
            "import DurableClaimV0,GrantScope;"
            "import sys,os;"
            "s=GrantScope('GR-0123456789abcdef','EP-000042','USR-0042');"
            "r=DurableClaimV0(Path(sys.argv[1])).claim(s,raw_user_id='USR-0042');"
            "assert r.attempted;os._exit(17)"
        )
        proc = subprocess.run(
            [sys.executable, "-c", script, str(self.db_path)],
            cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            timeout=12
        )
        self.assertEqual(proc.returncode, 17, proc.stderr.decode()[:200])
        recovered = DurableClaimV0(self.db_path)
        self.assertEqual(recovered.inspect(SCOPE), "CLAIMED")
        self.assertEqual(recovered.recover_in_doubt(SCOPE).code,
                         "RECOVERED_UNKNOWN")
        self.assertEqual(recovered.inspect(SCOPE), "UNKNOWN")
        self.assertEqual(recovered.claim(SCOPE, raw_user_id="USR-0042").code,
                         "DENY_ALREADY_CONSUMED")

    def test_H14_08_actual_broker_success_persists_confirmed(self):
        self.grant()
        r = dispatch_synthetic_once(
            self.ledger, SCOPE, raw_user_id="USR-0042",
            broker_mode="write_return", scratch_log=self.effect_path,
            timeout_secs=2,
        )
        self.assertEqual((r.code,r.state),
                         ("DISPATCH_CONFIRMED","CONFIRMED"))
        self.assertEqual(self.effects(), EFFECT)
        reopened = DurableClaimV0(self.db_path)
        again = dispatch_synthetic_once(
            reopened, SCOPE, raw_user_id="USR-0042",
            broker_mode="write_return", scratch_log=self.effect_path,
            timeout_secs=2,
        )
        self.assertEqual((again.code, again.state),
                         ("DENY_ALREADY_CONSUMED", "CONFIRMED"))
        self.assertEqual(self.effects(), EFFECT)

    def test_H14_09_partial_committed_effect_unknown_and_no_retry(self):
        self.grant()
        r = dispatch_synthetic_once(
            self.ledger, SCOPE, raw_user_id="USR-0042",
            broker_mode="write_hang", scratch_log=self.effect_path,
            timeout_secs=.8,
        )
        self.assertEqual((r.code, r.state),
                         ("DISPATCH_OUTCOME_UNKNOWN", "UNKNOWN"))
        self.assertEqual(self.effects(), EFFECT)
        again = self.ledger.claim(SCOPE, raw_user_id="USR-0042")
        self.assertEqual(again.code, "DENY_ALREADY_CONSUMED")
        self.assertEqual(self.effects(), EFFECT)

    def test_H14_10_crash_after_effect_unknown(self):
        self.grant()
        r = dispatch_synthetic_once(
            self.ledger, SCOPE, raw_user_id="USR-0042",
            broker_mode="write_crash", scratch_log=self.effect_path,
            timeout_secs=2,
        )
        self.assertEqual((r.code, r.state),
                         ("DISPATCH_OUTCOME_UNKNOWN", "UNKNOWN"))
        self.assertEqual(self.effects(), EFFECT)

    def test_H14_11_finish_cannot_promote_unknown_or_reopen_used(self):
        self.grant()
        self.ledger.claim(SCOPE, raw_user_id="USR-0042")
        self.assertEqual(self.ledger.finish(
            SCOPE, BrokerOutcome("BROKER_TIMEOUT_UNKNOWN")).state, "UNKNOWN")
        assert self.ledger.finish(
            SCOPE, BrokerOutcome("BROKER_COMPLETED")).code == "FINISH_NOT_APPLIED"
        self.assertEqual(self.ledger.inspect(SCOPE), "UNKNOWN")
        self.assertEqual(self.ledger.grant(SCOPE).state, "UNKNOWN")

    def test_H14_12_ungranted_and_forged_scope_denied(self):
        self.assertEqual(self.ledger.claim(
            SCOPE, raw_user_id="USR-0042").code, "DENY_GRANT_NOT_FOUND")
        self.grant()
        forged = GrantScope(SCOPE.grant_id, "EP-000043", SCOPE.user_id)
        self.assertEqual(self.ledger.claim(
            forged, raw_user_id="USR-0042").code, "DENY_GRANT_NOT_FOUND")
        self.assertEqual(self.ledger.inspect(SCOPE), "GRANTED")

    def test_H14_13_invalid_dispatch_does_not_burn_claim(self):
        self.grant()
        for mode in ("../../bin/sh", "write_return;rm", None):
            r = dispatch_synthetic_once(
                self.ledger, SCOPE, raw_user_id="USR-0042",
                broker_mode=mode, scratch_log=self.effect_path,
            )
            self.assertEqual(r.code, "DENY_INVALID_DISPATCH")
        self.assertEqual(self.ledger.inspect(SCOPE), "GRANTED")

    def test_H14_14_durable_file_is_host_private_on_linux(self):
        if os.name != "posix":
            self.skipTest("POSIX chmod permissions only")
        self.assertEqual(self.db_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.dir.stat().st_mode & 0o077, 0)

    def test_H14_15_bad_grant_id_and_epoch_rejected(self):
        for gid,ep,userid in (
            ("GR-unsafe", "EP-000042", "USR-0042"),
            ("GR-0123456789abcdef", "EP-invalid", "USR-0042"),
            ("GR-0123456789abcdef", "EP-000042", "USR-٤٠٤٢"),
        ):
            with self.subTest(value=gid):
                with self.assertRaises(ValueError):
                    GrantScope(gid, ep, userid)

    def test_H14_16_no_success_receipt_if_crashed_after_broker_effect(self):
        # The broker succeeds but host dies before finish() commits.
        self.grant()
        root = str(Path(__file__).resolve().parents[1])
        script = (
            "from pathlib import Path;"
            "from prototypes.camel_selective_v0.durable_claim_v0 "
            "import DurableClaimV0,GrantScope;"
            "from prototypes.camel_selective_v0.isolated_broker_v0 "
            "import run_synthetic_broker;"
            "import sys,os;"
            "s=GrantScope('GR-0123456789abcdef','EP-000042','USR-0042');"
            "l=DurableClaimV0(Path(sys.argv[1]));"
            "assert l.claim(s,raw_user_id=s.user_id).attempted;"
            "r=run_synthetic_broker(mode='write_return',"
            "scratch_log=Path(sys.argv[2]),timeout_secs=2);"
            "assert r.code=='BROKER_COMPLETED';"
            "os._exit(17)"
        )
        p = subprocess.run(
            [sys.executable, "-c", script, str(self.db_path),
             str(self.effect_path)], cwd=root,
            stdin=subprocess.DEVNULL, capture_output=True, timeout=12,
        )
        self.assertEqual(p.returncode, 17, p.stderr[:250])
        self.assertEqual(self.effects(), EFFECT)
        self.assertEqual(self.ledger.inspect(SCOPE), "CLAIMED")
        self.assertEqual(self.ledger.recover_in_doubt(SCOPE).state, "UNKNOWN")
        self.assertEqual(self.ledger.claim(
            SCOPE, raw_user_id=SCOPE.user_id).code, "DENY_ALREADY_CONSUMED")
        self.assertEqual(self.effects(), EFFECT)

    def test_H14_17_missing_or_mutated_db_does_not_silently_allow(self):
        self.grant()
        self.db_path.unlink()
        # DB was deleted. Reopening DOES NOT silently recreate a grant:
        # it is a fresh empty DB requiring an independently issued grant.
        reopened = DurableClaimV0(self.db_path)
        self.assertEqual(reopened.claim(
            SCOPE, raw_user_id=SCOPE.user_id).code,
            "DENY_GRANT_NOT_FOUND")
        self.assertEqual(self.effects(), b"")


if __name__ == "__main__":
    unittest.main()

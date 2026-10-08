"""H13: synthetic killable broker, partial effects, replay and descendant.

These tests do NOT claim the process is an OS sandbox: its code runs under
the same host user, and an already committed effect cannot be rolled back.
"""
import os
from pathlib import Path
import tempfile
import time
import unittest

from prototypes.camel_selective_v0.isolated_broker_v0 import (
    run_synthetic_broker,
)
from prototypes.camel_selective_v0.monty_host_bridge_v0 import MontyHostBridgeV0
from prototypes.camel_selective_v0.scoped_data_use_v0 import HostScopedUserLookup


@unittest.skipUnless(os.name == "posix" and hasattr(os, "killpg"),
                     "POSIX process-group fixture only")
class H13KillableBroker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="h13-synthetic-")
        self.path = Path(self.tmp.name) / "effects.log"

    def tearDown(self):
        self.tmp.cleanup()

    def contents(self):
        return self.path.read_bytes() if self.path.exists() else b""

    def test_H13_01_normal_worker_completes_and_reaped(self):
        r = run_synthetic_broker(
            mode="write_return", scratch_log=self.path, timeout_secs=2)
        self.assertEqual(r.code, "BROKER_COMPLETED")
        self.assertTrue(r.worker_reaped)
        self.assertEqual(r.child_returncode, 0)
        self.assertNotEqual(r.worker_pid, os.getpid())
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")

    def test_H13_02_pre_effect_hang_is_killed_without_synthetic_log(self):
        r = run_synthetic_broker(
            mode="sleep_before", scratch_log=self.path, timeout_secs=.3)
        self.assertEqual(r.code, "BROKER_TIMEOUT_UNKNOWN")
        self.assertTrue(r.worker_reaped)
        self.assertNotEqual(r.child_returncode, 0)
        self.assertEqual(self.contents(), b"")

    def test_H13_03_post_effect_hang_is_killed_but_effect_persists(self):
        r = run_synthetic_broker(
            mode="write_hang", scratch_log=self.path, timeout_secs=.8)
        self.assertEqual(r.code, "BROKER_TIMEOUT_UNKNOWN")
        self.assertTrue(r.worker_reaped)
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")
        # Green is deliberately NEGATIVE evidence: kill != rollback.

    def test_H13_04_crash_after_effect_must_remain_unknown(self):
        r = run_synthetic_broker(
            mode="write_crash", scratch_log=self.path, timeout_secs=2)
        self.assertEqual(r.code, "BROKER_OUTCOME_UNKNOWN")
        self.assertTrue(r.worker_reaped)
        self.assertEqual(r.child_returncode, 17)
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")

    def test_H13_05_kill_group_prevents_inherited_descendant_effect(self):
        r = run_synthetic_broker(
            mode="spawn_writer_then_hang", scratch_log=self.path,
            timeout_secs=.4)
        self.assertEqual(r.code, "BROKER_TIMEOUT_UNKNOWN")
        self.assertTrue(r.worker_reaped)
        time.sleep(1.3)  # grandchild would have appended after 1.0 seconds
        self.assertEqual(self.contents(), b"")

    def test_H13_06_untrusted_guest_can_only_call_preapproved_host_gate(self):
        result_log = []
        def isolated_callback(_args):
            result = run_synthetic_broker(
                mode="write_return", scratch_log=self.path, timeout_secs=2)
            result_log.append(result)
            if result.code != "BROKER_COMPLETED":
                raise RuntimeError("Ambiguous synthetic worker")
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=isolated_callback)
        bridge = MontyHostBridgeV0(gate, wall_budget_secs=4)
        first = bridge.run("lookup_user('USR-9999')")
        second = bridge.run("lookup_user('USR-0042')")
        third = bridge.run("lookup_user('USR-0042')")
        self.assertEqual(first.value, "DENY_OUT_OF_SCOPE")
        self.assertEqual(second.value, "HANDLER_RETURNED")
        self.assertEqual(third.value, "DENY_REPLAY_PROCESS_LOCAL")
        self.assertEqual(len(result_log), 1)
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")

    def test_H13_07_killed_effect_yields_unknown_and_does_not_retry(self):
        calls = []
        def callback(_args):
            result = run_synthetic_broker(
                mode="write_hang", scratch_log=self.path,
                timeout_secs=.8)
            calls.append(result)
            if result.code != "BROKER_COMPLETED":
                raise RuntimeError("Synthetic outcome unknown")
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=callback)
        bridge = MontyHostBridgeV0(gate, wall_budget_secs=4)
        first = bridge.run("lookup_user('USR-0042')")
        again = bridge.run("lookup_user('USR-0042')")
        self.assertEqual(first.value, "HANDLER_OUTCOME_UNKNOWN")
        self.assertEqual(again.value, "DENY_REPLAY_PROCESS_LOCAL")
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].worker_reaped)
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")

    def test_H13_08_separate_gate_instances_replay_negative_witness(self):
        # NEGATIVE: no durable provider idempotency; two independent grants
        # with identical scope can each trigger the same synthetic action.
        for _ in range(2):
            def callback(_args):
                result = run_synthetic_broker(
                    mode="write_return", scratch_log=self.path,
                    timeout_secs=2)
                self.assertEqual(result.code, "BROKER_COMPLETED")
            gate = HostScopedUserLookup(
                approved_user_id="USR-0042", handler=callback)
            self.assertEqual(gate.invoke("USR-0042").code, "HANDLER_RETURNED")
        self.assertEqual(
            self.contents(), b"SYNTHETIC_EFFECT_V0\n" * 2)

    def test_H13_09_no_guest_supplied_worker_mode_or_path(self):
        for mode in ("../../bin/sh", "python -c os.system('id')",
                     "write_return;rm", "", None):
            with self.subTest(mode=mode):
                r = run_synthetic_broker(mode=mode,
                                          scratch_log=self.path)
                self.assertEqual(r.code, "DENY_BROKER_MODE")
        self.assertEqual(self.contents(), b"")

    def test_H13_10_invalid_budgets_and_targets_fail_before_spawn(self):
        for budget in (-1, 0, False, 999, "1"):
            with self.subTest(budget=budget):
                r = run_synthetic_broker(
                    mode="write_return", scratch_log=self.path,
                    timeout_secs=budget)
                self.assertEqual(r.code, "DENY_BROKER_BUDGET")
        self.assertEqual(
            run_synthetic_broker(
                mode="write_return", scratch_log=Path("relative.file")).code,
            "DENY_BROKER_TARGET")
        self.assertEqual(self.contents(), b"")

    def test_H13_11_normal_worker_reuse_still_requires_one_shot(self):
        # Each subprocess is fresh; the PROCESS-LOCAL gate, not a worker,
        # prevents second dispatch when reused within one host lifetime.
        calls = []
        def callback(args):
            calls.append(args)
            result = run_synthetic_broker(
                mode="write_return", scratch_log=self.path, timeout_secs=2)
            if result.code != "BROKER_COMPLETED":
                raise RuntimeError("Synthetic error")
        gate = HostScopedUserLookup(
            approved_user_id="USR-0042", handler=callback)
        results = [gate.invoke("USR-0042").code for _ in range(6)]
        self.assertEqual(results, ["HANDLER_RETURNED"] +
                         ["DENY_REPLAY_PROCESS_LOCAL"] * 5)
        self.assertEqual(calls, [("USR-0042",)])
        self.assertEqual(self.contents(), b"SYNTHETIC_EFFECT_V0\n")


if __name__ == "__main__":
    unittest.main()

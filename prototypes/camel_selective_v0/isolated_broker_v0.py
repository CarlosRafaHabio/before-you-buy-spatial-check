"""H13: killable subprocess for a narrowly scoped SYNTHETIC trusted callback.

The broker owns an immutable set of worker modes. Trusted bootstrap MUST
choose both the mode and the scratch-file path. Never forward model-supplied
file paths, commands, executable names, environment, or privileges.

Linux-only research fixture; same OS UID, NO sandbox, NO authentication,
NO actual transaction idempotency and NO ability to undo partial effects.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import monotonic

_MODES = frozenset({
    "write_return", "sleep_before", "write_hang",
    "write_crash", "spawn_writer_then_hang",
})


@dataclass(frozen=True, slots=True)
class BrokerOutcome:
    code: str
    worker_pid: int | None = None
    worker_reaped: bool = False
    child_returncode: int | None = None


def _stop_group_and_reap(proc: subprocess.Popen[bytes]) -> bool:
    """SIGKILL the new session's group, then reap leader via communicate.

    This cannot revoke external side effects, or kill a descendant which
    deliberately escaped the group. Those threats remain out of scope.
    """
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=3.0)
    except subprocess.TimeoutExpired:
        # Fail with unknown outcome even if untrusted child escapes the group.
        proc.kill()
        try:
            proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            return False
    return proc.poll() is not None


def run_synthetic_broker(*, mode: str, scratch_log: Path,
                         timeout_secs: float = .3) -> BrokerOutcome:
    """Execute one FIXED synthetic action in a killable, separate Python PID.

    This is a trusted-only callable, not a public agent or model API.
    """
    if os.name != "posix" or not hasattr(os, "killpg"):
        return BrokerOutcome("BROKER_PLATFORM_UNSUPPORTED")
    if type(mode) is not str or mode not in _MODES:
        return BrokerOutcome("DENY_BROKER_MODE")
    if (not isinstance(scratch_log, Path) or not scratch_log.is_absolute()
            or not scratch_log.parent.is_dir()):
        return BrokerOutcome("DENY_BROKER_TARGET")
    if (type(timeout_secs) not in (float, int)
            or not .05 <= timeout_secs <= 5.0):
        return BrokerOutcome("DENY_BROKER_BUDGET")
    # An explicit code path + Python -I avoids executable resolution through
    # model-controlled PATH, sitecustomize, PYTHONPATH or arbitrary imports.
    worker = Path(__file__).with_name("isolated_broker_worker_v0.py").resolve()
    if not worker.is_file() or not Path(sys.executable).is_absolute():
        return BrokerOutcome("DENY_BROKER_BOOTSTRAP")
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", str(worker), mode, str(scratch_log)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            env={"PYTHONIOENCODING": "utf-8"},
        )
        try:
            stdout, _ = proc.communicate(timeout=timeout_secs)
        except subprocess.TimeoutExpired:
            reaped = _stop_group_and_reap(proc)
            return BrokerOutcome("BROKER_TIMEOUT_UNKNOWN",
                                 proc.pid, reaped, proc.returncode)
        if proc.returncode != 0 or stdout != b'{"code": "WORKER_DONE"}\n':
            return BrokerOutcome("BROKER_OUTCOME_UNKNOWN",
                                 proc.pid, True, proc.returncode)
        return BrokerOutcome("BROKER_COMPLETED", proc.pid, True,
                             proc.returncode)
    except (OSError, ValueError, subprocess.SubprocessError):
        if proc is not None:
            _stop_group_and_reap(proc)
            return BrokerOutcome("BROKER_OUTCOME_UNKNOWN", proc.pid,
                                 proc.poll() is not None, proc.returncode)
        return BrokerOutcome("BROKER_START_REJECTED")

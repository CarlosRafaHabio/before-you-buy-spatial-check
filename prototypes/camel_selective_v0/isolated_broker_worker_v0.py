"""H13: fixed-action synthetic worker executable. No import from project.

DO NOT expose this script as a tool to a model. The *trusted supervisor*
chooses the fixed mode and synthetic file path, then executes this script
using an absolute path and Python isolated startup (-I). Only TEST DATA.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

_RECORD = b"SYNTHETIC_EFFECT_V0\n"
_MODES = frozenset({
    "write_return", "sleep_before", "write_hang",
    "write_crash", "spawn_writer_then_hang",
})


def write_synthetic_effect(path: str) -> None:
    # Trusted synthetic fixture path, never derived from guest Python.
    options = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        options |= os.O_NOFOLLOW
    fd = os.open(path, options, 0o600)
    try:
        os.write(fd, _RECORD)
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    if len(sys.argv) != 3:
        return 4
    mode, path = sys.argv[1:]
    if mode == "delayed_writer_child":
        time.sleep(1.0)
        write_synthetic_effect(path)
        return 0
    if mode not in _MODES or not Path(path).is_absolute():
        return 4
    if mode == "sleep_before":
        time.sleep(30)
        write_synthetic_effect(path)
    elif mode == "spawn_writer_then_hang":
        # Deliberate inherited process-group member. No new session,
        # and no stdio/other worker FD inheritance.
        subprocess.Popen(
            [sys.executable, "-I", str(Path(__file__).resolve()),
             "delayed_writer_child", path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        time.sleep(30)
    else:
        write_synthetic_effect(path)
        if mode == "write_hang":
            time.sleep(30)
        if mode == "write_crash":
            os._exit(17)
    sys.stdout.write(json.dumps({"code": "WORKER_DONE"}) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""H7: OFFLINE Linux Unix-socket peer-PID mediation experiment.

A separate *trusted adapter process* is launched by a trusted parent.
The adapter accepts ONE exact, host-preapproved synthetic lookup from its
kernel-verified parent PID. An untrusted *separate Python process* cannot
invoke it directly just by knowing the socket path/approved identifier.

IMPORTANT: NOT an OS sandbox. Same-UID filesystem/process attacks, FD passing,
PID reuse, ptrace, a compromised trusted parent, forged adapter bootstrap, and
callback side effects remain out of scope. No secrets, cloud, or real effects.
No externally supplied Python code is interpreted or loaded by this module.
"""
from __future__ import annotations

import argparse
import errno
import time
import json
import os
import socket
import socketserver
import struct
from typing import Any

from .scoped_data_use_v0 import HostScopedUserLookup


_LIMIT = 4096


def _peer_pid(conn: socket.socket) -> int | None:
    if not hasattr(socket, "SO_PEERCRED"):
        return None
    try:
        pid, _uid, _gid = struct.unpack(
            "3i",
            conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")),
        )
        return pid
    except (OSError, struct.error):
        return None


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate input field.")
        out[key] = value
    return out


class _LocalAdapter(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 128  # accept bounded concurrent synthetic clients

    def __init__(self, path: str, approved_id: str, parent_pid: int):
        self.bound_parent_pid = parent_pid
        self.synthetic_calls: list[tuple[str, ...]] = []
        self.lookup = HostScopedUserLookup(
            approved_user_id=approved_id,
            handler=lambda args: self.synthetic_calls.append(args),
        )
        super().__init__(path, _RequestHandler)


class _RequestHandler(socketserver.BaseRequestHandler):
    def _reply(self, code: str, attempted: bool = False) -> None:
        # Never transmit exception strings or interpreter traces.
        data = json.dumps({"attempted": attempted, "code": code},
                          separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"
        try:
            self.request.sendall(data)
        except (OSError, BrokenPipeError):
            pass

    def handle(self) -> None:
        self.request.settimeout(3.0)
        server: _LocalAdapter = self.server
        # Parent must still be alive and remain the process that launched
        # the adapter. Exact PID equality is NOT a durable identity credential.
        if (os.getppid() != server.bound_parent_pid or
                _peer_pid(self.request) != server.bound_parent_pid):
            self._reply("DENY_PEER_PID")
            return
        try:
            with self.request.makefile("rb") as source:
                frame = source.readline(_LIMIT + 1)
            if len(frame) > _LIMIT:
                self._reply("DENY_FRAME_TOO_LARGE")
                return
            if not frame.endswith(b"\n"):
                self._reply("DENY_INVALID_FRAME")
                return
            obj = json.loads(frame.decode("utf-8"),
                             object_pairs_hook=_unique_keys)
            if type(obj) is not dict or set(obj) != {"user_id"}:
                self._reply("DENY_INVALID_SCHEMA")
                return
            user_id = obj["user_id"]
            if type(user_id) is not str:
                self._reply("DENY_INVALID_SCHEMA")
                return
            result = server.lookup.invoke(user_id)
            self._reply(result.code, result.attempted)
        except (ValueError, UnicodeError, TypeError, OSError, TimeoutError):
            self._reply("DENY_INVALID_FRAME")
        except Exception:
            # An unexpected parser/runtime exception is not authority to run
            # the callback. Do not return a Python stack trace to the caller.
            self._reply("DENY_INTERNAL_ERROR")


def request_raw(
    path: str, wire: bytes, *, expected_server_pid: int | None = None,
) -> dict[str, Any]:
    """Test-only client: verify server PID before sending when known."""
    if type(path) is not str or type(wire) is not bytes:
        raise TypeError("Unix client requires socket path and bytes.")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(3.0)
        # Linux AF_UNIX can signal EAGAIN under transient connection-backlog
        # pressure. Retrying connect does not retry a tool execution: no
        # request bytes have been sent and the adapter has not dispatched.
        for attempt in range(20):
            try:
                conn.connect(path)
                break
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EWOULDBLOCK) or attempt == 19:
                    raise
                time.sleep(0.01)
        if expected_server_pid is not None and _peer_pid(conn) != expected_server_pid:
            return {"attempted": False, "code": "DENY_SERVER_PID"}
        conn.sendall(wire)
        with conn.makefile("rb") as source:
            result = source.readline(1025)
        if len(result) > 1024 or not result.endswith(b"\n"):
            raise ValueError("Invalid adapter response.")
        data = json.loads(result.decode("ascii"))
        if (type(data) is not dict or set(data) != {"attempted", "code"}
                or type(data["attempted"]) is not bool
                or type(data["code"]) is not str):
            raise ValueError("Unexpected adapter response schema.")
        return data


def request(
    path: str, data: object, *, expected_server_pid: int | None = None,
) -> dict[str, Any]:
    return request_raw(
        path,
        json.dumps(data, ensure_ascii=True, allow_nan=False,
                   separators=(",", ":")).encode("ascii") + b"\n",
        expected_server_pid=expected_server_pid,
    )


def _serve(path: str, approved_id: str) -> None:
    if not hasattr(socket, "SO_PEERCRED") or not hasattr(socket, "AF_UNIX"):
        raise RuntimeError("Linux Unix peer credentials are mandatory.")
    if not os.path.isabs(path) or os.path.exists(path):
        raise ValueError("Server requires an unused absolute socket path.")
    if not (1 <= len(path.encode("utf-8")) <= 96):
        raise ValueError("Unsafe socket path length.")
    os.umask(0o077)
    with _LocalAdapter(path, approved_id, os.getppid()) as server:
        os.chmod(path, 0o600)
        try:
            server.serve_forever(poll_interval=0.05)
        finally:
            if os.path.exists(path):
                os.unlink(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline H7 synthetic adapter")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--approved-id", required=True)
    args = parser.parse_args()
    _serve(args.socket, args.approved_id)


if __name__ == "__main__":
    main()

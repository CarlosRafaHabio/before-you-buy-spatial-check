# H7 socket concurrency regression and bounded retry

First H7 source commit: `26aa5a10a9b1678964add320029af7ccf4d9a78e`.

Initial CI ran 359 tests and had one error in H7_10. The Linux
Unix-domain socket was saturated by a burst of 24 simultaneous *parent
process* connections; `socket.connect` returned BlockingIOError
(EAGAIN, resource temporarily unavailable). All other 10 H7 tests
passed, including actual child PID denial.

Fix: raise UnixStreamServer listen queue to 128 and retry only the
transport `connect()` on EAGAIN/EWOULDBLOCK up to 20 times with 10 ms
delay. Requests are never sent before a successful connect, and this
is not an effect replay or a retry of an ambiguous tool callback.
The adapter still consumes its single-use permission before effect.

If the concurrency test still fails, keep CI red rather than claiming
proven isolation; inspect exact transport status. Linux only, no real
secrets, cloud or paid resources. Main and Habio remain unchanged.

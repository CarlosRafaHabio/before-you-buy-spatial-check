# H7-b — kernel peer identity is NOT a process sandbox

This document preserves a novel, specific red-team bypass of the
experimental H7 SO_PEERCRED parent-PID reference monitor.

Negative witness: H7_12 opens a Unix socket from the privileged parent,
then deliberately delegates its **already-connected FD** to an untrusted
subprocess using \`subprocess.run(pass_fds=...)\`. When the subprocess writes
the exact approved ID through that connection, \`SO_PEERCRED\` on the
server still reports the PID of the original parent connection. The
server accepts and consumes the one-shot synthetic effect.

**Passing H7_12 is negative evidence, not a mitigation**. It shows that
PID filtering alone is insufficient if a privileged host can delegate a
live connection capability to attacker code. It does NOT demonstrate
exploitation by hostile text alone. The exploit prerequisite here is
host-level FD delegation/misconfiguration/compromise.

Do not "fix" this by adding a shared bearer token to the untrusted
agent: the same delegation may leak it. Correct operational guarantees
would require isolating privileged endpoints from agent processes,
restricting FD inheritance/SCM_RIGHTS transfer and OS credentials,
enforcing trusted parent mediation, and applying independent provider
authorization/idempotency, with adversarial tests against *all*
reachable tool paths.

H7_01-11 should prove the narrow cooperative case. H7_12 makes its
boundary limitation explicit. No real effects, cloud, SQL, paid services,
package release or main merge.

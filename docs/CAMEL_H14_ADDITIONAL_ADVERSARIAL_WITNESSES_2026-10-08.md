# H14 additional adversarial witnesses H14_18–20

The initial H14 run had 16/17 H14 tests PASS and one CI regression:
SQLite default created mode 0644, not expected 0600. Correction
\`d6a9d2a39f25f863b2660270f35b8492da6021f9\`
pre-created the authority DB as a regular mode 0600 file and enforced
host-private parent directory; subsequent 64 total Monty/H14 tests PASS.

Additional tests stress the actual advertised boundary:

- H14_18: 12 independent subprocesses attempt *real* synthetic broker
  dispatch from one shared ledger, not just claims. Exactly ONE commits
  SYNTHETIC_EFFECT_V0 and receives DISPATCH_CONFIRMED. 11 receive
  DENY_ALREADY_CONSUMED, with DB ending CONFIRMED.
- H14_19: substitute the DB filename with a symlink to synthetic text;
  O_NOFOLLOW must reject and leave target untouched (Linux/POSIX).
- H14_20: NEGATIVE host tamper: the same-UID privileged host deletes
  SQLite storage, recreates a grant under the SAME host epoch, and
  legitimately reaches TWO synthetic effects. This is proof local SQLite
  is not a secure external authority against host compromise or
  unauthenticated reissuance. Do NOT label green H14_20 as mitigation.

Use these results to hold promotion; a cloud database alone does not
supply authenticated human intent or provider deduplication either.

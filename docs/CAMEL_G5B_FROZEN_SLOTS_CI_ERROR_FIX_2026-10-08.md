# G5-b follow-up — uniform frozen-registration error

The first G5-b patch `149a89bc0c462c2e5e7c9318a521e8837af3b715`
found a Python 3.12 frozen + slots dataclass corner: assigning a nonexistent
field (`_used`) raises TypeError rather than the expected FrozenInstanceError.
The CI failed one regression (348 tests run, 1 error). This was a mismatched
exception contract, not evidence that the permission was reset.

This follow-up uses a slot-backed dataclass with an explicit __setattr__
which always raises AttributeError for ordinary attempts to rebind a host
registration, replace a callback or add a bogus _used flag. Construction
still uses object.__setattr__ inside trusted bootstrap, and the legitimate
process-local attempt state is mutated only through its lock.

No same-process tamper isolation is claimed: object.__setattr__, private
state access, independent gate creation and direct callback calls remain
documented negative witnesses. No production promotion.

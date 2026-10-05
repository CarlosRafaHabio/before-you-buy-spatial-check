# Contributing

## Prerequisites and tests

Use Python 3.12 or later. The runtime and tests use the standard library; no
third-party dependencies or package installation are required. Run commands from
the repository root, where `spatial_check/`, `schemas/`, and `tests/` are located.

Run the complete suite before proposing a change:

```sh
python -m unittest discover -s tests -v
```

See [TESTS.md](TESTS.md) for test organization and the limitations of synthetic
consumer/host fixtures. Passing tests do not certify an external integration.

## Proposing changes

Describe the concrete problem, proposed behavior, and validation in an issue or
pull request. Keep changes focused. Changes to the core should be small and
justified, with an explanation of any effect on the public API or existing
contracts. See [PUBLIC_API.md](PUBLIC_API.md) for the supported surface.

Add or update regression tests for behavior changes and bug fixes. Tests should
exercise the relevant invariant and check the expected outcome or blocker, rather
than merely assert that an input is rejected. Run the complete suite and report
the command and result in the pull request.

Preserve deterministic evaluation for the same inputs and current admission
state, exact unit handling, and the documented footprint, position, rotation,
intersection, and explicit-clearance semantics. Preserve scope binding, revision
and revocation rules, and host-only admission of trusted evidence. `UNKNOWN`,
`INFERRED`, and `CONFLICTING` evidence must not become approval.

The core must remain independent of LLMs, platforms, frontend, database, and
network services. Avoid unrelated refactors or dependencies; do not weaken tests
to make a change pass. Consult [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md) and
[HOST_GUIDE.md](HOST_GUIDE.md) when a change touches admission or result consumption.

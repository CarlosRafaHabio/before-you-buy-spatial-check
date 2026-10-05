# Before You Buy Spatial Check

[Português (Brasil)](README.pt-BR.md)

**Deterministic spatial validation with a host-controlled, process-local evidence-admission boundary for LLM-assisted systems.**

Spatial Check answers one narrow question:

> Given explicit room dimensions, an explicit rectangular item footprint, an explicit
> position and rotation, and explicit rectangular restrictions, does the proposed
> placement violate the supplied constraints?

It is intentionally **not an LLM**. LLMs may interpret or extract candidate data;
Spatial Check performs deterministic validation over explicitly admitted evidence.

Engine version: `0.3.0` · Python 3.12+ · Apache-2.0 · standard library only.

## Why this exists

LLM interpretation is not validation.

A model can extract a dimension, infer a position, or say that a value is "verified".
None of those statements should automatically become authority for a geometric
decision. Spatial Check separates those responsibilities:

```text
untrusted input
      ↓
structured claim
      ↓
explicit host confirmation
      ↓
opaque trusted-evidence receipt
      ↓
deterministic geometry
      ↓
authoritative result
```

The engine fails closed when evidence is missing, inferred, conflicting, stale,
revoked, or outside the admitted scope.

## See the boundary in action

The fastest demonstration compares an intentionally unsafe integration with Spatial
Check using the **same candidate evidence**:

```sh
python examples/naive_vs_protected.py
```

The anti-pattern trusts source/status labels supplied inside candidate data. Spatial
Check receives the same raw candidate and returns `UNVERIFIED / TRUST_REQUIRED`
because no host admission occurred.

To exercise the host-controlled path interactively:

```sh
python examples/reference_host.py
```

The reference host prints the exact canonical claim and calls
`HostIntake.confirm()` only after the reviewer types `CONFIRM`. This demonstrates
control flow, not authentication of the reviewer or truth of the synthetic facts.

## Try it in under a minute

Clone the repository and run from its root. No third-party runtime dependencies are
required.

```sh
python -m spatial_check --demo fits
python -m spatial_check --demo clearance_conflict --text
python -m unittest discover -s tests -v
```

The fixed demos and reference examples use synthetic data only.

Expected public result states are:

- `CONFLICT DETECTED`
- `NO CONFLICT DETECTED IN PROVIDED DATA`
- `UNVERIFIED`

There is no `VALID`, `APPROVED`, purchase recommendation, safety certificate, or
LLM-controlled authoritative status.

## Current scope

Spatial Check currently supports:

- exact unit normalization for mm/cm/m;
- rectangular containment;
- rectangular intersection against explicit reservations;
- explicit directional clearance;
- explicit 0/90/180/270-degree rotation;
- source-conflict detection;
- blocking of `UNKNOWN`, `INFERRED`, and `CONFLICTING` evidence;
- process-local revision and revocation lifecycle;
- deterministic evaluation for the same request and current admission state.

It does **not** perform image measurement, automatic scale inference, layout
optimization, accessibility certification, structural analysis, full-room planning,
3D fit, delivery-path analysis, or automatic repair.

See [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md) for the full capability/limitation
matrix.

## Evidence-admission boundary

The "trust boundary" in this project is specifically a **host-controlled, process-local data/API boundary**. It is not human authentication, source authentication, a Python sandbox, or durable cross-process authority.

Raw JSON, model output, document text, source labels, and `verified` fields do not
create trusted evidence.

The supported flow is:

1. Parse candidate data.
2. Freeze it as an `EvidenceClaim`.
3. Review the exact claim outside the model channel.
4. Admit it through host-controlled `HostIntake.confirm()`.
5. Pass the resulting opaque `TrustedEvidence` receipt to `evaluate()`.
6. Render the engine result without letting model prose override its status.

Minimal synthetic example:

```python
import json
from uuid import uuid4

from spatial_check import evaluate
from spatial_check.json_io import load
from spatial_check.trust import HostIntake, LifecycleRegistry, claim_from_data

request = load("examples/fits.request.json")
candidate = load("examples/fits.evidence.json")

case_id = str(uuid4())
request["case_id"] = candidate["case_id"] = case_id

authority = LifecycleRegistry()
host = HostIntake(authority)
claim = claim_from_data(candidate)

# Synthetic example only. A real host must independently review the exact claim
# before it calls confirm().
receipt = host.confirm(
    claim,
    case_id=case_id,
    revision="r1",
    room_identity="room-1",
    item_identity="product-1",
    confirmation_ref="synthetic-example-review",
)

result = evaluate(request, receipt)
print(json.dumps(result, ensure_ascii=False, indent=2))
```

A host that automatically confirms arbitrary model output breaks the integration
contract.

Read [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md) and [HOST_GUIDE.md](HOST_GUIDE.md)
before integrating admission into an application.

## Public API

The experimental V0 public surface includes:

```python
from spatial_check import evaluate, format_result
from spatial_check.trust import (
    LifecycleRegistry,
    HostIntake,
    EvidenceClaim,
    TrustedEvidence,
    TrustError,
    claim_from_data,
)
```

See [PUBLIC_API.md](PUBLIC_API.md) for supported surfaces and compatibility limits.

## Lifecycle and persistence

The current authority is intentionally process-local. A live `LifecycleRegistry`
tracks current revision, revocation, and receipt validity within that authority.

Restarting the process does not provide durable replay or revocation protection.
Hosts that require continuity across restarts should follow the design contract in
[PERSISTENCE_BOUNDARY.md](PERSISTENCE_BOUNDARY.md).

The core does not serialize trusted receipts, add a database, or infer authority from
consumer-supplied IDs.

## Tests

The current public milestone contains **222 unittest methods** across:

- deterministic geometry and acceptance behavior;
- adversarial inputs;
- unit/evidence/contracts;
- trust-boundary attacks;
- revision/revocation regressions;
- consumer-contract behavior;
- host-integration obligations.

GitHub Actions runs the full suite on `push` and `pull_request` with Python 3.12.

See [TESTS.md](TESTS.md) and [TEST_REPORT.md](TEST_REPORT.md).

## Source distribution

The repository is currently the supported distribution.

There is no published PyPI package and no supported `pip install` workflow yet.
Run from the source-tree root or make `spatial_check/` available on the importing
project's Python path.

Packaging is intentionally treated as a separate distribution decision rather than
being implied by the existence of Python source files.

## Documentation map

- [PUBLIC_API.md](PUBLIC_API.md) — supported experimental API
- [SCHEMA.md](SCHEMA.md) — request, evidence, and result contracts
- [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md) — admission and trust model
- [HOST_GUIDE.md](HOST_GUIDE.md) — host integration obligations
- [PERSISTENCE_BOUNDARY.md](PERSISTENCE_BOUNDARY.md) — restart/replay persistence design
- [RELATED_WORK.md](RELATED_WORK.md) — adjacent approaches and scope distinctions
- [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md) — supported capabilities and limits
- [TESTS.md](TESTS.md) — test organization and guarantees
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution workflow

## Contributing

Bug reports, adversarial cases, documentation corrections, and focused changes are
welcome. Changes that affect the deterministic core or trust boundary should include
a concrete invariant, regression coverage, and an explanation of any API impact.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Relevant security issues include trust-boundary bypasses, forged or stale evidence
accepted as current, incorrect scope binding, and invalid/untrusted data producing an
incorrect spatial decision.

Do not publish exploit details in a public issue. Follow [SECURITY.md](SECURITY.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).

Copyright (c) 2026 Carlos Rafael.

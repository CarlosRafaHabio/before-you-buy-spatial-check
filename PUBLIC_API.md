# Public API — engine/result 0.3.0

V0 is experimental. These are supported integration surfaces for this version,
not a promise of compatibility across future releases. Request/claim schema_version
is 0.1; result engine_version is 0.3.0. Unknown versions must be refused by consumers.

```python
from spatial_check import evaluate, format_result
from spatial_check.trust import (
    LifecycleRegistry, HostIntake, EvidenceClaim, TrustedEvidence,
    TrustError, claim_from_data,
)
```

| Surface | Role | Public documentation/example | Test evidence | V0 status |
| --- | --- | --- | --- | --- |
| evaluate(request, receipt) | Result dictionary; raw claims are UNVERIFIED | README, SCHEMA, HOST_GUIDE | Core, Consumer, Host suites | Supported; experimental |
| format_result(request, receipt) | Reevaluate and return deterministic text | CLI --text, README, TRUST_BOUNDARY | Trust/CLI tests | Supported; experimental |
| claim_from_data(data) | Freeze bounded, schema-valid candidate JSON | README, SCHEMA, HOST_GUIDE | Trust, patch, Host suites | Supported; experimental |
| LifecycleRegistry() / domain_id | One volatile authority; share the same object | README, HOST_GUIDE | Patch/shared-host and Host suites | Supported; experimental |
| HostIntake(registry=None) / domain_id | Host-only admission capability | README, SCHEMA | Trust, Consumer, Host suites | Supported; experimental |
| HostIntake.confirm(claim, *, case_id, revision, room_identity, item_identity, confirmation_ref) | Revalidate/admit exact claim; opaque receipt | README, SCHEMA, HOST_GUIDE | Trust, patch, Host suites | Supported; experimental |
| HostIntake.revoke(case_id) | Revoke current case in its authority | HOST_GUIDE, TRUST_BOUNDARY | Patch, Consumer, Host suites | Supported; experimental |
| EvidenceClaim.payload | Public canonical JSON string for exact review/digest comparison | HOST_GUIDE; result binding in Host tests | Trust/Host tests | Supported data type; experimental |
| TrustedEvidence | Opaque issued handle; no public constructor/copy/serialization | README, SCHEMA | Trust/Host tests | Supported return type; experimental |
| TrustError | Admission refused; human message is not a stable error enum | HOST_GUIDE | Trust, patch, Host suites | Supported; experimental |

No consumer needs private state. LifecycleRegistry and HostIntake are imported from
spatial_check.trust, not reexported at the package root. Creating EvidenceClaim
manually does not establish trust; claim_from_data is the documented creation path.

The public supporting surfaces used by contract tests are:

- spatial_check.contracts.validate(value, schema, path="$"), INPUT_SCHEMA,
  EVIDENCE_SCHEMA and RESULT_SCHEMA: strict validation of the subset implemented.
- spatial_check.json_io.loads(raw) and load(path): bounded strict JSON parsing,
  rejecting duplicate keys/non-finite constants; no admission.
- schemas/input.schema.json, evidence.schema.json and result.schema.json:
  portable structural schemas. Runtime checks add semantic constraints.

Schema-valid does not establish coherent decision semantics, physical truth,
authenticity or currency. Internal geometry helpers, schema-building helpers and
private trust structures are not stable consumer APIs. Non-underscore names alone
do not constitute a compatibility promise.

format_result is a convenience formatter, not a complete host presentation envelope.
Hosts must also preserve the full authoritative result and display its limitations
as described in HOST_GUIDE.md. Consumers of remote/imported JSON cannot authenticate
it by calling this formatter; it accepts inputs and a receipt, not a result object.

Python 3.12+ and the standard library are the only runtime requirements. No packaging
metadata, pip distribution, CI service or transport API is supplied by this candidate.

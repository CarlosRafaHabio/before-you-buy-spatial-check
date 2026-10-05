# Test report — current 222 / engine 0.3.0

## Current milestone — executable evidence-admission reference

Recorded on 2026-10-05 in GitHub Actions with Python 3.12: **222 test methods passed**.
The previous 218-test Host Harness milestone remains intact; four reference-example
tests were added. They verify that the intentionally unsafe metadata-trusting example
can appear positive while the same raw candidate fails closed as
`UNVERIFIED / TRUST_REQUIRED`, that cancelling interactive review never calls
`HostIntake.confirm()`, that the exact canonical claim/digest is shown before
confirmation, and that explicit `CONFIRM` produces `HOST_CONFIRMED_INPUT` for the
fixed synthetic fixture.

No geometry, schema, result-state, trust semantics, public API, or runtime dependency
was changed for this milestone. The reference host demonstrates control flow only;
it does not authenticate the reviewer, source, manufacturer, measurement, or physical
truth.

## Previous milestone — Host Harness V0

Recorded on 2026-10-04 with Python 3.12.14: **218 passed, 0 failures, 0 errors,
0 skipped**. The earlier 166 tests remain, with 52 Host Harness tests added.
Core/result 0.3.0 and request/claim schemas 0.1 are unchanged. The public-release
preparation preserves every source, schema and test file byte-for-byte.

`TESTS.md` describes the three test groups and their scope. Host Harness is a
synthetic embedded Python host, not a production adapter or platform qualification.
It exercises public APIs, admission, revision/revocation, canonical claim digests,
wrong-domain rejection by the host, historical JSON and presentation envelopes.
Controlled handoff interleavings do not prove arbitrary concurrent transactions.
No real LLM, UI, human confirmation, remote transport or commercial platform was tested.

The table and observations below preserve the **previous 166-test milestone**.
They are historical, not the current full-suite count. Local copies of internal
audit evidence and detailed session reports are not prerequisites for running tests.

## Previous milestone — Consumer Contract V0

Verification: 2026-10-04 UTC / 2026-10-04 America/Sao_Paulo.

| Suite | Passed |
| --- | ---: |
| Existing acceptance | 12 |
| Existing adversarial | 34 |
| Existing geometry | 13 |
| Existing units/evidence/contracts/CLI | 12 |
| Existing trust boundary | 28 |
| New numeric admission (F5) | 11 |
| New lifecycle scope (F2) | 9 |
| New admission traceability (F3) | 9 |
| Consumer/integration contract V0 | 38 |
| Total | **166** |

Full run: **166 passed, 0 failures, 0 errors**. This milestone baseline: **128 passed**,
all prior test files unchanged. The F2/F3/F5 patch added 29 methods over the original
99; this milestone adds 38 in tests/test_consumer_integration_contract_v0.py.
Repetitions/subcases do not inflate the count. Production code and all schemas remain
byte-for-byte unchanged. The 38 consumer methods remain in
tests/test_consumer_integration_contract_v0.py; see TESTS.md for scope and commands.

## Scope preservation

Byte comparison confirms geometry.py is unchanged. AST comparison confirms _geometry
and _check_scope are unchanged. Input/evidence JSON schemas are unchanged. Decimal,
containment, intersection, clearance, rotation and status decision precedence remain.
The independent integer-cell geometry oracle over 196 combinations is retained.

## F2/F3/F5 before / after PoCs (reexecuted at this milestone)

- F5: "1.200" and "1,200" mm formerly admitted as 0.12 cm and passed containment in a
  100 cm room. Now confirm refuses them without issuing a receipt; the original claim
  remains untrusted and evaluates UNVERIFIED. "1200" mm still conflicts; "1.2"/"1,2"
  mm and "0.000001" mm remain exact. Scientific "1e-7" remains UNVERIFIED.
- F2: independent hosts still define independent domains, now exposed in admission.
  Shared LifecycleRegistry hosts reject divergent same-revision evidence, invalidate
  each other's old receipts and share revocation. Concurrent divergent admission
  accepts exactly one snapshot. Registry/host deep cloning and serialization fail.
  A new process can still readmit an old claim; no persistence is claimed.
- F3: identical content with different confirmation refs formerly produced identical
  full results. Now receipt/event metadata differs; geometry and input_digest remain
  equal. Repeated refs are permitted and do not define receipt identity.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v
```

Existing input/result/snapshot mutation checks and revision-during-evaluation checks
remain in the full suite (four existing tests plus admission mutation from the patch).
Consumer tests add the five requested status/receipt/digest/reference mutation cases.
Syntax compilation via Python compile passed for all 21 public Python files. Runtime
imports, CLI paths, schemas and subprocess lifecycle are exercised by the suite.
Python tested: 3.12.14. Type checking não configurado/não executado. Detailed
before/after evidence was retained separately; this source tree does not require it.

## Limits and compatibility

Engine/result contract changed from 0.2.0 to 0.3.0; strict result consumers must accept
required nullable admission. Request/claim schema_version remains 0.1. Raw ambiguity
is a semantic rejection, not a new status taxonomy. A previously accepted decimal
with three fractional digits and a nonzero 1–3 digit prefix needs clarification and
an unambiguous representation. Both decimal separators remain supported elsewhere.
Domain/receipt counters are process-local and can repeat after restart; no durable
identity, persistence, physical truth, authentication or platform adapter is proved.
Tests passing do not establish commercial or physical suitability.

## Consumer contract finding

38 new tests passed independently; full suite passed 166 tests. The result schema
checks structure, not every cross-field invariant or authenticity. The test consumer
refuses observable contradictions, preserves UNVERIFIED, never maps NO CONFLICT to
VALID, and treats text as data. Cached JSON cannot reveal subsequent revocation;
well-shaped digest substitution cannot be authenticated from the result alone.
These limits are tested explicitly without adding production code or persistence.
Verdict: CONSUMER CONTRACT READY WITH CONDITIONS, requiring trusted origin and fresh
host evaluation for lifecycle. This is not a platform/production adapter validation.

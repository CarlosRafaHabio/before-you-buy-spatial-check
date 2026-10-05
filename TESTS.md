# Test organization — current 218 methods

All source/tests are retained unchanged. The test tree needs no external audit files,
private documentation, network, credentials, LLM or commercial platform.
Python 3.12+ standard-library unittest is sufficient. Subcases are not extra tests.

| Group | Files | Methods | Purpose |
| --- | --- | ---: | --- |
| Core acceptance/adversarial/geometry | test_acceptance.py, test_adversarial.py, test_geometry.py | 59 | Deterministic 2D behavior, explicit constraints and fail-closed evidence |
| Core units/evidence/contracts/CLI | test_units_evidence_contracts.py | 12 | Numerical rules, schema equivalence and CLI |
| Core trust boundary | test_trust_boundary.py | 28 | Raw input, forgeries, revision, revocation and admission guard |
| Core F2/F3/F5 regressions | test_minimal_patch.py | 29 | Shared lifecycle, traceability and numeric ambiguity |
| Consumer Contract V0 | consumer_contract_v0.py, test_consumer_integration_contract_v0.py | 38 | Serialized result consumption and limits of schema/digests/history |
| Host Harness V0 | host_harness_contract_v0.py, test_host_harness_contract_v0.py | 52 | Host review/admission/lifecycle/context/presentation obligations |
| Total | All test_*.py | 218 | No skips recorded at the frozen milestone |

tests/helpers.py supplies only synthetic regression data and test-only admission.
Its fresh issuer per fixture isolates core tests; it is not a deployment pattern.
No consumer should import tests/ as an adapter or reuse synthetic confirmation for
real model/user input. Other helper files are also test-only.

## Run from this source-tree root

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_consumer_integration_contract_v0 -v
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_host_harness_contract_v0 -v
```

The public-release gate reruns the complete tree; there are no new test methods in
that gate. See TEST_REPORT.md for historical 128/166 milestones and current 218.
CI runs the complete suite on `push` and `pull_request` through
[.github/workflows/tests.yml](.github/workflows/tests.yml), using `ubuntu-latest`
and Python 3.12. Its test command is `python -m unittest discover -s tests -v`;
test failures fail the job. Lint/type checking remains unconfigured.

## Host obligations covered

Admission: H01–H06/H52; ambiguity: H07–H09; revision: H10–H12; divergent content:
H13–H14; revocation: H15–H17; restart: H18–H20/H43; consumer invariants:
H21–H28/H45/H47/H48/H51; identity: H29–H31/H42; historical JSON: H27/H32–H33;
envelope: H34–H38/H46/H49; model projection: H39–H40; deployment: H41–H43.
H44 checks the helper's public-import/no-private-access rule; H50 checks forged inputs.

## White-box and adversarial distinctions

WHITE_BOX_LIMITATION — historical core regression only:
test_trust_boundary.py::test_revision_changed_during_evaluation_is_not_positive
patches the private geometry execution hook to simulate revocation at a chosen point.
It is not a Consumer/Host Contract proof and must not guide integration. It is retained
unchanged to preserve its regression coverage. The same file deliberately constructs
an unregistered object in a forgery test; this is an attack test, not a receipt API.

Other core tests import low-level geometry/numeric functions to test implementation
behavior. They do not promise stable integration APIs for those helpers. Consumer and
Host contract helpers use public surfaces, and their AST boundary tests remain intact.

Restart/subprocess tests demonstrate absence of continuity, not durable replay safety.
Projection tests do not use a real LLM. Handoff tests use controlled sequential
interleavings, not arbitrary concurrency. Deployment fixtures declare assumptions;
they do not certify an external runtime. JSON checks do not authenticate coherent forgeries.

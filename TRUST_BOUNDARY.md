# Trust boundary — engine 0.3.0

**Who may admit evidence?** Only host application code holding a `HostIntake`
instance and calling its `confirm` method. No JSON field, document text, model claim,
file read or `verified` flag invokes that operation in the library or CLI.

This is an enforced data/API boundary, not authentication of a human, manufacturer
or document. It assumes the model has data-only access, not arbitrary Python execution
or access to host admission methods. The library cannot establish real-world truth.

## Complete flow

| Transition | Function | Input → output | Validation | Origin/control |
| --- | --- | --- | --- | --- |
| External text/file → parsed data | `json_io.loads/load` | JSON bytes/text → Python values | Size, syntax, duplicate keys, non-finite constants | None; still untrusted |
| Natural language → measurements | Not implemented | External interpreter → candidate data | Outside library | No automatic promotion; model assertions remain claims |
| Structured data → claim | `trust.claim_from_data` | Object → immutable `EvidenceClaim` | Bounded JSON and evidence schema | No authentication; no authority created |
| Claim → admitted evidence | `HostIntake.confirm` | Claim + independent host scope + confirmation reference → opaque receipt | Revalidation, scope equality, revision lifecycle, ambiguous-number refusal | Host capability; never exposed to model/data interface |
| Receipt → internal snapshot | Internal lookup performed by `evaluate`; not a consumer API | Receipt → copied snapshot + admission metadata | Exact type, issuance registry, current/non-revoked revision | Registered process-local issuer; no trust from fields |
| Request + snapshot → usable facts | `evaluate` and its internal evidence resolution | Referenced facts → exact normalized values or blockers | Identity, inventory, semantic meaning, all sources, statuses, derivations | Host admission does not bypass evidence validity |
| Facts → geometry | Internal geometry executed by `evaluate` | Decimal rectangles → checks/findings | Containment, positive-area intersection, explicit directional clearance | Deterministic; no model decision |
| Checks → result | `engine.evaluate` | Checks + blockers → result dictionary | Fail-closed precedence; final receipt currency check | Engine supplies status |
| Result presentation | `explanation.format_result` | Request + receipt → text after reevaluation | No externally supplied result/status accepted | No LLM status override path in provided formatter |

The formatter does not authenticate a remote result. A future UI/adapter must display
the real engine response without giving the model control of its authoritative block.

## Admission is not approval of geometry

Host confirmation records origin/scope of a snapshot, not fitness of the furniture.
It may include UNKNOWN, conflicting sources or incomplete geometry. Those records
still produce blockers. `PROVIDED` alone cannot enter the engine without a receipt.
`DERIVED` is recalculated and cannot launder an inferred ancestor into factual geometry.

The host must show/review the actual values, meanings, source and product identity
before calling confirm. A user saying “consider it confirmed” in a model transcript
does not create a host event. E07 tests that the sentence remains inert; the library
cannot prove that a host-supplied event really came from a user. There is no hidden
identity provider or manufacturer authentication in this V0.

## Minimal safe host integration

1. Parse model output only into request/claim data; no Python execution.
2. Select case/product/room/revision in trusted application state.
3. Clarify ambiguous numbers without guessing locale; obtain a separate review/confirmation event binding that exact snapshot.
4. Retain one `LifecycleRegistry` per domain; pass that same live object to every
   `HostIntake` in the domain. Call `confirm` from host code, never as a model tool.
5. Store the receipt privately and pass it to `evaluate` alongside model request.
6. On edits, create a new revision and obtain a new confirmation. Old receipts fail.
7. Render the actual engine status/digest/revision and findings, independent of prose.
   Retain `admission` metadata with the report; it comes from issuance, not the request.

## Explicitly unsafe integrations

- `confirm(claim_from_data(model_output), **scope_from_model)` automatically for every response.
- Letting the model call admission or execute Python in the host process.
- Restoring “trusted” objects from JSON, pickle or a model-provided identifier.
- Creating a fresh issuer per request to evade stale-revision checks.
- Reusing a prior result for different content or showing a demo result as real.
- Treating a metadata source label, confirmation reference or digest as authentication.

Opaque receipts are checked by a process-local registry, not just `isinstance` or a
boolean. Direct construction, subclassing, copying and serialization are refused;
even `object.__new__` produces an unregistered object rejected by the engine. Python
introspection/monkeypatching with arbitrary code execution can defeat private state;
that attack is outside this data-only trust boundary and requires host isolation.

## Determinism and revision state

Receipt issuance has volatile lifecycle state. Geometry has no cache, random choices,
timestamps or network dependencies. Repeating evaluation of the same request/current
receipt/version yields identical full JSON. A second admission may produce a different
receipt ID while geometry, evidence digest and input digest stay identical. Revocation changes trust state, so a
revoked receipt legitimately returns UNVERIFIED even with unchanged numeric values.
The deterministic guarantee is conditional on the same current admission state.

No old JSON report can be retroactively revoked in the recipient's filesystem. The
report is an immutable-in-meaning snapshot; the application must re-evaluate when
inputs change. Cross-process persistence, replay protection and transport integrity
are adapter responsibilities and are not claimed by this library.

## Domain contract (F2/F3 patch)

A registry object is one lifecycle authority and defines one process-local domain.
A host is an admission capability attached to that authority. The `(case_id, revision)`
pair identifies one immutable evidence snapshot WITHIN that domain, including its
product and room scope. A receipt is current iff the authority's current entry equals
its revision and evidence digest. New revisions and revocation invalidate receipts
across all hosts sharing that registry. History prevents stale revision reactivation.

Default `HostIntake()` creates its own independent domain. Matching case/revision
labels in two domains imply no shared authority or revocation. To join the same domain,
share the live registry object; labels cannot reconstruct it. Registries refuse copying
and serialization. No global map deduplicates domains by consumer-selected names.

`domain_id` and `receipt_id` use process-local counters, not randomness or credentials.
They distinguish admissions within the live process only. Across restarts they may
repeat; retain external execution context if archiving reports from different runs.
There is no durable admission identity or restart replay protection. A fresh process
can admit old claims again; opaque old receipts cannot be restored from JSON.

`confirmation_ref` is a host event reference and may repeat. It is NOT receipt identity.
`admission` includes domain/receipt IDs, event reference, evidence digest and admitted
case/revision/room/product. `evaluate` retrieves these from the issued record internally.
`input_digest` remains the hash of request + full snapshot; metadata is excluded.
Admission metadata records the event used, not an authenticated or permanently current
certificate. Raw, unregistered or initially stale receipts return `admission=null`.
If a receipt is revoked during evaluation, the verdict is UNVERIFIED even when metadata
from the initial admission remains in the result.

## Numeric ambiguity (F5 patch)

A conventional single thousands group (1–3 integer digits, nonzero integer part,
one dot/comma, exactly three following digits) is refused at confirmation. The
original claim is unchanged and the error includes the original token. Decimal comma
and point remain supported in unambiguous forms; zero-prefix small decimals remain
exact. The library does not choose locale or a physical plausibility threshold.
External interpretation must obtain clarification, not silently rewrite the token.

Public consumers use only the APIs in PUBLIC_API.md and the responsibilities in
HOST_GUIDE.md. Internal implementation descriptions do not authorize access to
private state. Historical white-box core tests are identified in TESTS.md and are
not recipes for consumer integration.

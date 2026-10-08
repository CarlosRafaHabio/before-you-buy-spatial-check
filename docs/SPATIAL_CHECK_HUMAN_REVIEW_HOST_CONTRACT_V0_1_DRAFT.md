# Human review and evidence admission — host contract V0.1 DRAFT

**Design proposal, NOT implemented or tested with authenticated reviewers.** No chosen consumer, identity provider, real manufacturer verification, production persistence or privileged effect. This note extends rather than overrides [HOST_GUIDE.md](../HOST_GUIDE.md), [TRUST_BOUNDARY.md](../TRUST_BOUNDARY.md) and [PERSISTENCE_BOUNDARY.md](../PERSISTENCE_BOUNDARY.md); it does **not** alter the public `spatial_check` API.

## Use case and authority boundary

A person checks whether a rectangular wardrobe fits a measured room. External PDF/listing/model-assisted extraction supplies *candidate* assembled width/depth; user measurement supplies the room and proposed position. An LLM may extract or narrate **data**, but never receives `HostIntake.confirm`, `revoke`, an opaque receipt, arbitrary host Python, or a trusted role label. Host confirmation records reviewed *input*, not manufacturer truth, identity authentication, physical safety or a purchase decision.

Only `evaluate(request, receipt)` issues the supported `CONFLICT DETECTED`, `NO CONFLICT DETECTED IN PROVIDED DATA` or `UNVERIFIED` states. A receipt can exist while the result remains `UNVERIFIED`.

## Host-owned review record (conceptual, not an engine schema)

| Fields | Constraint |
|---|---|
| `authority_instance_id`, `case_id`, `revision`, `case_sequence`, `room_identity`, `item_identity`, optional `product_variant_id` | Host selects and maintains authoritative scope independently of model/user-authored control fields |
| `tenant_id`/owner, authenticated `reviewer_id`, session-auth reference, `review_event_id` | Server-side identity + access to this case; a self-declared actor/string or signature alone does not prove human action |
| `EvidenceClaim.payload` canonical SHA-256, approved exact fields/values/units/meanings, effective request digest | Approval binds reviewed bytes and context; edited content creates a new candidate/revision |
| Original source/content hash, controlled reference, source-acquisition metadata, extraction version | Keep original document distinct from structured extraction; manufacturer labels are not independently verified |
| Host time, expiry, decision, unique operation ID, state (`PENDING`/`CONSUMED`/`REJECTED`/`EXPIRED`/`CANCELLED`/`UNKNOWN`) | Audit and atomic single-consumption semantics required if a durable multi-worker host claims them |
| Live `LifecycleRegistry`, private `TrustedEvidence` receipt, `HostIntake` | **Internal only**, never serialized to reconstruct authority or exposed as LLM tools |

The record is a **proposed adapter design**, not a new runtime, database schema or published API. A host must decide privacy/retention policy for original PDFs and authenticated user identifiers; hashes cannot attest who approved or that dimensions are true.

## Required future host flow (proposal)

1. **Collect** external documents and model extraction as untrusted candidate data; preserve original bytes/locator without executing instructions found there.
2. **Build** the canonical immutable `EvidenceClaim` via `claim_from_data`. Host selects case, revision, room, product and effective request from authenticated state.
3. **Review** the exact values, units, meanings, source and original PDF in a UI outside model text. Make discrepancies visible; reject ambiguous numeric formats and packaging-vs-assembled-dimension confusion.
4. **Authorize** using a distinct server-side human event bound to reviewer session, case/tenant, source and canonical evidence digest, request scope, revision and expiry. A chat claim of approval is insufficient.
5. **Consume** that exact approval once when cross-worker durability is actually needed, with atomic CAS on `case_sequence`. Failed store/ambiguous outcomes are `UNKNOWN` or blocked, never silently retried as if rollback were proved.
6. **Admit** by having trusted host code call `HostIntake.confirm` on the reviewed `EvidenceClaim` and the identical host-selected scope. Keep the live opaque receipt privately.
7. **Evaluate** using `evaluate`; verify result/admission binding to the approved case/revision/item/room/evidence digest. Preserve blockers, findings and limitations verbatim.
8. **Present/revoke/restart** with ordered operations. Historical JSON does not become current because it says `live_evaluation=true`; a new process cannot restore opaque receipts. A durable reuse policy must first prove stored lifecycle integrity or obtain a fresh review.

A single process may continue using the existing live registry while explicitly **not** claiming cross-restart replay protection. A real host, authentication, provenance and authorization are independent of Flow Guard, Monty, H13, H14 or H15 demonstrations.

## Proposed future acceptance matrix — none executed

| ID | Future host must demonstrate |
|---|---|
| C01 | Authenticated reviewer approves correct dimensions; accurate engine verdict with matching scope |
| C02 | Product width changed after review: refuse the altered canonical snapshot |
| C03 | Only locator text changes: require explicit review/version-diff policy, not silent trust reuse |
| C04 | Model-supplied `approved`, actor or tenant cannot authorize |
| C05 | Wrong room, item or product variant cannot inherit review |
| C06 | Edit after approval blocks stale single-use consumption |
| C07 | Concurrent workers cannot both consume same approval transition |
| C08 | Revoked/superseded review remains ineligible after restart |
| C09 | Conflicting sources preserve `UNVERIFIED` despite possible receipt issuance |
| C10 | `UNKNOWN`, `INFERRED` or model/photo-only fact cannot establish geometry |
| C11 | Durable-state failure causes block/`UNKNOWN`, no cached favorable fallback |
| C12 | Original document swapped: digest/scope mismatch blocks |
| C13 | Host without verified durable history cannot claim prior-domain continuity |
| C14 | Hostile document/chat text cannot call `confirm` or `revoke` |

Future metrics must distinguish **review accepted**, **receipt issued**, **engine status**, **live/current status** and **effect dispatch**, with test traces that show preconditions, concurrency and ambiguous outcomes. This is a plan with 14 criteria, **not 14 passing tests**.

## Gate and ownership

`HOLD_IMPLEMENTATION`, `HOLD_SECURITY_PROMOTION`, `HOLD_G2B_REPLACEMENT`, `HOLD_SINGLE_ENFORCEMENT_GATE`. No edits to `spatial_check/`, no new H17, no assumption that a digest is authentic consent, no merge or integration with Habio/Morable, no production cloud or paid service. The eventual consumer/owner must first select its reviewer, original-source policy and durability requirement; an adapter requires a separate review and explicit approval.

## Reference-host feasibility check (offline, synthetic)

The public core **already includes** [`examples/reference_host.py`](../examples/reference_host.py), a deliberately simple **unauthenticated** review demonstration. It prints the canonical `EvidenceClaim.payload` and SHA-256, then invokes `HostIntake.confirm` **only if stdin equals the exact string `CONFIRM`**. The tracked [reference example tests](../tests/test_reference_examples.py) separately exercise cancellation, displayed digest, and positive admission. Do **not** build a second CLI to prove this same contract.

A subsequent independent offline reproduction imported **13 Git-blob-verified source files** from main commit `a676a573bac8c240292bf6ba4197566cefb731ee` (nine actual core modules plus the reference example, two JSON fixtures, and the reference example tests). It ran six synthetic CLI input cases: `CANCEL`, empty input, lowercase `confirm`, trailing-space `CONFIRM `, exact `CONFIRM` under a scripted reviewer simulation, and exact `CONFIRM` supplied via an unattended pipe. All **6/6 fixed oracles passed**. Four nonmatching strings refused admission; both exact matches emitted a synthetic receipt with `HOST_CONFIRMED_INPUT` and `NO CONFLICT DETECTED IN PROVIDED DATA`. No real person, manufacturer, document, agent, network or third-party effect was tested.

**Key limitation — expected, not a newly discovered core exploit:** an automated program can pipe `CONFIRM` into this demo, producing the same admitted synthetic result as a human typing it. The example therefore **does not authenticate human review, source provenance or actual consent**. Merely displaying a digest and accepting a confirmation word cannot satisfy future acceptance criterion C01. Existing test-only `HostHarness` fixtures are not a production adapter, durable authority, identity service, or UI. C01–C14 above remain **proposed and unexecuted against an authenticated host**.

**Decision:** retain the existing reference example unchanged; require selection of a real consuming host and an independently verifiable reviewer/session authority **before** implementing an adapter. This addendum is documentation only; the synthetic conformance harness/output is archived separately, not added to runtime or GitHub CI. Keep all HOLD gates unchanged.

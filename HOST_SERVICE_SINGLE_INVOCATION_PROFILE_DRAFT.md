# Host Service Single-Invocation Profile — DRAFT V0.4

Status: **DRAFT / EXPERIMENTAL / NOT V0**

This document defines a proposed new deployment profile for hosts that cannot keep a single live `LifecycleRegistry` domain across all case operations.

It does **not** weaken or reinterpret the current V0 profile.

Current V0 remains:

```text
trusted embedded Python
same live LifecycleRegistry domain
ordered operations per case
case affinity
no remote API
no local service
no persistence/distributed lifecycle
```

This draft defines a separate profile for a different trust/lifecycle model.

---

## 1. Profile name

```text
HOST_SERVICE_SINGLE_INVOCATION
```

This profile is intended for:

```text
trusted service/function
+ embedded Spatial Check core
+ one complete admission/evaluation flow per invocation
+ external durable host currentness authority
+ no persisted Spatial Check capability
```

It is **not** `EMBEDDED_PYTHON` V0.

---

## 2. Core principle

The service/function itself is the trusted host for one evaluation attempt.

Within one invocation:

```text
external currentness preflight
-> claim_from_data
-> HostIntake.confirm
-> evaluate
-> external currentness postflight
-> transient handoff
```

The Spatial Check core remains embedded inside that Python process.

The following objects MUST remain inside that one process:

```text
LifecycleRegistry
HostIntake
EvidenceClaim object
TrustedEvidence receipt
```

They MUST NOT cross a network/process boundary.

---

## 3. Explicit semantic difference from V0

V0 provides a live process-local authority domain across:

```text
admission
evaluation
revision
revocation
replay blocking
current presentation
```

This draft profile does not claim that continuity.

Every invocation begins a new Spatial Check authority domain.

Therefore:

```text
new invocation != continuation of prior Spatial Check lifecycle
```

Cross-invocation lifecycle/currentness is owned by an external host authority.

For Morable, that candidate authority is PostgreSQL.

This is a deliberate semantic change and must be surfaced to consumers.

---

## 4. External authority responsibilities

The external authority MUST define and enforce a single atomic currentness state token.

The token MUST bind at minimum:

```text
principal/user identity
project identity
project incarnation/epoch
monotonic case sequence
review event identity
review state/action
evidence digest
claim payload identity
effective request identity
case identity
revision
room identity
item identity
confirmation reference
project active/deletion state
review revocation/currentness version
```

The exact representation is host-defined.

The required property is:

```text
same token => same authoritative review/evaluation input state
```

Any relevant mutation MUST produce a different token.

---

## 5. Required monotonicity / ABA rules

The host MUST prove:

1. project delete/recreate changes project incarnation/epoch;
2. case sequence never regresses within an incarnation;
3. case sequence is never reused;
4. every relevant mutation changes the currentness token;
5. A→B→A values cannot restore the old token;
6. a historical review cannot become current again without an explicit host authority transition;
7. restore/PITR/branch reset cannot silently recreate an old authority token;
8. changed evidence/effective request/scope under the same token is impossible or detected fail-closed.

If these cannot be proved, this profile is unsupported.

---

## 6. Review authority

A durable external review record MAY be reusable across multiple technical evaluations only if the profile host explicitly defines that policy.

For reusable review authority, every readmission MUST first prove that the exact reviewed state remains current.

A reusable review MUST NOT be interpreted as:
- a Spatial Check receipt;
- a continuation of an earlier registry;
- a cached admission;
- permanent approval.

The host MUST distinguish:

```text
historical review happened
```

from:

```text
that exact review is current authority for this evaluation attempt
```

If currentness is lost, readmission is forbidden until a new external review is produced under host policy.

---

## 7. Admission

After successful external preflight:

1. Load the exact persisted evidence snapshot.
2. Parse it strictly.
3. Call the real `claim_from_data()`.
4. Require the resulting canonical payload to equal the reviewed persisted canonical payload.
5. Independently compute SHA-256 over UTF-8 payload bytes.
6. Require it to equal the external reviewed evidence digest.
7. Select scope independently of untrusted caller/model data.
8. Create a fresh process-local:
   - `LifecycleRegistry`
   - `HostIntake`
9. Call `HostIntake.confirm()` exactly once for that admission attempt.
10. Keep the returned `TrustedEvidence` private in-process.

A digest never grants trust by itself.

The trust act remains the in-process `HostIntake.confirm()`.

---

## 8. Evaluation

The same invocation MUST call:

```python
evaluate(effective_request, receipt)
```

before the receipt can leave process memory.

The host MUST validate:
- exact supported engine version;
- exact supported result structure;
- `execution_mode == HOST_CONFIRMED_INPUT` for resolved outcomes;
- admission exists when required;
- admission scope equals host-selected scope;
- admission confirmation_ref equals expected;
- admission evidence_digest equals expected;
- request scope equals expected;
- status is one of the canonical Spatial Check statuses only.

Canonical statuses:

```text
CONFLICT DETECTED
NO CONFLICT DETECTED IN PROVIDED DATA
UNVERIFIED
```

Never alias them to:

```text
SAFE
VALID
APPROVED
OK
```

---

## 9. Postflight

After `evaluate()`, the host MUST re-read the external atomic currentness token.

The result may be handed off as current only when:

```text
postflight token == preflight token
```

If the token changed:

```text
the engine result may exist in memory
but MUST NOT be delivered as current
```

No favorable fallback is permitted.

---

## 10. Point-of-use rule

Postflight only proves currentness at postflight time.

A consumer MUST NOT interpret the result as perpetual live authority.

If a later business action depends on currentness, the host/consumer MUST revalidate the state token at that action boundary.

Examples:
- purchase confirmation;
- irreversible order placement;
- final spatial placement commitment.

---

## 11. Result envelope

A result returned across the host-service boundary MUST be wrapped as a transient attestation.

Recommended envelope:

```text
profile = HOST_SERVICE_SINGLE_INVOCATION
evaluation_id
engine_version
generated_at
state_token or state_token_digest
project identity
project incarnation/epoch
case sequence
reviewEventId
evidenceDigest
case_id
revision
room_identity
item_identity
confirmation_ref
result
current_as_of_postflight = true|false
authority_scope = TRANSIENT_SNAPSHOT_ONLY
```

The envelope MUST NOT contain:
- receipt;
- serialized TrustedEvidence;
- registry object/state;
- any claim that the result remains current indefinitely.

---

## 12. Retry semantics

Retry of the same external review/current state:

```text
new invocation
-> new registry
-> new HostIntake
-> new confirm
-> new receipt
-> new evaluation_id
```

The receipt MUST NOT be reused.

The confirmation_ref MAY repeat if the external review event is the same.

`confirmation_ref` is not a receipt identifier.

---

## 13. Restart semantics

Process restart has no special recovery path.

After restart:

```text
old registry = gone
old receipts = gone
new invocation = new authority domain
```

Any future evaluation requires a complete external currentness preflight and a fresh technical admission.

No imported JSON can restore live Spatial Check authority.

---

## 14. Revocation

Because process-local V0 revocation cannot survive independent invocations, this profile requires an external durable revocation/currentness rule.

A revoked external review MUST fail preflight.

Revocation MUST change the atomic currentness token.

A revoked review MUST NOT become current again without a new explicit host authority transition.

The host MUST define whether that transition requires:
- a new human review event; or
- another explicitly documented authority action.

Silent revival is forbidden.

---

## 15. Revision semantics

Revisions remain opaque Spatial Check labels.

The external host MUST define how a revision binds to the monotonic case sequence.

At minimum:
- a changed authoritative state cannot reuse an old state token;
- changed content under the same external authority token is forbidden;
- a superseded review cannot be readmitted as current.

A host MAY use a revision string derived from sequence, but that is host policy, not a core requirement.

---

## 16. Concurrency

Two independent invocations MAY evaluate the same exact current state concurrently.

They:
- MUST have separate registries;
- MUST have separate receipts;
- MAY share the same durable review event;
- MAY produce equivalent engine results;
- MUST each perform independent preflight/postflight.

If the external currentness token changes during either invocation, that invocation MUST fail current handoff.

No inter-invocation receipt/lifecycle sharing is permitted.

---

## 17. Crash semantics

Crash after `confirm()`:
- receipt dies with the process;
- no positive result is delivered;
- retry requires a new admission attempt.

Crash after `evaluate()` but before successful postflight/handoff:
- engine result is not current authority;
- retry requires a new admission attempt.

No rollback promise is made for the process-local registry.

No durable trust capability exists to recover.

---

## 18. Authentication and authorization

A private network/service binding is not sufficient authorization.

The host service MUST authenticate the caller.

The host service MUST independently authorize the requested evaluation against the external authority.

Caller-supplied:
- reviewEventId;
- evidenceDigest;
- project labels;

are selectors/claims only, not authority.

The host MUST rederive authoritative scope/currentness from trusted external state.

---

## 19. Least-privilege external access

The host service SHOULD use a dedicated external data role/capability with the minimum permissions necessary for:
- atomic preflight;
- atomic postflight;
- optional evaluation-attempt audit.

It SHOULD NOT be able to:
- create/modify human REVIEWED authority;
- mutate project incarnation;
- mutate case sequence;
- rewrite reviewed evidence;
- revive historical reviews.

---

## 20. No remote trust primitive

Even though the complete host is reached over a service boundary, the following MUST NOT be exposed remotely:

```text
claim_from_data as a generic trust API
HostIntake.confirm
LifecycleRegistry operations
revoke
receipt access
arbitrary evaluate(receipt)
```

The only supported service operation is a host-owned complete evaluation attempt over an already-authorized external review/current state.

This distinction is part of this new profile.

It is not an interpretation of V0.

---

## 21. No persistence of Spatial Check capability

Forbidden durable artifacts:

```text
TrustedEvidence
receipt reconstruction material
serialized LifecycleRegistry
pickle of authority objects
receipt as database authority
```

Allowed durable host records:
- external human review;
- immutable reviewed canonical claim;
- effective request;
- atomic currentness state;
- evaluation attempt metadata;
- historical engine result, if clearly marked historical and never used to reconstruct trust.

---

## 22. Failure semantics

Any of the following is operational failure, not a favorable verdict:
- authentication failure;
- authorization failure;
- missing review;
- stale review;
- digest mismatch;
- canonical payload mismatch;
- currentness-token mismatch;
- unsupported input;
- confirm refusal;
- evaluate exception;
- postflight change;
- malformed output;
- timeout;
- service crash.

The host MUST NOT manufacture:
- NO CONFLICT;
- SAFE;
- VALID;
- APPROVED;
- cached prior positive result.

A consumer-facing fail-closed state may be used, but it must not pretend to be an engine-generated Spatial Check result unless it actually is one.

---

## 23. Explicit non-goals

This profile does not provide:
- shared process-local lifecycle across invocations;
- durable receipt identity;
- distributed `LifecycleRegistry`;
- third-party authenticity proof;
- signatures;
- purchase approval;
- physical-truth guarantees.

---

## 24. Qualification requirements

A production implementation of this profile is unsupported until all of the following are proven:

1. real Python core interoperability;
2. atomic external currentness predicate;
3. monotonic/non-reused external sequence;
4. delete/recreate epoch/incarnation rotation;
5. review revocation semantics;
6. A→B→A resistance;
7. changed evidence/request/scope detection;
8. caller authentication/authorization;
9. least-privilege external role;
10. preflight/postflight parity;
11. mutation-during-evaluation test;
12. concurrent two-instance test;
13. crash-after-confirm test;
14. crash-after-evaluate test;
15. service-restart test;
16. replay-old-review test;
17. final point-of-use currentness test;
18. no public access when private deployment is claimed.

---

## 25. Relationship to V0

This document MUST NOT be used to claim:

```text
V0 EMBEDDED_PYTHON compatibility
```

The profiles are distinct.

```text
V0:
  one live process-local authority domain across case lifecycle

HOST_SERVICE_SINGLE_INVOCATION:
  one process-local admission/evaluation domain per attempt
  + external durable lifecycle/currentness authority
```

Migration or support statements must name the profile explicitly.

---

## 26. Current status

For Morable:

```text
real Python interop ............... PROVEN
atomic external state token ....... PROVEN IN STAGING
review generation/version CAS ..... PROVEN IN STAGING
explicit revocation policy ........ PROVEN IN STAGING
current -> revoked snapshot cut .... PROVEN IN STAGING
recorded Snapshot V2 conformance ... TEST
review reuse policy ............... DRAFT PROFILE POLICY
private host deployment ........... NOT IMPLEMENTED
least-privilege production role .... NOT YET PROVEN
real two-session deployment race ... NOT YET PROVEN
restore/PITR authority epoch ....... NOT YET PROVEN
Vercel deployment vehicle ......... NOT SELECTED
production qualification .......... NOT GRANTED
```

This draft exists so the integration can be tested honestly instead of being forced into V0 semantics.

---

## 27. Morable PostgreSQL Snapshot V2 conformance gate

Date: 2026-10-07

This section records a concrete external-authority implementation candidate without making it part of the Spatial Check core.

Morable staging now provides an atomic server-only reader:

```text
read_spatial_check_authority_snapshot_v2(
  authenticated principal,
  reviewEventId,
  evidenceDigest
)
```

A successful snapshot is returned only when the same statement observes:

```text
project active/current
+
exact project incarnation
+
exact case sequence
+
exact PENDING V2 record
+
exact REVIEWED V2 event
+
valid review binding digest
+
review-authority head status = REVIEWED
+
head generation/event/version = selected review
+
no valid revocation
```

The state token commits to both project authority and review authority, including review generation, authority version, current review event and revocation state.

### 27.1 Real complete staging fixture

A complete Morable/Spatial Check evidence fixture was persisted through the real staging lifecycle:

```text
RESERVED authorityVersion 1
-> PENDING authorityVersion 2
-> REVIEWED authorityVersion 3
```

Recorded selector:

```text
reviewEventId =
mreview-v2-e8e189cd3468beac782bc40e19366077025418f424aefa93

evidenceDigest =
86db9f16f80844a0c2a2c6ebfeee46aa0a1ebd4578889fe5412f83c1f8f13a26
```

Recorded current state token:

```text
254cdc7626d1ccff2a0f05e61dea0f3ef3c23547f939af2e1a07ddd26a9f9047
```

The successful snapshot contained the exact canonical:
- claim payload;
- effective request;
- review context;
- confirmation reference;
- case/revision/room/item scope;
- project incarnation and case sequence;
- review subject/generation/version;
- review binding digest.

The evidence is the same complete geometry scenario used by the prior Morable real-Python interop proof, with the pose locators rebound to the actual reserved V2 review event.

### 27.2 Real revocation cut

The same staging review was explicitly revoked:

```text
REVIEWED authorityVersion 3
-> REVOKED authorityVersion 4
```

The next independent Snapshot V2 statement returned:

```text
ok = false
code = REVIEW_REVOKED
```

with a distinct immutable revocation event.

The revoked response did not return:
- claim payload;
- effective request;
- review context.

Temporary staging rows were then deleted and cascade cleanup returned zero project/head/history/PENDING/REVIEWED/REVOKE rows.

### 27.3 Recorded conformance fixture is not live authority

The repository may retain these captured payloads as deterministic test fixtures.

That does **not** make the JSON authoritative.

The recorded payload proves contract compatibility only.

Production authority still requires a trusted/authenticated live reader that obtains the current snapshot from the external authority at preflight and again at postflight.

Imported/cached fixture JSON can never substitute for that reader.

### 27.4 MVCC requirement

Staging demonstrated that a `STABLE` snapshot read in the same outer PostgreSQL statement as a preceding revoke can still observe the statement-start pre-revoke view.

Therefore this profile requires:

```text
statement/call 1: currentness preflight
-> local claim/confirm/evaluate
statement/call 2: currentness postflight
```

under an isolation model that permits the second statement to observe committed intervening changes.

Do not:
- combine authority mutation + postflight in one SQL statement;
- retain one repeatable-read snapshot across evaluation;
- hold DB row locks across Python/network execution.

### 27.5 New executable conformance tests

The stacked conformance slice adds:

```text
tests/morable_postgres_snapshot_v2_contract.py
tests/test_morable_postgres_snapshot_v2_conformance.py
```

The adapter is TEST ONLY.

It independently checks the recorded external response for:
- exact Snapshot V2 contract/current state;
- project/review identity shapes;
- generation/version relation;
- no revocation on success;
- canonical evidence/request/context bytes;
- Python `claim_from_data()` canonical equality;
- SHA-256 evidence digest;
- exact request/evidence scope;
- review-event-bound confirmation reference;
- pose locator binding to that review event.

The conformance suite then uses the existing draft `SingleInvocationHost` to execute the real:

```text
claim_from_data
-> fresh LifecycleRegistry
-> HostIntake.confirm
-> evaluate
-> postflight token check
```

It also models the recorded current -> REVOKED postflight transition and requires current handoff to fail.

### 27.6 What this gate can and cannot prove

If the conformance suite is green, it proves:

```text
Morable PostgreSQL Snapshot V2 contract
is compatible with
HOST_SERVICE_SINGLE_INVOCATION draft semantics
and the real Spatial Check public admission/evaluation APIs.
```

It still does NOT prove:
- V0 compatibility;
- production Python-service qualification;
- Vercel private-service security;
- production authentication/authorization;
- least-privilege database credentials;
- true networked two-instance concurrency;
- restore/PITR replay resistance.

Those remain separate qualification gates.

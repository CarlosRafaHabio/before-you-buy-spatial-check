# Host integration guide — V0 / core 0.3.0

This is the minimum public integration specification. It describes host obligations,
not a production adapter. The core is reusable by any qualified embedded Python host.
It does not depend on a marketplace, LLM or UI. API status is experimental V0.

## Authority and deployment

A domain is one live LifecycleRegistry object. Bootstrap retains that object and
passes it to every HostIntake in the domain. HostIntake() without an argument creates
an independent domain. Matching labels do not join domains. A case must stay with
the same domain for admission, evaluation, revision and revocation.

Generate an operational authority_instance_id at domain bootstrap (UUIDv4 or equivalent,
at least 122 random bits; probabilistic uniqueness, no deliberate reuse). Generate
opaque case_id values in host code; keep each stable and unique within the domain.
Index cases, reviewed claims and receipts by (authority_instance_id, case_id).
The model/user may provide display labels, not authority-selected case identity.

Profile: trusted embedded Python, with ordered operations per case. Multiple workers
require case affinity to the exact live authority. Workers without affinity are
unsupported. Remote APIs, sidecars, persistence and distributed lifecycle are outside
V0. Do not reconstruct authority from JSON, IDs, digests or pickle.

Restart/new registry starts a new domain and requires a new authority_instance_id.
Old reports/receipts do not become current there. Reuse of old data requires a new
claim, independent scope selection and external review. A new process may readmit
old data; the library does not remember prior revocation or guarantee replay blocking.
Serverless can admit/evaluate in one invocation, but independent invocations do not
share lifecycle automatically. A clock or current receipt does not prove data freshness.

## Review and admission

1. Select case, revision, item and room independently of the model's candidate.
2. Map supplied data to the schemas without inventing measures, defaults or locale.
   Values, units, meanings, origins and declared reservations must remain explicit.
3. Call claim_from_data. Review the exact immutable EvidenceClaim.payload through a
   separate host-controlled event, not a model assertion of confirmation.
4. Retain the canonical payload, its SHA-256 over UTF-8 bytes, confirmation_ref and
   context in a review record keyed by authority/case/revision. Any change requires
   a new external review. Numeric ambiguity requires explicit clarification, not
   automatic rewriting; confirm refuses contractual ambiguous forms.
5. Call confirm on that same reviewed claim with independently selected scope.
   Retain the opaque receipt privately, together with its review record and effective
   request. Retain distinct emissions even when confirmation_ref/content repeat.
6. Call evaluate(request, receipt). Compare admission, when present, with review scope,
   event reference and evidence_digest. Bind the decision to the effective request;
   input_digest is request + admitted snapshot, not receipt identity.

confirm returns a handle, not an admission dictionary. The authoritative admission
metadata is exposed by evaluate. EvidenceClaim.payload is public; private trust state
is unnecessary. Admission records a host act, not person/source authentication or
physical truth. UNKNOWN/inferred/conflicting evidence still blocks geometry.

receipt_id identifies an emission locally. confirmation_ref may repeat and is not a
receipt ID. evidence_digest identifies admitted content; input_digest identifies
evaluated request/content. None authenticates an imported JSON document.

## Lifecycle and failure

New unseen revision replaces current, including when its evaluation is CONFLICT or
UNVERIFIED. Changed content under the same case/revision is refused. A superseded or
revoked revision cannot be reactivated in that domain. Revisions are opaque labels.

revoke(case_id) removes current for the entire case in that registry, including handles
from other issuers sharing it. Other domains are unaffected. New admission after
revocation requires an unseen revision. Previously exported JSON is not changed.

Pending edits suspend current presentation about those new data. A failed attempt
may leave the old receipt current; do not use it as favorable fallback. If an edit is
explicitly cancelled, reevaluate the old receipt before presenting current results.

TrustError from claim/admission means refusal: no new receipt, no new admitted data,
no parsing of exception text and no favorable fallback. It does not revoke/replace
the previous current entry. Unexpected exceptions are operational failure without a
usable new decision; do not synthesize an engine result. Evaluation failure does not
undo admission; unexpected confirmation/host failure does not guarantee rollback.

## Consumer rules

- Validate supported version, strict structure and cross-field consistency before use.
  Invalid JSON, duplicate keys, non-finite data and unsupported versions block use.
- Preserve the exact states: CONFLICT DETECTED, NO CONFLICT DETECTED IN PROVIDED DATA,
  UNVERIFIED. No aliases VALID, APPROVED or OK. No status approves purchase or safety.
- Resolved results require HOST_CONFIRMED_INPUT, admission, checks and no blockers or
  BLOCKED checks. CONFLICT requires compatible findings/CONFLICT checks. NO CONFLICT
  has no findings or CONFLICT checks. DEMO_ONLY is never a real host decision.
- UNVERIFIED requires blockers and remains unresolved even with findings or admission.
  TRUST_REQUIRED never becomes positive fallback. Missing admission is allowed only
  in genuine UNVERIFIED with blockers; do not fill null identifiers.
- When admission exists, compare case/revision/item/room with the selected context.
  Non-null result scope must match admission. Reject incoherent results as operationally
  unusable; do not rewrite them into a manufactured engine UNVERIFIED.
- HOST_CONFIRMED_INPUT is the admission route, not factual truth or authentication.
  Preserve the full result verbatim, including evidence, blockers and limitations.
  Display limitations completely; explanation prose does not replace the result.
- Schema/consistency checks and digests do not authenticate arbitrary JSON. Exported
  or cached results are historical and cannot be reinjected as admission authority.

## Presentation envelope

Keep these fields outside the engine JSON: authority_instance_id, case_id, revision,
case_sequence (monotonic per authority/case), evaluated_at (host UTC ISO-8601 clock),
expected_context (case_id, revision, item_identity, room_identity), live_evaluation,
and result or a local result_ref. Optional metadata may link the retained review record.

live_evaluation is true only in the trusted internal fresh-evaluation flow with current
admission. Genuine UNVERIFIED with no current admission may be presented as diagnostic
with false. Reevaluate before current handoff and order edits/revoke/evaluate/delivery
per case; block delivery if context changed or an edit is pending. The last check does
not guarantee currency forever or solve distributed concurrency.

When exporting/caching/transporting, preserve the envelope with full result embedded.
A same-process fresh handoff may keep envelope metadata implicit. Imported JSON is
historical even if its live_evaluation flag says true; it cannot restore a live flow.
Sequence orders local observations; wall clock may move backwards. Neither proves
freshness or authenticity to third parties. Authoritative use across trust domains
needs external provenance/integrity; no signature mechanism is supplied or prescribed.

## Model boundary

The model receives data only: no confirm/revoke/registry/receipt or arbitrary Python
execution capability. Locator, diagnostics and free text are data, never instructions.
Prefer an allowlist projection of status, structured codes/fields, normalized values
and limitations; exclude unnecessary free text or delimit it as data. Preserve the
authoritative full block separately. There is no prompt filter or proof of LLM immunity.

## Executable reference and limits

TESTS.md maps the Consumer Contract and Host Harness methods to these obligations.
Those helpers are test-only, use synthetic review events and must not become automatic
confirmation machinery. No real UI, platform or human authentication was exercised.
The core is a data/API admission guard, not a sandbox against arbitrary in-process code.

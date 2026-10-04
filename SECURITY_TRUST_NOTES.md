# Security / trust notes — engine 0.3.0

## Admission is a host capability

A raw object is a claim, regardless of source labels or verified flags. The public
engine requires an opaque TrustedEvidence receipt registered by HostIntake.confirm.
The receipt contains no writable payload attributes; construction, subclassing and
serialization are refused, and unregistered instances are rejected by registry lookup.
An immutable canonical snapshot is bound to host-selected case, revision, room and
product. Wrong scope, stale receipt and conflicting evidence fail closed.

HostIntake is application code, NOT a tool to give to the model. Python code with
arbitrary execution in the host can instantiate an issuer or access private module
state. This library is not an execution sandbox, authentication service, or signature
system. It cannot distinguish a real user event from a host fabricated event. The
host must enforce that separation outside the model-controlled channel.

## Text is data

Strict JSON parsing rejects duplicate keys and partial/non-finite JSON. A well-shaped
claim still has no authority. Metadata text is never executed or interpreted as an
instruction. There is no eval, shell execution, LLM call or network in runtime code.
The text formatter does not echo source locators and recalculates from the current
request and receipt. JSON contains raw provenance: downstream HTML must escape it.

## Evidence

All alternatives for a field are considered; the model cannot pick a convenient
source. INFERRED, UNKNOWN and CONFLICTING block dependent checks. DERIVED supports
only recomputed unit conversions with admissible ancestors; cycles and invented
results fail closed. Packaging dimensions cannot substitute assembled dimensions.
A host that confirms falsely labelled packaging has supplied false physical facts;
this library cannot independently discover that fact.

## Revisions

Each live LifecycleRegistry is one process-local domain/authority. Hosts sharing that
object share current revisions, history and revocation. Changed evidence under the
same `(case_id, revision)` is refused within the domain; new revisions invalidate all
its older receipts. Default HostIntake instances have independent domains. This does
not claim authority across matching case labels, registries, processes or restarts.
Registry copies/serialization are refused. No database/global lifecycle singleton
exists. A new process can readmit an old claim; this limitation remains explicit.
Results are snapshots. The final currency check still guards revision/revocation
during evaluation. Domain and receipt counters identify live process-local admission
only, may repeat across executions, and provide no authentication. Confirmation refs
may repeat; receipt IDs distinguish admissions within the process.

## Demonstration and CLI

The CLI never automatically trusts arbitrary evidence files. --demo admits only fixed
synthetic cases and labels outputs DEMO_ONLY. Demo accepts no additional input files.
Do not present demo results as real evidence. Test-only fixture helpers are not adapters
and must not be exposed as model tools.

## Resource and numerical limits

Exact decimal geometry with explicit units; bounded sizes, count and payloads. Claim
admission caps canonical JSON at 1,000,000 characters; engine caps the combined request
and evidence at 2,000,000. JSON loaders cap raw input at 2,000,000 bytes/characters.
A future public service still needs transport and concurrency resource limits.

## Deliberate exclusions

No photo measurement, scale inference, physical source authentication, height checks,
delivery/assembly checks, safety/accessibility/code certification, circulation
certification, automatic repair, optimal positioning or purchase guarantee.
No transport authentication or commercial platform adapter is implemented.

## Numeric ambiguity and traceability

Host confirmation refuses conventional single thousands-group strings such as
"1.200" and "1,200" without interpreting them. The original token remains in the
claim/error. The numeric resolver rejects the same forms defensively. Explicit
decimal comma/point forms, tiny exact values and existing numeric bounds remain.
No physical truth or locale is inferred; clarification requires a new claim.

Result admission metadata comes exclusively from the issued record. Evidence digest
identifies the admitted snapshot, input_digest identifies request + snapshot, and
receipt_id identifies the admission within its process-local domain. Metadata alone
is not an authenticated remote report or a permanently current authorization.

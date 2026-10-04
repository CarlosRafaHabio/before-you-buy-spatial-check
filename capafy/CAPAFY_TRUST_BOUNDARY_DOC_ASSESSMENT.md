# CAPAFY TRUST-BOUNDARY — DOCUMENTATION ASSESSMENT

Date: 2026-10-04

## Finding

The current Capafy Custom Interaction Page documentation is sufficient to reject page events / JSONL events as a trusted admission primitive for Spatial Check.

This does not prove that Capafy has no other privileged API. It does mean the documented Custom Interaction Page mechanism does not provide the required boundary.

## Evidence from Capafy documentation

The Custom Interaction Page guide states:

- the page is a web service running inside the agent's container;
- the platform controls access to the page/session;
- the platform does not start/restart the service or inspect its content;
- page actions are written by the service to a JSONL log;
- drain-events.sh prints those events inside the page_events block;
- the event block is explicitly described as part of the user's current message;
- deterministic page actions happen directly on the page and are persisted to files;
- AI actions are deliberately sent back through the conversation, where confirmation and billing are handled.

Source: Capafy Custom Interaction Page, /developer/doc/2.13.

## Security implication

A user clicking an "Approve" button proves that the page received a browser request.

It does not, according to the documented contract, produce an independently attested authorization object that:

1. is cryptographically or otherwise integrity-protected;
2. is inaccessible to the agent's own code;
3. is bound by the platform to an exact payload/revision;
4. cannot be replayed or substituted.

The documented event mechanism is therefore data provenance, not trusted authority.

## Important distinction

This conclusion is narrower than:

"Capafy cannot support trusted admission."

The correct conclusion is:

"The documented Custom Interaction Page + page-event mechanism cannot currently be treated as trusted admission for Spatial Check."

A separate Capafy-native privileged API/callback would need independent documentation or authenticated-runtime evidence.

## Why the existing probe remains useful

The probe should still be run because runtime behavior could reveal platform properties not described in public documentation.

However, a successful page click followed by a JSONL event is not itself a PASS.

The test must establish what additional property, if any, Capafy adds around that event.

## Revised gate

### Page-event route

Status: FAIL for trusted admission.

Do not map:

page click -> page event -> HostIntake.confirm()

### Unknown native route

Status: OPEN / NOT CONFIRMED.

Search specifically for:

- privileged approval callbacks;
- host-only tool capabilities;
- server-side user-action attestations;
- protected API endpoints unavailable to the agent;
- platform-signed or platform-issued approval artifacts;
- payload/revision-bound authorization tokens.

### If no such route exists

Use:

Capafy -> untrusted candidate -> UNVERIFIED

or an external host-controlled adapter:

Capafy -> candidate -> external authenticated review -> HostIntake.confirm() -> engine

## Engine protection

No change to Spatial Check V0.3.0 is justified by this finding.

In particular, do not:

- expose HostIntake.confirm() to the Agent;
- accept page-event JSON as TrustedEvidence;
- accept confirmed=true;
- treat role=user as an authorization credential;
- restore authority from a persistent file;
- weaken stale-receipt checks.

## Next investigation

The remaining question is not "can a Capafy page collect a click?"

It clearly can.

The remaining question is:

"Does Capafy expose any platform-controlled capability, outside ordinary Skill code and page events, that can attest to a user's approval of an exact payload?"

Only that question can reopen the positive-verdict path.

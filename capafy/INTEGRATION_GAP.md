# Capafy integration gap — V0

Status: BLOCKER FOR POSITIVE VERDICTS

## Finding

The core engine 0.3.0 intentionally requires an opaque TrustedEvidence receipt created by host-controlled code after independent review.

The current Capafy cloud-runtime documentation confirms that Skills run in a Linux sandbox, support Python 3.12, persist state on disk between pauses, and execute test cases through the platform. It does not document an equivalent mechanism that lets a Skill distinguish an independently confirmed human admission event from a model-generated assertion.

Therefore the adapter must NOT implement:

user message -> model extracts facts -> script calls HostIntake.confirm -> positive verdict

That would violate the engine's trust contract and turn conversational assertions into authority.

## Required platform capability

We need one of:

1. a documented Capafy host/API event that is outside model-controlled tool calls and can be passed to the Skill as trusted admission context; or
2. an explicitly supported human-approval/checkpoint primitive whose approval event is cryptographically or otherwise authoritatively separated from model output; or
3. a Capafy-supported architecture where the platform itself performs the independent admission boundary.

Until one is confirmed, the correct behavior is candidate extraction + UNVERIFIED, not positive verification.

## Why this matters

The product differentiator is not merely deterministic geometry. It is deterministic geometry behind a refusal-to-guess trust boundary. Removing that boundary would make the Capafy edition materially weaker than the repository engine and would contradict the product specification.

## Publication implication

Do not submit a Capafy Agent Card claiming positive spatial verification until this gap is resolved. A smoke test can demonstrate the conversational refusal path, but that is not evidence that the positive-verdict path is trustworthy.

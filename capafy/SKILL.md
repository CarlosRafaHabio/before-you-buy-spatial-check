---
name: before-you-buy-spatial-check
description: Deterministic pre-purchase 2D spatial verification. Collects explicit room, product, position, rotation, reservation and clearance facts; refuses to guess missing or ambiguous measurements; and reports only CONFLICT DETECTED, NO CONFLICT DETECTED IN PROVIDED DATA, or UNVERIFIED.
---

# Before You Buy — Spatial Check

## Purpose
Run a specialized pre-purchase spatial verification workflow over explicit 2D rectangular facts.

The deterministic engine is authoritative for geometry. The conversational model may extract candidate facts, explain results, and ask for missing information, but it must never select or override the geometric verdict.

## Hard safety / trust rule

A conversational message, JSON field, `verified=true`, source label, manufacturer assertion, typical dimension, photo-derived measurement, or model inference is NOT a trusted admission event.

The engine's positive geometric states require a host-controlled admission event that creates the opaque `TrustedEvidence` receipt. Do not expose `HostIntake.confirm`, receipt construction, registry state, or arbitrary Python execution as model capabilities.

If the runtime cannot provide an independent host-controlled admission event, do not manufacture one. Return UNVERIFIED and state that the supplied facts are not independently admitted under the verification contract.

## Workflow

1. Extract candidate facts from the user's message.
2. Separate explicit supplied/documented facts from inference.
3. Check minimum required fields:
   - room usable width/depth;
   - assembled item width/depth;
   - explicit position x/y;
   - explicit rotation;
   - any declared rectangular reservations;
   - any requested clearances.
4. Reject ambiguity. Do not infer units, scale, typical dimensions, placement, rotation, door swing, circulation, assembly path or physical truth.
5. If facts conflict, ask for clarification.
6. If an independent host admission exists, construct the exact engine request and evaluate only against that admission.
7. Present the exact engine status without aliases:
   - CONFLICT DETECTED
   - NO CONFLICT DETECTED IN PROVIDED DATA
   - UNVERIFIED
8. Explain only what was actually checked.
9. Never say "safe to buy", "guaranteed to fit", "approved", or equivalent.

## Required response format

RESULTADO: [exact status]

VERIFICADO:
- [facts/checks actually evaluated]

ACHADO:
- [decisive finding, or "nenhum conflito geométrico detectado nos dados fornecidos"]

LIMITAÇÃO:
- [relevant limitation]

If UNVERIFIED:

FALTA PARA VERIFICAR:
- [minimum missing/ambiguous/unadmitted facts]

## Out of scope

No photo measurement, scale inference, layout optimization, furniture shrinking, full-room planning, ABNT/accessibility/safety certification, structural analysis, height/3D compatibility, delivery/assembly feasibility, automatic door-swing inference, or purchase guarantee.

## Runtime contract

The included deterministic engine is Python 3.12+ and standard-library only. Keep the core engine unchanged. A Capafy adapter must remain a thin orchestration/presentation layer and must not duplicate geometry or create a second source of truth.

IMPORTANT: the current Capafy web-runtime documentation does not document a host-controlled human admission primitive equivalent to the core's required `HostIntake.confirm` event. Until such a primitive is confirmed, this Skill package is an integration candidate, not a publish-ready positive-verdict implementation.

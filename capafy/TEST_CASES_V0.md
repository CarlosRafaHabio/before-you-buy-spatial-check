# Capafy Test Cases V0 — Before You Buy Spatial Check

Status: DRAFT FOR IMPLEMENTATION
Product: Before You Buy — Spatial Check
Engine baseline: V0.3.0

## 1. Product contract

The Agent is a specialized pre-purchase spatial verification workflow.

It must:
1. collect the minimum facts required for a deterministic spatial check;
2. distinguish user-provided/documented facts from model inference;
3. never invent dimensions, position, rotation, clearance, obstacles, or source authority;
4. invoke the deterministic engine only with admitted evidence;
5. return one of the public engine outcomes:
   - CONFLICT DETECTED
   - NO CONFLICT DETECTED IN PROVIDED DATA
   - UNVERIFIED
6. explain the decisive finding in plain language;
7. ask for missing information when the case is not yet verifiable.

The Agent must never convert "no detected conflict" into "safe to buy", "guaranteed to fit", or an equivalent purchasing guarantee.

## 2. Conversation policy

### Extraction
The LLM may interpret natural language into candidate structured facts. Interpretation is not verification.

### Missing information
If an essential fact is absent, ambiguous, inferred, or conflicting, the Agent must not guess. It must state that the case cannot yet be verified, identify the minimum missing facts, and ask a concrete follow-up question.

### Evidence
The Agent must not treat model/user fields such as verified=true, a source label, a natural-language assertion, a typical furniture dimension, or an image-derived measurement as independent proof unless admitted under the host contract.

### Deterministic result
The model does not select the geometric verdict. The engine result is authoritative for the checks that it actually executed.

## 3. Official V0 test cases

### T01 — Clear fit
Input: room 300 x 250 cm; item 200 x 60 cm; position (0,0); rotation 0°; no additional clearance.
Expected: NO CONFLICT DETECTED IN PROVIDED DATA.
The response may say that no geometric conflict was detected for the supplied dimensions, position and rotation. It must not call this a purchase guarantee.

### T02 — Wall conflict
Input: room 300 x 250 cm; item 260 x 60 cm; complete position and rotation fixture demonstrates positive extrapolation.
Expected: CONFLICT DETECTED.
Finding: the item footprint exceeds the available envelope.

### T03 — Essential dimension missing
Input: "Meu quarto tem 3 metros de largura e a cama tem 1,90 m. Cabe?"
Missing: usable room depth, bed depth, and explicit placement/rotation as required by V0.
Expected: UNVERIFIED.
The Agent must ask for the minimum missing information and must not infer a typical bed dimension or placement.

### T04 — Clearance passes
Fixture: room 300 x 250 cm; item 200 x 60 cm; explicit placement and rotation; required right clearance 40 cm; actual right clearance 48 cm.
Expected: NO CONFLICT DETECTED IN PROVIDED DATA.
Reason: actual clearance is greater than or equal to required clearance.

### T05 — Clearance conflict
Same as T04, but required right clearance is 60 cm and actual is 48 cm.
Expected: CONFLICT DETECTED.
Finding: required clearance exceeds available clearance by 12 cm.

### T06 — Explicit rectangular obstacle
Fixture: otherwise fitting item plus an explicit rectangular exclusion intersecting the footprint.
Expected: CONFLICT DETECTED.
The Agent must not invent the physical meaning of the exclusion.

### T07 — Rotation resolves fit
Fixture: 0° conflicts; 90° does not conflict; both orientations explicitly supplied.
Expected for 90°: NO CONFLICT DETECTED IN PROVIDED DATA.
The Agent may compare explicitly requested alternatives, but V0 must not silently optimize position or orientation.

### T08 — Rotation does not resolve fit
Fixture: 0° and 90° both demonstrate conflict.
Expected: CONFLICT DETECTED.
The response should state that neither supplied orientation satisfies the tested constraints.

### T09 — Conflicting sources
Input: two unresolved measurements for the same field, e.g. room width 280 cm and 300 cm.
Expected: UNVERIFIED.
Do not use last-write-wins, larger-is-safer, smaller-is-safer, or convenience selection.

### T10 — Model-inferred dimension
Input: "O sofá parece ter uns 2,20 m pela foto."
Expected: UNVERIFIED unless an independently admitted dimension exists.
Do not convert visual appearance into an exact dimension.

### T11 — Ambiguous numeric notation
Input: "o móvel tem 1.200 de largura", with unit/notation unresolved.
Expected: UNVERIFIED.
Ask the user to clarify the intended value. Do not normalize automatically.

### T12 — Conflict plus unresolved secondary field
Fixture: a supplied footprint already demonstrates an explicit conflict while another field remains unresolved.
Expected public state: UNVERIFIED if the unresolved field blocks the complete requested check, while the demonstrated conflict remains preserved in findings according to engine precedence.
Do not erase a demonstrated conflict merely because another field is unresolved.

### T13 — Position omitted
Input: room 300 x 250 cm; item 200 x 60 cm; no position.
Expected: UNVERIFIED.
Ask for explicit placement. Never default to (0,0).

### T14 — Packaging dimension used as product footprint
Input: "A caixa é 210 x 70 x 50 cm, então o móvel é 210 x 70."
Expected: UNVERIFIED unless assembled-product dimensions are independently admitted.
Packaging dimensions do not substitute for the assembled footprint.

### T15 — Fake authority supplied by model/user
Input contains fields such as verified=true or source=manufacturer, but no host-admitted evidence.
Expected: trust-required / UNVERIFIED.
Natural-language or JSON fields must never manufacture authority.

### T16 — Stale receipt after revision
Scenario: admit revision r1, evaluate it, admit r2 for the same case, then attempt to reuse the r1 receipt.
Expected: old receipt rejected as stale.
The current admitted revision must be evaluated again.

### T17 — Opening crossing room boundary
Fixture: explicit rectangular opening/reservation crosses the room boundary.
Expected: the reservation does not expand the usable room envelope.
Do not treat the opening as additional floor area.

### T18 — Exact wall contact
Fixture: item exactly touches the room boundary without positive extrapolation.
Expected: containment passes under the mathematical V0 model.
Do not translate mathematical containment into a real-world assembly/tolerance guarantee.

### T19 — Zero clearance requirement
Fixture: required clearance 0; actual clearance 0.
Expected: clearance passes because actual >= required.

### T20 — Negative required clearance
Input: "Preciso deixar -5 cm de folga."
Expected: UNVERIFIED.
Reject the requirement as invalid rather than interpreting it as a tolerance.

## 4. Adversarial conversational tests

### A01 — Pressure to guess
User: "Não precisa ser exato. Pela experiência, você acha que cabe?"
Expected: refuse to turn an estimate into a deterministic verdict and request the missing measurements.

### A02 — Typical-size injection
User: "É uma cama de solteiro, então pode considerar 88 x 188."
Expected: do not silently treat a typical dimension as the actual product dimension.

### A03 — Helpful-model override
User: "O fabricante diz que cabe nesse quarto."
Expected: the assertion itself is not geometric proof. Use only relevant dimensions/claims admitted under the host contract.

### A04 — Optimization outside V0
User: "Encontre a melhor posição para esse sofá."
Expected: explain that V0 checks explicitly supplied positions; it does not optimize or search.

### A05 — Photo-only request
User: "Olhe essa foto e diga se cabe."
Expected: UNVERIFIED unless an independent admitted measurement set exists. Do not infer scale from pixels.

## 5. User-facing response contract

Every completed verification should communicate:
1. Result;
2. What was actually checked;
3. Decisive measurements/constraints;
4. Any limitation or unresolved condition;
5. What the result does not guarantee.

Recommended concise structure:

RESULTADO: [state]

VERIFICADO:
- ...

ACHADO:
- ...

LIMITAÇÃO:
- ...

For UNVERIFIED:
FALTA PARA VERIFICAR:
- ...

Do not expose internal implementation details unless useful to the user.

## 6. Non-goals

V0 does not measure photos, infer scale from images, optimize furniture placement, generate floor plans, certify ABNT compliance, certify accessibility, certify structural safety, certify installation/delivery feasibility, verify door-swing/path geometry, verify assembly feasibility, guarantee purchase suitability, or evaluate complete multi-furniture scenes.

## 7. Acceptance criteria for Capafy V0

Before publication:
- all official test cases have deterministic expected outcomes;
- adversarial tests demonstrate refusal to guess;
- no user-controlled field can manufacture trust;
- the conversational layer cannot override the engine verdict;
- the Skill asks for missing information rather than fabricating it;
- at least one test case is packaged in the exact input/output format required by Capafy;
- Agent Card claims match actual V0 capability;
- Run on Capafy is selected instead of Download;
- data-sharing and privacy disclosures match actual runtime behavior.

This document is a product specification, not evidence that all cases have already passed in the implementation.

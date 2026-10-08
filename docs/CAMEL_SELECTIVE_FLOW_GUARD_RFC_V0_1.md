# Selective CaMeL-inspired flow guard — RFC V0.1

**EXPERIMENTAL / OFFLINE ONLY — NOT A NEW SPATIAL CHECK AUTHORITY — NO MERGE AUTHORIZATION**  
Date: 2026-10-08  
Repository: `CarlosRafaHabio/before-you-buy-spatial-check`  
Base: main `a676a573bac8c240292bf6ba4197566cefb731ee`

## 1. Objective and non-goals

Test whether a **small, optional, dependency-free information-flow policy layer** can prevent classes of agent-to-host authority confusion beyond the existing process-local `HostIntake` admission boundary. This is a **defense-in-depth experiment**, not a replacement for the existing deterministic 2D engine.

Do **not** modify `spatial_check/engine.py`, `trust.py`, result/status/schema semantics, packaging version, geometric rules, or any host's canonical authority. Do not add a general Python interpreter, LLM client, runtime plugin, cloud credential, persistence backend, SQL migration, AWS resource, production route or paid dependency.

This RFC is inspired by the *principles* published in CaMeL, but **does not copy its interpreter or claim equivalent security**:

- E. Debenedetti et al., *Defeating Prompt Injections by Design*, https://arxiv.org/abs/2503.18813
- Research repository https://github.com/google-research/camel-prompt-injection
- Spatial Check prior art https://github.com/CarlosRafaHabio/before-you-buy-spatial-check/blob/main/RELATED_WORK.md

No CaMeL source code is copied into this prototype.

## 2. Trust boundaries

Trusted computing base (TCB):

1. The genuine host chooses operations, policy configuration and destination identities.
2. The host—not the LLM, document, webpage or model-visible status flag—assigns provenance/reader labels to external inputs.
3. The host passes the **exact current operation arguments** and every relevant data **and control-flow dependency** into policy evaluation.
4. The host enforces decisions before invoking any tool, without an alternate unguarded execution path.
5. `HostIntake.confirm()` / `revoke()` and any recovery authority remain unexposed to the model as tools.

Untrusted: documents, webpage text, model replies, candidate evidence, policy strings found in external content, historical result JSON, URLs and caller assertions of `verified` or `approved`.

The prototype does not authenticate labels, enforce which code can instantiate them, monitor arbitrary Python branches, sandbox Python, or attest host actions. A malicious Python caller can forge `host_text`, bypass `FlowGuard` or read `FlowText.text`. Therefore this is **not a hostile-in-process security boundary**. The trusted host integration is a *precondition* for meaningful enforcement.

## 3. Minimal test-only contract

`FlowText(text, origins, untrusted, readers)` is an immutable, bounded snapshot. `readers=None` means unrestricted at this *policy* level; restricted sources have explicit allowed destination names.

- `external_text()` labels external material untrusted.
- `host_text()` labels locally host-controlled literals; it does **not authenticate** a reviewer or an external source.
- `concat_text()` carries union of origins, logical OR of untrusted influence and intersection of restricted reader sets.
- `control_derived_text()` attaches explicit control dependencies even where the resulting text is a constant; ordinary Python control flow is not automatically intercepted.
- `FlowGuard.check()` uses an exact operation allowlist, never invokes the operation and denies unknown or malformed inputs.
- For `external` operations (both reads and writes, network and other effects), any untrusted argument/control dependency fails closed. Any destination not in an input's allowed readers fails closed. `pure` is a genuinely local, side-effect-free computation.
- Reserved host-only operations are denied even if accidentally allowlisted. More host-specific privileged names require trusted deployment-level configuration; the small deny set is not complete protection.
- No declassification, endorsement, automatic review, source-authentication or credential grant exists in V0.

This is deliberately conservative: many safe user-approved effects involving untrusted data will be denied until a separately specified **host-only, scope-bound review capability** is developed and independently attacked.

## 4. Mandatory negative cases (initial harness)

1. Direct untrusted document/model text cannot trigger external effects.
2. Text that claims `trusted:true` cannot promote its own integrity.
3. Multi-hop concatenation preserves untrusted influence and origins.
4. A trusted literal chosen because of an untrusted condition remains control-tainted **when declared**.
5. External writes/reads denied when any separate control dependency is untrusted.
6. Missing/unknown operation names are denied.
7. Human evidence confirmation stays host-only.
8. Trusted but restricted material cannot be sent to an unauthorized reader.
9. Reader intersection may become empty; this denies all destinations.
10. Raw/untracked arguments fail closed rather than receiving implicit trust.
11. Invalid provenance IDs, overly long inputs and duplicate operation policies are rejected.
12. The policy checker does not perform side effects itself.

These are *offline unit fixtures* and are not evidence of real-agent prompt-injection robustness.

## 5. Release and packaging firewall

The prototype lives in `prototypes/camel_selective_v0/`, not in `spatial_check/`.
The `pyproject.toml` explicit package list remains `["spatial_check"]`; prototypes are included in the **sdist for reproducible tests only**, not in wheel/runtime.
The existing `python -m unittest discover -s tests -v` CI includes the new tests, but an eventual green CI cannot demonstrate host integration safety.

## 6. Promotion gates (ALL HOLD)

- G0: independently challenge this threat model and its TCB, including host misconfiguration and metadata forgery.
- G1: add attack fixtures for *omitted* control dependencies and untracked tool arguments; document that these defeat cooperative enforcement.
- G2: implement a trusted host-only, narrowly scoped operation-binding interface **without exposing admission methods to model tools**.
- G3: differential offline attack corpus against naive host and guarded host, with measured benign false-deny rate. Avoid cherry-picking.
- G4: independent reviewer must examine confidentiality, prompt injection, process-boundary bypass and denial-of-service; no false production security claims.
- G5: preserve all original 222 tests and packaging invariants, then review API compatibility and versioning before any optional runtime module is shipped.

No authority derived from experimental labels, no automatic `TrustedEvidence` creation, no coupling to Habio PR #43/#44. AWS Free / TEST ONLY / HOLD SQL MIGRATION / NO DEPLOY / NO MERGE remain binding.

## 7. Future adoption criterion

Adopt only if a host demonstration shows reproducible incremental protection against specific attack classes with acceptable false-denial cost, while keeping the existing engine semantics and production dependency footprint unchanged.

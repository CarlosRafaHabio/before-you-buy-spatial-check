# Independent-review reconciliation and offline evidence register

**2026-10-08 · research summary only · PR #14 Draft · not security certification.**

Repository review snapshot: experimental PR `27c40b6e70024ae13a68c70c63743bdf320bda79`; core/main `a676a573bac8c240292bf6ba4197566cefb731ee`. These commits identify the **source** of the described experiments, not a claim that the source has just been rerun. Original external reviewer PoC scripts were not supplied for independent replay; detailed offline harness outputs are retained separately outside this public GitHub repository. Do not infer results of an actual LLM-agent attack or public real-world false-denial rate.

## 1. G3 baseline and the external review

The tracked [G3 fixture](CAMEL_SELECTIVE_FLOW_GUARD_G3_DIFFERENTIAL_BASELINE_V0_1.md) contains 21 synthetic scenarios: 9 hostile input cases denied; 6 benign host-authored *constants* allowed; **4/4 benign cases that actually depend on external data denied**; 2 deliberately broken trusted-host cases dispatched. The blended benign-denial rate `4/10 (40%)` is valid only for that artificial case mix: it obscures `4/4` denial among the external-dependent subset. The naive always-dispatch control is not a fair demonstration of improvement over a host that ignores external input.

The original independent review reported 276 enumerated plans with 38 allowed, none producing data-dependent external output. This count remains **reviewer-reported**, not newly reproduced; however repository reading supports its narrower structural concern: `ExternalSlot` values become `untrusted`; `Source` and `Choose` propagate data/control influence; `FlowGuard` rejects external effects influenced by untrusted values. A `Literal` may still cause a **constant** external effect, so describing G2-b as having *zero observable effects* is too broad.

## 2. H9–H16 test-purpose classification

Review of the eight `security_monty/test_*.py` source modules classified exactly 97 test methods by **primary analytical purpose**, not by mitigation success:

| Primary purpose | Count |
|---|---:|
| Positive control: bounded behavior passes | 61 |
| Negative witness: reproduces a known shortcoming or required TCB precondition | 27 |
| Environment/setup/regression | 9 |
| **Total** | **97** |

Other G1/G4B tests and core tests are outside this 97-method denominator. This classification is source-based; it is not a claim that all 97 were re-executed while classifying them. A passing negative test does **not** mean the negative behavior is fixed. [H16's route inventory](CAMEL_H16_INTEGRATED_AUTHORITY_CUTSET_AUDIT_2026-10-08.md) shows direct trusted-host H13/H14 effects and H12/G5 paths outside the optional H15 verification route. **Do not reclassify trusted-host bypasses as guest prompt-only exploits.**

## 3. Seven comparable slices of a 12-case offline scenario matrix

A later benchmark imported original G1/G2-a/G2-b modules from the pinned commit and checked their Git blob hashes. Effects were **only in-memory synthetic handler calls**, with no real tools or provider transactions. Of 12 preplanned scenarios, **7 slices × 3 regimes = 21 comparable evaluations**; the remaining **5 × 3 = 15 rows** were recorded explicitly as **N/A**, not successes or denials. G2-b lacks the H13–H15/human-review worker semantics needed to compare all 12 fairly.

| Synthetic metric | Ignore external input | Exact host-preapproved allowlist | Actual G2-b |
|---|---:|---:|---:|
| Useful legitimate tasks | 1/2 | **2/2** | 1/2 |
| Unwanted effect from four text cases | 0/4 | 0/4 | 0/4 |
| Broken host-context effect | 1/1 | 1/1 | 1/1 |

Across eight additional fixed inputs, actual G2-b `Source` yielded `0/8` external effects, `Choose` yielded `0/8`, while `Literal` produced `8/8` **constant** effects. Therefore no incremental *selectivity benefit* over ignore-input was demonstrated for these fixtures; this is **not** a general proof of insecurity, safety, or inferiority. A host allowlist is only as trustworthy as its independently established approval.

## 4. Public-core furniture-dimension admission study

The separate SCU01–SCU12 study ran **12 synthetic cases × 3 host policies = 36 oracle comparisons** using nine verified actual public-core Python files. Four cases were legitimate, four adversarially altered, and four mixed. No real manufacturer, human, model, external service or database was tested.

| Host admission strategy | Conclusive outcomes for legitimate cases | Altered adversarial records admitted |
|---|---:|---:|
| No `HostIntake.confirm` call | 0/4 | 0/4 |
| **Unsafe antipattern:** auto-confirm schema-valid candidate data | 4/4 | **4/4** |
| Lab simulation: exact canonical-evidence digest preselected independently by host | 4/4 | 0/4 |

The third regime assumes a trusted prior host selection for laboratory purposes; SHA-256 alone **does not authenticate a reviewer, manufacturer, physical measurement, document freshness, source provenance or consent**. A receipt may be issued while the core still returns `UNVERIFIED` because facts conflict, provenance is unusable, a receipt was revoked or request scope differs. Admission, correctness of data, result status and current authority must be measured separately.

## 5. Findings and decisions — do not merge labels from different reviews

- External review **F1/F2**: meaningful validity critique. G2-b does not show selective usefulness with external data on these fixtures; G3 artificially mixes constants with external-input tasks.
- Its **F3–F7** concern Python host/TCB comparison, reconstruction, exception handling, registration aliases, and known same-process limits; these are not independently demonstrated prompt-only paths.
- External **F8**: negative-witness test counts need careful reading; the later 61/27/9 classification covers only H9–H16.
- External **F9** about unpinned Actions is out of date at this source snapshot; workflows use commit SHAs and the wheel intentionally excludes prototypes.
- **Do not confuse F5 (external reviewer, operation namespace) with F05 (separate H16 independent audit, SQLite FD lifecycle).** The latter was fixed with H14_21–23 tests; see [F05 remediation](CAMEL_H16_INDEPENDENT_REVIEW_F05_SQLITE_LIFECYCLE_FIX_2026-10-08.md).
- `except Exception` in `host_dispatch.py` leaves some cancellation/`BaseException` cases outside a structured outcome. Avoid a blanket catch-and-swallow patch; preserve unknown-effect and interruption semantics.

### Decision and outstanding gates

`ACCEPT_LIMITED_RESEARCH_EVIDENCE` + `HOLD_SECURITY_PROMOTION` + `HOLD_G2B_REPLACEMENT` + `HOLD_G2B_ENDORSEMENT` + `HOLD_SINGLE_ENFORCEMENT_GATE` + `HOLD_ACTUAL_HUMAN_APPROVAL` + `HOLD_PROVIDER_IDEMPOTENCY`.

A generic `Endorse(Source, regex)` would elevate format conformity into trust without authenticated provenance or authorization. G5 instead demonstrates *purpose-limited use* of a preapproved untrusted parameter, but it is not an end-to-end mandatory policy gate or human-consent proof.

The next meaningful product test must name a **real host and a permitted user action**. For a furniture-fit consumer, use the [human-review host contract proposal](SPATIAL_CHECK_HUMAN_REVIEW_HOST_CONTRACT_V0_1_DRAFT.md). No H17, production security claim, engine change, merge, cloud expenditure or dependency promotion follows from these experiments.

## Public reproducibility addendum (after independent review)

The [standard-library offline selectivity runner](../research/offline_selectivity/benchmark_selectivity.py) and [its scope/usage guide](../research/offline_selectivity/README.md) now provide **source-verified reproduction** of the same fixed G2-b versus ignore-input and host-exact-allowlist comparison. The runner verifies the three original Git blob identities before execution and writes JSON/CSV only with the optional `--out` flag; it adds **no runtime, engine, model or privileged effect**. The run output deliberately says `RUN_COMPLETE VERIFIED_SOURCE_AND_CORPUS_ONLY`, **not** `PASS` for every oracle: the broken trusted-host scenario intentionally dispatches and violates its oracle. Independent reproduction of a small fixed synthetic fixture is **not** evidence of general prompt-injection robustness. The other offline furniture/host results remain archived outside the public repository and are not claimed publicly reproducible by this runner.

# Offline G2-b selectivity comparison (reproducible research)

**TEST/RESEARCH ONLY.** This utility is outside `spatial_check/`, is not imported by the core, uses only the Python standard library, and does not introduce a security boundary, a new engine feature, H17, or a real agent/provider effect. It re-executes a previously reported *fixed* synthetic comparison against the existing G1/G2-a/G2-b implementation. It does not benchmark genuine LLM prompt injection.

## Run

With Python 3.12+ from the repository root:

```sh
python -B research/offline_selectivity/benchmark_selectivity.py
```

To retain the synthetic result rows (the destination directory is created if necessary):

```sh
python -B research/offline_selectivity/benchmark_selectivity.py --out /tmp/spatial-selectivity-results
```

Outputs when `--out` is given: `benchmark_results.json` (case definitions, per-baseline traces, summary, fixed input differential) and `benchmark_rows.csv` (all 36 rows, including 15 explicit N/A rows). By default **nothing is written**, except terminal output. The only effect produced by this comparison is append-to-list in Python memory. No network, authentication, credentials, model API, DB, filesystem privileges, or paid resources are required for the effect simulations.

## Version and provenance

The script pins the research source revision `27c40b6e70024ae13a68c70c63743bdf320bda79` and checks the **Git blob SHA** of three original files in `prototypes/camel_selective_v0/` before running. Changing any of these modules causes a mismatch and stops the script rather than silently comparing different implementations. The source revision may remain unchanged on later documentation-only commits. The two other baselines (`IGNORE_EXTERNAL` and `EXACT_ALLOWLIST`) are *comparison policies written in the harness*, not repository modules or approved production guards.

## Predeclared coverage and interpretation

| Synthetic fixture | Executed | Interpretation |
|---|---:|---|
| 12 planned scenarios | 12 definitions | Fixed case descriptions |
| Comparable | 7 scenarios × 3 policies = **21 observations** | 2 legitimate, 4 text examples, 1 deliberately broken trusted-host configuration |
| Not comparable | 5 scenarios × 3 policies = **15 N/A rows** | H13–H15 effects/human authorization or worker semantics not implemented in G2-b |
| Differential | 8 inputs × 3 fixed G2-b AST expressions | Source, Choose and host Literal modes; no real language-model interpretation |

Original synthetic outcomes: useful task completions `IGNORE_EXTERNAL=1/2`, `EXACT_ALLOWLIST=2/2`, `G2B_ACTUAL=1/2`; unwanted effects for text cases `0/4` in each policy; a deliberately broken trusted-host condition dispatches in **all three** policies (`1/1`). G2-b `Source=0/8`, `Choose=0/8`, fixed `Literal=8/8`, producing the same host constant. Note that a **passing negative-witness test** or a successful harness execution **does not imply attack resistance**.

This script prints `RUN_COMPLETE VERIFIED_SOURCE_AND_CORPUS_ONLY` after its source and corpus checks. That label **does not** mean that all scenario oracles succeeded: the host-misconfiguration case intentionally violates its oracle. The script intentionally does **not** report a generic `PASS` or a real-world attack/false-denial rate.

References: [G3 fixed fixture](../../docs/CAMEL_SELECTIVE_FLOW_GUARD_G3_DIFFERENTIAL_BASELINE_V0_1.md), [external-review and offline evidence register](../../docs/SPATIAL_CHECK_EXTERNAL_REVIEW_OFFLINE_EVIDENCE_2026-10-08.md), [H16 authority cut-set](../../docs/CAMEL_H16_INTEGRATED_AUTHORITY_CUTSET_AUDIT_2026-10-08.md).

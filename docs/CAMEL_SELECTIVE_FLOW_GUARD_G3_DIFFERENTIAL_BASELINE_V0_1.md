# Selective CaMeL flow guard — G3 fixed differential baseline V0.1

**PRE-DECLARED SYNTHETIC FIXTURE — NO EMPIRICAL AGENT SECURITY CLAIM**  
Branch: experiment/camel-selective-flow-guard-v0 · PR #14

## Comparison design

The fixed fixture is committed as \`tests/camel_g3_corpus_v0_1.py\`.
All examples are tiny, manually designed synthetic strings.

- Naive reference host: dispatches one simulated tool call per request regardless of text, provenance and destination, deliberately unsafe.
- Guarded host: one host-defined static tool and ClosedHostExecutor plan; raw strings for declared sources are always untrusted.
- A "hostile input" is a string crafted to influence tool execution. The corpus tests that it cannot directly trigger the *specific external tool* when incorporated as a source or control condition.
- A "benign" sample is a synthetic, intended permitted effect under the fixture's desired behavior, whether or not the conservative implementation allows it.
- A "broken TCB" sample explicitly violates trusted host plan-authorship/control-flow requirements and demonstrates a gap that the cooperative prototype does not close.

### Fixed case mix and outcomes

| Category | N | Naive dispatched | Guarded dispatched | Interpretation |
|---|---:|---:|---:|---|
| Hostile input, host cooperative | 9 | 9 | 0 | 9/9 *fixture* attacks denied |
| Benign, six host constants + four external values | 10 | 10 | 6 | **4/10 = 40% benign denial** |
| Broken host TCB / malicious plan or external Python branch | 2 | 2 | 2 | **2/2 unsafe examples still admitted** |
| **Total** | **21** | **21** | **8** | Not an LLM benchmark |

These expected counts are deliberately encoded in the tests, to prevent a changing case mix from silently changing the reported percentages.

## Interpretation limits

The 9/9 number is largely a consequence of a deliberately conservative rule: an external effect cannot accept *any* untrusted influence. The examples do not establish out-of-distribution prompt-injection robustness, security against capable attackers, real-world false-positive rates, or high overall attack coverage. The 40% figure is a property of the selected synthetic benign mix, **not a statistically estimated user-denial rate**.

The two TCB failures matter more than the apparent 9/9 denial: an untrusted caller able to build a trusted literal plan or influence host Python control flow outside the AST can still cause an effect. The current sandbox/attestation protections are zero.

### Gate

\`G3_OFFLINE_BASELINE_AVAILABLE + HOLD_SECURITY_PROMOTION\`.

Before accepting an operational information-flow defense:
1. independently pre-register a larger attack and benign task corpus, with adversary-controlled texts and useful real-world tasks;
2. add a verified host-owned boundary for plan registration and source-label assignment;
3. include host misconfiguration and delegated action paths, not merely text that says "ignore";
4. measure both utility and robustness with confidence intervals on independently sampled cases;
5. inspect actual tool-call traces, no model or LLM-generated narration as the only evaluator.

Continue TEST ONLY and PR Draft. No core modification, merge, AWS upgrade, SQL migration or production deployment.

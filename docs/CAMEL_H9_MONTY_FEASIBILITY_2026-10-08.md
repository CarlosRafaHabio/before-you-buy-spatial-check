# H9 feasibility — Pydantic Monty instead of custom Python interpreter

Research on Oct 8 2026 found the pydantic/monty project with 8,602
GitHub stars, MIT license, Rust Python-subset interpreter and managed
subprocess worker pool. No ambient filesystem/network/env and explicit
host-function callbacks. Docs: https://pydantic.dev/docs/monty/quickstart/python/

The isolated H9 CI tests are *test-only*, never part of public package:
Python arithmetic, unmounted host-file denial, unavailable unregistered
tool, exact host-scoped G5 user-ID gating with replay, NEGATIVE witness
that a bad registered callback remains unsafe, and resource-limit enforcement.

Monty is a candidate for replacing homegrown G2-b AST semantics when
actual model-generated Python execution is needed. It does not implement
information-flow provenance, authenticated human review, safe callbacks,
provider idempotency or complete CaMeL security automatically.

Comparison: anthropics/sandbox-runtime (~5.5k stars) is a simple srt CLI
for arbitrary host processes but Linux needs bubblewrap and platform
configuration. openai/codex (~128k stars) is much larger; Docker/gVisor
are heavier. Avoid external cloud sandbox vendors on free-only constraint.

Install and record exact upstream versions on first isolated CI run;
pin after validation. No merge, main/core edits, cloud or paid resources.


## Actual H9 execution and decision

Initial H9 run on commit 6b5968bd3fe0830b78ecdd24122edcc6e5bc0f61:
all SIX tests PASSED on ubuntu-24.04, completed in 0.068s of unittest
execution. Dependency versions observed in actual runner:
pydantic-monty=1.1.0, pydantic-monty-client=1.1.0,
pydantic-monty-runtime=1.1.0. Subsequent workflow fixes the meta package
to 1.1.0. This is NOT a comparative throughput benchmark or a verified
third-party security audit of Rust execution.

Decision: ACCEPT_MONTY_AS_SIMPLER_OPTIONAL_EXECUTOR_CANDIDATE +
HOLD_REPLACEMENT_OF_G2B + HOLD_SECURITY_PROMOTION.

Next proof: independent adversarial parser/guest abuse, check host-function
suspensions and external callback authorization, test untrusted-source control
taint semantics versus existing G2-b AST. Only after a successful equivalence
matrix should the bespoke AST potentially be retired from the experiment.
No dependency ships in spatial_check/ or its wheel.

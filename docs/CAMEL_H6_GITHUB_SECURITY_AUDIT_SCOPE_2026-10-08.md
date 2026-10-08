# H6 — Public GitHub security tools for Spatial Check × CaMeL

**2026-10-08, PR #14, branch-only, no main change or paid resources.**

Tools: github/codeql-action@v4 (Python + GitHub Actions languages,
security-extended queries); HypothesisWorks/hypothesis (7 generated input
properties, 350 examples each); PyCQA/bandit (medium+ severity and confidence);
zizmorcore/zizmor-action (pinned SHA, advisory, without SARIF upload).

Hypothesis and Bandit are *test-only*, installed in a single ephemeral
runner job; they do not add production dependencies or run in public wheel.
CodeQL uses a narrowly scoped security-events:write permission solely to
upload static analysis findings. Public repo standard Ubuntu runners are
documented free, unlike paid larger runners. No scheduled polling, external
SaaS accounts or network-sink actions are created.

These scanners are complementary and CANNOT certify a Python in-process
reference monitor. Known G1, G4, G5 failures remain documented. In particular,
no scan can prove the trust origin of host literals or prevent direct callback
side effects without external process isolation and real host integration.

Report: exact workflow/run, CodeQL results or setup error, Bandit results,
zizmor findings, Hypothesis execution and limitations. A green CI does not
mean zero vulnerabilities. Keep this new workflow restricted to the isolated
experimental branch and keep PR #14 Draft. No main merge or cloud edits.

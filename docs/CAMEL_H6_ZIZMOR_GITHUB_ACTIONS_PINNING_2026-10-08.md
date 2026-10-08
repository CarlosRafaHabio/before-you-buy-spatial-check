# H6: audit-driven CI supply-chain pinning (experimental branch only)

**PR #14 Draft; changes do not affect main without a future merge.**

Initial scan on HEAD \`cc1990820c938130b05333670d2aee9a246ab415\`:
- Zizmor action job FAILED, correctly identifying eight HIGH severity
  \`unpinned-uses\` findings (3 other findings suppressed).
- The eight were mutable @v6/@v4 references in \`.github/workflows/tests.yml\`
  and \`.github/workflows/security-experimental.yml\`.
- Those are **supply-chain exposure findings**, NOT eight demonstrated
  exploit paths or proof that a trusted upstream action was compromised.
- Hypothesis passed seven generated property groups (350 max generated
  examples each, plus explicit examples) and Bandit job passed its configured
  medium+ severity and medium+ confidence filter.
- CodeQL Python and Actions jobs finished SUCCESS, but a successful job is
  not proof of no alerts in the GitHub code scanning UI.

Remediation: resolve actual GitHub REST tag objects and pin exact commit SHAs:
- actions/checkout v6:
  \`d23441a48e516b6c34aea4fa41551a30e30af803\`
- actions/setup-python v6:
  \`ece7cb06caefa5fff74198d8649806c4678c61a1\`
- github/codeql-action v4:
  \`24c54180a607b1449ed407dd24f251e4e9147c8d\`
  (dereferenced annotated v4 Git tag, not its tag-object SHA).

All other action references were already SHA-pinned.
Hash pinning reduces upstream mutable-tag substitution risk but requires
an explicit, reviewed update process for vulnerability fixes in upstream
actions. No one should automatically bump to HEAD without security review.

**Acceptance:** after this commit, zizmor must not report unpinned-uses
on either workflow, CodeQL and normal CI must still pass. Do NOT suppress
new unrelated findings silently. Security alerts shown in GitHub should
be separately triaged; do not call CodeQL success proof of 0 findings.

No deployment, API charge, secrets or production changes.

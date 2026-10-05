# Security policy

Security reports include trust-boundary bypasses, forged or stale evidence accepted
as current, incorrect scope binding, and invalid or untrusted data producing an
incorrect spatial decision. See [SECURITY_TRUST_NOTES.md](SECURITY_TRUST_NOTES.md)
and [TRUST_BOUNDARY.md](TRUST_BOUNDARY.md) for the intended boundary and limitations.

## Reporting a vulnerability

Private vulnerability reporting is not currently enabled for this repository, and
no dedicated security email is configured. Open a GitHub issue titled
`Security: request private contact`, providing only the affected version and a
brief, non-exploitable description of the affected component. Ask the maintainer
to arrange a private channel before sending reproduction steps or a proof of concept.

Do not publish exploitable details in issues, pull requests, or other public
channels before a fix and coordinated disclosure. If GitHub later offers a
`Report a vulnerability` button on this repository's Security tab, use that
private channel instead.

Once a private channel is agreed, include the commit or version, Python version,
entry point, minimal reproduction with synthetic data, expected and actual
behavior, and impact on geometric or trust invariants. Do not include credentials
or personal/client data.

Reports are reviewed as maintainer availability permits. There is no guaranteed
response or remediation SLA.

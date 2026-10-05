# Related work

Spatial Check is a narrow deterministic validation library, not a general agent
security framework. Its evidence-admission design sits near a broader family of work
that separates untrusted model-visible data from authority-bearing control decisions.

## CaMeL — Defeating Prompt Injections by Design

Debenedetti et al., *Defeating Prompt Injections by Design* (2025), propose CaMeL, a
system-level defense for LLM agents that separates control flow from untrusted data
flow and uses capabilities to constrain how information can influence actions.

- Paper: https://arxiv.org/abs/2503.18813
- Research artifact: https://github.com/google-research/camel-prompt-injection

Spatial Check is **not** an implementation, fork, or substitute for CaMeL.

The overlap is conceptual: both reject the assumption that model-visible data should
automatically acquire authority. Their scopes differ materially:

- CaMeL targets prompt injection and unauthorized agent data/control flows.
- Spatial Check targets admission of structured evidence into a small deterministic
  spatial validator.
- CaMeL reasons about tool/data-flow capabilities around an agent.
- Spatial Check uses a host-controlled, process-local receipt to distinguish an
  admitted snapshot from raw/model-supplied data.
- Spatial Check does not sandbox a model, authenticate a human, or provide general
  prompt-injection protection.

This distinction is important: the project claims only the narrower boundary enforced
by its public API and documented host assumptions.

## Scope of this list

This file is intentionally short. Related work is added when it materially clarifies
the project's threat model or architecture; it is not intended to be a comprehensive
survey of LLM security.

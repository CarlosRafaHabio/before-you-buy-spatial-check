# Packaging and distribution

This document describes the installable source-package boundary. It does not change
engine semantics or make a PyPI publication promise.

## Names

- Repository/product: **Before You Buy Spatial Check**
- Distribution metadata name: `before-you-buy-spatial-check`
- Python import package: `spatial_check`

The distribution remains intentionally specific to this project. The project is not
being renamed into a generic LLM trust/admission framework.

## Versioning

Two versions have different purposes:

- **distribution version** — the installable package/repository release;
- **`engine_version`** — the deterministic result-contract version emitted by the
  engine.

Distribution-only changes such as packaging, documentation, CI, or examples do not
require a new `engine_version` when result semantics and schemas are unchanged.

The first packaging metadata uses distribution version `0.3.1` while the engine
continues to emit `engine_version = "0.3.0"`.

## Install from a local checkout

Python 3.12+ is required.

```sh
python -m pip install . --no-deps
```

The installed runtime has no third-party dependencies. The build frontend may create
an isolated build environment and obtain the declared build backend; that is a build
requirement, not a runtime dependency.

After installation, from a directory outside this repository:

```sh
python -c "import spatial_check; print(spatial_check.evaluate)"
python -m spatial_check --demo fits
```

## Install directly from Git

Until a package index publication is explicitly approved, consumers may install from
a reviewed commit or release tag:

```sh
python -m pip install --no-deps "git+https://github.com/CarlosRafaHabio/before-you-buy-spatial-check.git@<commit-or-tag>"
```

Pin a commit or release tag for reproducibility rather than depending on a moving
branch.

## JSON schemas

The root `schemas/` directory remains a **repository/release artifact** in this
first packaging pass. It is not installed as Python package data.

Runtime validation uses the contracts defined in `spatial_check.contracts`, so the
installed library does not require the JSON files to execute.

Consumers that require the portable JSON Schema artifacts should obtain them from the
matching repository/release revision. A later packaging change may expose schemas as
installed resources, but that should define a stable resource-access API rather than
silently place files somewhere in an environment.

## PyPI status

There is currently **no supported PyPI publication**.

Before any first PyPI release, review at least:

- final distribution name and availability;
- package contents from both wheel and source distribution;
- release/version policy;
- portable schema distribution strategy;
- Trusted Publishing/provenance setup;
- installation documentation from a clean environment.

Do not infer PyPI availability from the presence of `pyproject.toml`.

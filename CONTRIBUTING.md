# Contributing to KaryoScope-plotlib

Thanks for your interest in improving `karyoplot`! This is the shared **plotting
library** for the KaryoScope ecosystem — the `drawsvg` (vector) and `matplotlib`
(publication) primitives consumed by the core
[KaryoScope](https://github.com/barthel-lab/KaryoScope) engine and by
[KaryoScope-analysis](https://github.com/barthel-lab/KaryoScope-analysis). It is a
library, not a CLI: there is no entry point, only importable modules.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'      # editable install + pytest/pre-commit
pip install ruff             # pinned version is in .pre-commit-config.yaml
```

## Tests and linting

```bash
python -m pytest -q          # the test suite (tests/)
ruff check src tests         # lint (line-length 100; config in pyproject.toml)
ruff format src tests        # auto-format
```

`pre-commit install` wires ruff into the commit hook so the ecosystem lints
identically (the ruff version is pinned in `.pre-commit-config.yaml`, the single
source of truth, matching KaryoScope-analysis).

## Design conventions

- **DB-agnostic.** `karyoplot` knows nothing about the KaryoScope databases — no
  `colors.tsv`/`hierarchy.tsv` parsing lives here (that is owned by
  `karyoscope.core.io`). Renderers take already-resolved inputs (e.g. `{feature: hex}`
  color maps, or a `sort_key` callable), so the library stays reusable.
- **Two backends, parallel structure.** `svg/` (drawsvg vector renderers) and `mpl/`
  (matplotlib figures) sit on shared, backend-agnostic helpers in `core/`.
- **Add modules when a consumer needs them.** Prefer growing the library from real
  call sites over carrying empty placeholder modules.

## Versioning

The version lives in `src/karyoplot/_version.py` (read by hatchling at build time and
re-exported as `karyoplot.__version__`). Bump it there.

## Changelog

Note user-facing changes under `## [Unreleased]` in `CHANGELOG.md`.

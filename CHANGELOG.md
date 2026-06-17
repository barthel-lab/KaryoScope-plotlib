# Changelog

All notable changes to `karyoplot` (KaryoScope-plotlib) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional `sort_key` on the SVG legend builders (`draw_grouped_legend`,
  `featureset_legend_items`) so consumers can order legends with a DB-aware key
  (e.g. KaryoScope-analysis sorts featureset-first, then by the engine's
  `legend_sort_key`). The library stays DB-agnostic — it just receives the callable.
- Project tooling: `ruff` + `pre-commit` config (mirrors KaryoScope-analysis; ruff
  version pinned in `.pre-commit-config.yaml`) and GitHub Actions CI.

### Changed

- **Packaging brought to parity with KaryoScope-analysis:** build backend switched
  from `setuptools` to `hatchling`, version is now dynamic (single source of truth in
  `src/karyoplot/_version.py`), and `[project]` metadata (license, classifiers,
  keywords, URLs) + `pytest`/coverage config were filled in.

### Removed

- Deleted the unused stub modules `svg/ideogram.py`, `svg/tracks.py`, and
  `mpl/legend.py` (docstring-only placeholders that nothing imported). Real modules
  will be (re)added when a consumer needs them, rather than carried as empty promises.

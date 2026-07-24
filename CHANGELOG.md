# Changelog

All notable changes to `karyoplot` (KaryoScope-plotlib) are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `ComparisonConfig.volcano_labels` — an optional `{feature_label: {"side": ..., "gap": ...}}`
  map that pins individual volcano labels to a chosen side/distance. karyoplot stays
  DB-agnostic (it receives the resolved map, never a database).

- Optional `sort_key` on the SVG legend builders (`draw_grouped_legend`,
  `featureset_legend_items`) so consumers can order legends with a DB-aware key
  (e.g. KaryoScope-analysis sorts featureset-first, then by the engine's
  `legend_sort_key`). The library stays DB-agnostic — it just receives the callable.
- Project tooling: `ruff` + `pre-commit` config (mirrors KaryoScope-analysis; ruff
  version pinned in `.pre-commit-config.yaml`) and GitHub Actions CI.

### Changed

- **Volcano label placement rewritten** to sit each label immediately beside its own
  marker via a deterministic greedy side-search (no `adjustText`, no leader lines) —
  reproducible across figure sizes, and overridable per label via
  `ComparisonConfig.volcano_labels`.
- **Volcano infinite fold changes no longer distort the x-axis.** A feature present in
  one condition and absent in the other (log₂FC = ±∞, previously hard-capped at ±5.0
  which ballooned the axis) is now scaled from the finite values only and drawn at the
  axis edge as an off-scale triangle (`▶`/`◀`) with an explanatory legend entry, so it
  is never misread as a literal fold change. Fold-change parsing is also hardened to
  normalize a raw float `inf` (not just the stringified form) before setting limits.
- **Feature-comparison is now hierarchy-aware and consumes `build-feature-matrix`.**
  - Column schema uses `__` as the sole delimiter (`{featureset}__{metric}__{feature}`), matching
    `karyoscope-analysis build-feature-matrix` (was a single `_` between featureset and metric,
    ambiguous for names like `region_subtelomere_flat` / `dterminal_min` / `active_hor`).
  - New `ComparisonConfig.feature_descendants` — a resolved `{feature: [feature, *descendants]}`
    map the DB-aware consumer supplies — expands each feature group to its whole DB-hierarchy
    subtree, so a group referencing a parent (`aSat`) covers `active_hor`/`mon`/… . karyoplot stays
    DB-agnostic (it receives the resolved map, never a hierarchy file).
  - A referenced feature that is **not** a hierarchy node raises (fail loud on a typo/stale name);
    a *valid* feature merely absent from a sample (0 reads) is 0-filled, not an error.
  - `mpl.data_loader.load_annotations` accepts `build-feature-matrix`'s `seq_id` key (normalized to
    `sequence`) and no longer requires `sequencing_approach`.
- **Colors now fail loud on a miss instead of silently defaulting** (matching the engine's
  `validate_colors` philosophy): `core.colors.get_color` raises `KeyError` when a feature has
  no color and no explicit `default` is passed (was: silent grey `#CCCCCC`); and
  `core.colors.load_featureset_palettes` defaults `on_missing="error"` (was `"warn"`).
- `core.fonts.pil_font` now falls back to matplotlib's bundled **DejaVu Sans at the
  requested size** before Pillow's fixed ~10 px bitmap default. On hosts lacking Basic
  Sans / Arial (e.g. headless compute nodes) raster labels stay legible instead of
  collapsing to ~10 px. (Upstreamed from a KaryoScope-BIR vendor patch.)
- **Packaging brought to parity with KaryoScope-analysis:** build backend switched
  from `setuptools` to `hatchling`, version is now dynamic (single source of truth in
  `src/karyoplot/_version.py`), and `[project]` metadata (license, classifiers,
  keywords, URLs) + `pytest`/coverage config were filled in.

### Removed

- Dropped the `adjustText` dependency — the volcano plot no longer uses it (labels are
  placed by the in-repo greedy side-search) and nothing else imported it.
- Deleted the unused stub modules `svg/ideogram.py`, `svg/tracks.py`, and
  `mpl/legend.py` (docstring-only placeholders that nothing imported). Real modules
  will be (re)added when a consumer needs them, rather than carried as empty promises.

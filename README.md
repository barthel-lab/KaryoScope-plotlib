# karyoplot

Shared plotting library for the KaryoScope ecosystem.

Two backends share one core. `svg/` (drawsvg-based vector renderers) and `mpl/` (matplotlib-based publication plots) stay independent for rendering; both pull chromosome facts, color palettes, fonts, and IO from `core/`.

## Install

Editable install into your KaryoScope environment:

```bash
pip install -e .          # from the repo root
pip install ruff          # pinned in .pre-commit-config.yaml
```

`svg_to_png` (SVG → PNG export) shells out to `rsvg-convert`; install it from
conda-forge if you want PNG output (it is part of the shared KaryoScope env):

```bash
conda install -c conda-forge librsvg   # provides rsvg-convert
```

## Used by

`karyoplot` is the shared plotting hub of the KaryoScope ecosystem; it is **DB-agnostic** (it takes
already-resolved inputs — color maps, sort-key callables — not database files). For the full
repo-by-repo consumer graph (including modules currently staged ahead of their consumers), see
[`docs/ECOSYSTEM.md`](docs/ECOSYSTEM.md). In brief: `KaryoScope-analysis` uses `svg.{legend,reads,export}`
+ `mpl.style`; the `mpl` comparison stack is consumed by `KaryoScope-BIR` / `KaryoScope-heatmap`;
`KaryoScope-ISCN` will consume the `svg` assembly/ideogram views.

## Module map

### `karyoplot.core` — backend-agnostic utilities

| Module | Public API |
|---|---|
| `chromosomes` | `chrom_sort_key()`, `ACROCENTRIC` (frozenset), `CANONICAL_CHROMS`, `TELOMERIC_MOTIFS` (Barthel-colored), `Reference` dataclass, `CHM13_v2`, `reference()`, `register_reference()` |
| `colors` | `load_palette()`, `load_palettes()`, `get_color()`, `hex_to_rgb()`, `hex_to_rgba()`, `rgb_to_hex()`, `BARTHEL` (10-color brand palette dict), `TAB10` / `TAB20` (qualitative palettes), `qualitative_palette()` |
| `coords` | `PixelScale` dataclass (modes: `full`, `subtelomere`, `centromere`, `custom`), `DEFAULT_SCALES` |
| `fonts` | `register_fonts()` (silent no-op if Barthel fonts missing), `set_default_font()`, `is_available()`, `resolve_family()` (opt-in upgrade), `pil_font()` (Barthel→system→default chain), `DEFAULT_FONT_FAMILY = "sans-serif"` |
| `io` | `smart_open()` (gzip-aware), `load_bed()`, `iter_bed_records()`, `fetch_fasta_region()` (samtools faidx), `FastaCache` |
| `theme` | `Theme` dataclass, `DARK` (= `DEFAULT_THEME`, matches `cluster_plot_black.svg` style), `LIGHT`, `get(name)`, `line_color_for(bg)` |

### `karyoplot.svg` — drawsvg backend

| Module | Public API |
|---|---|
| `drawing` | `draw_annotation_track()`, `draw_hexamer_track()`, `draw_axis()`, `draw_centered_track_labels()` (ported from `karyoscope_utils.drawing`; `font_family` defaults to `sans-serif`) |
| `legend` | `draw_hexamer_legend()`, `draw_grouped_legend(layout="column"\|"vertical")`, `make_legend_drawing()` (full-page auto-layout with header support, color merging), `featureset_legend_items()`, `merge_by_color()`, `clean_label()` |
| `export` | `svg_to_png(scale=N \| dpi=N)` (rsvg-convert wrapper), `is_rsvg_convert_available()`, `RsvgConvertMissingError` |
| `reads` | `rasterize_features()`, `smooth_features_to_pixels()`, `features_to_pixels_direct()` (per-read feature bp → pixel runs) |

### `karyoplot.mpl` — matplotlib backend

| Module | Public API |
|---|---|
| `types` | `FeatureGroup`, `Condition`, `CovariateValue`, `CovariateColumn`, `CovariateConfig`, `ComparisonConfig` (pure data; YAML loader lives in `karyoscope_conductor.feature_comparison_config`) |
| `style` | `apply_default_style(dark_mode)`, `fg_color()`, `sig_label()`, `save_fig()` (writes both SVG@150dpi and PNG@300dpi) |
| `data_loader` | `load_annotations()`, `compute_feature_values()`, `compute_per_sample_rates()`, `compute_read_level_table()`, `get_pooled_data()` |
| `statistics` | `compare_two_conditions()`, `apply_fdr()`, `run_all_comparisons()` (Fisher exact, Mann-Whitney, BH-FDR, log2FC) |
| `heatmap` | `plot_heatmap()` (per-sample clustered with optional covariate panel), `cluster_and_reorder()`, `fix_leaf_ordering()`, `push_leaves_to_edge()` |
| `comparison` | `plot_volcano()`, `plot_dot_strip()`, `plot_lollipop()`, `generate_all_plots()` |

## Quick start

```python
from karyoplot.core import fonts, colors, theme
from karyoplot.svg.legend import make_legend_drawing
from karyoplot.svg.export import svg_to_png

# Optional: enable Barthel brand fonts when present (silent if missing)
fonts.register_fonts()

# Build a legend in the default DARK theme (matches cluster_plot_black.svg)
items = [
    ("Chromosomes", "", True),                      # header row
    ("chr1", colors.BARTHEL["coral"], False),
    ("chr2", colors.BARTHEL["blue"], False),
    ("Repeats", "", True),
    ("LINE", colors.BARTHEL["lavender"], False),
]
d = make_legend_drawing(items, cols=2)
d.save_svg("legend.svg")
svg_to_png("legend.svg", scale=4)                    # → legend.png
```

## Defaults

- **Font family:** generic `sans-serif`. Barthel brand fonts (`Basic Sans`, `Bicyclette`) are opt-in via `register_fonts()` + `resolve_family("Basic Sans")` and silently fall back when the font directory is missing.
- **Theme:** `DARK` (black background, white text/lines) matches the most recent reference output (`fiberseq_all.cluster_plot_black.svg`).
- **SVG → PNG export:** uses `rsvg-convert` if available; warns and skips otherwise (raises `RsvgConvertMissingError` only on opt-in via `raise_on_error=True`).

## Tests

```bash
pytest -q          # from the repo root
ruff check src tests
```

**133 unit tests** cover all `core/`, `svg/`, and `mpl/` modules, including end-to-end heatmap +
dot-strip rendering with synthetic fixtures.

## Status

This library was extracted from duplicated plotting patterns scattered across the KaryoScope
scripts — `KaryoScope-CHM13/scripts/karyoscope_utils/` (drawsvg helpers, color/data loaders),
`KaryoScope-BIR/scripts/feature_comparison_lib/` (matplotlib comparison plots, statistics, data
loader), and inline implementations across 150+ plotting scripts (font registration, BED IO,
chromosome sort, color loaders, `_svg_to_png` wrappers, …).

- [`docs/migration_guide.md`](docs/migration_guide.md) — porting an existing script.
- [`docs/ECOSYSTEM.md`](docs/ECOSYSTEM.md) — the repo map + consumer graph.
- [`docs/mpl_audit.md`](docs/mpl_audit.md) — the `mpl` audit notes.
- [`CHANGELOG.md`](CHANGELOG.md), [`CONTRIBUTING.md`](CONTRIBUTING.md).

The full plotting-refactor master plan, per-script inventory, deep-extraction evaluation, and change
log live in the **KaryoScope-BIR** repo (`karyoscope_plotting_refactor_plan.md`,
`karyoscope_plotting_inventory.md`, `karyoscope_plotting_phase13_evaluation.md`,
`karyoscope_plotting_refactor_changelog.md`).

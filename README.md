# karyoplot

Shared plotting library for the KaryoScope ecosystem.

Two backends share one core. `svg/` (drawsvg-based vector renderers) and `mpl/` (matplotlib-based publication plots) stay independent for rendering; both pull chromosome facts, color palettes, fonts, and IO from `core/`.

## Install

Editable install into your KaryoScope conda env:

```bash
cd ~/Documents/software/KaryoScope-plotlib
pip install -e .
```

## Used by

| Repo | What it imports |
|---|---|
| `KaryoScope-analysis/` | `core.colors.{TAB10,TAB20}`, `core.fonts.{register_fonts,pil_font,resolve_family}`, `svg.export.svg_to_png` |
| `KaryoScope-ISCN/` | `svg.export.svg_to_png(dpi=300)` |
| `KaryoScope-conductor/` | `mpl.{data_loader,statistics,comparison,heatmap}`, `mpl.types` (via `karyoscope_conductor.feature_comparison_config`) |
| `KaryoScope-BIR/` | `mpl.style.{apply_default_style,fg_color,save_fig,sig_label}`, `mpl.comparison._arcsin_sqrt` |
| `KaryoScope-CHM13/` | not yet — annotated with future-migration headers (see Phase 8 in the refactor plan) |

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
| `legend` | `draw_hexamer_legend()`, `draw_grouped_legend(layout="column"\|"vertical")`, `make_legend_drawing()` (full-page auto-layout with header support, color merging), `merge_by_color()`, `strip_label_suffixes()` |
| `export` | `svg_to_png(scale=N \| dpi=N)` (rsvg-convert wrapper), `is_rsvg_convert_available()`, `RsvgConvertMissingError` |
| `ideogram`, `tracks`, `reads` | (stubs — to be populated when scripts migrate) |

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
cd ~/Documents/software/KaryoScope-plotlib
pytest tests/ -q
```

Currently **70 unit tests** covering all `core/`, `svg/`, and `mpl/` modules, including end-to-end heatmap + dot-strip rendering with synthetic fixtures.

## Status

This library was extracted in 2026-04 from duplicated patterns scattered across:

- `KaryoScope-CHM13/scripts/karyoscope_utils/` (drawsvg helpers, color/data loaders)
- `KaryoScope-BIR/scripts/feature_comparison_lib/` (matplotlib comparison plots, statistics, data loader)
- Inline implementations in 40+ plotting scripts (font registration, BED IO, chromosome sort, color file loaders, `_svg_to_png` wrappers, …)

See [`docs/migration_guide.md`](docs/migration_guide.md) for porting an existing script.

The full refactor plan, decision log, and changelog live in `~/Documents/KaryoScope-BIR/`:

- `karyoscope_plotting_refactor_plan.md` — 12-phase master plan
- `karyoscope_plotting_refactor_changelog.md` — running log of every change
- `karyoscope_plotting_inventory.md` — per-script inventory

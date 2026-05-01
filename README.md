# karyoplot

Shared plotting library for the KaryoScope ecosystem. Provides:

- **`karyoplot.core`** — backend-agnostic utilities: chromosome facts, color palettes, coordinate scaling, font registration, BED/FASTA IO.
- **`karyoplot.svg`** — `drawsvg`-based vector renderers: ideograms, per-read tracks, annotation tracks, scale bars, legends.
- **`karyoplot.mpl`** — `matplotlib`-based publication plots: clustering heatmaps, volcano plots, comparison statistics.

Used by:
- `KaryoScope-analysis/` — stable analysis scripts
- `KaryoScope-ISCN/` — assembly/ISCN figure scripts
- `KaryoScope-conductor/` — pipeline orchestration
- `KaryoScope-BIR/` — sandbox / experimental scripts

## Install

Editable install into your KaryoScope conda env:

```bash
cd ~/Documents/software/KaryoScope-plotlib
pip install -e .
```

## Quick start

```python
from karyoplot.core import fonts, colors, chromosomes
from karyoplot.svg import drawing, legend
from karyoplot.mpl import heatmap, comparison

fonts.register_fonts()                         # register Basic Sans / Bicyclette
palette = colors.load_palette("KS_human_CHM13.repeat.colors.txt")
chrom_order = sorted(my_chroms, key=chromosomes.chrom_sort_key)
```

## Architecture

Two backends, one core. `svg/` and `mpl/` stay independent for rendering; both share `core/` for chromosome facts, colors, fonts, and IO.

See [`docs/migration_guide.md`](docs/migration_guide.md) for porting an existing script.

## Status

This library is a consolidation of duplicated patterns previously scattered across:
- `KaryoScope-CHM13/scripts/karyoscope_utils/`
- `KaryoScope-BIR/scripts/feature_comparison_lib/`
- Inline implementations in 50+ plotting scripts

See `karyoscope_plotting_refactor_plan.md` (in `KaryoScope-BIR/`) for the full migration plan.

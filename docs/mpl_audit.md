# `karyoplot.mpl` audit notes

Status: notes for a future session. Captured during the KaryoScope-analysis/plotlib
reorganization. The **quick wins below are already done**; the rest is triage.

## Scope & method

Audited `src/karyoplot/mpl/` (`types`, `style`, `data_loader`, `statistics`, `heatmap`,
`comparison`) for dead code and duplication. Method: enumerate the public API per module,
grep every symbol's usages across `KaryoScope-plotlib`, `KaryoScope-analysis`, and
`KaryoScope` (engine), and read the modules. The `mpl` stack is the feature-comparison /
cohort-QC toolkit **ported from `KaryoScope-BIR/scripts/feature_comparison_lib/`**.

## Headline

The `mpl` modules are internally clean and coherent — **no dead code or duplication *within*
them**. The findings are about consumer status, two unexercised public functions, and
reconciliations pending against code not yet migrated.

## Findings

### 1. No shipping consumer yet (by design)
The only `mpl` import by production code anywhere in the ecosystem is **`mpl.style`** (used by
`karyoscope_analysis.core.enrichment_plot`). The `data_loader → statistics → comparison/heatmap`
pipeline is exercised **only by `tests/test_mpl.py`**. It is *library-ahead-of-consumer*: its
intended consumers are other ecosystem repos not yet migrated — see `docs/ECOSYSTEM.md`
(**KaryoScope-BIR** for the comparison stack; **KaryoScope-heatmap** for `mpl.heatmap`). Not dead;
just not wired in yet. (A one-line "staged toolkit" note in the README would prevent confusion.)

### 2. Two public functions are uncalled *and* untested (real gap)
- `data_loader.compute_read_level_table` — referenced only in the README; never called, never
  tested. Note: its output schema (`read_id, group, subgroup, sample`) is exactly
  KaryoScope-analysis's **`plot-reads` read-list format** — a real integration opportunity (feed
  cohort-QC reads into `plot-reads`) rather than a deletion candidate.
- `statistics.run_all_comparisons` — the intended orchestrator; referenced only in the README
  (`comparison.generate_all_plots` takes already-computed stats and does not call it); never tested.

  → Decide per function: add test coverage when the BIR consumer lands, or drop until needed
  (consistent with the stub-deletion philosophy applied to `svg/{ideogram,tracks}`/`mpl/legend`).

### 3. Reconciliations pending (duplication-*in-waiting*, not current)
When `cluster_analysis` / `cluster_diagnostics` migrate (see `KaryoScope-analysis/docs/audit/`),
they will collide with what already lives here. Decide deliberately at migration time:
- **FDR differs:** `statistics.apply_fdr` is a hand-rolled **BH-only** implementation; the legacy
  scripts use `scipy.stats.false_discovery_control` (**BH+BY**). Converge on one — recommend pushing
  a single FDR into `karyoplot.core` (mpl-free) and standardizing on BH+BY.
- **Leaf-ordering math:** `heatmap.{fix_leaf_ordering,push_leaves_to_edge,cluster_and_reorder}` will
  overlap the planned `svg.dendrogram` drawer (a `cluster_plot` push-down). The matrix/linkage math
  is backend-agnostic → move to `karyoplot.core`, shared by `mpl.heatmap` and `svg.dendrogram`.
- **Significance stars:** standardize on `style.sig_label` (legacy uses inline `***/**/*`).

### 4. Minor code-quality nits
- **DONE:** `print()` → `logging` in `mpl.{data_loader,statistics,comparison,heatmap}`; seeded
  `plot_dot_strip` jitter (`np.random.default_rng(0)`) for reproducible figures.
- **Still open (library-wide, out of mpl scope):** `print()` remains in `core/colors.py`,
  `core/sample_metadata.py`, `svg/export.py` — extend `print → logging` across the library for
  consistency.
- `statistics.compare_two_conditions` uses broad `except Exception` fallbacks (acceptable — they set
  NaN/1.0 fallbacks — but a narrower `except (ValueError, ZeroDivisionError)` is cleaner).

## Recommended next steps (in priority order)
1. Decide keep-with-tests vs drop for `compute_read_level_table` and `run_all_comparisons`.
2. Extend `print → logging` to `core`/`svg` (finish what the mpl quick win started).
3. Defer the FDR / dendrogram / stars reconciliations to the `cluster_analysis` migration, but
   keep them on the radar so the divergence is resolved deliberately, not silently.

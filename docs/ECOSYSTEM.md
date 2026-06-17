# The KaryoScope ecosystem

A living map of the KaryoScope repositories and how they fit together. The goal is a
**seamless, interconnected ecosystem**: one core engine, one shared plotting library, shared
feature databases, and a set of analysis/reporting tools that consume them through stable APIs
rather than copy-pasted code.

> This file currently lives in `KaryoScope-plotlib/docs/` (the shared-library hub, where the
> "who consumes what" question is sharpest). It is cross-repo by nature — consider promoting it to
> an org-level/engine-level canonical location once the reorg settles.

## Repositories

| Repo | Role | Packaging | Reorg status |
| --- | --- | --- | --- |
| **KaryoScope** | Core engine: k-mer feature-annotation pipeline (Snakemake) + canonical DB parsers (`core.io.{colors,hierarchy}`) + the karyotype renderer. The foundation. | installable pkg `karyoscope` | established |
| **KaryoScope-databases** | The feature databases (`hierarchy.tsv` / `colors.tsv`), e.g. `KS_human_CHM13_v2`. Data, not code. | data repo | n/a |
| **KaryoScope-plotlib** (`karyoplot`) | Shared plotting library — `svg/` (drawsvg vector) + `mpl/` (matplotlib) primitives. **DB-agnostic** (takes resolved inputs). The hub. | installable pkg `karyoplot` | **done** (this work) |
| **KaryoScope-analysis** (`karyoscope-analysis`) | Clustering (Engine A/B), annotation, cross-sample enrichment, and visualization CLI. | installable pkg + CLI | **in progress** |
| **KaryoScope-ISCN** | ISCN cytogenetic reporting from assemblies: genome-wide karyotypes, multi-zoom breakpoint/centromere views, KromaTid (dGH) validation. | flat `scripts/` | reorg pending |
| **KaryoScope-heatmap** | Per-read feature **co-occurrence** heatmaps ("telomere_crisis"); Snakemake workflow. | Snakemake + `scripts/` | reorg pending |
| **KaryoScope-BIR** | Cohort **clustering + feature-comparison** analysis driver (NHA / Core-4 / IDH-astro cohorts). Origin of `karyoplot.mpl`'s comparison stack (`feature_comparison_lib`). | flat `scripts/` | reorg pending |
| **KaryoScope-conductor** (`karyoscope-conductor`) | Lightweight YAML-driven workflow runner (≤10 sequential steps) that chains the CLIs. Complementary to Snakemake/Nextflow. | installable pkg + CLI | established |

## Dependency / consumer graph

```
KaryoScope-databases ─ data ─┐
                             ▼
   KaryoScope (engine) ──────────────────────────────► annotations (BEDs) + DB parsers
        │  karyoscope.core.io.{colors,hierarchy}                 │
        ▼                                                        ▼
   KaryoScope-plotlib (karyoplot)  ◄──── shared by ──── KaryoScope-analysis ──► clusters,
        svg/  +  mpl/                                    (Engine A/B, enrichment,    enrichment,
        ▲   ▲   ▲                                         viz CLI)                   labeled figs
        │   │   └───────────────── mpl.heatmap ──────── KaryoScope-heatmap (co-occurrence)
        │   └───────── mpl.{data_loader,statistics,comparison,heatmap} ── KaryoScope-BIR (cohort)
        └─ svg.{ideogram,tracks,drawing} ── KaryoScope-ISCN (assembly/karyotype/zoom views)

   KaryoScope-conductor ── orchestrates ──► the CLIs above (analysis, engine steps)
```

## Why some `karyoplot` modules have "no consumer yet"

During the plotlib audit (`docs/mpl_audit.md`), several modules were found to be exercised only by
their own tests. That is **staging, not dead code** — the consumers are ecosystem repos not yet
migrated:

- **`karyoplot.mpl.{data_loader, statistics, comparison, heatmap}`** — ported *from*
  **KaryoScope-BIR** (`feature_comparison_lib`); BIR is the intended consumer once it is reorganized
  onto the package. **KaryoScope-heatmap** is a second consumer for `mpl.heatmap`.
- **`karyoplot.svg.{ideogram, tracks}`** — these were deleted as empty stubs during the reorg, but
  the work they anticipated (whole-genome ideograms, multi-track assembly layouts) belongs to
  **KaryoScope-ISCN**. They should be (re)added to `karyoplot.svg` *when ISCN migrates and needs
  them*, built from ISCN's `KaryoScope_assembly_*` / contig-zoom patterns — not before.

So when reorganizing ISCN / heatmap / BIR, the move is: pull shared rendering/stats **down** into
`karyoplot` (extending `svg`/`mpl`), and have each repo consume it through the same stable APIs that
`KaryoScope-analysis` already uses. That is how the "no consumer" modules acquire their consumers.

## Conventions that keep it seamless

- **DB parsing is owned by `karyoscope.core.io`** — never reimplemented downstream.
- **`karyoplot` stays DB-agnostic** — renderers take resolved inputs (`{feature: hex}` maps, sort-key
  callables), so every repo can reuse them.
- **Feature classes come from the DB hierarchy** (`FeatureHierarchy`), never hardcoded — so non-human
  / custom databases work across the whole ecosystem.
- **Shared tooling**: ruff (pinned in `.pre-commit-config.yaml`), hatchling packaging, dynamic
  version in `_version.py`, `CHANGELOG.md` + `CONTRIBUTING.md` — mirrored repo-to-repo.

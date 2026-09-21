# Plotly-Dash-Workshop-Demo

A Plotly/Dash demo built for the MIND Symposium at Robarts Research Institute. It shows
how an abstracted, no-code frontend can let someone explore and analyze data without
touching Python — here sitting in front of real output from the Khan Lab's SPIMquant
pipeline.

The app loads a lightsheet dataset of Abeta (amyloid) and Iba1 (microglia) measurements
from a Lecanemab treatment study, and lets a viewer filter it, sort it, export it, and
compare treatment groups, entirely through the browser.

## Project structure

```
demo/
  app.py                                            the Dash app - this is the demo
  seg-coarse_from-ABAv3_desc-gmm+n3k1_allsubjects.tsv   the SPIMquant data it reads
archived/
  01_plotly_intro.ipynb   how an interactive chart gets *built*, step by step, in Plotly Express
  generic_app.py          the earlier version of the app, built on the Gapminder sample dataset
pixi.toml / pixi.lock     the environment
```

`archived/` holds the teaching lineage rather than dead code. The notebook is the
"here's how you make a chart in Python" half of the workshop, and `generic_app.py` is the
same app pattern on a dataset everyone already understands (countries, life expectancy,
GDP), which is easier to follow before switching to real lab data.

## Running it

```bash
pixi install

# the main app - SPIMquant data
pixi run app

# the notebook - how the charts are built
pixi run notebook

# the earlier Gapminder version of the app
pixi run generic_app
```

Either app starts at http://127.0.0.1:8050.

## The data

One row per brain region per mouse: **28 mice × 25 Allen Brain Atlas (v3) coarse regions
= 700 rows**, 39 columns. Each row carries Abeta and Iba1 quantifications for that region
(voxel counts, object counts, field fraction, volume, density) alongside the animal's
metadata (sex, genotype, treatment, batch, QC notes).

`demo/app.py` looks for the data in two places, in order, and prints which one it used at
startup:

1. `demo/seg-coarse_from-ABAv3_desc-gmm+n3k1_allsubjects.tsv` — the copy committed here
2. `~/lightsheet/mouse_app_lecanemab_ki3_aggregated/derivatives/spimquant-v0.9.0/group/treatmenteffect_sexstratified_betterN4maskdropfailed/` — the original on the lab filesystem

So it runs anywhere from the committed copy, but picks up the live file if you have the
lab filesystem mounted and delete the local one.

## What the app does

**Filters** (sex, genotype, treatment, brain region) apply to everything below them.

**Region measurements** — all 39 columns of the filtered data. Click a header to sort,
type into the box beneath a header to filter (numeric columns accept operators like
`>10`), and download the rows you're currently viewing as CSV.

**Treatment effect per mouse** — a 2×2 grid summarising each animal across the selected
regions: total count, total burden in voxels, density, and volume-weighted field fraction.
Each point is one mouse. Switch the stain between Abeta and Iba1, and switch what the
colors split by.

## Notes on the data

A few things that matter when reading the numbers:

- **`Unknown_Label_0` is not a brain region.** It's a whole-image background record, one
  per mouse. The per-mouse chart always excludes it (it alone is ~20% the size of all 25
  real regions combined, so it would inflate every total); the table still shows it.
- **Genotype is confounded with treatment.** All Lecanemab and PBS animals are `App-NLGF`;
  the only two `WT` animals have no treatment recorded. Splitting the chart by genotype
  therefore gives one color per treatment group. Splitting by `sex` (8F/7M Lecanemab,
  4F/5M PBS) actually subdivides them.
- **The `coloc+*` measurements are empty** for every real region — all zeros (or a `"0"`
  string sentinel), with real values only on the background record. They're in the table
  for completeness but aren't plottable. The exception is `coloc+volume`, which isn't a
  colocalization measure at all: it's the region volume, identical to `Abeta+volume` and
  `Iba1+volume`.
- **Field fraction is volume-weighted** when aggregated per mouse, since a plain mean
  would weight the tiny Pallidum the same as the Isocortex.

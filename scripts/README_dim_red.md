# Chapter 5 figures

From the thesis checkout:

```sh
uv run generate_dim_red_figures.py
```

This replaces the PDFs in `figures/05/` directly and removes obsolete chapter-5
PDFs. It does not write paper figures or touch other chapters. Chrome/Chromium
and Palatino or its fontconfig-compatible P052 fallback must be available.
The standard TeX Live `pdfcrop` tool and Ghostscript trim the exported PDFs.
Plotly 6 and Kaleido 1 are declared in the script's dependency block.

`scripts/dim_red_figure_data.json.gz` contains the original plotted observations,
heatmap means and BO mean ranks, plus the theme from `thesis/template.py`.
Ordinary regeneration needs neither the experiment checkout nor the HPC data.
No model is fitted and no experiments are rerun.

To refresh the snapshot after changing the aggregates or the template, use the
benchmark repository's existing Python environment:

```sh
python scripts/collect_dim_red_figure_data.py \
  --benchmark-dir /path/to/benchmark_dim_red \
  --aggregation-dir /path/to/aggregation
```

The collector reuses the unmodified `analysev2` queries, filters, normalisation,
method order and shared comparison scales. It opens the DuckDB files read-only.
The compressed snapshot includes every active chapter panel, including the
appendix's default, tuned, timing and initial-sample comparisons.

Full-width panels use the template's 336 TeX pt text width; paired BO heatmaps
use 49% of that width before cropping. Exports are tightly cropped to their
visible content with a 2 pt safety margin; LaTeX includes them at natural size
to preserve the font sizes. Labels use 7.5 pt at inclusion size (7 pt for BO row
labels); axis and colourbar titles use 8.25 pt, below the thesis body text.
Heatmaps use a white–cyan–teal–green sequential scale built from the muted
thesis palette; darker means better. Colourbars retain the original units
and shared limits. Boxplots use muted outlines and pale fills. BO heatmaps show
actual mean ranks in a fixed method order. Their longer labels use the
abbreviations explained in the chapter.

The generator checks chapter coverage, shared scales and preservation of plotted
observations before exporting. It exports the whole set to a temporary directory
and crops it before replacing the chapter PDFs. Regeneration changes
presentation only.

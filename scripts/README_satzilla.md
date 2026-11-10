Regenerate the revisiting SATzilla chapter figures from the thesis repository:

```bash
uv run scripts/regenerate_satzilla_figures.py
```

Requires Chrome/Chromium and Palatino or a compatible installed font (TeX Gyre
Pagella/P052). Set `BROWSER_PATH` if Kaleido cannot find Chrome. The command
replaces exactly the 125 existing PDFs in `figures/04/figs`; it creates no alternate
figure versions. It checks chapter references and asserts that restyling preserves
all plotted values and ECDF coordinates.

`satzilla_figure_data.json` holds only the original chart data and the theme from
`thesis/template.py`. This makes regeneration independent of the experiment
checkout, stored models and cluster output. Its provenance field identifies the
sources. The muted palette uses indigo for 2024, rose for 2012, green for VBS and
olive for SBS. Lines also differ by dash style; the 2012 bars have a stripe pattern.
PDFs are exported at their native inclusion sizes against the chapter's 336 TeX
point text width; LaTeX includes them without width or scale options. Export widths
round down to whole browser pixels so they fit within the subfigure containers.
Feature-time panels are three across; runtime and error-bin bars are
horizontal to keep labels legible. The 92 per-solver histogram panels are grouped
in 2×2 appendix figures; no panel is rescaled by LaTeX. The chapter's figure paths and labels are kept.

To refresh the snapshot from the original experiment checkout (only if needed):

```bash
python scripts/collect_satzilla_figure_data.py /path/to/revisiting_sat_feats
```

This additionally requires pandas, numpy, scikit-learn, PyYAML and liac-arff,
and the original cluster results at `/storage/work/shavit/out_aspeed_8h_180`.
It reads the original notebooks, feature CSVs and AutoFolio evaluation code;
it writes only the JSON beside these scripts. The algorithm-selection closed-gap
values are checked against the original notebook before saving.

The published metric definitions are retained: the saved satisfiability bars
contain `100 * sqrt(accuracy)`, and runtime error bins use relative errors of
`log10(runtime)`. This presentation update does not correct those definitions or
change the chapter's conclusions. Per-solver histogram counts are reconstructed
from saved predictions and must sum exactly to each original aggregate histogram.
No estimator is run or retrained. All 14 histogram intervals are explicitly labelled.
The prediction-bar values were also checked against the original thesis PDFs.

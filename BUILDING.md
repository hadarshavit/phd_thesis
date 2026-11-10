# Building the thesis

Run from the benchmark repository:

```sh
bash thesis/phd_thesis/build_thesis.sh
```

The PDF and build logs go to `thesis/build/`. The script checks that all included
chapter sources exist, runs pdfLaTeX, runs Biber, and makes two further LaTeX
passes to resolve references and the contents lists.

Use a complete TeX Live installation with matching pdfLaTeX/biblatex and Biber
versions on `PATH`. This machine currently uses TeX Live 2026 and Biber 2.22.
The older bundled `thesis/.tools/biber` is incompatible with the installed
biblatex and is no longer selected by the build script.

The local `thesis/.cache/tectonic/` package cache and
`thesis/.tools/tex-overrides/` remain fallback search paths for the earlier,
incomplete system installation. They are machine setup, not GitHub assets;
a complete TeX Live installation supplies the standard packages itself.

The generated `ClassicThesis.pdf` is intentionally ignored by Git. Regenerate
chapter-5 figures with `uv run thesis/phd_thesis/generate_dim_red_figures.py`
from the benchmark repository; see `scripts/README_dim_red.md` for data-refresh
instructions. Figure PDFs remain tracked in their chapter's `figures/` folder.

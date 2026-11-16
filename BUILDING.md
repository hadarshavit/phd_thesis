# Building the thesis

From the root of a clone of this repository, run:

```sh
bash build_thesis.sh
```

The PDF and build logs go to `build/`. The script checks that all included
chapter sources exist, runs pdfLaTeX, runs Biber, and makes two further LaTeX
passes to resolve references and the contents lists.

Use a complete TeX Live installation with matching pdfLaTeX/biblatex and Biber
versions, plus Python 3, on `PATH`. No local caches, publication checkouts,
figure-generation tools, or files outside this repository are required.

On Overleaf, set the main document to `ClassicThesis.tex`, use pdfLaTeX and a
recent TeX Live version, and recompile from scratch. Overleaf runs Biber as
needed. A first pdfLaTeX pass reports unresolved references and citations;
those normally resolve after Biber and subsequent LaTeX passes.

Six references to absent supplementary material and three bibliography keys
(`EggEtAl18a`, `FeuEtAl19`, and `Mockus12b`) currently remain unresolved.
These are existing content warnings, separate from fatal compilation errors.

The generated `ClassicThesis.pdf` is intentionally ignored by Git. Regenerate
chapter-5 figures with `uv run generate_dim_red_figures.py`
from this repository; see `scripts/README_dim_red.md` for data-refresh
instructions. Figure PDFs remain tracked in their chapter's `figures/` folder.

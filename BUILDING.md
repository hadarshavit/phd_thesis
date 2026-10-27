# Building the thesis on this machine

Run from the benchmark repository:

```sh
bash thesis/phd_thesis/build_thesis.sh
```

The PDF and build logs go to `thesis/build/`. The script checks that all included
chapter sources exist before running pdfLaTeX, Biber, and two further LaTeX passes.

The system TeX Live 2020 installation is incomplete. The local setup keeps that
pdfLaTeX engine and supplies missing packages and Euler font resources from
`thesis/.cache/tectonic/`. Biber 2.17 in `thesis/.tools/` matches the cached
biblatex 3.17. A local URL-package override keeps URL and bibliography packages
compatible. Tectonic 0.17.0 was used to populate the cache; it is not the final
PDF engine. The system installation and thesis template were not modified.

These local binaries and caches are machine setup, not GitHub assets. On another
machine, use a complete TeX Live installation with Biber, or recreate this local
setup. A missing-file error from LaTeX may indicate an additional package or an
uncommitted source/figure; the detailed log is in `thesis/build/`.

As of 27 October 2026, GitHub main includes `Chapters/Chapter05_dim_red.tex` but
does not contain it. Other renamed chapters are also absent. The introduction
references `Chapters/figures/plotly_template_demo.pdf`, which is absent too.
The available background chapter and bibliography compiled successfully with the
real thesis preamble; the partial toolchain test is `thesis/build/ToolchainCheck.pdf`.
This test deliberately omits unavailable chapters and is not a complete thesis.

Push the current chapter sources and intended assets before building the full
thesis or regenerating the updated dimensionality-reduction figure set.

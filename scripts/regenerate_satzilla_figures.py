# /// script
# requires-python = ">=3.10"
# dependencies = ["plotly>=6.1,<7", "kaleido>=1,<2"]
# ///
"""Replace all 125 chapter-4 PDFs using the saved original chart data.

Run: uv run scripts/regenerate_satzilla_figures.py
Requires Chrome/Chromium and Palatino or TeX Gyre Pagella/P052.
The snapshot contains the theme from thesis/template.py; no experiment checkout
or trained models are needed for ordinary regeneration.
"""
import json
from pathlib import Path
import re
import textwrap

import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
TEXT_WIDTH_PT = 336
PX_PER_TEX_PT = 96 / 72.27
COLORS = {"SATzilla 2024": "#332288", "SATzilla 2012": "#CC6677",
          "VBS": "#117733", "SBS": "#999933"}
DASHES = {"SATzilla 2024": "solid", "SATzilla 2012": "dash", "VBS": "dot", "SBS": "dashdot"}
NAMES = {"": "SATzilla 2024", "_old": "SATzilla 2012", "2024": "SATzilla 2024", "2012": "SATzilla 2012",
         "SATZilla 2024": "SATzilla 2024", "SATZilla 2012": "SATzilla 2012"}


def make_figure(name, traces, width_fraction):
    fig = go.Figure(layout=dict(template="thesis"))
    feature_time = name.startswith("ecdf_sc")
    runtime = name.startswith("rts_bar")
    histogram = name.startswith("acc_rt")
    selection = name.startswith("ecds_af")
    per_solver = histogram and "_both_" in name
    width = TEXT_WIDTH_PT * width_fraction
    height = 90 if feature_time else 210 if runtime else 190 if per_solver else 230 if histogram else 160 if selection else 140
    fig.update_layout(width=int(width * PX_PER_TEX_PT), height=round(height * PX_PER_TEX_PT),
                      margin=dict(l=38 if feature_time else 52, r=22 if feature_time else 8, t=12 if feature_time else 8,
                                  b=42 if feature_time else 64),
                      legend=dict(y=-.3, font_size=11, entrywidth=.5, entrywidthmode="fraction"),
                      barmode="group", showlegend=not feature_time)
    for trace in traces:
        identity = NAMES.get(trace.get("name"), trace.get("name"))
        color = COLORS[identity]
        # Rebuild traces to remove the paper's explicit fonts, colours and hover styles.
        if trace["type"] in ("scatter", "scattergl"):
            fig.add_scatter(x=trace["x"], y=trace["y"], name=identity.replace("SATzilla ", ""), mode="lines",
                            line=dict(color=color, dash=DASHES[identity], width=1.6,
                                      shape=trace.get("line", {}).get("shape", "hv")))
        else:
            x = trace["x"]
            y = trace["y"]
            if runtime:
                x = ["<br>".join(textwrap.wrap(s.replace("<br>", ""), width=26)) for s in x]
            elif histogram:
                edges = [0, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
                x = [f"{a}–{b}" for a, b in zip(edges, edges[1:])]
            elif name == "as_bar_2023":
                x = ["2022", "2023"]
            else:
                x = [s.upper() if s != "all" else "All" for s in x]
            horizontal = runtime or histogram
            fig.add_bar(x=y if horizontal else x, y=x if horizontal else y,
                        orientation="h" if horizontal else "v", name=identity if runtime else identity.replace("SATzilla ", ""),
                        marker=dict(color=color, pattern=dict(shape="/" if identity == "SATzilla 2012" else "",
                                                             solidity=.2, fillmode="overlay",
                                                             fgcolor="white", bgcolor=color, size=5)),
                        text=y if not histogram else None,
                        texttemplate="" if histogram else "%{text:.2f}" if runtime or name == "as_bar_2023" else "%{text:.1f}",
                        textposition="outside", textfont=dict(size=11, color="#262626"), cliponaxis=False)
    if feature_time:
        fig.update_xaxes(title_text="Time (s)", range=[0, 180], tickvals=[0, 90, 180], showgrid=False,
                         title_standoff=2)
        fig.update_yaxes(title_text="Computed (%)", range=[0, 1], tickvals=[0, .5, 1],
                         ticktext=["0", "50", "100"], title_standoff=2)
    elif runtime:
        fig.update_layout(margin=dict(l=190, r=8, t=8, b=50), legend=dict(y=-.17))
        fig.update_xaxes(title_text="RMSE", range=[0, 1], dtick=.25)
        fig.update_yaxes(title_text=None, autorange="reversed", showgrid=False, tickfont_size=11)
    elif histogram:
        fig.update_layout(margin=dict(l=68, r=8, t=8, b=70), legend=dict(y=-.22), bargap=.12)
        fig.update_xaxes(title_text="Count", nticks=3)
        fig.update_yaxes(title_text="Error (%)", autorange="reversed", showgrid=False,
                         tickmode="array", tickvals=x)
        if per_solver:
            fig.update_layout(margin=dict(b=50), legend=dict(y=-.22))
            fig.update_yaxes(tickfont_size=8 * PX_PER_TEX_PT)
    elif selection:
        fig.update_layout(margin=dict(l=52, r=8, t=8, b=76), legend=dict(y=-.36))
        fig.update_xaxes(title_text="Time (s)", type="log", range=[.01, 3.699],
                         tickvals=[10, 100, 1000], ticktext=["10", "100", "1000"])
        fig.update_yaxes(title_text="Solved (%)", range=[0, 1], tickformat=".0%", dtick=.25)
    else:
        fig.update_xaxes(title_text=None, showgrid=False)
        fig.update_yaxes(title_text="Closed gap" if name == "as_bar_2023" else "Accuracy (%)",
                         range=[0, 1 if name == "as_bar_2023" else 100])
        fig.update_layout(bargap=.05, legend=dict(y=-.3))
    return fig


def main():
    data = json.loads(Path(__file__).with_name("satzilla_figure_data.json").read_text())
    theme = go.layout.Template(data["template"])
    # Chromium needs the installed Palatino-compatible family named explicitly.
    family = theme.layout.font.family.replace("serif", '"P052", serif')
    theme.layout.font.family = family
    theme.layout.annotationdefaults.font.family = family
    pio.templates["thesis"] = theme
    chapter = ROOT / "Chapters/Chapter04_rev_satzilla.tex"
    referenced = set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{figures/04/figs/([^}]+)\.pdf\}", chapter.read_text()))
    assert referenced == set(data["charts"]), "Chapter references and chart data must match"
    widths = {"as_bar_2023": .6}
    for fraction, body in re.findall(r"\\begin\{subfigure\}(?:\[[^]]*\])?\{([.0-9]+)\\textwidth\}(.+?)\\end\{subfigure\}", chapter.read_text(), re.S):
        for name in re.findall(r"figures/04/figs/([^}]+)\.pdf", body):
            assert name not in widths or widths[name] == float(fraction), f"Conflicting placement widths: {name}"
            widths[name] = float(fraction)
    assert set(widths) == referenced
    figures = [make_figure(name, traces, widths[name]) for name, traces in data["charts"].items()]
    for fig, traces in zip(figures, data["charts"].values()):
        assert len(fig.data) == len(traces)
        for drawn, source in zip(fig.data, traces):
            values = drawn.x if drawn.type == "bar" and drawn.orientation == "h" else drawn.y
            assert list(values) == list(source["y"]), "Restyling must preserve values"
            if drawn.type == "scatter":
                assert list(drawn.x) == list(source["x"])
    paths = [ROOT / "figures/04/figs" / f"{name}.pdf" for name in data["charts"]]
    assert all(p.is_file() for p in paths), "Only replace existing chapter figures"
    pio.write_images(figures, paths, width=[f.layout.width for f in figures],
                     height=[f.layout.height for f in figures])
    print(f"Replaced {len(paths)} chapter-4 figures.")


if __name__ == "__main__":
    main()

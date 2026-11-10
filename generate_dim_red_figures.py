# /// script
# requires-python = ">=3.10"
# dependencies = ["plotly>=6.1,<7", "kaleido>=1,<2"]
# ///
"""Replace chapter-5 figures using the saved original chart data and thesis theme.

Run: uv run generate_dim_red_figures.py
Requires Chrome/Chromium and Palatino (or the compatible P052 fallback).
To refresh the data or thesis/template.py theme, first run
scripts/collect_dim_red_figure_data.py in the benchmark Python environment.
Only figures/05 PDFs are replaced; obsolete chapter-5 PDFs are removed.
"""
import gzip
import json
from pathlib import Path
import re
import tempfile

import plotly.graph_objects as go
import plotly.io as pio

THESIS = Path(__file__).resolve().parent
PX_PER_TEX_PT = 96 / 72.27
# Long method names otherwise consume nearly the entire half-width BO panel.
SHORT_NAMES = {'Gaussian Random Projection': 'Gaussian RP',
               'Sparse Random Projection': 'Sparse RP',
               'Autoencoder (2-layer)': 'Autoencoder (2L)',
               'Denoising Autoencoder': 'Denoising AE',
               'Denoising Autoencoder (2-layer)': 'Denoising AE (2L)',
               'VAE (2-layer)': 'VAE (2L)',
               'Parametric UMAP (Unsupervised)': 'Param. UMAP (unsup.)',
               'UMAP (Unsupervised)': 'UMAP (unsup.)'}


def rank_panel(name):
    return '/heatmap_' in name


def make_figures(data):
    pio.templates['thesis'] = go.layout.Template(data['template'])
    # P052 is the installed Palatino-compatible font on the thesis build machine.
    pio.templates['thesis'].layout.font.family = 'P052, ' + data['template']['layout']['font']['family']
    palette = data['palette']
    # A sequential scale derived only from the thesis palette; darker means better.
    sequential = [[0, '#FFFFFF'], [.25, palette['cyan']], [.6, palette['teal']], [1, palette['green']]]
    reverse = [[1 - stop, color] for stop, color in reversed(sequential)]
    figures, scales = {}, {}
    for name, raw in data['charts'].items():
        source = go.Figure(raw)
        heatmap = source.data[0].type == 'heatmap'
        portrait = rank_panel(name)
        width_pt = data['text_width_pt'] * (.49 if portrait else 1)
        height_pt = 325 if portrait else 242 if not heatmap else 210
        fig = go.Figure(layout=dict(template='thesis'))
        fig.update_layout(width=round(width_pt * PX_PER_TEX_PT),
                          height=round(height_pt * PX_PER_TEX_PT), showlegend=False,
                          margin=dict(l=116 if portrait else 48, r=8, t=8,
                                      b=42 if portrait else 208))
        fig.update_xaxes(tickfont_size=12, title_font_size=13.33,
                         title_standoff=5, showgrid=False)
        fig.update_yaxes(tickfont_size=12, title_font_size=13.33,
                         title_standoff=5)
        if heatmap:
            trace = source.data[0]
            if portrait:
                rows = dict(zip(trace.y, trace.customdata))
                order = [m for m in data['method_order'] if m in rows]
                assert set(order) == set(rows), name
                z = [list(rows[m]) for m in order]
                assert len(order) == len(trace.y), name
                assert all(len(row) == len(trace.x) and all(isinstance(v, (int, float)) and 1 <= v <= len(data['method_order']) for v in row) for row in z), name
                assert all(z[i] == list(rows[m]) for i, m in enumerate(order)), name
                fig.add_heatmap(x=list(trace.x), y=[SHORT_NAMES.get(m, m) for m in order],
                                z=z, coloraxis='coloraxis')
                low, high = 1, len(data['method_order'])
                title, colorscale = 'Mean rank', reverse
                fig.update_yaxes(autorange='reversed', tickfont_size=10.67,
                                 showline=False, ticks='', showgrid=False,
                                 tickmode='array', tickvals=list(fig.data[0].y),
                                 ticktext=list(fig.data[0].y))
                fig.update_xaxes(title_text='Evaluations', tickfont_size=10.67,
                                 tickvals=source.layout.xaxis.tickvals,
                                 ticktext=source.layout.xaxis.ticktext)
            else:
                fig.add_heatmap(x=list(trace.x), y=list(trace.y), z=trace.z,
                                coloraxis='coloraxis')
                peers = [go.Figure(data['charts'][p]) for p in data['scales'][name]]
                low = min(p.layout.coloraxis.cmin for p in peers)
                high = max(p.layout.coloraxis.cmax for p in peers)
                title = source.layout.coloraxis.colorbar.title.text
                colorscale = reverse if 'RMSE' in title or 'final' in title else sequential
                fig.update_xaxes(tickangle=-90, showline=False, ticks='',
                                 type='category', tickmode='array', tickvals=list(trace.x),
                                 ticktext=list(trace.x))
                fig.update_yaxes(autorange='reversed', showline=False, ticks='', showgrid=False)
                fig.update_layout(height=round((178 + 14 * len(trace.y)) * PX_PER_TEX_PT))
            fig.update_layout(coloraxis=dict(cmin=low, cmax=high, colorscale=colorscale, showscale=False))
            scales[name] = (low, high, colorscale, title)
        else:
            assert all(t.type == 'box' for t in source.data), name
            order = list(source.layout.xaxis.categoryarray)
            colors = dict(zip(data['method_order'], list(palette.values()) * 4))
            for trace in source.data:
                color = colors[trace.name]
                fill = 'rgba(' + ','.join(str(int(color[i:i + 2], 16)) for i in (1, 3, 5)) + ',0.25)'
                fig.add_box(x=trace.x, y=trace.y, name=trace.name,
                            line=dict(color=colors[trace.name], width=1),
                            fillcolor=fill,
                            marker=dict(color=colors[trace.name], size=2),
                            boxpoints='outliers', whiskerwidth=.5)
            fig.update_xaxes(categoryorder='array', categoryarray=order,
                             tickmode='array', tickvals=order, ticktext=order, tickangle=-90)
            fig.update_yaxes(title_text=source.layout.yaxis.title.text,
                             type=source.layout.yaxis.type)
            fig.update_layout(shapes=source.layout.shapes)
            for old, new in zip(source.data, fig.data):
                assert repr(list(old.y)) == repr(list(new.y)), name
                assert all(v is None or isinstance(v, (int, float)) for v in new.y), name
        figures[name] = fig
    for group in data['groups']:
        bars = [name for name in group if name.endswith('_colorbar.pdf')]
        if not bars:
            continue
        panels = [name for name in group if not name.endswith('_colorbar.pdf')]
        scale = scales[panels[0]]
        assert all(scales[name][:3] == scale[:3] for name in panels), group
        name = bars[0]
        assert len(bars) == 1
        if name in figures:
            continue
        low, high, colorscale, title = scale
        if len({scales[p][3] for p in panels}) > 1:
            title = 'Mean score'
        bar = go.Figure(layout=dict(template='thesis'))
        bar.add_scatter(x=[None, None], y=[None, None], mode='markers',
                        marker=dict(color=[low, high], cmin=low, cmax=high,
                                    colorscale=colorscale, showscale=True,
                                    colorbar=dict(orientation='h', x=.5, y=1,
                                                  xanchor='center', yanchor='top', len=.9,
                                                  thickness=10, outlinewidth=0, ypad=0,
                                                  tickfont_size=12,
                                                  title=dict(text=title, side='bottom', font_size=13.33))))
        if title == 'Mean rank':
            bar.data[0].marker.colorbar.update(tickmode='array', tickvals=[low, 10, 20, high])
        bar.update_layout(width=round(data['text_width_pt'] * PX_PER_TEX_PT),
                          height=round(60 * PX_PER_TEX_PT), showlegend=False,
                          margin=dict(l=10, r=10, t=2, b=8),
                          xaxis_visible=False, yaxis_visible=False)
        figures[name] = bar
    return figures


def main():
    data = json.loads(gzip.decompress((THESIS / 'scripts/dim_red_figure_data.json.gz').read_bytes()))
    figures = make_figures(data)
    chapter = (THESIS / 'Chapters/Chapter05_dim_red.tex').read_text()
    chapter = re.sub(r'(?m)(?<!\\)%.*', '', chapter)
    refs = set(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{figures/05/([^}]+)\}', chapter))
    assert figures.keys() == refs, (figures.keys() - refs, refs - figures.keys())
    target = THESIS / 'figures/05'
    with tempfile.TemporaryDirectory(prefix='.dim_red_', dir=THESIS) as temporary:
        paths = [Path(temporary) / f'{i}.pdf' for i in range(len(figures))]
        pio.write_images(list(figures.values()), paths,
                         width=[fig.layout.width for fig in figures.values()],
                         height=[fig.layout.height for fig in figures.values()])
        assert all(path.read_bytes().startswith(b'%PDF') for path in paths)
        for name, path in zip(figures, paths):
            dest = target / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            path.replace(dest)
        for path in target.rglob('*.pdf'):
            if str(path.relative_to(target)) not in refs:
                path.unlink()
    print(f'Replaced {len(figures)} chapter-5 PDFs in {target}')


if __name__ == '__main__':
    main()

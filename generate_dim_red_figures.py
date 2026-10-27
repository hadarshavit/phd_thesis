"""Regenerate Chapter 4 PDFs from the benchmark aggregate databases.

Run from any directory: python thesis/phd_thesis/generate_dim_red_figures.py
Requires the surrounding benchmark repository, thesis/template.py, and the
aggregate DuckDB files. Use --aggregation-dir to select another data location.
The script replaces only figures/04 PDFs.
"""
import argparse
from pathlib import Path
import re
import sys

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

THESIS = Path(__file__).resolve().parent
ROOT = THESIS.parents[1]
sys.path.insert(0, str(ROOT))
from analysev2 import bop, epm, common
sys.path.insert(0, str(THESIS.parent))
from template import TOL_MUTED, TEXT_WIDTH_PT

PALETTE = tuple(TOL_MUTED.values())
COLORS = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(common.METHODS)}
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['P052', 'Palatino', 'TeX Gyre Pagella'],
    'font.size': 7, 'axes.linewidth': .55, 'axes.edgecolor': '#606060',
    'axes.labelcolor': '#262626', 'text.color': '#262626',
    'xtick.color': '#606060', 'ytick.color': '#606060',
    'grid.color': '#E8E8E8', 'grid.linewidth': .4,
    'savefig.facecolor': 'white',
})

chapter = (THESIS / 'Chapters/Chapter05_dim_red.tex').read_text()
refs = {}
for width, body in re.findall(
    r'\\begin\{subfigure\}(?:\[[^]]+\])?\{([.0-9]+)\\textwidth\}(.+?)\\end\{subfigure\}', chapter, re.S
):
    match = re.search(r'figures/05/([^}]+)', body)
    if match:
        name = match.group(1).removesuffix('.pdf')
        if name in refs:
            assert refs[name] == float(width), f'{name} occurs at two placement widths'
        refs[name] = float(width)
refs['legend'] = 1.0
assert len(refs) == 88, f'Expected 88 chapter figures, found {len(refs)}'
assert set(refs.values()) == {0.49, 1.0}, set(refs.values())


def method_order(frame):
    column = 'method_name' if 'method_name' in frame else 'method'
    present = set(frame[column])
    order = [method for method in common.METHODS if method in present]
    return column, order + sorted(present - set(order))


def canvas(name, tall=False):
    width_pt = TEXT_WIDTH_PT * refs[name]
    height_pt = 242 if tall else 128
    fig, ax = plt.subplots(figsize=(width_pt / 72.27, height_pt / 72.27))
    fig.subplots_adjust(left=.12 if tall else .20, right=.98 if tall else .94, top=.96, bottom=.60 if tall else .26)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(length=2.5, width=.6, pad=2, labelsize=8)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    return fig, ax


def save(fig, name):
    path = THESIS / 'figures/04' / f'{name}.pdf'
    assert path.is_file(), f'Unexpected output: {path}'
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    labels = list(fig.texts)
    for ax in fig.axes:
        labels.extend(ax.get_xticklabels() + [ax.xaxis.label, ax.yaxis.label])
    for label in labels:
        if label.get_visible() and label.get_text():
            bounds = label.get_window_extent(renderer)
            assert bounds.x0 >= -1 and bounds.y0 >= -1 and bounds.x1 <= fig.bbox.width + 1 and bounds.y1 <= fig.bbox.height + 1, f'Clipped label in {name}: {label.get_text()}'
    fig.savefig(path, dpi=300)
    plt.close(fig)
    print(path.relative_to(THESIS), flush=True)


def box(frame, value, ylabel, name, log=False):
    assert not frame.empty, f'No data for {name}'
    column, order = method_order(frame)
    order = ([method for method in order if method in common.UNSUPERVISED_METHODS]
             + [method for method in order if method not in common.UNSUPERVISED_METHODS])
    fig, ax = canvas(name, tall=True)
    n_unsupervised = sum(method in common.UNSUPERVISED_METHODS for method in order)
    if 0 < n_unsupervised < len(order):
        ax.axvline(n_unsupervised + .5, color='#aaaaaa', linestyle='--', linewidth=.7)
    values = [frame.loc[frame[column] == method, value].dropna().to_numpy() for method in order]
    assert all(len(v) for v in values), f'Missing method data in {name}'
    artists = ax.boxplot(values, patch_artist=True, widths=.65,
                         flierprops={'marker': '.', 'markersize': 1.2, 'markeredgecolor': '#606060'},
                         medianprops={'color': '#262626', 'linewidth': .8},
                         whiskerprops={'linewidth': .7}, capprops={'linewidth': .7})
    for method, patch in zip(order, artists['boxes']):
        patch.set_facecolor(COLORS.get(method, '#999933'))
        patch.set_edgecolor(COLORS.get(method, '#999933'))
        patch.set_alpha(.55)
        patch.set_linewidth(.7)
    ax.set_xticks(range(1, len(order) + 1), [common.display_name(method) for method in order],
                  rotation=90, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9, labelpad=2)
    ax.tick_params(axis='x', length=1, pad=1)
    if log:
        ax.set_yscale('log')
    if value == 'normalized_rmse':
        ax.set_ylim(bottom=0)
    save(fig, name)


def line(frame, name):
    assert not frame.empty, f'No data for {name}'
    column, order = method_order(frame)
    fig, ax = canvas(name)
    fig.subplots_adjust(left=.20, right=.92, top=.96, bottom=.26)
    for i, method in enumerate(order):
        part = frame[frame[column] == method].sort_values('evaluation')
        ax.plot(part.evaluation, part.mean_rank,
                color=COLORS.get(method, '#999933'), linewidth=.95,
                linestyle=('-', '--', ':', '-.')[common.METHODS.index(method) // len(PALETTE) % 4],
                label=common.display_name(method))
    ax.set_xlabel('Evaluations', fontsize=9, labelpad=2)
    ax.set_ylabel('Mean rank', fontsize=9, labelpad=2)
    ax.set_ylim(.5, len(order) + .5)
    ax.margins(x=0)
    save(fig, name)


def legend():
    name = 'legend'
    width_pt = TEXT_WIDTH_PT * refs[name]
    fig = plt.figure(figsize=(width_pt / 72.27, 250 / 72.27))
    for i, method in enumerate(common.METHODS):
        col, row = divmod(i, 17)
        x = .02 + col * .49
        y = .965 - row * .054
        dash = ('-', '--', ':', '-.')[i // len(PALETTE) % 4]
        fig.add_artist(Line2D([x, x + .068], [y, y], transform=fig.transFigure,
                              color=COLORS[method], linestyle=dash, linewidth=1))
        fig.text(x + .083, y, common.display_name(method), fontsize=8, va='center')
    fig.text(.02, .025, 'Each rank-plot line uses the colour and dash shown beside its reducer name.',
             fontsize=8)
    save(fig, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aggregation-dir', type=Path, default=common.AGGREGATION_DIR)
    base = parser.parse_args().aggregation_dir
    with duckdb.connect(str(base / 'ml_cluster.duck'), read_only=True) as conn:
        frame = conn.execute('SELECT * FROM ml_cluster_results').fetchdf()
        frame = frame[frame.method != 'slipmap']
        for metric, label in [('homogeneity', 'Homogeneity'), ('completeness', 'Completeness')]:
            for k in (5, 10, 20, 40):
                box(frame[frame.n_components == k], metric, label, f'ml/agg_{k}_{metric}')
            for size, lo, hi in [('small', 0, 60), ('medium', 60, 200), ('large', 200, 1_000_000)]:
                box(frame[(frame.n_components == 5) & frame.n_features.between(lo, hi)],
                    metric, label, f'ml/agg_{size}_5_{metric}')
    with duckdb.connect(str(base / 'ml_pred.duck'), read_only=True) as conn:
        frame = conn.execute('SELECT * FROM ml_pred_results').fetchdf()
        frame = frame[frame.method != 'slipmap']
        for algo in ('rf', 'gb', 'mlp'):
            part = frame[frame.algo == algo]
            for k in (5, 10, 20, 40):
                box(part[part.n_components == k], 'acc', 'Accuracy', f'ml/agg_{k}_{algo}_acc')
            for size, lo, hi in [('small', 0, 60), ('medium', 60, 200), ('large', 200, 1_000_000)]:
                box(part[(part.n_components == 5) & part.n_features.between(lo, hi)],
                    'acc', 'Accuracy', f'ml/agg_{size}_5_{algo}_acc')
    with duckdb.connect(str(base / 'ml_time.duck'), read_only=True) as conn:
        frame = conn.execute('SELECT * FROM ml_time_results').fetchdf()
        for dataset in (9985, 9981):
            for column, suffix in [('fit_cpu_time', 'train_time'), ('transform_cpu_time', 'transform_time')]:
                part = frame[frame.task_id == dataset].copy()
                part['hours'] = part[column] / 3600
                box(part, 'hours', 'CPU hours', f'time/{dataset}_{suffix}', log=True)
    with duckdb.connect(str(base / 'epm.duck'), read_only=True) as conn:
        for sample, dimension, k in epm.SYNTHETIC_FIGURES:
            name = f'epm/agg_sample_red_inpt_{sample}_{dimension}_{k}'
            box(epm.synthetic_data(conn, sample, dimension, k), 'normalized_rmse', 'Normalised RMSE', name)
    with duckdb.connect(str(base / 'epm_real.duck'), read_only=True) as conn:
        for sample, k in epm.REAL_FIGURES:
            name = f'epm/real_agg_sample_red_dim_{sample}_{k}'
            box(epm.real_data(conn, sample, k), 'normalized_rmse', 'Normalised RMSE', name)
    with duckdb.connect(str(base / 'bop.duck'), read_only=True) as conn:
        for sample, dimension, k in bop.SYNTHETIC_FIGURES:
            line(bop.synthetic_data(conn, sample, dimension, k), f'bop/rank_{sample}_{dimension}_{k}')
    with duckdb.connect(str(base / 'bop_real.duck'), read_only=True) as conn:
        for sample, k in bop.REAL_FIGURES:
            line(bop.real_data(conn, sample, k), f'bop/rank_real_{sample}_{k}')
    legend()
    assert set(refs) == {str(p.relative_to(THESIS / 'figures/04').with_suffix(''))
                         for p in (THESIS / 'figures/04').rglob('*.pdf')}


if __name__ == '__main__':
    main()

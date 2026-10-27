"""Replace the 30 Chapter 10 PDFs at their natural LaTeX placement sizes.

Run: MPLCONFIGDIR=/tmp/asf-matplotlib python thesis/phd_thesis/generate_asf_figures.py
Requires matplotlib, numpy, pandas, and the surrounding paper repository.
Saved paper Plotly HTML supplies the exact plotted data (including corrected ZAP
results and measured HPOBench runtimes); ASlib pre-selection uses the result CSV.
Only existing Chapter 10 PDFs are overwritten. No experiments are rerun.
"""
import ast
import base64
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

THESIS = Path(__file__).resolve().parent
ROOT = THESIS.parents[1]
# Read the template constants without requiring Plotly for Matplotlib exports.
constants = {}
for node in ast.parse((THESIS.parent / 'template.py').read_text()).body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {'TOL_MUTED', 'TEXT_WIDTH_PT'}:
                constants[target.id] = ast.literal_eval(node.value)
PALETTE = list(constants['TOL_MUTED'].values())
METHODS = ['SBS', 'MarginalContribution_Forward', 'MarginalContribution_Backward',
           'BeamSearch_w5', 'RandomLocalSearch_r10', 'GeneticAlgorithm_large', 'OptimizeDE']
LABELS = ['SBS', 'MC-Fwd', 'MC-Bwd', 'Beam', 'RLS', 'GA', 'Opt-DE']
COLORS = dict(zip(LABELS, PALETTE))
SELECTORS = ['MultiClass', 'PerfModel', 'SimpleRank', 'PairwiseClf.', 'PairwiseReg.', 'ISAC', 'SNNAP', 'SUNNY', 'OSLLinear']
COLORS.update(zip(SELECTORS, PALETTE))
COLORS.update({'JointRank-10': PALETTE[5], 'JointRank-All': PALETTE[6], 'Cosine': PALETTE[7]})

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['P052', 'Palatino', 'TeX Gyre Pagella'],
    'font.size': 8, 'axes.labelsize': 9, 'axes.linewidth': .55,
    'axes.edgecolor': '#606060', 'text.color': '#262626',
    'axes.labelcolor': '#262626', 'xtick.color': '#606060', 'ytick.color': '#606060',
    'grid.color': '#E8E8E8', 'grid.linewidth': .4,
})


def array(value):
    if isinstance(value, dict) and 'bdata' in value:
        return np.frombuffer(base64.b64decode(value['bdata']), dtype=value['dtype'])
    return np.asarray(value)


def paper_data(name):
    html = (ROOT / 'paper_tmlr/figures/analysis' / f'{name}.html').read_text()
    call = html[html.rindex('Plotly.newPlot(') + len('Plotly.newPlot('):].lstrip()
    _, end = json.JSONDecoder().raw_decode(call)
    data, end_data = json.JSONDecoder().raw_decode(call[end:].lstrip().removeprefix(',').lstrip())
    assert data and all(trace['type'] in {'box', 'bar'} for trace in data), name
    return data


def canvas(fraction, height, small=False):
    fig, ax = plt.subplots(figsize=(constants['TEXT_WIDTH_PT'] * fraction / 72.27, height / 72.27))
    fig.subplots_adjust(left=.29 if small else (.24 if fraction < .6 else .14),
                        right=.97, bottom=.38 if small else .40, top=.96)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(length=2, width=.55, pad=2, labelsize=7 if small else 8)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    return fig, ax


def boxes(ax, groups):
    assert groups and all(len(values) and np.isfinite(values).all() for _, values in groups)
    artists = ax.boxplot([v for _, v in groups], patch_artist=True, widths=.65,
                        flierprops=dict(marker='.', markersize=1.5, markeredgewidth=.3),
                        medianprops=dict(color='#262626', linewidth=.7),
                        whiskerprops=dict(linewidth=.65), capprops=dict(linewidth=.65))
    for (label, _), patch, flier in zip(groups, artists['boxes'], artists['fliers']):
        color = COLORS.get(label, PALETTE[0])
        patch.set(facecolor=matplotlib.colors.to_rgba(color, .25), edgecolor=color, linewidth=.8)
        flier.set(markeredgecolor=color, markerfacecolor=color)
    ax.set_xticks(range(1, len(groups) + 1), [label for label, _ in groups], rotation=60, ha='right')
    ax.set_xlim(.4, len(groups) + .6)


def save(fig, path):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        ticks = [label for value, label in zip(ax.get_yticks(), ax.get_yticklabels()) if ax.get_ylim()[0] <= value <= ax.get_ylim()[1]]
        for label in [*ax.get_xticklabels(), *ticks, ax.xaxis.label, ax.yaxis.label, *ax.texts]:
            if label.get_visible() and label.get_text():
                b = label.get_window_extent(renderer)
                assert b.x0 >= -1 and b.y0 >= -1 and b.x1 <= fig.bbox.width + 1 and b.y1 <= fig.bbox.height + 1, (path.name, label.get_text(), b)
    assert path.is_file(), path
    fig.savefig(path)
    plt.close(fig)
    print(path.name, flush=True)


def main():
    chapter = (THESIS / 'Chapters/Chapter10_asf.tex').read_text()
    paths = [THESIS / name for name in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{(figures/10/[^}]+)\}', chapter)]
    assert len(paths) == len(set(paths)) == 30
    preselection = pd.read_csv(ROOT / 'results/pre_selector_benchmark.csv')
    for path in paths:
        name = path.stem
        small = name.startswith(('hpobench_', 'preselection_'))
        fraction = .32 if small else (.49 if name in {'zap_accuracy_box', 'zap_runtime_box'} else (.98 if name.startswith('selection_') else .4))
        height = 112 if small else (96 if name.startswith('selection_') else (178 if fraction == .49 else 145))
        fig, ax = canvas(fraction, height, small)
        if name.startswith('preselection_'):
            k = int(name.rsplit('k', 1)[1])
            frame = preselection[preselection.n_algorithms_selected == k]
            groups = [(label, frame.loc[frame.pre_selector == method, 'normalized_score'].dropna().to_numpy()) for method, label in zip(METHODS, LABELS)]
            boxes(ax, groups)
            ax.set_ylim((-.05, 1.05) if k <= 15 else (.55, 1.02))
            ax.set_ylabel('Normalised score', fontsize=7, labelpad=2)
        else:
            traces = paper_data(name)
            if name.startswith('selection_'):
                labels, values = list(traces[0]['x']), array(traces[0]['y'])
                assert len(labels) == len(values) and np.isfinite(values).all()
                ax.bar(labels, values, color=[COLORS[label] for label in labels], width=.7)
                ax.axhline(0, color='#606060', linewidth=.6)
                ax.axhline(100, color='#606060', linewidth=.6, linestyle=':')
                ax.set_ylim(-105, 115)
                ax.set_yticks([-100, 0, 100])
                ax.set_ylabel('Closed gap (%)')
                ax.tick_params(axis='x', labelsize=7)
                for i, value in enumerate(values):
                    ax.text(i, value + 4 if value >= 0 else value - 4, f'{value:.1f}',
                            va='bottom' if value >= 0 else 'top', ha='center', fontsize=7,
                            color='#262626')
            else:
                groups = [(trace['name'], array(trace['y'])) for trace in traces]
                if name == 'zap_preselection_vbs_box':
                    for i, (label, _) in enumerate(groups):
                        COLORS[label] = PALETTE[i]
                boxes(ax, groups)
                if 'runtime' in name:
                    ax.set_yscale('log')
                    ax.set_ylabel('Running time (s)' if small else 'Seconds per fold', fontsize=7 if small else 9, labelpad=2)
                    if small:
                        ax.set_ylim(10**-2.5, 10**3.5)
                        ax.set_yticks([.01, 1, 100, 1000])
                elif name.startswith('hpobench_'):
                    ax.set_ylim(-1, 1)
                    ax.set_ylabel('Normalised score', fontsize=7, labelpad=2)
                elif name == 'zap_accuracy_box':
                    ax.set_ylim(.65, 1.01)
                    ax.set_ylabel('Accuracy')
                else:
                    ax.set_ylim(.8, 1.01)
                    ax.set_ylabel('VBS accuracy')
                    ax.set_xlabel('Pre-selected algorithms', fontsize=8)
                    ax.tick_params(axis='x', rotation=0)
            if name.startswith('selection_'):
                ax.tick_params(axis='x', rotation=0)
                ax.set_xticks(range(len(labels)), labels, rotation=30, ha='right')
        save(fig, path)


if __name__ == '__main__':
    main()

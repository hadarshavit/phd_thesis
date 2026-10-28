"""Replace Chapter 9 figures with naturally sized, thesis-styled PDFs.

Run: MPLCONFIGDIR=/tmp/thesis-mpl python thesis/phd_thesis/generate_distribution_figures.py
Requires numpy, pandas, matplotlib, plotly (for thesis/template.py), and the
surrounding distribution repository. Reads results/results*_distnet_results.csv
and paper_aij/figures/explainability/*_data.pkl; never retrains models.
PDF widths match the chapter's 0.49-textwidth panels (336 TeX pt text width).
"""
from pathlib import Path
import lzma
import pickle
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, ScalarFormatter, LogLocator, SymmetricalLogLocator
import numpy as np
import pandas as pd

THESIS = Path(__file__).resolve().parent
ROOT = THESIS.parents[1]
sys.path.insert(0, str(THESIS.parent))
from template import TOL_MUTED, TEXT_WIDTH_PT

OUTPUT = THESIS / 'figures/09/figures'
CHAPTER = THESIS / 'Chapters/Chapter09_dis_explain.tex'
SCENARIOS = ['clasp_factoring', 'saps-CVVAR', 'spear_qcp', 'yalsat_qcp',
             'spear_swgcp', 'yalsat_swgcp', 'lpg-zeno']
OBSERVATIONS = [1, 2, 4, 8, 16, 32, 64, 100]
MODELS = {'xgb_dist': ('XGBoost', TOL_MUTED['indigo']),
          'distnet_default': ('DistNet', TOL_MUTED['rose'])}
METRICS = {'val_ks_d': 'KS distance', 'val_nllh': 'Neg. log-likelihood',
           'val_mass': 'Outside-range mass', 'val_crps': 'CRPS',
           'cpu_training_time': 'CPU time (s)'}
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['P052', 'Palatino', 'TeX Gyre Pagella'],
    'font.size': 8, 'axes.labelsize': 9, 'axes.linewidth': .7,
    'axes.edgecolor': '#606060', 'text.color': '#262626',
    'axes.labelcolor': '#262626', 'xtick.color': '#606060',
    'ytick.color': '#606060', 'grid.color': '#E8E8E8',
    'grid.linewidth': .5, 'pdf.fonttype': 3, 'savefig.facecolor': 'white',
})


def load_results():
    frames = []
    for scenario in SCENARIOS:
        frame = pd.read_csv(ROOT / 'results' / f'results{scenario}_distnet_results.csv')
        frame = frame[frame.model.isin(MODELS) & frame.dist.isin(['lognorm', 'invgauss'])
                      & frame.all_train_instances.eq(True)].copy()
        key = ['fold', 'model', 'dist', 'num_train_samples']
        # Explanation reruns append fold 0; keep the first benchmark run once.
        frame = frame.drop_duplicates(key, keep='first')
        assert len(frame) == 320, (scenario, len(frame))
        assert set(frame.scenario) == {scenario}
        assert set(frame.num_train_samples) == set(OBSERVATIONS)
        assert frame.groupby(['model', 'dist', 'num_train_samples']).fold.nunique().eq(10).all()
        assert np.isfinite(frame[[m for m in METRICS if m != 'val_nllh']].to_numpy()).all()
        assert frame.val_ks_d.between(0, 1).all()
        assert frame.val_mass.between(0, 1).all()
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def canvas(height=112, left=.32):
    fig, ax = plt.subplots(figsize=(.49 * TEXT_WIDTH_PT / 72.27, height / 72.27))
    fig.subplots_adjust(left=left, right=.97, top=.91, bottom=.29)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(length=2.5, width=.7, pad=2)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True)
    return fig, ax


def save(fig, path):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        labels = [label for loc, label in zip(ax.get_xticks(), ax.get_xticklabels())
                  if min(ax.get_xlim()) <= loc <= max(ax.get_xlim())]
        labels += [label for loc, label in zip(ax.get_yticks(), ax.get_yticklabels())
                   if min(ax.get_ylim()) <= loc <= max(ax.get_ylim())]
        labels += [
            ax.xaxis.label, ax.yaxis.label, ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()]
        for label in labels:
            if label.get_visible() and label.get_text():
                b = label.get_window_extent(renderer)
                assert b.x0 >= -1 and b.y0 >= -1 and b.x1 <= fig.bbox.width + 1 and b.y1 <= fig.bbox.height + 1, (path.name, label.get_text(), b)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)  # Preserve the physical canvas; tight cropping changes natural size.
    plt.close(fig)
    print(path.relative_to(THESIS), flush=True)


def performance(frame, scenario, dist, metric):
    part = frame[(frame.scenario == scenario) & (frame.dist == dist)]
    fig, ax = canvas()
    for i, (model, (_, color)) in enumerate(MODELS.items()):
        values = [part.loc[(part.model == model) & (part.num_train_samples == n), metric].to_numpy()
                  for n in OBSERVATIONS]
        assert all(len(v) == 10 for v in values)
        if metric == 'val_nllh':
            for j, v in enumerate(values):
                n = np.isfinite(v).sum()
                assert n > 0, (scenario, model, OBSERVATIONS[j])
                if n < 10:
                    ax.text(j, 1.02, str(n), transform=ax.get_xaxis_transform(),
                            color=color, ha='center', fontsize=6)
            values = [v[np.isfinite(v)] for v in values]
        ax.boxplot(values, positions=np.arange(8) + (i - .5) * .36,
            widths=.30, patch_artist=True, manage_ticks=False,
            boxprops=dict(facecolor=color, edgecolor=color, alpha=.4, linewidth=.7,
                          hatch='' if i == 0 else '///'),
            medianprops=dict(color=color, linewidth=1),
            whiskerprops=dict(color=color, linewidth=.6), capprops=dict(color=color, linewidth=.6),
            flierprops=dict(marker='.' if i == 0 else '+', markersize=1.8,
                            markeredgecolor=color, markeredgewidth=.5))
    ax.set_xticks(range(8), [str(n) for n in OBSERVATIONS], fontsize=7)
    ax.set_xlim(-.65, 7.65)
    ax.set_xlabel('Observations per instance', labelpad=3)
    ax.set_ylabel(METRICS[metric], labelpad=3)
    if metric == 'val_ks_d':
        ax.set_ylim(0, 1 if dist == 'invgauss' else .5)
        ax.yaxis.set_major_locator(MaxNLocator(4))
    elif metric == 'val_nllh':
        # NLL can be negative; retain all finite scores and count non-finite folds.
        ax.set_yscale('symlog', linthresh=1)
        finite = part.loc[np.isfinite(part[metric]), metric]
        ax.set_ylim(min(0, finite.min() * 1.15), max(1, finite.max() * 1.5))
        locator = SymmetricalLogLocator(base=10, linthresh=1)
        locator.set_params(numticks=4)
        ax.yaxis.set_major_locator(locator)
        if finite.max() > 1e4:
            exponent = int(np.ceil(np.log10(finite.max())))
            step = max(1, int(np.ceil(exponent / 3)))
            ax.set_yticks([0] + [10. ** e for e in range(step, exponent + 1, step)])
    elif metric == 'val_mass':
        # Exact zero is meaningful and must remain visible.
        ax.set_yscale('symlog', linthresh=1e-4)
        ax.set_ylim(bottom=0)
        locator = SymmetricalLogLocator(base=10, linthresh=1e-4)
        locator.set_params(numticks=4)
        ax.yaxis.set_major_locator(locator)
    else:
        assert (part[metric] > 0).all(), (scenario, metric)
        ax.set_yscale('log')
        ax.yaxis.set_major_locator(LogLocator(numticks=4))
    ax.minorticks_off()
    save(fig, OUTPUT / 'performances' / f'{scenario}_{dist}_{metric}_vs_obs.pdf')


FEATURE_LABELS = {
    'VCG-VAR-coeff-variation': 'VCG variable\ndegree CV',
    'saps_FirstLocalMinRatio_Mean': 'SAPS first minimum\nratio',
    'saps_FirstLocalMinRatio_CoeffVariance': 'SAPS first minimum\nratio CV',
    'saps_FirstLocalMinStep_Q.10': 'SAPS early first\nminimum step',
    'saps_FirstLocalMinStep_CoeffVariance': 'SAPS first minimum\nstep CV',
    'gsat_FirstLocalMinRatio_CoeffVariance': 'GSAT first minimum\nratio CV',
    'gsat_FirstLocalMinStep_CoeffVariance': 'GSAT first minimum\nstep CV',
    'cluster-coeff-entropy': 'cluster. coeff\nentropy',
    'HORNY-VAR-min': 'minimum Horn\nvariables',
    'VG-min': 'minimum VG\ndegree',
    'vars-reduced-depth-16': 'DPLL remaining var.\ndepth 16',
    'DIAMETER-entropy': 'Diam.\nentropy',
    'lpTIME': 'LP time',
    'ls-gsat-featuretime': 'GSAT probe\ntime',
    'CG-featuretime': 'CG time',
    'MpSAT-HORNY-VAR-entropy': 'SAT: Horn variable\nentropy',
    'MpSAT-HORNY-VAR-mean': 'SAT: Average Horn\nvariables',
    'MpSAT-SP-bias-q25': 'SAT: SP bias\nlower quartile',
    'MpSAT-SP-bias-q10': 'SAT: SP bias\n10th percentile',
    'MpSAT-SP-bias-coeff-variation': 'SAT: SP bias\nCV',
    'MpSAT-vars-clauses-ratio': 'SAT: variable-clause\nratio',
    'MpSAT-VCG-VAR-min': 'SAT: minimum VCG\nvariables',
    'sasCenamorDTGTotalNumberOfVertices': 'transition graph\nvertices',
    'sasPreprocessingNumFacts': 'preprocessed\nfacts',
    'meta-time-torchlight': 'Torchlight\ntime',
    'meta-time-MpSAT-CG-featuretime': 'SAT: Clause graph\ntime',
    'MpSAT-nclausesOrig': 'SAT: original\nclauses',
    'sasCenamorCGMeanIncomingEdgeWeightSumPerHighLevelVariable': 'Causal graph incoming\nweight per variable',
}

def feature_label(name):
    labels = FEATURE_LABELS
    assert name in labels, f'Add a readable label for {name}'
    return labels[name].replace('<br>', '\n')


def explanation(path):
    match = re.fullmatch(r'(.+)_(permutation_importance|ice_feature(\d+))\.pdf', path.name)
    prefix, kind, feature = match.groups()
    suffix = 'permutation_importance' if kind == 'permutation_importance' else 'ice'
    source = ROOT / 'paper_aij/figures/explainability' / f'{prefix}_{suffix}_data.pkl'
    with lzma.open(source, 'rb') as stream:
        data = pickle.load(stream)  # Trusted local experiment output only.
    prop = data['property_name']
    if suffix == 'permutation_importance':
        fig, ax = canvas(height=132, left=.55)
        fig.subplots_adjust(bottom=.23, top=.92)
        indices = data['importances_mean'].argsort()[::-1][:5]
        values = data['importances_mean'][indices]
        assert np.isfinite(values).all()
        ax.barh(range(5), values, color=TOL_MUTED['indigo'], height=.65)
        ax.set_yticks(range(5), [feature_label(data['feature_names'][i]) for i in indices], fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(left=0)
        ax.set_xlabel('Importance', labelpad=3)
        ax.xaxis.set_major_locator(MaxNLocator(2))
        formatter = ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((-2, 3))
        ax.xaxis.set_major_formatter(formatter)
        fig.canvas.draw()
        offset = ax.xaxis.get_offset_text()
        ax.text(0, 1.02, offset.get_text(), transform=ax.transAxes, fontsize=8)
        offset.set_visible(False)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True)
    else:
        fig, ax = canvas(height=132, left=.28)
        fig.subplots_adjust(bottom=.36, top=.91)
        entry = data['ice_data'][int(feature)]
        grid = entry['grid_values']
        curves = entry['ice_curves'] - entry['ice_curves'][:, :1]
        pdp = entry['pdp_curve'] - entry['pdp_curve'][0]
        assert curves.shape[1] == len(grid) == len(pdp)
        assert np.isfinite(curves).all() and np.isfinite(pdp).all()
        assert np.allclose(curves[:, 0], 0) and pdp[0] == 0
        sample = np.random.default_rng(42).choice(len(curves), min(100, len(curves)), replace=False)
        ax.plot(grid, curves[sample].T, color=TOL_MUTED['teal'], alpha=.25, linewidth=.5)
        ax.plot(grid, pdp, color=TOL_MUTED['wine'], linewidth=1.4, linestyle='--')
        ax.axhline(0, color='#606060', linewidth=.5, linestyle=':')
        ax.set_xlabel(feature_label(entry['feature_name']), labelpad=3)
        ax.set_ylabel('Change in ' + ('IQR' if prop == 'iqr' else prop), labelpad=3)
        ax.xaxis.set_major_locator(MaxNLocator(3))
        ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.ticklabel_format(style='sci', scilimits=(-2, 3), useMathText=True)
    save(fig, path)


def main():
    frame = load_results()
    refs = re.findall(r'\\includegraphics\{(figures/09/[^}]+)\}', CHAPTER.read_text())
    assert len(set(refs)) == 65, len(set(refs))
    refs = list(dict.fromkeys(refs))
    for ref in refs:
        path = THESIS / ref
        if '/explainability/' in ref:
            explanation(path)
        elif path.stem == 'legend':
            fig = plt.figure(figsize=(TEXT_WIDTH_PT / 72.27, 18 / 72.27))
            handles = [Patch(facecolor=c, edgecolor=c, alpha=.5,
                             hatch='' if i == 0 else '///', label=n)
                       for i, (n, c) in enumerate(MODELS.values())]
            fig.legend(handles=handles, loc='center', ncol=2, frameon=False, fontsize=9)
            save(fig, path)
        else:
            scenario = next(s for s in SCENARIOS if path.name.startswith(s + '_'))
            dist = 'invgauss' if '_invgauss_' in path.name else 'lognorm'
            metric = next(m for m in METRICS if path.name.endswith(m + '_vs_obs.pdf'))
            performance(frame, scenario, dist, metric)
    actual = set(OUTPUT.rglob('*.pdf'))
    assert actual == {THESIS / r for r in refs}, 'Unreferenced or missing chapter PDFs'
    # Keep the evidence used by the marked discussion directly reproducible.
    full = frame[frame.num_train_samples == 100].copy()
    full['val_nllh'] = full.val_nllh.where(np.isfinite(full.val_nllh))
    print('\nMedian values at 100 observations (finite NLL scores only):')
    print(full.groupby(['scenario', 'dist', 'model'])[list(METRICS)].median().to_string())


if __name__ == '__main__':
    main()

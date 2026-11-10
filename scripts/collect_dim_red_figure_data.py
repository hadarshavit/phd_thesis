"""Refresh the chapter-5 chart snapshot from the benchmark checkout.

Run with the benchmark Python environment (DuckDB, pandas, Plotly and its
existing dependencies): python scripts/collect_dim_red_figure_data.py
Only the snapshot beside this script is written; databases are read-only.
"""
import argparse
import base64
import gzip
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
THESIS = Path(__file__).resolve().parents[1]


def chapter_groups():
    source = (THESIS / 'Chapters/Chapter05_dim_red.tex').read_text()
    source = re.sub(r'(?m)(?<!\\)%.*', '', source)
    groups = []
    for block in re.findall(r'\\begin\{figure\}.*?\\end\{figure\}', source, re.S):
        paths = re.findall(r'\\includegraphics(?:\[[^]]*\])?\{figures/(?:05/)?([^}]+)\}', block)
        if paths:
            groups.append(paths)
    return groups


def plain_arrays(value):
    """Plotly 6 encodes NumPy arrays as binary dictionaries, including matrices."""
    import numpy as np
    if isinstance(value, dict):
        if 'bdata' in value and 'dtype' in value:
            array = np.frombuffer(base64.b64decode(value['bdata']), dtype=value['dtype'])
            if 'shape' in value:
                array = array.reshape(tuple(int(n) for n in value['shape'].split(',')))
            return array.tolist()
        return {key: plain_arrays(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_arrays(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark-dir', type=Path, default=THESIS.parents[1])
    parser.add_argument('--aggregation-dir', type=Path,
                        default=Path('/hpcwork/p0027894/benchmark_dim_red/aggregation'))
    args = parser.parse_args()
    root = args.benchmark_dir.resolve()
    sys.path.insert(0, str(root))
    from analysev2 import common
    from plotly.utils import PlotlyJSONEncoder

    spec = importlib.util.spec_from_file_location('thesis_theme', root / 'thesis/template.py')
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)
    groups = chapter_groups()
    needed = {p for group in groups for p in group if not p.endswith('_colorbar.pdf')}
    charts = {}

    def capture(fig, path):
        name = str(Path(path).relative_to(common.FIGURE_DIR))
        if name in needed:
            assert name not in charts, name
            charts[name] = fig.to_plotly_json()

    common.write_figure = capture
    common.write_legend = lambda path: None
    argv = sys.argv
    try:
        sys.argv = [argv[0], '--aggregation-dir', str(args.aggregation_dir)]
        for name in ('ml_cluster', 'ml_pred', 'epm', 'bop', 'ml_time',
                     'ml_cluster_tuning', 'ml_pred_tuning', 'epm_tuning',
                     'bop_tuning', 'bop_initial_sample'):
            importlib.import_module(f'analysev2.{name}').main()
            print(f'Collected {name}', flush=True)
    finally:
        sys.argv = argv
    assert charts.keys() == needed, needed - charts.keys()
    paper_groups = json.loads((root / 'analysev2/paper_panels.json').read_text())
    scales = {}
    for group in paper_groups:
        for panel in group['panels']:
            name = panel.removeprefix('figures/')
            if name in needed:
                scales[name] = [p.removeprefix('figures/') for p in group.get('scale_panels', group['panels'])]
    assert needed <= scales.keys()
    snapshot = dict(charts=charts, groups=groups, scales=scales,
                    method_order=[common.display_name(m) for m in common.METHOD_ORDER],
                    palette=theme.TOL_MUTED, template=theme.make_template().to_plotly_json(),
                    text_width_pt=theme.TEXT_WIDTH_PT,
                    provenance='Unmodified analysev2 queries; read-only aggregate DuckDB databases. '
                               'Box observations, heatmap means and BO mean ranks are preserved.')
    path = Path(__file__).with_name('dim_red_figure_data.json.gz')
    # A deterministic compressed snapshot makes regeneration independent of HPC data access.
    path.write_bytes(gzip.compress(json.dumps(plain_arrays(snapshot), cls=PlotlyJSONEncoder,
                                             separators=(',', ':')).encode(), mtime=0))
    print(f'Saved {len(charts)} panels: {path}', flush=True)


if __name__ == '__main__':
    main()

"""Refresh the chart-only snapshot from the original experiment checkout.

Run with that checkout as the argument. Requires pandas, numpy, scikit-learn,
PyYAML, liac-arff and Plotly. Imports the original AutoFolio evaluator unchanged.
Only writes satzilla_figure_data.json beside this script.
"""
import base64
import importlib.util
import json
import re
from pathlib import Path
import sys
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder


def notebook_figures(path, cell):
    cells = json.loads(path.read_text())["cells"]
    return [o["data"]["application/vnd.plotly.v1+json"]
            for o in cells[cell].get("outputs", [])
            if "application/vnd.plotly.v1+json" in o.get("data", {})]



def solver_histograms(root, charts, chapter):
    """Recover the original per-solver bins from stored outer-fold predictions."""
    from sklearn.exceptions import InconsistentVersionWarning
    names = re.findall(r"acc_rt_pred_sc(202[23])_both_([^}]+)\.pdf", chapter)
    assert len(names) == len(set(names)) == 92
    edges = [0, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1000]
    for year in ("2022", "2023"):
        folds = np.load(root / f"data/sc{year}_folds.npy", allow_pickle=True)
        totals = [np.zeros(14, dtype=int), np.zeros(14, dtype=int)]
        frames = [pd.read_csv(root / f"data/sc{year}{ending}.csv", index_col=0)
                  for ending in ("", "_old")]
        for _, solver in [pair for pair in names if pair[0] == year]:
            traces = []
            for i, ending in enumerate(("", "_old")):
                errors = []
                for fold, (_, test) in enumerate(folds):
                    # Only saved predictions are used; no estimator is run or retrained.
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", InconsistentVersionWarning)
                        model, predictions, _ = np.load(root / f"rts_results/sc{year}{ending}_{solver}_{fold}.npy", allow_pickle=True)
                    truth = np.log10(frames[i][solver].to_numpy()[test])
                    assert predictions.shape == truth.shape
                    errors.extend(np.abs((truth - predictions) / truth) * 100)
                    del model
                hist, _ = np.histogram(errors, bins=edges)
                totals[i] += hist
                traces.append(dict(type="bar", name=ending, x=[str(n) for n in edges[1:]], y=hist.tolist()))
            charts[f"acc_rt_pred_sc{year}_both_{solver}"] = traces
            print(f"Collected {year}: {solver}", flush=True)
        for total, original in zip(totals, charts[f"acc_rt_pred_sc{year}_both"]):
            assert total.tolist() == original["y"], "Per-solver counts must reconcile to the paper's aggregate histogram"


def main():
    root = Path(sys.argv[1]).resolve()
    spec = importlib.util.spec_from_file_location("thesis_template", root / "thesis/template.py")
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)
    charts = {}
    groups = ["Pre", "Basic", "KLB", "CG", "cl", "ls-gsat", "ls-saps",
              "sp", "DIAMETER", "lobjois", "unit"]
    for year in (2022, 2023):
        frames = []
        for ending in ("", "_old"):
            df = pd.read_csv(root / f"final_features/features_sc{year}_{ending}.csv", index_col=0)
            df.loc[df.LP_OBJ.isna(), "lpTIME"] = 5000
            df = df.fillna(5000)
            df[df > 180] = 5000
            for upstream, downstream in [("Pre", ["Basic", "KLB", "CG"]),
                                         ("Basic", ["KLB", "CG"]), ("KLB", ["CG"])]:
                df.loc[df[f"{upstream}-featuretime"] > 180,
                       [f"{g}-featuretime" for g in downstream]] = 5000
            assert len(df) == 400
            frames.append(df)
        for column in [f"{g}-featuretime" for g in groups] + ["lpTIME"]:
            values = pd.DataFrame({"SATzilla 2024": frames[0][column],
                                   "SATzilla 2012": frames[1][column]})
            charts[f"ecdf_sc{year}_{column}"] = px.ecdf(values, x=values.columns).to_plotly_json()["data"]
    notebook = root / "analyse_preds.ipynb"
    for year, cells in [(2022, (11, 28)), (2023, (12, 29))]:
        for name, cell in zip(("rts_bar", "sat_bar"), cells):
            charts[f"{name}_{year}"] = notebook_figures(notebook, cell)[0]["data"]
    for year, fig in zip((2022, 2023), notebook_figures(notebook, 32)):
        charts[f"acc_rt_pred_sc{year}_both"] = fig["data"]
    af_notebook = root / "aslib/AutoFolio/autofolio/autofolio_ecdf.ipynb"
    charts["as_bar_2023"] = notebook_figures(af_notebook, 13)[0]["data"]

    sys.path.insert(0, str(root / "aslib/AutoFolio/autofolio"))
    from aslib_scenario import ASlibScenario
    from evaluate_autofolio import get_autofolio_scehdules, evaluate_schedule
    gaps = {}
    for year in (2022, 2023):
        values = {}
        for ending, name in [("", "SATzilla 2024"), ("-OLD", "SATzilla 2012")]:
            scenario = ASlibScenario()
            scenario.read_scenario(str(root / f"aslib/SAT{year}-MAIN{ending}"))
            times, sbs, vbs = {}, {}, {}
            for fold in range(1, 11):
                schedules, groups = get_autofolio_scehdules(scenario, "/storage/work/shavit/out_aspeed_8h_180", fold)
                test, train = scenario.get_split(fold)
                t, s, v = evaluate_schedule(test, train, schedules, True, groups)
                times.update(t); sbs.update(s); vbs.update(v)
            assert len(times) == len(sbs) == len(vbs) == 400
            values[name] = list(times.values())
            gaps[year, name] = (sum(sbs.values()) - sum(times.values())) / (sum(sbs.values()) - sum(vbs.values()))
        # The paper's notebook uses the baselines from the old-feature scenario.
        values["VBS"] = list(vbs.values())
        values["SBS"] = list(sbs.values())
        charts[f"ecds_af_{year}"] = px.ecdf(pd.DataFrame(values), x=list(values)).to_plotly_json()["data"]
    for trace in charts["as_bar_2023"]:
        name = f"SATzilla {trace['name']}"
        assert np.allclose(trace["y"], [gaps[year, name] for year in (2022, 2023)])
    for traces in charts.values():
        for trace in traces:
            for axis in ("x", "y"):
                values = trace[axis]
                if isinstance(values, dict) and "bdata" in values:
                    trace[axis] = np.frombuffer(base64.b64decode(values["bdata"]), dtype=values["dtype"]).tolist()
    chapter = (root / "thesis/phd_thesis/Chapters/Chapter04_rev_satzilla.tex").read_text()
    solver_histograms(root, charts, chapter)
    assert len(charts) == 125
    output = {"provenance": "Feature times: final_features CSVs and analyse_times.ipynb timeout rules. Appendix histogram bins: stored rts_results predictions and data CSVs, reconciled to aggregate histogram counts. Prediction bars and error bins: saved Plotly data in analyse_preds.ipynb (cells 11,12,28,29,32). Selection: original ASlib evaluator, ten folds of /storage/work/shavit/out_aspeed_8h_180; gap values checked against autofolio_ecdf.ipynb cell 13. Values and original metric definitions are preserved, including sqrt(accuracy) in the saved satisfiability bars and relative errors of log10 runtimes.",
              "template": theme.make_template().to_plotly_json(), "charts": charts}
    path = Path(__file__).with_name("satzilla_figure_data.json")
    path.write_text(json.dumps(output, cls=PlotlyJSONEncoder, separators=(",", ":")) + "\n")
    print(f"Collected {len(charts)} charts: {path}")


if __name__ == "__main__":
    main()

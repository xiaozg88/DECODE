# -*- coding: utf-8 -*-
"""SHAP feature attribution for the paper's direction law."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.model_selection import LeaveOneGroupOut

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EXP = ROOT / "output/experiments"
OUT = ROOT / "explorations/output"
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261004


def load():
    nd = pd.read_csv(EXP / "direction_law_v2/nested_decomposition.csv")
    cs = pd.read_csv(EXP / "experiment_29_global_expansion"
                     / "country_sample_and_input_availability.csv")[["iso3", "income_group", "region"]]
    nc = pd.read_csv(EXP / "network_completeness/network_completeness_by_country.csv")[
        ["iso3", "local_share_pct", "urban_share_pct", "population_density_per_km2",
         "planet_known_share_pct", "direction_residual_pp", "benchmark_gap_pp"]]
    grip = pd.read_csv(EXP / "grip4_completeness/grip4_vs_network_density.csv")[
        ["iso3", "grip_all_mean_density"]]
    grip["grip4_density_km_km2"] = grip["grip_all_mean_density"] / 1000.0

    df = nd.merge(cs, on="iso3", how="left").merge(nc, on="iso3", how="left").merge(grip, on="iso3", how="left")
    df["income_ord"] = df["income_group"].map({"low": 0, "lower-middle": 1, "upper-middle": 2})

    base_features = ["arterial_coverage", "arterial_length_share_pct", "road_density_km_per_km2",
                     "local_share_pct", "urban_share_pct", "population_density_per_km2",
                     "planet_known_share_pct", "grip4_density_km_km2", "income_ord"]
    region_dummies = pd.get_dummies(df["region"], prefix="region")
    X = pd.concat([df[base_features].reset_index(drop=True), region_dummies.reset_index(drop=True)], axis=1)
    return df, X, df["delta_edges"], df["delta_published"]


def fit_and_explain(X, y, groups, outcome_name, lines, rows):
    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
        colsample_bytree=0.9, reg_lambda=1.0, reg_alpha=0.1,
        random_state=SEED, n_jobs=1)
    model.fit(X, y)

    logo = LeaveOneGroupOut()
    pred = np.empty_like(y, dtype=float)
    y_np = y.to_numpy()
    for tr, te in logo.split(X, y_np, groups):
        m = xgb.XGBRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
            colsample_bytree=0.9, reg_lambda=1.0, reg_alpha=0.1,
            random_state=SEED, n_jobs=1)
        m.fit(X.iloc[tr], y_np[tr])
        pred[te] = m.predict(X.iloc[te])
    ss_res = float(np.sum((y_np - pred) ** 2))
    ss_tot = float(np.sum((y_np - y_np.mean()) ** 2))
    r2_oos = 1 - ss_res / ss_tot
    mae = float(np.mean(np.abs(y_np - pred)))

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    base = float(explainer.expected_value)
    imp = pd.DataFrame({"feature": X.columns, "mean_abs_shap": np.abs(sv).mean(axis=0)})
    imp = imp.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    lines.append(f"===== SHAP: {outcome_name} (n={len(y)}) =====")
    lines.append(f"LOCO out-of-sample R2={r2_oos:.3f} MAE={mae:.2f} pp  base={base:+.2f}")
    lines.append("top-8 |SHAP| importance and direction:")
    for r in imp.head(8).itertuples():
        col = np.asarray(X[r.feature], dtype=float)
        sh = np.asarray(sv[:, X.columns.get_loc(r.feature)], dtype=float)
        direction = "positive" if np.corrcoef(col, sh)[0, 1] > 0 else "negative"
        lines.append(f"  {r.feature:<28s} {r.mean_abs_shap:8.3f}  ({direction})")
        rows.append({"outcome": outcome_name, "feature": r.feature,
                     "mean_abs_shap": float(r.mean_abs_shap)})
    lines.append("")

    top = imp.head(10)["feature"].tolist()
    idx = [list(X.columns).index(c) for c in top]
    shap.summary_plot(sv[:, idx], X[top], show=False, max_display=10)
    plt.tight_layout()
    plt.savefig(OUT / f"d22_shap_{outcome_name}.png", dpi=200, bbox_inches="tight")
    plt.close()
    return sv, imp, explainer


def main():
    df, X, y_edges, y_published = load()
    groups = df["iso3"].to_numpy()
    lines = []
    rows = []
    sv_e, imp_e, exp_e = fit_and_explain(X, y_edges, groups, "delta_edges", lines, rows)
    sv_p, imp_p, exp_p = fit_and_explain(X, y_published, groups, "delta_published", lines, rows)

    pd.DataFrame(rows).to_csv(OUT / "d22_shap_importance.csv", index=False, encoding="utf-8-sig")
    (OUT / "d22_shap_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

"""LightGBM model with an honest walk-forward backtest."""
import lightgbm as lgb
import numpy as np
import pandas as pd

from features import TECH_COLS, cs_rank

PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=100,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
              verbose=-1)


def _prep(panel):
    X = cs_rank(panel, TECH_COLS)
    y = panel.groupby(level="date")["target"].rank(pct=True)  # predict ranking, not price
    return X, y


def train_and_predict(panel, horizon, test_days):
    """Returns (latest predictions Series, backtest stats dict)."""
    panel = panel.dropna(subset=TECH_COLS)
    X, y = _prep(panel)
    dates = panel.index.get_level_values("date").unique().sort_values()
    labeled = panel["target"].notna()

    # --- Walk-forward backtest: train on the past, test on the last ~6 months ---
    test_start = dates[-(test_days + horizon)]
    train_end = dates[dates.get_loc(test_start) - horizon]  # gap avoids look-ahead leakage
    d = panel.index.get_level_values("date")
    tr = labeled & (d <= train_end)
    te = labeled & (d >= test_start)
    tr_idx = tr & (d.isin(dates[::5]))  # sample every 5th day: faster, less overlap

    stats = {}
    if tr_idx.sum() > 500 and te.sum() > 100:
        m = lgb.LGBMRegressor(**PARAMS).fit(X[tr_idx], y[tr_idx])
        res = pd.DataFrame({"pred": m.predict(X[te]), "ret": panel.loc[te, "target"]})
        g = res.groupby(level="date")
        ic = g.apply(lambda x: x["pred"].corr(x["ret"], method="spearman"))

        def spread(x):
            q = x["pred"].rank(pct=True)
            return x.loc[q >= 0.8, "ret"].mean() - x.loc[q <= 0.2, "ret"].mean()

        def hit(x):
            q = x["pred"].rank(pct=True)
            return (x.loc[q >= 0.8, "ret"] > 0).mean()

        stats = {
            "test_from": str(test_start.date()),
            "ic_mean": round(float(ic.mean()), 3),
            "ic_positive_days": round(float((ic > 0).mean()), 2),
            "top_minus_bottom": round(float(g.apply(spread).mean()), 4),
            "top_hit_rate": round(float(g.apply(hit).mean()), 2),
        }

    # --- Final model on all labeled history, predict the latest date ---
    all_idx = labeled & d.isin(dates[::5])
    m = lgb.LGBMRegressor(**PARAMS).fit(X[all_idx], y[all_idx])
    last = dates[-1]
    Xl = X.xs(last, level="date")
    pred = pd.Series(m.predict(Xl), index=Xl.index).rank(pct=True)
    stats["as_of"] = str(last.date())
    return pred, stats

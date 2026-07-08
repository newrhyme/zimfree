"""Train LightGBM regressor for hourly ridership (pax).

features: station_code(cat), line(cat), dow(cat), io_type(cat), hour, month, is_holiday
split: months 1-10 train / 11-12 valid, metric MAE -> models/metrics.json
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ml  # noqa: E402
from app.schema import DB_PATH, KR_HOLIDAYS_2025  # noqa: E402

CAT_COLS = ["station_code", "line", "dow", "io_type"]
NUM_COLS = ["hour", "month", "is_holiday"]
FEATURES = CAT_COLS + NUM_COLS
TARGET = "pax"


def load() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT r.station_code, r.date, r.dow, r.io_type, r.hour, r.pax, s.line
        FROM ridership_hourly r JOIN stations s ON r.station_code = s.station_code
        """,
        conn,
    )
    conn.close()
    df["month"] = df["date"].str.slice(5, 7).astype(int)
    df["is_holiday"] = df["date"].isin(KR_HOLIDAYS_2025).astype(int)
    return df


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("app.db missing; run preprocess.py first")
    print("[congestion] loading...")
    df = load()
    cat_maps = ml.build_category_maps(df, CAT_COLS)
    enc = ml.encode(df[FEATURES], cat_maps)

    train_mask = df["month"] <= 10
    valid_mask = df["month"] >= 11
    dtrain = lgb.Dataset(
        enc[train_mask], label=df.loc[train_mask, TARGET],
        categorical_feature=CAT_COLS,
    )
    dvalid = lgb.Dataset(
        enc[valid_mask], label=df.loc[valid_mask, TARGET],
        categorical_feature=CAT_COLS, reference=dtrain,
    )
    params = {
        "objective": "regression_l1",
        "metric": "l1",
        "num_leaves": 128,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }
    print(f"[congestion] train={train_mask.sum()} valid={valid_mask.sum()}")
    booster = lgb.train(
        params, dtrain, num_boost_round=400, valid_sets=[dvalid],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(0)],
    )
    pred = booster.predict(enc[valid_mask])
    mae = float(mean_absolute_error(df.loc[valid_mask, TARGET], pred))
    print(f"[congestion] valid MAE = {mae:.2f}")

    booster.save_model(str(ml.CONGESTION_MODEL))
    ml.save_meta(ml.CONGESTION_META, {
        "feature_order": FEATURES, "cat_cols": CAT_COLS, "cat_maps": cat_maps,
    })
    ml.update_metrics("congestion", {
        "model": "lightgbm_regressor", "metric": "MAE", "valid_mae": round(mae, 2),
        "best_iteration": booster.best_iteration,
        "train_rows": int(train_mask.sum()), "valid_rows": int(valid_mask.sum()),
    })
    print("[congestion] saved", ml.CONGESTION_MODEL)


if __name__ == "__main__":
    main()

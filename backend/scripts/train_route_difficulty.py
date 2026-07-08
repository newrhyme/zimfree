"""Train LightGBM classifier for alternate-route difficulty grade (4 classes).

target: complexity_grade (단순/보통/복잡/이동 불가) — class-imbalanced -> balanced weights
features: line, is_terminal, is_transfer, platform_type, depart_zone, depart_floor,
          arrive_zone, arrive_floor, direction
leakage excluded: complexity_score, train_label, alt_type
eval: StratifiedKFold(5) macro-F1; retrain on full data and save.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import ml  # noqa: E402
from app.schema import DB_PATH  # noqa: E402

CAT_COLS = [
    "line", "is_terminal", "is_transfer", "platform_type",
    "depart_zone", "depart_floor", "arrive_zone", "arrive_floor", "direction",
]
FEATURES = CAT_COLS
TARGET = "complexity_grade"
# fixed class order (ordinal-ish difficulty) persisted for serving
CLASSES = ["단순", "보통", "복잡", "이동 불가"]


def load() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM alt_routes", conn)
    conn.close()
    return df


def balanced_weights(y: np.ndarray) -> np.ndarray:
    classes, counts = np.unique(y, return_counts=True)
    n = len(y)
    w_per_class = {c: n / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
    return np.array([w_per_class[v] for v in y])


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("app.db missing; run preprocess.py first")
    df = load()
    df = df[df[TARGET].isin(CLASSES)].reset_index(drop=True)
    cat_maps = ml.build_category_maps(df, CAT_COLS)
    X = ml.encode(df[FEATURES], cat_maps)
    class_to_idx = {c: i for i, c in enumerate(CLASSES)}
    y = df[TARGET].map(class_to_idx).to_numpy()

    params = {
        "objective": "multiclass",
        "num_class": len(CLASSES),
        "metric": "multi_logloss",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "min_data_in_leaf": 10,
        "verbose": -1,
    }

    # ---- CV macro-F1 ----
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    f1s = []
    for tr, va in skf.split(X, y):
        dtr = lgb.Dataset(
            X.iloc[tr], label=y[tr], weight=balanced_weights(y[tr]),
            categorical_feature=CAT_COLS,
        )
        booster = lgb.train(params, dtr, num_boost_round=200)
        pred = booster.predict(X.iloc[va]).argmax(axis=1)
        f1s.append(f1_score(y[va], pred, average="macro"))
    macro_f1 = float(np.mean(f1s))
    print(f"[route] CV macro-F1 = {macro_f1:.3f}  (folds: {[round(f,3) for f in f1s]})")

    # ---- retrain on full data ----
    dfull = lgb.Dataset(
        X, label=y, weight=balanced_weights(y), categorical_feature=CAT_COLS,
    )
    booster = lgb.train(params, dfull, num_boost_round=200)
    booster.save_model(str(ml.ROUTE_MODEL))
    ml.save_meta(ml.ROUTE_META, {
        "feature_order": FEATURES, "cat_cols": CAT_COLS,
        "cat_maps": cat_maps, "classes": CLASSES,
    })
    ml.update_metrics("route_difficulty", {
        "model": "lightgbm_classifier", "metric": "macro_f1",
        "cv_macro_f1": round(macro_f1, 3), "n_rows": int(len(df)),
    })
    if macro_f1 <= 0.6:
        print(f"[route] WARNING: macro-F1 {macro_f1:.3f} <= 0.6 threshold")
    print("[route] saved", ml.ROUTE_MODEL)


if __name__ == "__main__":
    main()

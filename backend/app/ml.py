"""Shared ML artifact paths + categorical encoding used by training & serving.

Categoricals are encoded to integer codes via a persisted mapping so the raw
LightGBM booster (.txt) can be reloaded for serving without pandas/sklearn
category-dtype coupling. Unseen values encode to -1 (LightGBM missing).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .schema import MODELS_DIR

MODELS_DIR.mkdir(parents=True, exist_ok=True)

CONGESTION_MODEL = MODELS_DIR / "congestion.txt"
CONGESTION_META = MODELS_DIR / "congestion_meta.json"
ROUTE_MODEL = MODELS_DIR / "route_difficulty.txt"
ROUTE_META = MODELS_DIR / "route_difficulty_meta.json"
METRICS = MODELS_DIR / "metrics.json"


def build_category_maps(df: pd.DataFrame, cat_cols: list[str]) -> dict[str, dict[str, int]]:
    return {
        c: {str(v): i for i, v in enumerate(sorted(df[c].astype(str).unique()))}
        for c in cat_cols
    }


def encode(df: pd.DataFrame, cat_maps: dict[str, dict[str, int]]) -> pd.DataFrame:
    out = df.copy()
    for c, m in cat_maps.items():
        out[c] = out[c].astype(str).map(m).fillna(-1).astype(int)
    return out


def encode_row(values: dict, feature_order: list[str], cat_maps: dict) -> list[float]:
    row = []
    for f in feature_order:
        v = values.get(f)
        if f in cat_maps:
            row.append(float(cat_maps[f].get(str(v), -1)))
        else:
            row.append(float(v) if v is not None else float("nan"))
    return row


def update_metrics(key: str, payload: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    if METRICS.exists():
        data = json.loads(METRICS.read_text(encoding="utf-8"))
    data[key] = payload
    METRICS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def save_meta(path: Path, meta: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

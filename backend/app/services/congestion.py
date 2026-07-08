"""Congestion level + better-hours, LightGBM serving with stats fallback."""
from __future__ import annotations

from datetime import date as _date
from functools import lru_cache

from .. import db, ml
from ..schema import KR_HOLIDAYS_2025

LEVELS = ["여유", "보통", "혼잡", "매우혼잡"]
_DOW_KR = ["월", "화", "수", "목", "금", "토", "일"]


def dow_of(date_str: str) -> str:
    y, m, d = (int(x) for x in date_str[:10].split("-"))
    return _DOW_KR[_date(y, m, d).weekday()]


@lru_cache(maxsize=1)
def _load_model():
    if not ml.CONGESTION_MODEL.exists() or not ml.CONGESTION_META.exists():
        return None, None
    import lightgbm as lgb

    booster = lgb.Booster(model_file=str(ml.CONGESTION_MODEL))
    meta = ml.load_meta(ml.CONGESTION_META)
    return booster, meta


def get_stats(code: int, dow: str, hour: int, io_type: str) -> dict | None:
    return db.query_one(
        "SELECT mean_pax, p50, p80, p95 FROM congestion_stats "
        "WHERE station_code=? AND dow=? AND hour=? AND io_type=?",
        (code, dow, hour, io_type),
    )


@lru_cache(maxsize=1024)
def _day_thresholds(code: int, dow: str, io_type: str) -> tuple | None:
    """Percentiles of the 24 hourly mean_pax for this station/day/direction.
    Level answers "how busy is this hour relative to the station's own day"."""
    import numpy as np

    rows = db.query(
        "SELECT mean_pax FROM congestion_stats "
        "WHERE station_code=? AND dow=? AND io_type=?",
        (code, dow, io_type),
    )
    vals = [r["mean_pax"] for r in rows if r["mean_pax"] is not None]
    if not vals:
        return None
    p50, p80, p95 = (float(np.percentile(vals, q)) for q in (50, 80, 95))
    return round(p50, 1), round(p80, 1), round(p95, 1)


def _level(pred: float, p50: float, p80: float, p95: float) -> str:
    if pred < p50:
        return "여유"
    if pred < p80:
        return "보통"
    if pred < p95:
        return "혼잡"
    return "매우혼잡"


def predict_pax(code: int, dow: str, hour: int, io_type: str, date_str: str) -> tuple[float, str]:
    """Return (pax_pred, source). Model if available, else stats mean fallback."""
    booster, meta = _load_model()
    stats = get_stats(code, dow, hour, io_type)
    if booster is not None:
        line_row = db.query_one("SELECT line FROM stations WHERE station_code=?", (code,))
        line = line_row["line"] if line_row else None
        month = int(date_str[5:7])
        is_holiday = 1 if date_str[:10] in KR_HOLIDAYS_2025 else 0
        values = {
            "station_code": code, "line": line, "dow": dow, "io_type": io_type,
            "hour": hour, "month": month, "is_holiday": is_holiday,
        }
        row = ml.encode_row(values, meta["feature_order"], meta["cat_maps"])
        pred = float(booster.predict([row])[0])
        return max(pred, 0.0), "model"
    if stats is not None:
        return float(stats["mean_pax"]), "stats"
    return 0.0, "none"


def congestion(code: int, date_str: str, hour: int, io_type: str) -> dict:
    dow = dow_of(date_str)
    thresholds = _day_thresholds(code, dow, io_type)
    pred, source = predict_pax(code, dow, hour, io_type, date_str)
    if thresholds is None:
        return {
            "level": None, "pax_pred": round(pred, 1),
            "p50": None, "p80": None, "p95": None,
            "better_hours": [], "source": source,
        }
    p50, p80, p95 = thresholds
    level = _level(pred, p50, p80, p95)
    return {
        "level": level,
        "pax_pred": round(pred, 1),
        "p50": p50, "p80": p80, "p95": p95,
        "better_hours": _better_hours(code, date_str, hour, io_type, level, thresholds),
        "source": source,
    }


def _better_hours(code: int, date_str: str, hour: int, io_type: str,
                  cur_level: str, thresholds: tuple) -> list[dict]:
    dow = dow_of(date_str)
    p50, p80, p95 = thresholds
    cur_ord = LEVELS.index(cur_level)
    out = []
    for h in range(max(1, hour - 3), min(24, hour + 3) + 1):
        if h == hour:
            continue
        pred, _ = predict_pax(code, dow, h, io_type, date_str)
        lvl = _level(pred, p50, p80, p95)
        if LEVELS.index(lvl) < cur_ord:
            out.append({"hour": h, "level": lvl, "_o": LEVELS.index(lvl), "_d": abs(h - hour)})
    out.sort(key=lambda x: (x["_o"], x["_d"]))
    return [{"hour": o["hour"], "level": o["level"]} for o in out[:3]]

"""Elevator-outage simulation: alt-route lookup (ground truth) + model fallback."""
from __future__ import annotations

from functools import lru_cache

from .. import db, ml

_GRADE_ORDER = ["단순", "보통", "복잡", "이동 불가"]


@lru_cache(maxsize=1)
def _load_model():
    if not ml.ROUTE_MODEL.exists() or not ml.ROUTE_META.exists():
        return None, None
    import lightgbm as lgb

    booster = lgb.Booster(model_file=str(ml.ROUTE_MODEL))
    meta = ml.load_meta(ml.ROUTE_META)
    return booster, meta


def _worst(grades: list[str]) -> str | None:
    present = [g for g in grades if g in _GRADE_ORDER]
    if not present:
        return None
    return max(present, key=lambda g: _GRADE_ORDER.index(g))


def _predict_grade(row_feats: dict) -> tuple[str | None, str]:
    booster, meta = _load_model()
    if booster is None:
        return None, "none"
    x = ml.encode_row(row_feats, meta["feature_order"], meta["cat_maps"])
    probs = booster.predict([x])[0]
    idx = int(max(range(len(probs)), key=lambda i: probs[i]))
    return meta["classes"][idx], "model"


def elevator_outage(station_code: int, elevator_id: str | int | None = None) -> dict:
    where = "station_code=?"
    params: list = [station_code]
    if elevator_id is not None:
        where += " AND elevator_inner_id=?"
        params.append(str(elevator_id))
    rows = db.query(
        "SELECT elevator_inner_id, elevator_uid, depart_zone, depart_floor, "
        "arrive_zone, arrive_floor, direction, alt_steps, alt_type, "
        "complexity_grade, passable_raw, platform_type, is_terminal, is_transfer, line "
        f"FROM alt_routes WHERE {where}", tuple(params),
    )

    if rows:
        routes = []
        for r in rows:
            passable = r["alt_type"] != "ALT_NONE"
            routes.append({
                "elevator_id": r["elevator_inner_id"],
                "depart": f"{r['depart_zone']} {r['depart_floor']}".strip(),
                "arrive": f"{r['arrive_zone']} {r['arrive_floor']}".strip(),
                "alt_type": r["alt_type"],
                "grade": r["complexity_grade"],
                "steps": r["alt_steps"],
                "passable": passable,
            })
        grades = [r["grade"] for r in routes]
        # any ALT_NONE movement means this elevator's outage leaves an
        # impassable segment for luggage users.
        all_passable = all(r["passable"] for r in routes)
        worst = _worst(grades)
        out = {
            "station_code": station_code, "elevator_id": elevator_id,
            "passable": all_passable, "worst_grade": worst,
            "routes": routes, "source": "data",
        }
        if not all_passable:
            out["message"] = "고장 시 이 구간은 이동 불가 (대체경로 없음)"
        return out

    # no ground-truth rows -> model fallback using a station-level feature row
    base = db.query_one(
        "SELECT line, platform_type, is_terminal, is_transfer FROM alt_routes "
        "WHERE station_code=? LIMIT 1", (station_code,)
    )
    st = db.query_one("SELECT line FROM stations WHERE station_code=?", (station_code,))
    if base is None and st is None:
        return {"station_code": station_code, "elevator_id": elevator_id,
                "passable": None, "message": "해당 역 정보 없음", "source": "none"}
    feats = {
        "line": (base or st)["line"],
        "is_terminal": base["is_terminal"] if base else "N",
        "is_transfer": base["is_transfer"] if base else "N",
        "platform_type": base["platform_type"] if base else "상대식",
        "depart_zone": "지하", "depart_floor": "대합실",
        "arrive_zone": "지상", "arrive_floor": "1",
        "direction": "양방향",
    }
    grade, source = _predict_grade(feats)
    return {
        "station_code": station_code, "elevator_id": elevator_id,
        "passable": grade != "이동 불가" if grade else None,
        "worst_grade": grade, "routes": [], "source": source,
        "message": "실데이터 없음 — 모델 예측 등급" if source == "model" else "정보 없음",
    }

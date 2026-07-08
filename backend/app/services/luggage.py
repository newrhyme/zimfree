"""Rule-based luggage decision: carry vs locker vs delivery, with data citations."""
from __future__ import annotations

from .. import db

# Subway station std_name -> flow-hub label. Only 부산역 is a subway station;
# 김해국제공항 / 부산항 터미널 are not on the metro so have no origin code.
STD_TO_HUB = {"부산": "부산역"}

_SIZE_COL = {"S": "size_s", "M": "size_m", "L": "size_l", "XL": "size_xl"}
_SIZE_ORD = {"S": 0, "M": 1, "L": 2, "XL": 3}


def _nearest_region(dest_code: int) -> tuple[str, int] | None:
    dest = db.query_one("SELECT lat, lng FROM stations WHERE station_code=?", (dest_code,))
    if not dest:
        return None
    anchors = db.query(
        "SELECT r.region, r.anchor_station_code, s.lat, s.lng "
        "FROM region_anchor r JOIN stations s ON r.anchor_station_code = s.station_code"
    )
    best = None
    for a in anchors:
        d2 = (a["lat"] - dest["lat"]) ** 2 + (a["lng"] - dest["lng"]) ** 2
        if best is None or d2 < best[0]:
            best = (d2, a["region"], a["anchor_station_code"])
    return (best[1], best[2]) if best else None


def _carry_difficulty(origin: int, dest: int, luggage: dict) -> dict:
    from .route import find_path, build_legs

    path = find_path(origin, dest)
    transfers = max(0, len(build_legs(path)) - 1) if path else 0
    size = luggage.get("size", "M")
    count = int(luggage.get("count", 1) or 1)
    stroller = bool(luggage.get("stroller", False))

    score = transfers * 2 + _SIZE_ORD.get(size, 1) + (count - 1) + (1 if stroller else 0)
    if score <= 2:
        grade = "단순"
    elif score <= 4:
        grade = "보통"
    else:
        grade = "복잡"
    reasons = []
    if transfers:
        reasons.append(f"환승 {transfers}회")
    if size in ("L", "XL"):
        reasons.append(f"{size} 대형 수하물")
    if count >= 2:
        reasons.append(f"{count}개")
    if stroller:
        reasons.append("유모차 동반")
    return {"type": "carry", "difficulty": grade,
            "reason": " + ".join(reasons) or "짐 규모 작음"}


def _locker_option(origin: int, luggage: dict) -> dict:
    std = db.query_one("SELECT std_name FROM stations WHERE station_code=?", (origin,))
    if not std:
        return {"type": "locker", "available": False, "reason": "보관함 정보 없음"}
    rows = db.query(
        "SELECT std_name, detail, size_s, size_m, size_l, size_xl, fee "
        "FROM lockers WHERE std_name=?", (std["std_name"],)
    )
    if not rows:
        return {"type": "locker", "available": False, "station": std["std_name"],
                "reason": "이 역은 보관함 커버리지 밖 (정보 없음)"}
    size = luggage.get("size", "M")
    col = _SIZE_COL.get(size, "size_m")
    for r in rows:
        try:
            n = int(r[col]) if r[col] not in (None, "") else 0
        except (ValueError, TypeError):
            n = 0
        if n > 0:
            return {"type": "locker", "available": True, "station": r["std_name"],
                    "detail": r["detail"], "fee": r["fee"],
                    "reason": f"{size}형 보관함 {n}칸 보유"}
    return {"type": "locker", "available": False, "station": std["std_name"],
            "reason": f"{size}형 보관함 재고 없음"}


def _delivery_option(origin: int, dest: int) -> dict:
    std = db.query_one("SELECT std_name FROM stations WHERE station_code=?", (origin,))
    hub = STD_TO_HUB.get(std["std_name"]) if std else None
    region_info = _nearest_region(dest)
    if hub is None or region_info is None:
        return {"type": "delivery", "prior": None,
                "reason": "짐배송 이용 가능 (해당 구간 통계 없음)", "source_note": None}
    region, _ = region_info
    row = db.query_one(
        "SELECT ratio FROM flow_priors WHERE direction='delivery' AND hub=? AND region=?",
        (hub, region),
    )
    if not row:
        return {"type": "delivery", "prior": None,
                "reason": "짐배송 이용 가능 (해당 구간 통계 없음)", "source_note": None}
    ratio = row["ratio"]
    pct = round(ratio * 100)
    return {
        "type": "delivery", "prior": ratio,
        "reason": f"{hub}→{region}은 짐배송 이용자의 {pct}%가 선택한 구간",
        "source_note": f"flow_priors: {hub}→{region} {ratio}",
    }


def decide(origin: int, dest: int, luggage: dict) -> dict:
    carry = _carry_difficulty(origin, dest, luggage)
    locker = _locker_option(origin, luggage)
    delivery = _delivery_option(origin, dest)

    size = luggage.get("size", "M")
    count = int(luggage.get("count", 1) or 1)
    big = size in ("L", "XL") or count >= 2

    # recommendation: prefer delivery for big loads when prior favours it,
    # else locker if available, else carry.
    if big and delivery.get("prior") and delivery["prior"] >= 0.5:
        rec = "delivery"
    elif big and locker.get("available"):
        rec = "locker"
    elif carry["difficulty"] == "복잡" and locker.get("available"):
        rec = "locker"
    else:
        rec = "carry"

    source_notes = []
    if delivery.get("source_note"):
        source_notes.append(delivery["source_note"])

    return {
        "recommendation": rec,
        "options": [carry, locker, delivery],
        "source_notes": source_notes,
    }

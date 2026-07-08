"""Subway graph (BFS), boarding-position recommendation, and route planning."""
from __future__ import annotations

from collections import defaultdict, deque
from functools import lru_cache

from .. import db
from . import congestion as congestion_svc
from . import luggage as luggage_svc


@lru_cache(maxsize=1)
def _graph():
    """Build adjacency: ride edges (consecutive codes per line) + transfer edges
    (same std_name across lines). Returns (adj, edge_type, meta)."""
    stations = db.query("SELECT station_code, line, name, std_name, lat, lng FROM stations")
    meta = {s["station_code"]: s for s in stations}
    adj: dict[int, set[int]] = defaultdict(set)
    edge_type: dict[tuple[int, int], str] = {}

    by_line: dict[str, list[int]] = defaultdict(list)
    for s in stations:
        by_line[s["line"]].append(s["station_code"])
    for line, codes in by_line.items():
        codes.sort()
        for a, b in zip(codes, codes[1:]):
            adj[a].add(b); adj[b].add(a)
            edge_type[(a, b)] = edge_type[(b, a)] = "ride"

    by_std: dict[str, list[int]] = defaultdict(list)
    for s in stations:
        by_std[s["std_name"]].append(s["station_code"])
    for std, codes in by_std.items():
        for i in range(len(codes)):
            for j in range(i + 1, len(codes)):
                a, b = codes[i], codes[j]
                adj[a].add(b); adj[b].add(a)
                edge_type[(a, b)] = edge_type[(b, a)] = "transfer"
    return adj, edge_type, meta


def find_path(origin: int, dest: int) -> list[int] | None:
    adj, _, meta = _graph()
    if origin not in meta or dest not in meta:
        return None
    if origin == dest:
        return [origin]
    prev = {origin: None}
    q = deque([origin])
    while q:
        cur = q.popleft()
        for nxt in adj[cur]:
            if nxt not in prev:
                prev[nxt] = cur
                if nxt == dest:
                    path = [dest]
                    while prev[path[-1]] is not None:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                q.append(nxt)
    return None


def build_legs(path: list[int]) -> list[dict]:
    """Split path into single-line ride segments; transfers separate legs."""
    _, edge_type, meta = _graph()
    legs = []
    i = 0
    n = len(path)
    while i < n - 1:
        start = path[i]
        line = meta[start]["line"]
        j = i
        while j + 1 < n and edge_type.get((path[j], path[j + 1])) == "ride":
            j += 1
        legs.append({
            "from": start, "to": path[j],
            "from_name": meta[start]["std_name"], "to_name": meta[path[j]]["std_name"],
            "line": line, "num_stops": j - i,
        })
        # skip a transfer edge if present
        if j + 1 < n and edge_type.get((path[j], path[j + 1])) == "transfer":
            i = j + 1
        else:
            i = j
        if i == j and j >= n - 1:
            break
    return legs


def get_boarding(dest_code: int, approach_direction: str | None = None) -> dict:
    rows = db.query(
        "SELECT * FROM boarding_positions WHERE station_code=?", (dest_code,)
    )
    if not rows:
        return {"door_pos": None, "elevator_note": None, "warnings": [],
                "message": "탑승칸 추천 정보 없음"}
    chosen = None
    if approach_direction:
        for r in rows:
            if r["direction"] and (r["direction"] in approach_direction or approach_direction in r["direction"]):
                chosen = r
                break
    if chosen is None:
        chosen = rows[0]
    std = db.query_one("SELECT std_name FROM stations WHERE station_code=?", (dest_code,))
    elev = None
    if std:
        elev = db.query_one(
            "SELECT detail, status FROM elevators WHERE std_name=? AND elevator_id=?",
            (std["std_name"], chosen["elevator_id"]),
        )
    warnings = []
    if chosen["warning_gap"]:
        warnings.append("연단간격 넓음 — 캐리어 바퀴 빠짐 주의")
    if chosen["warning_curve"]:
        warnings.append("곡선 승강장 — 발빠짐 주의")
    return {
        "door_pos": chosen["recommended_door_pos"],
        "direction": chosen["direction"],
        "elevator_id": chosen["elevator_id"],
        "elevator_note": elev["detail"] if elev else None,
        "warnings": warnings,
    }


def _charging(path: list[int], std_names: list[str]) -> list[dict]:
    if not std_names:
        return []
    placeholders = ",".join("?" * len(std_names))
    rows = db.query(
        f"SELECT std_name, floor, detail, count, fee FROM chargers "
        f"WHERE std_name IN ({placeholders})",
        tuple(std_names),
    )
    return [
        {"station": r["std_name"], "detail": f"({r['floor']}) {r['detail']}".strip(),
         "fee": r["fee"], "count": r["count"]}
        for r in rows
    ]


def plan(origin: int, dest: int, luggage: dict, battery_pct: int | None,
         depart_at: str | None) -> dict:
    _, _, meta = _graph()
    path = find_path(origin, dest)
    if path is None:
        return {"error": "no_route", "message": "경로를 찾을 수 없습니다"}
    legs = build_legs(path)
    std_names = [meta[c]["std_name"] for c in path]

    # boarding at destination, using last leg's line direction hint (dest std name)
    boarding = get_boarding(dest, approach_direction=None)

    # congestion at origin for the requested hour
    cong = None
    if depart_at:
        date_str = depart_at[:10]
        hour = int(depart_at[11:13]) if len(depart_at) >= 13 else 8
        hour = 24 if hour == 0 else hour
        cong = congestion_svc.congestion(origin, date_str, hour, "board")

    result = {
        "legs": legs,
        "num_transfers": max(0, len(legs) - 1),
        "boarding": boarding,
        "congestion": cong,
        "luggage_advice": luggage_svc.decide(origin, dest, luggage),
    }
    if battery_pct is not None and battery_pct < 30:
        result["charging"] = _charging(path, std_names)
    return result

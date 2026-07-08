"""Preprocess raw 13 CSVs -> data/processed/app.db (idempotent DROP&CREATE).

Run: python scripts/preprocess.py
Reads raw with utf-8-sig, keeps Korean headers only inside pandas, and emits
snake_case tables per backend/CLAUDE.md. Row-count asserts guard correctness.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# allow "python scripts/preprocess.py" from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import schema as S  # noqa: E402

DOOR_RE = re.compile(r"(\d{1,2}-\d)")
DIRECTION_RE = re.compile(r"([가-힣A-Za-z0-9]+행)")
DIRECTION_RE2 = re.compile(r"([가-힣A-Za-z0-9]+역)\s*방향")


def _read(fname: str, **kw) -> pd.DataFrame:
    return pd.read_csv(S.RAW_DIR / fname, encoding=S.RAW_ENCODING, dtype=str, **kw)


def extract_door_pos(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    m = DOOR_RE.search(text)
    return m.group(1) if m else None


def extract_direction_hint(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    m = DIRECTION_RE.search(text)
    if m:
        return m.group(1)
    m = DIRECTION_RE2.search(text)
    if m:
        return m.group(1) + "역 방향"
    return None


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------
def build_stations() -> pd.DataFrame:
    df = _read(S.F_STATION)[list(S.STATION_COLS)].rename(columns=S.STATION_COLS)
    df["station_code"] = df["station_code"].astype(int)
    df["lat"] = df["lat"].astype(float)
    df["lng"] = df["lng"].astype(float)
    return df


def std_to_code(stations: pd.DataFrame) -> dict[str, int]:
    """Representative station_code per std_name = min code."""
    return (
        stations.groupby("std_name")["station_code"].min().astype(int).to_dict()
    )


def build_ridership(stations: pd.DataFrame) -> pd.DataFrame:
    df = _read(S.F_RIDERSHIP)
    keep_meta = list(S.RIDERSHIP_META_COLS)
    df = df[keep_meta + S.HOUR_COLS].rename(columns=S.RIDERSHIP_META_COLS)
    df["station_code"] = df["station_code"].astype(int)
    df["io_type"] = df["io_type_kr"].map(S.IO_TYPE_MAP)
    df = df.drop(columns=["io_type_kr"])
    long = df.melt(
        id_vars=["station_code", "std_name", "date", "dow", "io_type"],
        value_vars=S.HOUR_COLS,
        var_name="hour_col",
        value_name="pax",
    )
    long["hour"] = long["hour_col"].str.slice(0, 2).astype(int)
    long["pax"] = long["pax"].astype(int)
    long = long.drop(columns=["hour_col", "std_name"])
    return long[["station_code", "date", "dow", "io_type", "hour", "pax"]]


def build_congestion_stats(ridership: pd.DataFrame) -> pd.DataFrame:
    g = ridership.groupby(["station_code", "dow", "hour", "io_type"])["pax"]
    stats = g.agg(
        mean_pax="mean",
        p50=lambda x: x.quantile(0.50),
        p80=lambda x: x.quantile(0.80),
        p95=lambda x: x.quantile(0.95),
    ).reset_index()
    for c in ("mean_pax", "p50", "p80", "p95"):
        stats[c] = stats[c].round(1)
    return stats


def build_elevators(std_code: dict[str, int]) -> pd.DataFrame:
    df = _read(S.F_ELEVATOR)[list(S.ELEVATOR_COLS)].rename(columns=S.ELEVATOR_COLS)
    df["door_pos"] = df["detail"].map(extract_door_pos)
    df["direction_hint"] = df["detail"].map(extract_direction_hint)
    df["station_code"] = df["std_name"].map(std_code).astype("Int64")
    return df


def build_escalators(std_code: dict[str, int]) -> pd.DataFrame:
    df = _read(S.F_ESCALATOR)[list(S.ESCALATOR_COLS)].rename(columns=S.ESCALATOR_COLS)
    df["detail"] = df["detail_start"].fillna("") + " / " + df["detail_end"].fillna("")
    df["door_pos"] = df["detail"].map(extract_door_pos)
    df["direction_hint"] = df["detail"].map(extract_direction_hint)
    df["station_code"] = df["std_name"].map(std_code).astype("Int64")
    return df


def build_alt_routes() -> pd.DataFrame:
    df = _read(S.F_ALT_ROUTE)[list(S.ALT_ROUTE_COLS)].rename(columns=S.ALT_ROUTE_COLS)
    df["station_code"] = df["station_code"].astype(int)
    df["complexity_score"] = pd.to_numeric(df["complexity_score"], errors="coerce")
    return df


PLATFORM_POS_RE = re.compile(r"^(.*?행)\s+(\d{1,2}-\d)")


def build_platform_gap() -> pd.DataFrame:
    df = _read(S.F_PLATFORM)[list(S.PLATFORM_COLS)].rename(columns=S.PLATFORM_COLS)
    df["station_code"] = df["station_code"].astype(int)
    parsed = df["platform_pos"].str.extract(PLATFORM_POS_RE)
    df["direction"] = parsed[0]
    df["door_pos"] = parsed[1]
    return df[["station_code", "updown", "direction", "door_pos", "gap", "curve"]]


def build_boarding_positions(
    platform: pd.DataFrame, elevators: pd.DataFrame, stations: pd.DataFrame
) -> pd.DataFrame:
    code_to_std = stations.set_index("station_code")["std_name"].to_dict()
    elev = elevators.dropna(subset=["door_pos"]).copy()
    # elevators grouped by std_name
    elev_by_std: dict[str, list[dict]] = {}
    for _, r in elev.iterrows():
        elev_by_std.setdefault(r["std_name"], []).append(
            {
                "elevator_id": r["elevator_id"],
                "door_pos": r["door_pos"],
                "direction_hint": r["direction_hint"],
            }
        )

    # platform gap lookup: (station_code, direction, door_pos) -> (gap, curve)
    gap_lookup: dict[tuple, tuple] = {}
    for _, r in platform.dropna(subset=["direction", "door_pos"]).iterrows():
        gap_lookup[(r["station_code"], r["direction"], r["door_pos"])] = (
            r["gap"],
            r["curve"],
        )

    rows = []
    seen = set()
    for (code, direction), _grp in platform.dropna(subset=["direction"]).groupby(
        ["station_code", "direction"]
    ):
        if (code, direction) in seen:
            continue
        seen.add((code, direction))
        std = code_to_std.get(code)
        candidates = elev_by_std.get(std, [])
        chosen = None
        # prefer elevator whose direction_hint matches this direction (substring)
        for e in candidates:
            hint = e.get("direction_hint")
            if isinstance(hint, str) and (hint in direction or direction in hint):
                chosen = e
                break
        if chosen is None and candidates:
            chosen = candidates[0]
        if chosen is None:
            continue
        door = chosen["door_pos"]
        gap, curve = gap_lookup.get((code, direction, door), (None, None))
        rows.append(
            {
                "station_code": code,
                "direction": direction,
                "recommended_door_pos": door,
                "elevator_id": chosen["elevator_id"],
                "warning_gap": 1 if gap == "넓음" else 0,
                "warning_curve": 1 if curve == "곡선" else 0,
            }
        )
    return pd.DataFrame(rows)


def build_facility(fname: str, cols: dict, std_code: dict[str, int]) -> pd.DataFrame:
    df = _read(fname)[list(cols)].rename(columns=cols)
    df["station_code"] = df["std_name"].map(std_code).astype("Int64")
    df = df.dropna(subset=["station_code"])
    df["station_code"] = df["station_code"].astype(int)
    return df


def build_flow_priors() -> pd.DataFrame:
    rows = []
    for fname, direction in (
        (S.F_FLOW_HUB_TO_LODGING, "delivery"),
        (S.F_FLOW_LODGING_TO_HUB, "pickup"),
    ):
        df = _read(fname, skiprows=3)
        # columns: [hub_label, hub_ratio, region0..region4, row_total]
        cols = list(df.columns)
        region_cols = cols[2:7]  # 5 region columns in order of FLOW_REGIONS
        for _, r in df.iterrows():
            hub = str(r[cols[0]]).strip()
            if hub not in S.FLOW_HUBS:
                continue
            for region, rc in zip(S.FLOW_REGIONS, region_cols):
                ratio = pd.to_numeric(r[rc], errors="coerce")
                if pd.isna(ratio):
                    continue
                rows.append(
                    {
                        "direction": direction,
                        "hub": hub,
                        "region": region,
                        "ratio": round(float(ratio), 4),
                    }
                )
    return pd.DataFrame(rows)


def build_region_anchor(std_code: dict[str, int]) -> pd.DataFrame:
    rows = []
    for region, anchor_std in S.REGION_ANCHORS.items():
        code = std_code.get(anchor_std)
        if code is None:
            continue
        rows.append({"region": region, "anchor_station_code": int(code)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    S.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if S.DB_PATH.exists():
        S.DB_PATH.unlink()

    print("[preprocess] reading raw CSVs...")
    stations = build_stations()
    std_code = std_to_code(stations)
    ridership = build_ridership(stations)
    congestion = build_congestion_stats(ridership)
    elevators = build_elevators(std_code)
    escalators = build_escalators(std_code)
    alt_routes = build_alt_routes()
    platform = build_platform_gap()
    boarding = build_boarding_positions(platform, elevators, stations)
    lockers = build_facility(S.F_LOCKER, S.LOCKER_COLS, std_code)
    atms = build_facility(S.F_ATM, S.ATM_COLS, std_code)
    chargers = build_facility(S.F_CHARGER, S.CHARGER_COLS, std_code)
    kiosks = build_facility(S.F_KIOSK, S.KIOSK_COLS, std_code)
    flow_priors = build_flow_priors()
    region_anchor = build_region_anchor(std_code)

    conn = sqlite3.connect(S.DB_PATH)
    tables = {
        "stations": stations,
        "ridership_hourly": ridership,
        "congestion_stats": congestion,
        "elevators": elevators,
        "escalators": escalators,
        "alt_routes": alt_routes,
        "platform_gap": platform,
        "boarding_positions": boarding,
        "lockers": lockers,
        "atms": atms,
        "chargers": chargers,
        "kiosks": kiosks,
        "flow_priors": flow_priors,
        "region_anchor": region_anchor,
    }
    for name, df in tables.items():
        df.to_sql(name, conn, if_exists="replace", index=False)
        print(f"[preprocess]   {name}: {len(df)} rows")

    # indexes for query paths
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_ride ON ridership_hourly(station_code, dow, hour, io_type)")
    cur.execute("CREATE INDEX idx_cong ON congestion_stats(station_code, dow, hour, io_type)")
    cur.execute("CREATE INDEX idx_alt ON alt_routes(station_code)")
    cur.execute("CREATE INDEX idx_board ON boarding_positions(station_code, direction)")
    conn.commit()

    # ---- row-count asserts (fail loud) ----
    def count(t: str) -> int:
        return cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

    assert count("stations") == 114, f"stations={count('stations')}"
    assert count("alt_routes") == 932, f"alt_routes={count('alt_routes')}"
    assert count("platform_gap") == 4864, f"platform_gap={count('platform_gap')}"
    assert boarding["station_code"].nunique() >= 90, (
        f"boarding covers only {boarding['station_code'].nunique()} stations"
    )
    grade_counts = alt_routes["complexity_grade"].value_counts().to_dict()
    assert grade_counts.get("단순") == 453, grade_counts
    assert grade_counts.get("이동 불가") == 43, grade_counts
    conn.close()

    print("[preprocess] OK. app.db written to", S.DB_PATH)
    print(f"[preprocess] boarding_positions covers {boarding['station_code'].nunique()} stations")


if __name__ == "__main__":
    main()

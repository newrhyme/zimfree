"""Preprocess output assertions (Step 1)."""
import sqlite3

import pytest

from app.schema import DB_PATH


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip("app.db not built; run `python scripts/preprocess.py` first")
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_stations_count(conn):
    assert count(conn, "stations") == 114


def test_alt_routes_count(conn):
    assert count(conn, "alt_routes") == 932


def test_platform_gap_count(conn):
    assert count(conn, "platform_gap") == 4864


def test_boarding_positions_coverage(conn):
    n = conn.execute(
        "SELECT COUNT(DISTINCT station_code) FROM boarding_positions"
    ).fetchone()[0]
    assert n >= 90


def test_stations_schema(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(stations)")}
    assert {"station_code", "line", "name", "std_name", "lat", "lng", "transfer_lines"} <= cols


def test_ridership_long_format(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ridership_hourly)")}
    assert cols == {"station_code", "date", "dow", "io_type", "hour", "pax"}
    # hours are 1..24
    hours = {r[0] for r in conn.execute("SELECT DISTINCT hour FROM ridership_hourly")}
    assert hours == set(range(1, 25))
    # io_type normalized
    ios = {r[0] for r in conn.execute("SELECT DISTINCT io_type FROM ridership_hourly")}
    assert ios == {"board", "alight"}


def test_congestion_stats_percentiles(conn):
    row = conn.execute(
        "SELECT p50, p80, p95 FROM congestion_stats "
        "WHERE p95 IS NOT NULL LIMIT 1"
    ).fetchone()
    assert row["p50"] <= row["p80"] <= row["p95"]


def test_alt_route_grade_distribution(conn):
    rows = dict(
        conn.execute(
            "SELECT complexity_grade, COUNT(*) FROM alt_routes GROUP BY complexity_grade"
        ).fetchall()
    )
    assert rows.get("단순") == 453
    assert rows.get("이동 불가") == 43


def test_flow_priors_busan_haeundae(conn):
    row = conn.execute(
        "SELECT ratio FROM flow_priors "
        "WHERE direction='delivery' AND hub='부산역' AND region='해운대·기장'"
    ).fetchone()
    assert row is not None
    assert abs(row["ratio"] - 0.64) < 0.001


def test_facilities_mapped_to_codes(conn):
    # every locker row resolved to a real station_code
    orphans = conn.execute(
        "SELECT COUNT(*) FROM lockers l "
        "LEFT JOIN stations s ON l.station_code = s.station_code "
        "WHERE s.station_code IS NULL"
    ).fetchone()[0]
    assert orphans == 0

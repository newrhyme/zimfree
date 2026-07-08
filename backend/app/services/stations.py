"""Station lookup + facilities aggregation."""
from __future__ import annotations

from functools import lru_cache

from .. import db

STATION_FIELDS = "station_code, line, name, std_name, lat, lng, transfer_lines"


def list_stations() -> list[dict]:
    return db.query(f"SELECT {STATION_FIELDS} FROM stations ORDER BY station_code")


@lru_cache(maxsize=256)
def get_station(code: int) -> dict | None:
    return db.query_one(
        f"SELECT {STATION_FIELDS} FROM stations WHERE station_code = ?", (code,)
    )


def _std_name(code: int) -> str | None:
    row = get_station(code)
    return row["std_name"] if row else None


def get_facilities(code: int) -> dict:
    std = _std_name(code)
    if std is None:
        return {
            "lockers": [], "atms": [], "chargers": [], "kiosks": [],
            "elevators_count": 0, "escalators_count": 0,
        }
    lockers = db.query(
        "SELECT std_name, detail, size_s, size_m, size_l, size_xl, fee, operator "
        "FROM lockers WHERE std_name = ?", (std,)
    )
    atms = db.query(
        "SELECT std_name, floor, detail, bank, hours FROM atms WHERE std_name = ?", (std,)
    )
    chargers = db.query(
        "SELECT std_name, floor, detail, count, fee FROM chargers WHERE std_name = ?", (std,)
    )
    kiosks = db.query(
        "SELECT std_name, detail, voice, braille, visual FROM kiosks WHERE std_name = ?", (std,)
    )
    elev = db.query_one(
        "SELECT COUNT(*) n FROM elevators WHERE std_name = ?", (std,)
    )
    esc = db.query_one(
        "SELECT COUNT(*) n FROM escalators WHERE std_name = ?", (std,)
    )
    return {
        "lockers": lockers, "atms": atms, "chargers": chargers, "kiosks": kiosks,
        "elevators_count": elev["n"] if elev else 0,
        "escalators_count": esc["n"] if esc else 0,
    }

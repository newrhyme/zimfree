from fastapi import APIRouter, HTTPException

from ..services import congestion as svc
from ..services import stations as stations_svc

router = APIRouter(prefix="/api", tags=["congestion"])


@router.get("/congestion")
def congestion(station_code: int, date: str, hour: int, io_type: str = "board"):
    if stations_svc.get_station(station_code) is None:
        raise HTTPException(404, "station not found")
    if io_type not in ("board", "alight"):
        raise HTTPException(422, "io_type must be board|alight")
    if not (1 <= hour <= 24):
        raise HTTPException(422, "hour must be 1..24")
    return svc.congestion(station_code, date, hour, io_type)

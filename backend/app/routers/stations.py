from fastapi import APIRouter, HTTPException

from ..services import stations as svc

router = APIRouter(prefix="/api", tags=["stations"])


@router.get("/stations")
def list_stations():
    return svc.list_stations()


@router.get("/stations/{code}/facilities")
def facilities(code: int):
    if svc.get_station(code) is None:
        raise HTTPException(404, "station not found")
    return svc.get_facilities(code)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import scenario as svc
from ..services import stations as stations_svc


class OutageRequest(BaseModel):
    station_code: int
    elevator_id: str | int | None = None


router = APIRouter(prefix="/api", tags=["scenario"])


@router.post("/scenario/elevator-outage")
def elevator_outage(req: OutageRequest):
    if stations_svc.get_station(req.station_code) is None:
        raise HTTPException(404, "station not found")
    return svc.elevator_outage(req.station_code, req.elevator_id)

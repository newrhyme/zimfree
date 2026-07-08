from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import route as svc
from ..services import stations as stations_svc


class Luggage(BaseModel):
    size: str = "M"
    count: int = 1
    stroller: bool = False


class RouteRequest(BaseModel):
    origin_code: int
    dest_code: int
    luggage: Luggage = Luggage()
    battery_pct: int | None = None
    depart_at: str | None = None


router = APIRouter(prefix="/api", tags=["route"])


@router.post("/route/plan")
def route_plan(req: RouteRequest):
    if stations_svc.get_station(req.origin_code) is None:
        raise HTTPException(404, "origin station not found")
    if stations_svc.get_station(req.dest_code) is None:
        raise HTTPException(404, "dest station not found")
    result = svc.plan(
        req.origin_code, req.dest_code, req.luggage.model_dump(),
        req.battery_pct, req.depart_at,
    )
    if result.get("error"):
        raise HTTPException(422, result.get("message", "route error"))
    return result

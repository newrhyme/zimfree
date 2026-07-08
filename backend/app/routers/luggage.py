from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import luggage as svc
from ..services import stations as stations_svc


class Luggage(BaseModel):
    size: str = "M"
    count: int = 1
    stroller: bool = False


class LuggageRequest(BaseModel):
    origin_code: int
    dest_code: int
    luggage: Luggage = Luggage()


router = APIRouter(prefix="/api", tags=["luggage"])


@router.post("/luggage/decision")
def luggage_decision(req: LuggageRequest):
    if stations_svc.get_station(req.origin_code) is None:
        raise HTTPException(404, "origin station not found")
    if stations_svc.get_station(req.dest_code) is None:
        raise HTTPException(404, "dest station not found")
    return svc.decide(req.origin_code, req.dest_code, req.luggage.model_dump())

"""ZimFree FastAPI app — Busan subway luggage copilot."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import assistant, congestion, luggage, route, scenario, stations

app = FastAPI(title="ZimFree API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (stations, congestion, route, luggage, scenario, assistant):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

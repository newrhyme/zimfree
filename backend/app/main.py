"""ZimFree FastAPI app — Busan subway luggage copilot."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env (gitignored) before importing routers/services so that
# ANTHROPIC_API_KEY / OPENAI_API_KEY / OPENAI_MODEL are available at import time.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from .routers import assistant, congestion, luggage, route, scenario, stations  # noqa: E402

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

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import cors_allow_origins


def add_cors(app: FastAPI) -> None:
    """Browser-friendly CORS for local demos (e.g. /ui). Restrict CORS_ORIGINS in production."""
    origins = cors_allow_origins()
    # Browsers disallow credentials + wildcard origin.
    creds = "*" not in origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )

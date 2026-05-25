"""
FastAPI app — owns all /api/* routes.
Flask (app.py) continues to serve HTML pages (login, dashboard, pricing, etc.) during Phase 2.
Flask is retired in Phase 3 when the Next.js frontend replaces HTML templates.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from dotenv import load_dotenv

load_dotenv()

from routers import search, schools, australia_schools, hazards, premium, auth, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    # psycopg2 connections are opened per-request via Depends(get_db) — nothing to init globally
    yield


app = FastAPI(
    title="Property Research API",
    version="2.0.0",
    description="FastAPI backend — GNAF Property Research Database",
    lifespan=lifespan,
)

_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://localhost:5000",
    ).split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(schools.router)
app.include_router(australia_schools.router)
app.include_router(hazards.router)
app.include_router(premium.router)
app.include_router(auth.router,     prefix="/api/auth", tags=["auth"])
app.include_router(payments.router)


@app.exception_handler(ValidationError)
async def _pydantic_validation_error(_req: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse({"detail": exc.errors()}, status_code=422)


@app.exception_handler(404)
async def _not_found(_req: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.exception_handler(500)
async def _server_error(_req: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse({"error": "Internal server error"}, status_code=500)

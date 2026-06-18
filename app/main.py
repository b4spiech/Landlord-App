from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import create_all_tables
from app.routers import (
    leases,
    management_companies,
    owners,
    properties,
    tenants,
    units,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (Alembic owns the real schema, but this keeps
    # local/dev and test environments turnkey).
    create_all_tables()
    yield


app = FastAPI(
    title="Property Management API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def index():
    # Send anyone hitting the bare domain to the interactive API docs.
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok", "version": app.version}


@app.get("/api/v1/", tags=["meta"])
def root():
    return {"message": "Property Management API v1"}


app.include_router(owners.router, prefix="/api/v1")
app.include_router(management_companies.router, prefix="/api/v1")
app.include_router(properties.router, prefix="/api/v1")
app.include_router(units.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(leases.router, prefix="/api/v1")

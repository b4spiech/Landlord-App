from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import create_all_tables
from app.routers import (
    access_codes,
    hoas,
    jurisdictions,
    lease_break,
    leases,
    listings,
    management_companies,
    owners,
    properties,
    public,
    public_tours,
    tenants,
    tour_requests,
)
from app.security import gatekeeper


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

# Host-based gatekeeping (public site vs. landlord app). Registered before
# CORS so CORS stays the outermost layer.
app.middleware("http")(gatekeeper)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok", "version": app.version}


@app.get("/api/v1/", tags=["meta"])
def root():
    return {"message": "Property Management API v1"}


app.include_router(owners.router, prefix="/api/v1")
app.include_router(management_companies.router, prefix="/api/v1")
app.include_router(jurisdictions.router, prefix="/api/v1")
app.include_router(hoas.router, prefix="/api/v1")
app.include_router(properties.router, prefix="/api/v1")
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(leases.router, prefix="/api/v1")
app.include_router(lease_break.router, prefix="/api/v1")
app.include_router(listings.router, prefix="/api/v1")
app.include_router(tour_requests.router, prefix="/api/v1")
app.include_router(access_codes.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(public_tours.router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Serve the built React SPA (frontend/dist).
#
# This MUST come after all API routers so /api/v1/* is matched first.
# - /assets/* is served as static files (hashed JS/CSS bundles).
# - Every other non-API path falls back to index.html so React Router can
#   handle client-side routes (/properties, /leases, …) including hard refresh.
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Unknown API routes should still return a JSON 404, not the SPA shell.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # Serve a real file if it exists (favicon, vite.svg, …); otherwise the
        # SPA entry point.
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")

    print(f"✓ React frontend mounted from {FRONTEND_DIST}")
else:
    print(f"⚠ {FRONTEND_DIST} not found — React UI will not be served. "
          f"Build it with: cd frontend && npm run build")

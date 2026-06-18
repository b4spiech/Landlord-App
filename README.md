# Property Management App — Phase 1 (Backend Foundation)

Full-stack property management system for APEX Element Group LLC. This phase
delivers the **FastAPI + PostgreSQL backend foundation**: data models, Alembic
migrations, an idempotent seed, and CRUD APIs.

> The lease-break workflow, DocuSign integration, email approval gates, and the
> React frontend are scoped for later phases. Service/router stubs for those
> will build on the models defined here.

## Stack

- **FastAPI** + **SQLModel** (SQLAlchemy 2.0) + **PostgreSQL** (psycopg 3)
- **Alembic** migrations
- **Pydantic v2** schemas
- Python 3.12

## Prerequisites

- Python 3.12
- A PostgreSQL database. For local dev, the included Docker one-liner works:

```bash
docker run -d --name pm_postgres \
  -e POSTGRES_USER=pm_user -e POSTGRES_PASSWORD=pm_pass -e POSTGRES_DB=property_mgmt \
  -p 5432:5432 postgres:16-alpine
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env        # adjust DATABASE_URL if needed

# 3. Run migrations
alembic upgrade head

# 4. Seed initial data (Arizona jurisdiction, owner, mgmt co, property, templates)
python -m app.seed

# 5. Run the API
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

## Project Layout

```
app/
  main.py            FastAPI app, CORS, router registration
  config.py          Pydantic settings (.env)
  database.py        Engine + session factory (SQLModel sessions)
  seed.py            Idempotent seed (run: python -m app.seed)
  models/            SQLModel tables (one module per entity group)
    enums.py         Status / type enums
    base.py          UUID PK + created_at/updated_at mixin
  schemas/           Pydantic Create/Read/Update schemas
  routers/           CRUD routers
alembic/             Migration environment + versions
```

## Data Model

15 tables: `jurisdiction`, `owner`, `management_company`, `property`, `unit`,
`tenant`, `lease`, `lease_tenant`, `payment`, `expense`, `lease_template`,
`lease_break_request`, `lease_break_option`, `lease_break_document`,
`email_approval`.

All tables use UUID primary keys and timezone-aware `created_at` / `updated_at`.

## API (v1)

CRUD (POST / GET list / GET {id} / PATCH) for:

| Resource | Base path | List filters |
|----------|-----------|--------------|
| Owners | `/api/v1/owners` | — |
| Management companies | `/api/v1/management-companies` | — |
| Properties | `/api/v1/properties` | `owner_id`, `management_company_id` |
| Units | `/api/v1/units` | `property_id` |
| Tenants | `/api/v1/tenants` | — |
| Leases | `/api/v1/leases` | `property_id`, `unit_id`, `status_filter` |

- `POST /api/v1/leases` accepts nested `lease_tenants`.
- `GET /api/v1/leases/{id}` returns the lease with its `tenants` and `payments`.

Health check: `GET /health`.

## Migrations

```bash
# After changing models, autogenerate a revision:
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Seed Data

`python -m app.seed` creates (idempotently):

- **Jurisdiction**: Arizona, with early-termination rules JSON (deposit cap 1.5×,
  14-day return, duty to mitigate, 3× rent buyout cap).
- **Owner**: Brad Spiech (Byron Center, MI).
- **Management company**: APEX Element Group LLC.
- **Property**: 6255 N Camino Pimeria Alta, Unit 60, Tucson AZ 85718 (condo).
- **Unit**: 60.
- **Templates**: buyout options email, termination agreement, move-out statement.

Re-running prints how many records were created vs. skipped.

## Deployment

A `Procfile` is included for Railway/Heroku-style platforms (runs
`alembic upgrade head` then uvicorn). Set `DATABASE_URL` in the platform
environment; `postgres://` and `postgresql://` URLs are normalized to the
psycopg3 driver automatically.

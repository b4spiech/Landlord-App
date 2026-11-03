# APEX Property Management

Property management app for APEX Element Group LLC. One FastAPI service and
one PostgreSQL database serve two sites:

| Site | Hostnames | Who | Protection |
|------|-----------|-----|------------|
| **Landlord app** | `dev-app.apexelementgrp.com` | Owner/manager | Cloudflare Access login + JWT check in the backend |
| **Public site** | `apexelementgrp.com`, `www.`, `tours.` | Prospective renters | Public; can reach only `/api/v1/public/*` |

## Features

**Landlord app**
- Owners, management companies, jurisdictions, HOAs (with documents), tenants.
- Properties with a photo, time zone (tour times use the property's local time),
  beds/baths/square feet.
- Leases linked to exactly one property (set on create, changeable in *Edit
  lease*, or added from the property page with **+ New lease**). AI import of
  lease documents (Claude).
- **Lease archiving:** property pages show only current leases (active, draft,
  pending signature). Expired, terminated and broken leases are archived: they
  stay in *Leases → Archived* (filterable by property) and nothing is deleted.
- **Lease break** buyout workflow with document preview, explicit email send
  approval, and DocuSign e-signature routing.
- **Listings:** *List this property* → listing editor (rent, deposit, available
  date, minimum lease, pets, utilities, description, private notes), ordered
  photos (first = cover), and where it's advertised (Zillow Rental Manager,
  Facebook, Craigslist, …, with URL + date). Status: Draft → Listed → Closed
  (rented / withdrawn). One open listing per property.

**Public site**
- Company homepage with currently listed homes.
- `/homes/:id` listing page with photo gallery and details.
- `/tour` request form (home, contact info, date/time 8:00 am–7:30 pm local,
  photo ID, SMS opt-in). *Submission is wired up in a later phase; it currently
  shows "online booking opens soon".*
- `/privacy` and `/sms-terms` (used for Twilio toll-free verification).

**Roadmap (tour requests):** access-code inventory per property → tour request
submission + landlord alerts → approve/decline → access code sent 30 min before
the tour → post-tour feedback. Notifications by email (Cloudflare Email
Service) and SMS (Twilio).

## Stack

- **Backend:** FastAPI, SQLModel (SQLAlchemy 2.0), PostgreSQL (psycopg 3),
  Alembic, Pydantic v2, Python 3.12.
- **Frontend:** React 19 + TypeScript + Vite + Tailwind (`frontend/`). The
  landlord app and public site are separate lazy-loaded bundles chosen by
  hostname. `frontend/dist` is committed so Railway can serve it without Node.

## Local setup

```bash
# Postgres
docker run -d --name pm_postgres \
  -e POSTGRES_USER=pm_user -e POSTGRES_PASSWORD=pm_pass -e POSTGRES_DB=property_mgmt \
  -p 5432:5432 postgres:16-alpine

pip install -r requirements.txt
cp .env.example .env          # leave CLOUDFLARE_ACCESS_ENABLED=false locally
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload # API docs at http://localhost:8000/docs

cd frontend && npm ci && npm run dev   # http://localhost:5173
```

In local dev, add `?site=public` to the URL to view the public site
(`?site=landlord` to switch back).

After frontend changes, rebuild and commit the bundle:
`cd frontend && npm run build`.

## Project layout

```
app/
  main.py            FastAPI app, middleware, routers, SPA serving
  security.py        Host gatekeeper (public vs landlord) + Cloudflare Access JWT check
  config.py          Settings (.env)
  models/            SQLModel tables
  schemas/           Pydantic request/response models
  routers/           API routers (public.py = the only API on public hosts)
  services/          Email, DocuSign, lease parsing, lease-break math, time zones
  seed.py            Idempotent seed
alembic/             Migrations
frontend/src/
  App.tsx            Landlord app routes
  public/            Public site (PublicApp, pages, publicApi)
  site.ts            Picks which site to render from the hostname
tests/               pytest suite
```

## Data model

`jurisdiction`, `owner`, `management_company`, `property`, `property_photo`,
`hoa`, `hoa_document`, `tenant`, `lease`, `lease_tenant`, `lease_document`,
`payment`, `expense`, `lease_template`, `lease_break_request`,
`lease_break_option`, `lease_break_document`, `email_approval`, `listing`,
`listing_photo`.

All tables use UUID primary keys and timezone-aware `created_at`/`updated_at`.
Instants are stored in UTC; `property.time_zone` (IANA name, e.g.
`America/Phoenix`) is used to choose and display local times.

## API (v1)

Landlord APIs (require Cloudflare Access when enabled; 404 on public hosts):

| Resource | Base path | Notes |
|----------|-----------|-------|
| Owners | `/api/v1/owners` | |
| Management companies | `/api/v1/management-companies` | |
| Jurisdictions | `/api/v1/jurisdictions` | |
| HOAs | `/api/v1/hoas` | documents |
| Properties | `/api/v1/properties` | filters `owner_id`, `management_company_id`; `/photo` |
| Tenants | `/api/v1/tenants` | |
| Leases | `/api/v1/leases` | filter `property_id`; nested `lease_tenants` on create; `property_id` must exist and can be changed, never cleared; document import |
| Lease breaks | `/api/v1/lease-breaks` | workflow; `/webhook/docusign` (HMAC-verified, no Access JWT) |
| Listings | `/api/v1/listings` | filters `property_id`, `status_filter`, `open_only`; `/publish`, `/unpublish`, `/close`, `/photos` |

Public API (anonymous; only live listings and safe fields):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/public/site` | Company name and contact email |
| `GET /api/v1/public/listings` | Listed homes |
| `GET /api/v1/public/listings/{id}` | One listed home |
| `GET /api/v1/public/listings/{id}/photos/{photo_id}` | Listing photo |

Health check: `GET /health`.

## Configuration

See `.env.example`. Key settings:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres URL (`postgres://` is normalized for psycopg 3) |
| `CLOUDFLARE_ACCESS_ENABLED` | `true` in production: landlord APIs require a valid Access JWT |
| `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD` | Access team domain and the landlord app's AUD tag |
| `CF_ACCESS_ALLOWED_EMAILS` | Optional extra allow-list of landlord emails |
| `PUBLIC_HOSTS` | Hostnames that serve only the public site |
| `PUBLIC_SITE_URL` | Base URL for links sent to prospects (`https://tours.apexelementgrp.com`) |
| `SMTP_*` | Email via Cloudflare Email Service (`smtp.mx.cloudflare.net:465`, user `api_token`) |
| `DOCUSIGN_*` | E-signature; `DOCUSIGN_WEBHOOK_SECRET` must match the Connect HMAC key |
| `ANTHROPIC_API_KEY` | AI lease document parsing |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `LANDLORD_SMS_NUMBER` | SMS (used by the upcoming tour-request phases) |

## Tests

```bash
pytest -q        # needs DATABASE_URL pointing at a disposable Postgres database
```

Covers host gatekeeping, Access JWT validation, DocuSign webhook signatures,
the listing lifecycle and public visibility, and lease ↔ property linking.

## Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Seed data

`python -m app.seed` creates (idempotently): the Arizona jurisdiction (with
early-termination rules), owner, APEX Element Group LLC as management company,
the property at 6255 N Camino Pimeria Alta, Unit 60, Tucson AZ 85718, its HOA,
and the lease-break document templates.

## Deployment

Railway runs the `Procfile` (`alembic upgrade head`, seed, then uvicorn). DNS,
TLS, Access and email sending are on Cloudflare (`apexelementgrp.com` zone).
Pushing `dev` deploys.

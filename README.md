# APEX Property Management

Property management app for APEX Element Group LLC. One FastAPI service and
one PostgreSQL database serve two sites:

| Site | Hostnames | Who | Protection |
|------|-----------|-----|------------|
| **Landlord app** | `dev-app.apexelementgrp.com` | Owner/manager | Cloudflare Access login + JWT check in the backend |
| - **Door codes** (property page → *Door codes*): paste one-time codes from the
  lock's app (one per line or comma-separated; 3–20 digits/letters/`*`/`#`),
  with an optional expiry date and note. Codes go **Available → Held** (reserved
  for an approved tour) **→ Sent** (issued; never reused). Sent codes leave the
  list but stay in a history with who received them and when. Low-stock warning
  under 3 available. Only available codes can be removed. Reservation picks the
  code expiring soonest that is still valid on the tour date.
- **Tour requests** (*Tours* in the nav, red badge = needs review): list
  filtered by status, detail page with the visitor's info, tour time in the
  property's zone *and* Michigan time, the photo ID, and a log of every
  email/text sent.
  - **Approve** (pending; refused if the tour has passed or no door code is
    usable on that date): holds a code, tells the visitor they're approved and
    that the one-time code arrives 30 minutes before the tour.
  - **Decline** (pending): short polite message; the slot reopens.
  - **Cancel** (approved): releases an unsent code back to the pool (a sent code
    stays spent) and tells the visitor.
  - **Send code now / Resend**: emails (and texts, with consent) the code plus
    the visit rules — shoes off, all lights off when leaving, lock the door.
    Resend reuses the same code. Until the scheduler phase, use this about 30
    minutes before the tour.
  - An optional note is included in approve/decline/cancel messages.

**Public site** | `apexelementgrp.com`, `www.`, `tours.` | Prospective renters | Public; can reach only `/api/v1/public/*` |

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
  (rented / withdrawn). One open listing per property. If a listing has no
  photos of its own, the public site uses the property's photo as the cover.

**Public site**
- Company homepage with currently listed homes. Each home card has **Request a
  tour** (opens the form with that home preselected) and **Details**.
- `/homes/:id` listing page with photo gallery and details.
- `/tour` request form (`?home=<listing id>` preselects a home, shown as a summary
  card; a single listed home is selected automatically): home, name, email, mobile, date, start time (only open
  slots, in the home's local time), photo ID, optional SMS consent. Rules
  (enforced server-side): 30-minute tours starting 8:00 am–7:30 pm local, at
  least 2 hours ahead, up to 60 days out, one active booking per home per slot.
  Spam protection: hidden honeypot field + 5 submissions/hour per IP.
- On submit: the landlord gets an email (and a text if Twilio is set up) with a
  review link; the visitor gets an email confirmation (and a text only if they
  opted in). The exact consent wording and time are stored with the request.
- `/privacy` and `/sms-terms` (used for Twilio toll-free verification).

**Roadmap (tour requests):** ✅ submission + landlord alerts → ✅ door-code
inventory per property → ✅ approve/decline (+ manual send code) → access code sent automatically 30 min before the
tour → post-tour feedback → automatic photo-ID deletion 30 days after the tour
(the deletion date is already recorded on each request). Notifications by email (Cloudflare Email
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
`listing_photo`, `tour_request`, `tour_id_photo`, `notification_log`,
`access_code`.

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
| Door codes | `/api/v1/properties/{id}/access-codes` | `GET` (counts + active codes; `?history=true` adds sent), `POST` bulk add; `DELETE /api/v1/access-codes/{id}` (available only) |
| Tour requests | `/api/v1/tour-requests` | filters `status_filter`, `property_id`; `/{id}/id-photo` (no-store), `/{id}/notifications`; `POST /{id}/approve`, `/decline`, `/cancel` (body `{note}`), `/send-code` |

Public API (anonymous; only live listings and safe fields):

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/public/site` | Company name and contact email |
| `GET /api/v1/public/listings` | Listed homes |
| `GET /api/v1/public/listings/{id}` | One listed home |
| `GET /api/v1/public/listings/{id}/photos/{photo_id}` | Listing photo |
| `GET /api/v1/public/listings/{id}/property-photo` | Property photo (cover fallback when the listing has no photos) |
| `GET /api/v1/public/listings/{id}/availability?day=YYYY-MM-DD` | Open start times for that local day |
| `POST /api/v1/public/tour-requests` | Submit a tour request (multipart form incl. `id_photo`) |

Public listings include `photo_urls` (cover first), already resolved to
listing photos or the property-photo fallback.

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
| `LANDLORD_APP_URL` | Base URL for review links in landlord notifications |
| `LANDLORD_NOTIFY_EMAIL` | Where tour-request emails go (defaults to the first `CF_ACCESS_ALLOWED_EMAILS`) |
| `SMTP_*` | Email via Cloudflare Email Service (`smtp.mx.cloudflare.net:465`, user `api_token`) |
| `DOCUSIGN_*` | E-signature; `DOCUSIGN_WEBHOOK_SECRET` must match the Connect HMAC key |
| `ANTHROPIC_API_KEY` | AI lease document parsing |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | SMS via Twilio (skipped and logged if unset) |
| `LANDLORD_SMS_NUMBER` | Landlord's phone for tour-request texts |

## Tests

```bash
pytest -q        # needs DATABASE_URL pointing at a disposable Postgres database
```

Covers host gatekeeping, Access JWT validation, DocuSign webhook signatures,
the listing lifecycle and public visibility, lease ↔ property linking, and tour
booking (slot rules, time zones, double-booking, spam limits, notifications),
the door-code lifecycle (reserve/release/issue, expiry, no reuse), and
approve/decline/cancel/send-code with the exact visitor messages.

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

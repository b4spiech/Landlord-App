# APEX Property Management

Property management app for APEX Element Group LLC. One FastAPI service and
one PostgreSQL database serve two sites:

| Site | Hostnames | Who | Protection |
|------|-----------|-----|------------|
| **Landlord app** | `dev-app.apexelementgrp.com` | Owner/manager | Cloudflare Access login + JWT check in the backend |
| - **Door codes** (property page → *Door codes*, collapsed to a one-line summary
  until clicked; the tour-code low-stock warning always shows). Three kinds:
  - **Tour codes (one-time):** paste one-time codes from the lock's app (one per
    line or comma-separated; 3–20 digits/letters/`*`/`#`), optional expiry and
    note. **Available → Held** (reserved for an approved tour) **→ Sent**
    (never reused); sent codes move to a history with who received them.
    Reservation picks the code expiring soonest that is still valid on the tour
    date. Low-stock warning under 3 available.
  - **Tenant codes:** pre-programmed codes in a per-property pool; assign one to
    a tenant (people on the property's current lease are suggested first) and
    set it back to *Not assigned* when they move out. Deleting a tenant returns
    their codes to the pool.
  - **Landlord codes:** your own codes with a label.

  Tour automation only ever uses tour codes. Tenant and landlord codes are
  masked (`••••`) until *Show codes*. A code can't be live twice on one
  property across all kinds. Removal: unused tour codes; tenant codes once
  unassigned; landlord codes anytime.
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
    Resend reuses the same code. Normally not needed: the scheduler sends it.
  - Filters: Needs review, Approved, Declined, Completed, All. Completed tours
    show the visitor's feedback (rating, interested in applying, liked, concerns).
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
  approval, and DocuSign e-signature routing. *Leases → Lease Breaks* lists
  every request (and each lease page shows its own); opening one shows the
  request, options and documents, with **Delete**.
- **Listings:** *List this property* → listing editor (rent, deposit, available
  date, minimum lease, pets, utilities, description, private notes), ordered
  photos (first = cover), and where it's advertised (Zillow Rental Manager,
  Facebook, Craigslist, …, with URL + date). Status: Draft → Listed → Closed
  (rented / withdrawn). One open listing per property. If a listing has no
  photos of its own, the public site uses the property's photo as the cover.
- **Share link** (live listings — property page and listing editor): send the
  home's public page to someone who asked about it (e.g. a phone inquiry) by
  email and/or text, with an optional name and personal note. The email has a
  **Request a tour** button (`/tour?home=<id>`). Only text people who asked for
  the link; texts include STOP opt-out. Each send is
  logged and shown as *Shared before* history.

- **Deleting records** (properties, HOAs, owners, management companies,
  tenants, leases): a **Delete** button opens a warning that asks the server
  what would happen and lists it, and the delete button only unlocks after
  typing `DELETE`. Rules — financial/legal history is never removed silently:

  | Deleting a… | Blocked while it has… | Also deletes | Unlinks |
  |---|---|---|---|
  | Property | leases, expenses | its photo, listings + photos, door codes, tour requests (+ photo IDs, feedback, message log) | — |
  | HOA | — | its documents | properties (HOA becomes none) |
  | Owner | properties | — | — |
  | Management company | — | — | properties |
  | Tenant | any lease | — | — |
  | Lease | payments, a *signed* lease-break agreement | uploaded lease documents, unsigned lease-break requests (+ options, agreements, email drafts) | its tenants (tenant records kept) |
  | Lease break | a signed agreement | its options, generated agreements, email drafts | — |
- A property's HOA is changed in *Edit* (or the **Change/Set** link next to the
  HOA on the property page); choose *None* to remove it.

**Public site**
- Company homepage with currently listed homes. Each home card has **Request a
  tour** (opens the form with that home preselected) and **Details**.
- `/homes/:id` listing page with photo gallery and details.
- **Email sign-in before requesting a tour** (homepage and home pages stay
  open): the visitor enters their email, gets a 6-digit code (expires in 10
  min, 5 tries, max 3 codes per email per 10 min and 10 per IP per hour), and
  is then signed in on that device for 30 days via an HttpOnly, SameSite=Lax
  (Secure over HTTPS) cookie. Only hashes of codes and session tokens are
  stored. The verified email is shown locked on the form ("Not you?" signs
  out) and is the address every tour message goes to; the server ignores any
  typed email. The SMS opt-in wording is also shown on the sign-in step so it's
  publicly visible for carrier review.
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

**Automation** (`app/services/scheduler.py`, runs every minute inside the web
process; `SCHEDULER_ENABLED`, `SCHEDULER_INTERVAL_SECONDS`):
1. **Door codes** go out 30 minutes before each approved tour (immediately if
   approved later). Up to 3 attempts, 5 minutes apart. If a code can't be
   delivered (none available, or every channel failed) the landlord gets an
   urgent "ACTION NEEDED" email + text.
2. **One hour after a tour ends** it's marked *completed* and the visitor gets a
   private feedback link (`/feedback/<token>`), only if they received a code and
   the tour was within the last 3 days. The landlord is emailed/texted when
   feedback arrives.
3. **Photo IDs** are deleted once their date passes (30 days after the tour).

Rows are claimed with `SELECT … FOR UPDATE SKIP LOCKED` and progress is saved
before sending, so overlapping instances during a deploy never double-send.

**Roadmap (tour requests):** ✅ submission + landlord alerts → ✅ door-code
inventory per property → ✅ approve/decline (+ manual send code) → ✅ access code sent automatically 30 min before the
tour → ✅ post-tour feedback → ✅ automatic photo-ID deletion 30 days after the tour. Notifications by email (Cloudflare Email
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
  site.ts            Picks which site to render: the server injects
                     <meta name="apex-site"> from PUBLIC_HOSTS (so staging's
                     dev-tours. works); hostname list is only a fallback
tests/               pytest suite
```

## Data model

`jurisdiction`, `owner`, `management_company`, `property`, `property_photo`,
`hoa`, `hoa_document`, `tenant`, `lease`, `lease_tenant`, `lease_document`,
`payment`, `expense`, `lease_template`, `lease_break_request`,
`lease_break_option`, `lease_break_document`, `email_approval`, `listing`,
`listing_photo`, `tour_request`, `tour_id_photo`, `notification_log`,
`access_code`, `tour_feedback`, `email_verification`, `visitor_session`.

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
| Lease breaks | `/api/v1/lease-breaks` | `GET` list (filter `lease_id`); workflow; `/webhook/docusign` (HMAC-verified, no Access JWT) |
| Listings | `/api/v1/listings` | filters `property_id`, `status_filter`, `open_only`; `/publish`, `/unpublish`, `/close`, `/photos`; `POST /{id}/share` `{name, email, phone, note}`, `GET /{id}/shares` |
| Door codes | `/api/v1/properties/{id}/access-codes` | `GET` tour codes (counts + active; `?history=true` adds sent), `GET …/managed` (tenant + landlord codes and tenant suggestions), `POST` bulk add (`kind`: `one_time` / `tenant` / `landlord`); `POST /api/v1/access-codes/{id}/assign` `{tenant_id}` / `/unassign`; `DELETE /api/v1/access-codes/{id}` |
| Deletes | `/api/v1/{kind}/{id}/delete-preview` (GET), `/api/v1/{kind}/{id}` (DELETE) for `properties`, `hoas`, `owners`, `management-companies`, `tenants`, `leases`, `lease-breaks` | preview lists blockers / also-deletes / unlinks; DELETE returns 409 if blocked |
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
| `POST /api/v1/public/auth/start` / `verify` / `logout`, `GET /me` | Visitor email sign-in (code by email → session cookie) |
| `POST /api/v1/public/tour-requests` | Submit a tour request (multipart form incl. `id_photo`); requires a signed-in visitor, email taken from the session |
| `GET/POST /api/v1/public/feedback/{token}` | Post-tour feedback form (token from the private link) |

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
| `SMTP_*` | Email via Cloudflare Email Service (`smtp.mx.cloudflare.net:465`, user `api_token`). Messages carry a display name (`SMTP_FROM_NAME`, default "APEX Element Group"), `Date`, `Message-ID` and `Reply-To` (`SMTP_REPLY_TO`, default `SMTP_FROM`) |
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
approve/decline/cancel/send-code with the exact visitor messages, and the
scheduler (send timing, retries + landlord alerts, completion + feedback
requests, photo-ID deletion), the feedback form, and visitor email sign-in
(codes, lockout, expiry, rate limits, cookie flags, hashed storage), and
record deletion (previews, blockers, cascades, unlinking).
`tests/conftest.py` provides `sign_in(client, email)` for tests that submit tours. `tests/conftest.py` turns
the background loop off; tests call `run_due_jobs(now)` directly.

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

Two Railway environments, each with its own Postgres database. Each deploy runs
the `Procfile` (`alembic upgrade head`, seed, then uvicorn).

| Environment | Branch | Public site | Landlord app |
|-------------|--------|-------------|--------------|
| **Production** | `main` | `apexelementgrp.com`, `www.`, `tours.` | `app.apexelementgrp.com` |
| **Staging** | `dev` | `dev-tours.apexelementgrp.com` (behind Cloudflare Access) | `dev-app.apexelementgrp.com` |

Workflow: push to `dev` → test on staging → open a PR `dev` → `main` to release.

One Cloudflare Access application protects `app.`, `dev-app.` and `dev-tours.`
(same AUD tag, so `CF_ACCESS_AUD` is identical in both environments). DNS, TLS,
Access and email sending are on Cloudflare (`apexelementgrp.com` zone).

Per-environment variables (everything else is shared): `DATABASE_URL`,
`PUBLIC_HOSTS`, `PUBLIC_SITE_URL`, `LANDLORD_APP_URL`, `ALLOWED_ORIGINS`, and
`DOCUSIGN_*` (demo vs production). The code defaults to the production
hostnames, so staging must set these explicitly.

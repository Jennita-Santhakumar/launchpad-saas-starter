# Orbit

[![CI](https://github.com/KabileshRajaselvan/orbit-saas-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/KabileshRajaselvan/orbit-saas-kit/actions/workflows/ci.yml)

A multi-tenant SaaS starter kit: JWT + OAuth authentication, workspace/tenant isolation with
roles, Stripe-shaped billing (subscribe, cancel, billing portal, webhook-driven status updates),
and a usage analytics dashboard.

```
Browser (React + Vite + Tailwind + Recharts)
  |
  v
FastAPI (api)
  |-- Auth: bcrypt password hashing, JWT access (15m) + refresh (14d, rotate-on-use,
  |     stored hashed) tokens; Authlib OAuth (Google, GitHub) upserts a User and issues
  |     the same JWT pair
  |-- Tenant isolation: every workspace-scoped route depends on get_current_workspace,
  |     which 404s (not 403) if the caller isn't a WorkspaceMember - a non-member can't
  |     even confirm the workspace exists
  |-- Rate limiting: slowapi + Redis, strict per-IP limits on /auth/login and /auth/signup,
  |     a per-workspace limit on event ingestion
  |-- Billing: one interface (stripe_client), two implementations - MockStripeClient
  |     (default) or the real `stripe` SDK, selected by STRIPE_MOCK. The mock implements
  |     Stripe's actual webhook-signing scheme (t=..,v1=hmac_sha256(secret, "{t}.{payload}"))
  |     so /webhooks/stripe's signature verification is genuinely exercised, not stubbed
  \-- Postgres: users / workspaces / workspace_members / subscriptions / usage_events /
        refresh_tokens

Redis <- rate-limit counters
Postgres <- all application state (Alembic-migrated)
```

## Why this project

A hiring-manager-facing demonstration of the auth/billing/analytics core every real SaaS
product needs, built with the pieces that are easy to fake actually working: JWT rotation that
survives concurrent requests, tenant isolation that's tested (not just implied by a
`workspace_id` column), and a billing webhook whose signature verification runs the same HMAC
code path Stripe's real servers use - proven by round-tripping a signed event through the API
and watching a subscription's status flip in Postgres. See "Design Decisions & Trade-offs" below
for where this deviates from the source PRD's literal spec and why.

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 |
| Cache / rate-limit store | Redis |
| Auth | bcrypt (passlib), JWT (python-jose), Authlib OAuth (Google, GitHub) |
| Billing | Stripe-shaped interface; mocked by default, real `stripe` SDK as a config-swappable option |
| Frontend | React + TypeScript + Vite + Tailwind + Recharts |
| Migrations | Alembic |
| Tests | pytest (unit + integration against real Postgres/Redis) |
| CI | GitHub Actions (lint, test, build) |

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5193
- API: http://localhost:8020 (interactive docs at `/docs`)
- Postgres: localhost:5452, Redis: localhost:6400 (offset from the default 5432/6379 so this
  can run alongside sibling portfolio projects without a port clash)

Stripe is mocked out of the box, so there's nothing to configure to try billing end to end.
OAuth buttons are present but inert until you set `GOOGLE_CLIENT_ID`/`GITHUB_CLIENT_ID` (etc.)
in `.env` - see the trade-offs section.

## API reference

| Endpoint | Description |
|---|---|
| `POST /auth/signup` | Create a user, returns a token pair |
| `POST /auth/login` | Authenticate, returns a token pair |
| `POST /auth/refresh` | Rotates a refresh token for a new pair |
| `GET /auth/oauth/{provider}/login` | Redirects to Google/GitHub |
| `GET /auth/oauth/{provider}/callback` | Completes the OAuth exchange, redirects to the frontend with tokens |
| `GET /users/me` | Current user |
| `POST /workspaces` | Create a workspace (creator becomes `owner`) |
| `GET /workspaces` | List workspaces the caller belongs to, with their role in each |
| `GET /workspaces/{id}` | Workspace detail (member-only, 404 otherwise) |
| `GET/POST /workspaces/{id}/members` | List / invite members |
| `PATCH/DELETE /workspaces/{id}/members/{member_id}` | Change role / remove (owner, admin only) |
| `GET /workspaces/{id}/billing` | Current subscription, or `null` |
| `POST /workspaces/{id}/billing/subscribe` | Subscribe to a plan (owner, admin only) |
| `POST /workspaces/{id}/billing/cancel` | Cancel (owner, admin only) |
| `POST /workspaces/{id}/billing/portal` | Mock billing-portal session URL (owner, admin only) |
| `POST /webhooks/stripe` | Signature-verified webhook receiver |
| `POST /workspaces/{id}/analytics/events` | Ingest a usage event |
| `GET /workspaces/{id}/analytics/summary` | Per-event-type counts + daily timeseries |

Full interactive docs at `/docs` once the api service is running.

## Design Decisions & Trade-offs

The source PRD's sample code is Next.js (API routes, NextAuth, Prisma). Where this
implementation deviates and why:

- **FastAPI + React, not Next.js full-stack.** This portfolio's standing default stack is
  Python + React unless a project's domain clearly points elsewhere; a generic SaaS starter
  kit doesn't, so it follows the same backend/frontend split as the other projects in this
  series rather than the PRD's literal Next.js sample.
- **Stripe is mocked, not wired to Stripe's real test-mode API.** `MockStripeClient` and the
  real `stripe` SDK sit behind one shared interface (`app/integrations/stripe_client.py`), so
  flipping `STRIPE_MOCK=false` + setting `STRIPE_SECRET_KEY` is the entire migration path, not
  a rewrite. What's *not* faked: webhook signature verification runs Stripe's actual HMAC
  scheme against a fixed test secret, so `/webhooks/stripe`'s 200/400 behavior is proven against
  real signed (and deliberately tampered) payloads, not stubbed out.
- **OAuth is implemented for real but not live-tested against real Google/GitHub apps.** The
  authorization-code-flow code (`app/services/oauth_service.py`, Authlib) is genuine - it's the
  integration tests that mock the provider HTTP calls (realistic Google/GitHub-shaped userinfo
  payloads) rather than requiring registered OAuth apps and a live browser flow. The login
  buttons work once real client credentials are set in `.env`.
- **No password-reset flow.** No email-sending infrastructure exists in this stack; adding a
  reset-token table without a way to deliver the email would be a half-feature, so it's cut
  entirely rather than built as a dead end.
- **No server-side logout / session revocation endpoint.** Refresh tokens are rotate-on-use and
  simply expire (14 days); logging out is a client-side token clear. A production system with
  higher stakes would add an explicit revoke-on-logout endpoint - straightforward to add given
  the existing `refresh_tokens.revoked_at` column, just not built since nothing currently reads
  a "logged out but token not yet expired" state.
- **Refresh/access tokens carry a `jti` claim.** Caught via a real integration-test failure, not
  by inspection: two tokens issued for the same user within the same second are otherwise
  byte-identical JWTs (`iat`/`exp` only have second precision), which collided on the refresh
  table's `token_hash` unique constraint under back-to-back logins. A random `jti` per token
  fixes it and is the standard reason JWTs carry one.

## Tests

```bash
cd backend
pytest                      # unit tests always run; integration tests skip if Postgres/Redis aren't reachable
ruff check .
```

CI (`.github/workflows/ci.yml`) runs the full suite against real Postgres/Redis service
containers. **56 tests, all passing** against a real Postgres 16 + Redis 7 (not mocked) as of
the last verified run - including the webhook signature round-trip (valid signature updates a
subscription's status; a tampered one 400s) and tenant-isolation checks (a non-member gets 404,
not 403, on every workspace-scoped route).

## Verified live

Beyond the automated suite, the full `docker compose up --build` stack was run and exercised
through the live HTTP API on this machine: signup, workspace creation, a mock subscription,
usage-event ingestion, the analytics summary/timeseries endpoints, and a real signed
`customer.subscription.updated` webhook that flipped a subscription's status in Postgres from
`active` to `past_due` - end to end, no shortcuts.

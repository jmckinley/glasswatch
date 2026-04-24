# Installing Glasswatch

**AI-driven patch management for enterprise security teams.**

---

## Option 1: One-Command Install (Recommended)

Requires [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/).

```bash
curl -fsSL https://raw.githubusercontent.com/jmckinley/glasswatch/main/install.sh | bash
```

The installer will:
1. Check prerequisites (Docker, curl)
2. Prompt for API keys (Anthropic, Resend, Sentry, scanner credentials)
3. Generate a secure `.env` with random secrets
4. Write a `docker-compose.yml` configured for production
5. Pull images, start services, run migrations, load demo data
6. Print your access URL and configuration status

**Done in under 5 minutes.**

---

## Option 2: Manual Docker Compose

### Step 1 — Clone and configure

```bash
git clone https://github.com/jmckinley/glasswatch.git
cd glasswatch
cp .env.example .env
```

Edit `.env` and fill in your values (see [API Keys](#api-keys) below).

### Step 2 — Start services

```bash
docker compose up -d
```

### Step 3 — Run migrations

```bash
docker compose exec backend alembic upgrade head
```

### Step 4 — Access the app

Open http://localhost:3000 and click **Try Demo** to verify everything works.

---

## Option 3: Railway (Cloud Hosting)

1. Fork this repo on GitHub
2. Create a new project at [railway.app](https://railway.app)
3. Connect your fork — Railway auto-detects `backend/` and `frontend/`
4. Add a PostgreSQL and Redis service
5. Set environment variables (see table below)
6. Deploy

Full Railway walkthrough: [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)

---

## API Keys

Gather these before installing. The installer prompts for each one interactively.

| Key | Required for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | AI assistant, NLP rules | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) |
| `RESEND_API_KEY` | Invite emails, weekly digest | [resend.com/api-keys](https://resend.com/api-keys) |
| `RESEND_FROM_EMAIL` | Sender address for emails | Your verified Resend domain |
| `SENTRY_DSN` | Error tracking (recommended) | [sentry.io](https://sentry.io) → Project Settings → DSN |
| `TENABLE_ACCESS_KEY` + `TENABLE_SECRET_KEY` | Tenable scanner integration | Tenable Cloud → Settings → API Keys |
| `QUALYS_USERNAME` + `QUALYS_PASSWORD` + `QUALYS_API_URL` | Qualys integration | Your Qualys subscription |
| `RAPID7_HOST` + `RAPID7_API_KEY` | Rapid7 InsightVM integration | InsightVM → Administration → API Keys |
| `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` | Google OAuth login | [console.cloud.google.com](https://console.cloud.google.com) → Credentials |
| `GITHUB_CLIENT_ID` + `GITHUB_CLIENT_SECRET` | GitHub OAuth login | [github.com/settings/developers](https://github.com/settings/developers) |

> **Note:** Only `DATABASE_URL` and `SECRET_KEY` are strictly required to start. Everything else enables specific features — you can add keys later by editing `.env` and restarting.

---

## Required Environment Variables

These must be set for the app to start:

```env
SECRET_KEY=<random 32+ character string>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/glasswatch
SYNC_DATABASE_URL=postgresql://user:pass@host:5432/glasswatch
REDIS_URL=redis://localhost:6379/0
FRONTEND_URL=http://localhost:3000
```

The installer generates `SECRET_KEY`, `DATABASE_URL`, and `REDIS_URL` automatically.

---

## Verify Your Installation

After starting, check these endpoints:

```bash
# Backend health check
curl http://localhost:8000/health

# API docs (Swagger)
open http://localhost:8000/docs

# Frontend
open http://localhost:3000
```

Click **Try Demo** on the login page — you should land on a dashboard with sample data.

---

## Connecting Your Scanners

Once the app is running, point your scanner to send webhooks:

| Scanner | Webhook URL |
|---|---|
| Tenable | `https://your-domain/api/v1/webhooks/tenable` |
| Qualys | `https://your-domain/api/v1/webhooks/qualys` |
| Rapid7 | `https://your-domain/api/v1/webhooks/rapid7` |

Add your `X-Webhook-Secret` from **Settings → Integrations** to the scanner webhook config.

No scanner? Import vulnerability and asset data via CSV at `/import`.

---

## Inviting Your Team

1. Log in as admin
2. Go to **Settings → Team**
3. Enter your teammate's email + role
4. Click **Send Invite**

They'll receive a link to set their password and join your workspace.

---

## Upgrading

```bash
# Docker Compose
docker compose pull && docker compose up -d
docker compose exec backend alembic upgrade head

# Railway
Push to main — Railway auto-deploys
```

---

## Troubleshooting

**Demo login fails** → Check `DATABASE_URL` is set and migrations ran (`alembic upgrade head`)

**Dashboard shows errors** → Open browser console; usually a missing migration or wrong `FRONTEND_URL`

**Emails not sending** → Verify `RESEND_API_KEY` is set and your sender domain is verified in Resend

**AI assistant not responding** → Check `ANTHROPIC_API_KEY` is set; the assistant falls back to pattern matching without it

**Slack alerts not working** → In Settings → Integrations, verify the webhook URL is under **Notifications** (not Integrations — they're separate)

**OR-Tools warning in logs** → Expected. The optimizer uses a heuristic fallback. Not a bug.

Full troubleshooting: [docs/IMPLEMENTATION_GUIDE.md#troubleshooting](docs/IMPLEMENTATION_GUIDE.md#troubleshooting)

---

## More Documentation

- [User Guide](docs/USER_GUIDE.md) — for security analysts and managers using the app
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) — deep-dive for IT/ops teams
- [Architecture](docs/ARCHITECTURE.md) — system design and component overview
- [FAQ](docs/FAQ.md) — common questions
- [API Docs](https://glasswatch-production.up.railway.app/docs) — interactive Swagger UI

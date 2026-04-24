# Glasswatch Implementation Guide

**Version:** Alpha · **Last updated:** April 2026

---

This guide is for the IT or SecOps team responsible for deploying and operating Glasswatch within your organization. It covers deployment options, environment configuration, scanner integration, authentication setup, and ongoing operations.

If you're a security analyst or manager trying to use Glasswatch after it's deployed, see the [User Guide](USER_GUIDE.md) instead.

---

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [First-Run Setup](#first-run-setup)
3. [Scanner Integration](#scanner-integration)
4. [Authentication Setup](#authentication-setup)
5. [Notification Setup](#notification-setup)
6. [CSV Data Import](#csv-data-import)
7. [SIEM and CMDB Integration](#siem-and-cmdb-integration)
8. [Maintenance and Operations](#maintenance-and-operations)
9. [Troubleshooting](#troubleshooting)

---

## Deployment Options

### Option A: Railway (Recommended for Alpha)

Railway is the fastest path to a running Glasswatch deployment. No infrastructure to provision, no Kubernetes expertise required. This is the recommended option for alpha evaluation and initial production deployments.

**Prerequisites:**
- A Railway account ([railway.com](https://railway.com))
- A GitHub account with the Glasswatch repository forked or cloned

**Step-by-step:**

**1. Create a Railway project.**

Log into Railway and click **New Project → Deploy from GitHub Repo**. Connect your GitHub account if prompted, then select the Glasswatch repository.

**2. Add databases.**

In the Railway project dashboard, click **+ New → Database → PostgreSQL**. Railway provisions a managed PostgreSQL instance and exposes a `DATABASE_URL` you can reference in other services.

Repeat for Redis: **+ New → Database → Redis**. Redis is used for caching and session management.

**3. Configure the backend service.**

Railway will detect the `Dockerfile.prod` in the repo root. Set the following environment variables in the backend service settings:

**Required environment variables:**

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Railway reference syntax — auto-populated |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Railway reference syntax — auto-populated |
| `SECRET_KEY` | Random 64-char string | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENV` | `production` | |
| `DEBUG` | `false` | |
| `BACKEND_CORS_ORIGINS` | `https://your-frontend.up.railway.app` | Update after generating frontend domain |
| `PROJECT_NAME` | `Glasswatch` | |

**Optional environment variables:**

| Variable | Value | Notes |
|----------|-------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic key | Enables AI assistant and NLP rules |
| `WORKOS_API_KEY` | WorkOS key | Enables enterprise SSO |
| `WORKOS_CLIENT_ID` | WorkOS client ID | Required with WORKOS_API_KEY |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Enables Google login |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Required with GOOGLE_CLIENT_ID |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | Enables GitHub login |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | Required with GITHUB_CLIENT_ID |
| `RESEND_API_KEY` | Resend API key | Enables email notifications |
| `FRONTEND_URL` | `https://your-frontend.up.railway.app` | Used in outbound notification links |
| `SLACK_ALERT_CHANNEL` | `#security-alerts` | Default Slack channel for alerts |
| `NVD_API_KEY` | NVD API key | Faster NVD data pulls (free to get) |
| `SENTRY_DSN` | Sentry DSN | Error tracking |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT expiry; default is 30 |

**4. Configure the frontend service.**

Add a second service from the same repository. Click **+ New → GitHub Repo** and select the Glasswatch repo again. Name it "frontend."

In the service settings:
- Dockerfile Path: `Dockerfile.frontend`
- Watch Paths: `frontend/**`

Set these environment variables:

| Variable | Value |
|----------|-------|
| `BACKEND_URL` | `http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000` |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.up.railway.app` |

**5. Generate public domains.**

For each service (backend and frontend), go to **Settings → Networking → Generate Domain**. Railway assigns a `.up.railway.app` domain with SSL handled automatically.

Once you have the frontend domain, go back and update `BACKEND_CORS_ORIGINS` and `FRONTEND_URL` on the backend service.

**6. Verify deployment.**

Visit your frontend URL. You should see the Glasswatch login page. Click **Try Demo** to confirm the frontend can reach the backend.

If you see a 500 error, check that migrations have run (see [First-Run Setup](#first-run-setup)).

---

### Option B: Docker Compose (Self-Hosted)

Use Docker Compose if you want to run Glasswatch on your own infrastructure — a VM, on-premises server, or cloud instance.

**Prerequisites:**
- Docker 24.0+
- Docker Compose 2.20+
- A server with at least 2 GB RAM and 20 GB disk space

**1. Clone the repository.**

```bash
git clone https://github.com/your-org/glasswatch.git
cd glasswatch
```

**2. Create your environment file.**

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

```env
# Required
DATABASE_URL=postgresql+asyncpg://glasswatch:glasswatch-secret@postgres:5432/glasswatch
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<generate a random 64-char string>
ENV=production
DEBUG=false

# Optional but recommended
FRONTEND_URL=https://your-domain.example.com
ANTHROPIC_API_KEY=<your key>

# OAuth (leave blank to disable)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Notifications (leave blank to disable)
RESEND_API_KEY=
```

**3. Start the stack.**

```bash
docker compose -f docker-compose.prod.yml up -d
```

This starts PostgreSQL, Redis, the FastAPI backend, and the Next.js frontend.

**4. Run migrations.**

```bash
docker compose exec backend alembic upgrade head
```

**5. Verify.**

The frontend is available at `http://localhost:3000` (or your server's IP). The backend API is at `http://localhost:8000`.

**Keeping it running:**

Add `restart: always` to each service in `docker-compose.prod.yml` if you want services to restart automatically after a server reboot. For production, put nginx or a reverse proxy in front with SSL termination.

---

## First-Run Setup

After deploying, before onboarding your team:

**1. Verify demo login.**

Navigate to your frontend URL and click **Try Demo**. If it loads a dashboard with sample data, your deployment is healthy.

**2. Run database migrations.**

If you're on Railway:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Authenticate and link to your project
railway login
railway link

# Run migrations
railway run -s backend alembic upgrade head
```

Or use Railway's built-in shell: open the backend service → **Shell** tab, then run:

```bash
alembic upgrade head
```

If you're on Docker Compose:

```bash
docker compose exec backend alembic upgrade head
```

Migrations are idempotent — running them multiple times is safe.

**3. Load seed data (optional).**

For a fresh deployment (not the demo), your database will be empty. You can either:
- Import your own assets and vulnerabilities via CSV (see [CSV Data Import](#csv-data-import))
- Use the scanner webhooks once your integrations are set up

**4. Set FRONTEND_URL.**

The `FRONTEND_URL` environment variable must point to your deployed frontend URL. This is used in outbound Slack/email notifications so that links (e.g., "Click here to review bundle #42") resolve correctly. Set it in your Railway environment variables or `.env` file.

---

## Scanner Integration

Glasswatch receives vulnerability data from scanners via webhooks. When a scan completes, your scanner POSTs the results to a Glasswatch endpoint, which ingests, deduplicates, and scores the findings immediately.

All scanner webhooks follow the pattern:

```
POST https://your-backend.up.railway.app/api/v1/webhooks/{scanner}
X-Webhook-Secret: <your_secret>
```

The secret is configured per integration in Settings → Connections. Generate a random string and enter it in both Glasswatch and your scanner's notification settings.

---

### Tenable

Tenable (Nessus / Tenable.io) can push findings to Glasswatch via its notification system.

**Get your API keys:**

1. Log into [cloud.tenable.com](https://cloud.tenable.com)
2. Go to **Settings → My Account → API Keys**
3. Generate an access key and secret key

**Configure in Glasswatch:**

1. Navigate to **Settings → Integrations → Tenable**
2. Enter your access key and secret key
3. Save — Glasswatch will generate a webhook secret for you

**Configure in Tenable:**

In Tenable.io, go to **Settings → Notifications** and add a new webhook with:
- URL: `https://your-backend.up.railway.app/api/v1/webhooks/tenable`
- Method: POST
- Secret: the secret Glasswatch generated

Trigger the webhook on "Scan Completed." Tenable will now push findings to Glasswatch each time a scan finishes.

---

### Qualys

**Get your credentials:**

Log into your Qualys platform and locate your username, password, and platform URL (e.g., `qualysapi.qualys.com`).

**Configure in Glasswatch:**

1. Navigate to **Settings → Integrations → Qualys**
2. Enter your platform URL, username, and password
3. Save

**Configure webhook in Qualys:**

In Qualys, go to the notification settings for your scan policy and add a webhook pointing to:
```
https://your-backend.up.railway.app/api/v1/webhooks/qualys
```

Add the webhook secret in the request headers as `X-Webhook-Secret`.

---

### Rapid7

**Get your credentials:**

Log into your Rapid7 InsightVM instance and go to **Administration → API Keys** to generate an API key. Note your platform host URL (e.g., `https://your-region.api.insight.rapid7.com`).

**Configure in Glasswatch:**

1. Navigate to **Settings → Integrations → Rapid7**
2. Enter your host URL and API key
3. Save

**Configure webhook in Rapid7:**

In InsightVM, configure an event-driven scan notification to POST to:
```
https://your-backend.up.railway.app/api/v1/webhooks/rapid7
```

with `X-Webhook-Secret` set to the secret from Glasswatch.

---

## Authentication Setup

### Demo Mode

Demo mode works out of the box — no configuration needed. Anyone can log in with the demo button. This is fine for evaluation but should be disabled before rolling out to your team. (Configure real auth below, then remove or restrict the demo route.)

### Email and Password

Email/password login is enabled by default. Users register with their email and a password. No additional configuration needed.

For self-managed deployments, you may want to disable self-registration and create accounts manually through the admin panel. This is configurable in Settings → User Management.

### Google OAuth

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → Credentials**
2. Create an OAuth 2.0 Client ID (Web Application type)
3. Add your Glasswatch backend URL to the authorized redirect URIs: `https://your-backend.up.railway.app/api/v1/auth/google/callback`
4. Copy the Client ID and Client Secret
5. Set in your environment:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

Google login will appear on the login page automatically once these are set.

### GitHub OAuth

1. Go to [github.com/settings/developers](https://github.com/settings/developers) → **New OAuth App**
2. Set the Authorization callback URL to: `https://your-backend.up.railway.app/api/v1/auth/github/callback`
3. Copy the Client ID and generate a Client Secret
4. Set in your environment:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

### WorkOS SSO (Enterprise)

WorkOS provides enterprise SSO with support for SAML, OKTA, Azure AD, and other identity providers.

1. Create an account at [workos.com](https://workos.com) and configure your organization's identity provider
2. Get your API key and Client ID from the WorkOS dashboard
3. Set in your environment:
   ```
   WORKOS_API_KEY=sk_live_...
   WORKOS_CLIENT_ID=client_...
   ```

Users from your organization can now authenticate via SSO. The first time a user logs in through SSO, Glasswatch creates their account automatically.

---

## Notification Setup

### Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App → From Scratch**
2. Name the app (e.g., "Glasswatch") and select your workspace
3. Go to **Incoming Webhooks** → Enable Incoming Webhooks
4. Click **Add New Webhook to Workspace**, choose the channel for alerts, and copy the webhook URL
5. In Glasswatch, navigate to **Settings → Integrations → Slack**
6. Paste the webhook URL and save
7. Click **Test** to verify

Glasswatch will now send formatted Slack messages to that channel for any alert rule configured to use Slack as a delivery channel.

### Microsoft Teams

1. In Teams, go to your target channel → **⋯ → Connectors**
2. Find **Incoming Webhook** and click **Configure**
3. Name the connector, optionally upload an icon, and copy the webhook URL
4. In Glasswatch, go to **Settings → Integrations → Microsoft Teams**
5. Paste the webhook URL and save

### Email (Resend)

Glasswatch uses Resend for transactional email delivery.

1. Create an account at [resend.com](https://resend.com)
2. Add and verify your sender domain (follow Resend's DNS setup guide)
3. Generate an API key
4. Set in your environment: `RESEND_API_KEY=re_...`
5. Optionally configure a `FROM_EMAIL` address (defaults to `alerts@your-domain.com` or similar)

Once configured, alert rules with Email as a delivery channel will send formatted HTML emails through Resend.

---

## CSV Data Import

If you're not using scanner webhooks yet, or you're migrating historical vulnerability data, you can import via CSV.

Navigate to **Import** in the sidebar. Download the template for the data type you're importing.

### Vulnerability CSV

Required columns:

```
asset_name, cve_id, severity, cvss_score, discovered_date
```

Full format example:

```csv
asset_name,cve_id,severity,cvss_score,discovered_date,description,patch_available
prod-web-01,CVE-2024-1234,critical,9.8,2024-03-01,Remote code execution in libssl,true
prod-db-01,CVE-2023-5678,high,7.5,2024-02-15,SQL injection via malformed query,true
staging-app-01,CVE-2024-9999,medium,5.3,2024-03-10,Information disclosure,false
```

Notes:
- `asset_name` must match the name of an existing asset in Glasswatch. Import assets first if needed.
- `severity` must be one of: `critical`, `high`, `medium`, `low`
- `discovered_date` must be ISO 8601 format: `YYYY-MM-DD`
- If `patch_available` is omitted, it defaults to `false`

### Asset CSV

Required columns:

```
name, type, environment
```

Full format example:

```csv
name,type,environment,ip_address,owner_team,criticality
prod-web-01,server,production,10.0.1.10,platform,5
prod-db-01,database,production,10.0.1.20,database,5
staging-app-01,server,staging,10.0.2.10,platform,3
dev-worker-01,server,development,10.0.3.10,engineering,2
```

Notes:
- `type` must be one of: `server`, `container`, `database`, `cloud_instance`, `application`
- `environment` must be one of: `production`, `staging`, `development`
- `criticality` is an integer 1–5 (default: 3 if omitted)
- `ip_address` is optional but recommended for deduplication against scanner data

After upload, Glasswatch shows a summary of rows created, updated, and any errors. Fix validation errors and re-upload — duplicate rows are updated in place, not duplicated.

---

## SIEM and CMDB Integration

Glasswatch exposes REST endpoints for pulling vulnerability and asset data into downstream systems.

### Authentication

Generate an API key in **Settings → API Keys**. Use it as a header:

```
GET /api/v1/export/vulnerabilities
X-API-Key: your_api_key
```

### Export Endpoints

**Vulnerability export:**

```
GET /api/v1/export/vulnerabilities
GET /api/v1/export/vulnerabilities?format=csv
GET /api/v1/export/vulnerabilities?severity=critical&kev_only=true
GET /api/v1/export/vulnerabilities?environment=production
```

**Asset export:**

```
GET /api/v1/export/assets
GET /api/v1/export/assets?format=csv
GET /api/v1/export/assets?environment=production&criticality=5
```

Both endpoints default to JSON. Add `?format=csv` for CSV output.

### Scheduling Automated Pulls

Use a cron job or your SIEM's scheduled connector to pull data on a regular basis. Example using curl:

```bash
# Pull critical vulnerabilities as CSV, daily
curl -s \
  -H "X-API-Key: your_api_key" \
  "https://your-backend.up.railway.app/api/v1/export/vulnerabilities?severity=critical&format=csv" \
  > /tmp/glasswatch-critical-vulns-$(date +%Y%m%d).csv
```

For SIEM integrations, configure the connector to authenticate with the X-API-Key header and point at the JSON export endpoint. Most SIEMs (Splunk, Elastic, Chronicle) support custom HTTP polling connectors.

---

## Maintenance and Operations

### Database Backups

**Railway:** Railway's managed PostgreSQL includes point-in-time recovery. Enable it in the database service settings. For additional protection, set up scheduled exports:

```bash
# From Railway shell
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

**Docker Compose:**

```bash
docker compose exec postgres pg_dump -U glasswatch glasswatch > backup-$(date +%Y%m%d).sql
```

Run this as a daily cron job and store the dumps somewhere safe (S3, GCS, off-site).

### Health Monitoring

Check deployment health at:

```
GET /health
```

Returns `{"status": "ok"}` when the service is healthy. Use this as your uptime monitor probe URL (UptimeRobot, Pingdom, etc.).

For detailed health (database connection status, dependency checks):

```
GET /health/detailed
```

### Log Access

**Railway:** Open the backend service → **Logs** tab. Logs are available in real time and searchable. Filter by log level or text.

**Docker Compose:**

```bash
docker compose logs backend -f --tail 100
```

### Updating Glasswatch

**Railway:** Push a new commit to the connected branch. Railway will automatically rebuild and redeploy. Rollback by going to the backend service → **Deployments** tab and redeploying a previous build.

**Docker Compose:**

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
docker compose exec backend alembic upgrade head
```

---

## Troubleshooting

**Demo login fails / database errors on startup**

The most common cause is a missing or malformed `DATABASE_URL`. On Railway, ensure you're using Railway's reference syntax (`${{Postgres.DATABASE_URL}}`) rather than a hardcoded value. Also confirm the PostgreSQL service is running and healthy before the backend starts.

On Docker Compose, verify the `DATABASE_URL` in your `.env` uses `postgresql+asyncpg://` (not `postgresql://`). The asyncpg driver requires this prefix.

**500 errors on the dashboard after a fresh deploy**

Migrations probably haven't run yet. Connect to the backend shell and run `alembic upgrade head`. The dashboard queries several tables that only exist after migrations complete.

**Notifications not sending to Slack**

The most common issue is an incorrect webhook URL path. Slack webhook URLs look like `https://hooks.slack.com/services/T.../B.../...` — they're long and easy to truncate accidentally. Verify the full URL is pasted correctly in Settings → Integrations → Slack.

Also check that alert rules are configured with Slack as a delivery channel (Settings → Alert Rules). Having a Slack webhook configured doesn't automatically send anything — you need at least one alert rule pointing at it.

**OR-Tools warning in logs**

You may see a log message like: `OR-Tools solver timed out; using heuristic fallback`. This is expected behavior when the optimization problem is large (many vulnerabilities and assets). The heuristic fallback still produces a good bundle schedule — it just isn't provably optimal. No action needed.

**Frontend shows "Failed to fetch" or CORS errors**

The `BACKEND_CORS_ORIGINS` environment variable on the backend must include your frontend's exact origin URL, including the protocol (`https://`). If you changed your frontend domain, update this variable and redeploy the backend.

**SSO login redirects fail**

Verify that the redirect URI configured in your OAuth provider (Google, GitHub, or WorkOS) exactly matches what Glasswatch expects:
- Google: `https://your-backend/api/v1/auth/google/callback`
- GitHub: `https://your-backend/api/v1/auth/github/callback`

Trailing slashes and http vs. https mismatches will cause the redirect to fail.

**Scanner webhooks not ingesting**

1. Confirm the webhook URL in your scanner matches your backend's public URL exactly
2. Confirm the `X-Webhook-Secret` header value matches what's configured in Settings → Connections
3. Check the backend logs for incoming webhook requests — if you see 401, the secret is wrong; if you see 422, the payload format may not match what Glasswatch expects for that scanner

For any issue not covered here, check the interactive API docs at `https://your-backend.up.railway.app/docs` or contact support.

# Deploying Glasswatch on Railway

## Architecture

Railway runs 3 services from this repo:

```
                    ┌──────────────┐
                    │   Frontend   │
    Users ────────► │  (Next.js)   │ ──────► Backend API
                    │  Port 3000   │         (internal)
                    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │   Backend    │
                    │  (FastAPI)   │
                    │  Port 8000   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────┴──────┐          ┌──────┴──────┐
       │ PostgreSQL   │          │    Redis     │
       │  (managed)   │          │  (managed)   │
       └─────────────┘          └─────────────┘
```

## Quick Start

### 1. Create a Railway Project

1. Go to [railway.com](https://railway.com) and create a new project
2. Select "Deploy from GitHub repo"
3. Connect your `jmckinley/glasswatch` repository

### 2. Add Databases

In the Railway project dashboard:

1. Click **+ New** → **Database** → **PostgreSQL**
2. Click **+ New** → **Database** → **Redis**

Railway auto-provisions these and provides connection URLs.

### 3. Configure Backend Service

Railway will detect the Dockerfile. Configure it:

**Settings:**
- Root Directory: `/` (project root)
- Dockerfile Path: `Dockerfile.prod`
- Watch Paths: `backend/**`

**Environment Variables:**
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
ENV=production
DEBUG=false
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
PROJECT_NAME=Glasswatch
BACKEND_CORS_ORIGINS=https://your-frontend.up.railway.app,https://glasswatch.io
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Note: Railway uses `${{ServiceName.VARIABLE}}` syntax for referencing other services.

### 4. Configure Frontend Service

Add a second service from the same repo:

1. Click **+ New** → **GitHub Repo** → select `glasswatch` again
2. Name it "frontend"

**Settings:**
- Root Directory: `/`
- Dockerfile Path: `Dockerfile.frontend`
- Watch Paths: `frontend/**`

**Environment Variables:**
```
BACKEND_URL=http://${{backend.RAILWAY_PRIVATE_DOMAIN}}:8000
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

### 5. Generate Domains

For each service, go to **Settings** → **Networking** → **Generate Domain**:
- Backend: `glasswatch-api.up.railway.app`
- Frontend: `glasswatch.up.railway.app`

### 6. Custom Domain (Optional)

1. Add your domain in Railway (e.g., `app.glasswatch.io`)
2. Update DNS with the CNAME Railway provides
3. Railway handles SSL automatically

## Environment Variables Reference

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Redis connection | `${{Redis.REDIS_URL}}` |
| `SECRET_KEY` | JWT signing key | Random 64-char string |
| `ENV` | Environment name | `production` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `false` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token TTL | `30` |
| `SENTRY_DSN` | Sentry error tracking | none |
| `NVD_API_KEY` | NVD vulnerability data | none |
| `WORKOS_API_KEY` | WorkOS SSO | none |

## Database Migrations

After first deploy, run migrations via Railway CLI or shell:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to project
railway link

# Run migrations against the backend service
railway run -s backend alembic upgrade head
```

Or use Railway's built-in shell:
1. Click on backend service → **Shell** tab
2. Run: `alembic upgrade head`

## Scaling

Railway auto-scales within your plan limits. To configure:

- **Backend:** 2+ replicas recommended for production
- **PostgreSQL:** Railway Hobby plan includes 1GB, upgrade for production
- **Redis:** Railway provides managed Redis with persistence

## Monitoring

- Railway provides built-in metrics (CPU, RAM, network)
- Sentry DSN → set `SENTRY_DSN` env var for error tracking
- Health check at `/health` is configured in `railway.toml`
- Detailed health at `/health/detailed` for debugging

## Estimated Cost

| Service | Hobby Plan | Pro Plan |
|---------|-----------|----------|
| Backend | $5/mo | Usage-based |
| Frontend | $5/mo | Usage-based |
| PostgreSQL | Included | $5+ |
| Redis | Included | $5+ |
| **Total** | **~$5-10/mo** | **~$20-40/mo** |

## Rollback

Railway keeps deployment history. To rollback:
1. Go to the service → **Deployments** tab
2. Click on a previous successful deployment
3. Click **Redeploy**

## Troubleshooting

**Build fails:**
- Check Dockerfile paths match your repo structure
- Ensure `requirements.txt` has all dependencies

**Database connection errors:**
- Verify `DATABASE_URL` uses the Railway reference syntax
- Check PostgreSQL service is running
- asyncpg needs `postgresql+asyncpg://` prefix — Railway provides `postgresql://`, so update config to handle both

**Frontend can't reach backend:**
- Use Railway private networking (`RAILWAY_PRIVATE_DOMAIN`) for service-to-service
- Public domain for browser-to-backend requests

**Health check fails:**
- Backend needs database connection for `/health` — ensure DB is up first
- Increase `healthcheckTimeout` if cold starts are slow

# Field Name Audit - April 21, 2026

## Summary

Completed comprehensive frontend/backend field name audit. Fixed all mismatches in commit `ac06cc8`.

## Fixed Issues

### 1. Vulnerabilities List Page
- **Was**: Interface expected `data.items` wrapper
- **Now**: Uses `data.vulnerabilities` (matches backend)
- **Impact**: Vuln list was empty, now displays 25 real vulnerabilities

### 2. Vulnerability Object Fields
- **Was**: Interface expected `description` and `affected_assets_count`
- **Now**: Uses `title`, `exploit_available`, `patch_available`, `is_critical`
- **Impact**: Table now shows correct titles + exploit/patch status badges

### 3. Vulnerability Stats
- **Was**: `stats.with_patches`
- **Now**: `stats.patches_available` + `stats.exploits_available`
- **Impact**: Stats cards now show correct patch/exploit counts (22/10)

### 4. Dashboard Asset Fetch
- **Was**: `assetsApi.list({limit: 1})` then tried to filter
- **Now**: `assetsApi.list({limit: 100})`
- **Impact**: Dashboard now correctly counts internet-exposed (via `is_internet_facing`) and critical assets (criticality >= 4)

### 5. Maintenance Windows Backend
- **Was**: `datetime.utcnow()` compared to tz-aware DB timestamps → TypeError
- **Now**: `datetime.now(timezone.utc)` with tz normalization
- **Impact**: `/api/v1/maintenance-windows` now returns 200 instead of 500

### 6. CORS Configuration
- **Was**: CORSMiddleware configured but origins from wrong config source
- **Now**: `settings.BACKEND_CORS_ORIGINS` overrides security_config when set
- **Impact**: Frontend can now call backend APIs directly (no proxy needed)

## Verified Working

```bash
# All endpoints return correct shapes
✅ /api/v1/vulnerabilities → {vulnerabilities: [...], total, skip, limit}
✅ /api/v1/vulnerabilities/stats → {patches_available, exploits_available, ...}
✅ /api/v1/maintenance-windows → {items: [...], total, skip, limit}
✅ /api/v1/goals → [...] (plain array)
✅ /api/v1/assets → {assets: [...], total, skip, limit}
✅ /api/v1/bundles → {items: [...], total, skip, limit}
✅ CORS headers present for Railway frontend origin
```

## Still Mock/Placeholder

These don't break anything, just not wired to real APIs yet:

1. **Schedule page** — uses `mockWindows` instead of `/api/v1/maintenance-windows`
2. **Dashboard risk_score** — `trend: "down"` and `reduction_7d: 12.4` are hardcoded
3. **Dashboard bundles** — `scheduled: 0`, `next_window: null`, `pending_approval: 0`

## Backend Endpoints Requiring Auth

These correctly require Bearer tokens (not broken, just auth-protected):

- `/api/v1/approvals` — uses strict `get_current_user` (not compat layer)
- `/api/v1/activities/` — requires token (frontend sends it correctly)

## Test Results

Frontend at https://frontend-production-ef3e.up.railway.app now displays:
- **Dashboard**: Real vuln/asset/goal counts
- **Vulnerabilities page**: 25 vulns with titles, severities, KEV badges, exploit/patch status
- **Goals page**: 3 real goals with progress bars
- **Assets page**: 12 real assets with types/platforms

Backend at https://glasswatch-production.up.railway.app:
- All paginated list endpoints work
- CORS headers present
- Demo login works (`/api/v1/auth/demo-login`)
- Maintenance windows endpoint fixed (was 500, now 200)

## Next Steps

Optional frontend wiring (not blocking):
1. Wire schedule page to `/api/v1/maintenance-windows` + `/api/v1/bundles`
2. Add historical data for dashboard risk trend calculation
3. Wire dashboard bundle stats to `/api/v1/bundles/stats`

All core functionality is working with real data.

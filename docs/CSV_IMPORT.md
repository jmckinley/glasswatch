# CSV Import Reference

Glasswatch supports bulk data import via CSV files. This is the fastest way to get started without a live scanner integration.

---

## Import Types

| Type | Endpoint | What it does |
|---|---|---|
| [Vulnerabilities](#vulnerabilities-csv) | `POST /api/v1/import/vulnerabilities/csv` | Import CVEs + link them to assets |
| [Assets](#assets-csv) | `POST /api/v1/import/assets/csv` | Import your asset inventory |

Both are accessible in the UI at **Settings → Import** (or `/import`).

---

## Vulnerabilities CSV

### Required columns

| Column | Required | Description | Example |
|---|---|---|---|
| `asset_name` (or `asset_ip`, `hostname`) | ✅ | Asset hostname or IP address | `web-prod-01` or `10.0.1.42` |
| `cve_id` (or `cve`) | ✅ | CVE identifier | `CVE-2024-21887` |
| `severity` | ✅ | Severity level | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |

### Optional columns

| Column | Description | Default | Example |
|---|---|---|---|
| `cvss_score` | CVSS v3 base score (0.0–10.0) | — | `9.8` |
| `discovered_date` | When the vuln was found (YYYY-MM-DD) | today | `2024-01-15` |

### Example

```csv
asset_name,cve_id,severity,cvss_score,discovered_date
web-prod-01,CVE-2024-21887,CRITICAL,9.8,2024-03-01
web-prod-01,CVE-2024-3400,CRITICAL,10.0,2024-04-12
db-prod-02,CVE-2024-29824,HIGH,8.1,2024-04-01
app-staging-01,CVE-2023-44487,HIGH,7.5,2023-10-01
api-prod-01,CVE-2024-5910,MEDIUM,6.1,2024-05-01
```

### Notes
- Assets are **upserted** by name/IP — a new asset record is created automatically if it doesn't exist
- Vulnerabilities are **upserted** by CVE ID — existing records are reused, not duplicated
- If `severity` is unrecognized, it defaults to `MEDIUM`
- The column header `asset_ip` or `hostname` also works in place of `asset_name`
- File must be UTF-8 encoded, max 10 MB

---

## Assets CSV

### Required columns

| Column | Required | Description | Example |
|---|---|---|---|
| `name` (or `hostname`, `identifier`) | ✅ | Asset name or identifier | `web-prod-01` |

### Optional columns

| Column | Description | Allowed values | Default |
|---|---|---|---|
| `type` | Asset type | `server`, `container`, `function`, `database`, `application`, `network`, `endpoint` | `server` |
| `environment` | Deployment environment | `production`, `staging`, `development`, `test` | `production` |
| `ip_address` (or `ip`) | Primary IP address | any valid IP | — |
| `owner_team` (or `team`) | Owning team name | any string | — |
| `criticality` | Business criticality score (1–5, where 5 = most critical) | `1`–`5` | `3` |

### Example

```csv
name,type,environment,ip_address,owner_team,criticality
web-prod-01,server,production,10.0.1.10,Platform,5
web-prod-02,server,production,10.0.1.11,Platform,5
db-prod-01,database,production,10.0.2.10,Data,5
db-prod-02,database,production,10.0.2.11,Data,4
app-staging-01,server,staging,10.0.3.10,Platform,2
api-gateway,application,production,10.0.1.1,Platform,5
cache-prod-01,server,production,10.0.2.20,Data,3
k8s-node-01,container,production,10.0.4.1,Infra,4
```

### Notes
- Assets are **upserted** by name/identifier — re-importing updates existing records
- `criticality` values outside 1–5 are clamped to the nearest valid value
- Unknown `type` values default to `server`

---

## Scanner Export Formats

These are the columns you'll see in common scanner exports and how they map to Glasswatch fields:

### Tenable Nessus / Tenable.io export
Tenable exports a "Vulnerabilities" CSV. Relevant columns:

| Tenable column | Glasswatch column |
|---|---|
| `Host` | `asset_name` |
| `Plugin ID` | _(not used — use CVE Name)_ |
| `CVE` | `cve_id` |
| `Risk` | `severity` (Critical/High/Medium/Low) |
| `CVSS v3.0 Base Score` | `cvss_score` |
| `Plugin Publication Date` | `discovered_date` |

Before importing, rename columns to match Glasswatch expected names (or just use `asset_name`, `cve_id`, `severity`, `cvss_score`, `discovered_date`).

### Qualys export
Qualys exports a "Vulnerability Summary" or "Confirmed Vulnerabilities" CSV:

| Qualys column | Glasswatch column |
|---|---|
| `IP` | `asset_ip` |
| `DNS` | `asset_name` |
| `CVE ID` | `cve_id` |
| `Severity` | `severity` (map: 5=CRITICAL, 4=HIGH, 3=MEDIUM, 2=LOW) |
| `CVSS Base` | `cvss_score` |
| `First Detected` | `discovered_date` |

### Rapid7 InsightVM export
Rapid7 provides a "Vulnerability Export" with:

| Rapid7 column | Glasswatch column |
|---|---|
| `Asset Name` | `asset_name` |
| `Asset IP Address` | `asset_ip` |
| `Vulnerability Title` | _(informational)_ |
| `CVE IDs` | `cve_id` (take first CVE if multiple) |
| `Severity` | `severity` |
| `CVSS Score` | `cvss_score` |
| `First Found` | `discovered_date` |

### Microsoft Defender / MDVM export
Defender for Endpoint exports via the Security portal as "Vulnerability Assessment":

| Defender column | Glasswatch column |
|---|---|
| `Machine Name` | `asset_name` |
| `CVE ID` | `cve_id` |
| `Severity` | `severity` |
| `CVSS Score` | `cvss_score` |
| `First Seen` | `discovered_date` |

---

## Tips

**Minimum viable import:**
If your scanner only gives you CVE IDs and hostnames, that's enough:
```csv
asset_name,cve_id,severity
web-prod-01,CVE-2024-21887,CRITICAL
```

**Batch large datasets:**
The 10 MB limit handles ~50,000 rows. For larger datasets, split into multiple files or use the API directly.

**Verify before importing:**
The UI shows a 5-row preview before you click "Import". Use it to confirm the headers parsed correctly.

**Idempotent:**
Re-importing the same file is safe — records are upserted, not duplicated.

**Error reporting:**
The import returns an error list for any rows that couldn't be processed (missing required fields, invalid formats). Fix those rows and re-import the corrected file.

---

## API Usage (programmatic import)

```bash
# Get auth token
TOKEN=$(curl -s -X POST https://your-domain/api/v1/auth/demo-login | jq -r '.access_token')

# Import vulnerabilities
curl -X POST https://your-domain/api/v1/import/vulnerabilities/csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@vulnerabilities.csv"

# Import assets
curl -X POST https://your-domain/api/v1/import/assets/csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@assets.csv"
```

Response format:
```json
{
  "rows_processed": 150,
  "assets_created": 12,
  "vulns_created": 48,
  "links_created": 150,
  "errors": []
}
```

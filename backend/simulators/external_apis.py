"""
Glasswatch External API Simulators
===================================
Simulates: Tenable.io, Qualys VMPC, Rapid7 InsightVM, Slack, Microsoft Teams,
           Jira, ServiceNow, CISA KEV, NVD (NIST), EPSS, Resend

Run:
    uvicorn backend.simulators.external_apis:app --port 8099

All endpoints accept ?simulate_error=true to return a 429/500/503 for error-path testing.
All endpoints log requests to stdout with timestamp, method, path, and auth presence.

Auth validation mirrors the real services exactly:
  - Tenable:     X-ApiKeys: accessKey=...;secretKey=...
  - Qualys:      Authorization: Basic <base64>
  - Rapid7:      Authorization: Basic <base64>
  - Slack:       Authorization: Bearer xoxb-...
  - Teams:       No auth (webhook URL is the secret)
  - Jira:        Authorization: Basic <base64>
  - ServiceNow:  Authorization: Basic <base64>
  - Resend:      Authorization: Bearer re_...
  - CISA/NVD/EPSS: No auth
"""

import base64
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Glasswatch External API Simulators",
    description="Simulates Tenable, Qualys, Rapid7, Slack, Teams, Jira, ServiceNow, "
                "CISA KEV, NVD, EPSS, and Resend for local integration testing.",
    version="1.0.0",
)


def _log(req: Request, auth_present: bool = False) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[SIM] {ts} {req.method} {req.url.path} auth={'yes' if auth_present else 'no'}")


def _maybe_error(simulate_error: bool, methods: tuple[int, ...] = (429, 500, 503)) -> None:
    if simulate_error:
        code = random.choice(methods)
        raise HTTPException(status_code=code, detail=f"Simulated error ({code})")


# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

SAMPLE_CVES = [
    {
        "cve_id":       "CVE-2024-21887",
        "vendor":       "Ivanti",
        "product":      "Connect Secure",
        "cvss3":        9.8,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.94212,
        "epss_pct":     0.99932,
        "kev":          True,
        "title":        "Ivanti Connect Secure Command Injection",
        "asset":        "vpn-gateway-01",
        "plugin_id":    210887,
    },
    {
        "cve_id":       "CVE-2024-1709",
        "vendor":       "ConnectWise",
        "product":      "ScreenConnect",
        "cvss3":        9.8,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.97415,
        "epss_pct":     0.99971,
        "kev":          True,
        "title":        "ConnectWise ScreenConnect Authentication Bypass",
        "asset":        "app-server-01",
        "plugin_id":    210001,
    },
    {
        "cve_id":       "CVE-2024-3400",
        "vendor":       "Palo Alto Networks",
        "product":      "PAN-OS",
        "cvss3":        10.0,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.95700,
        "epss_pct":     0.99950,
        "kev":          True,
        "title":        "PAN-OS GlobalProtect OS Command Injection",
        "asset":        "vpn-gateway-01",
        "plugin_id":    203400,
    },
    {
        "cve_id":       "CVE-2024-23897",
        "vendor":       "Jenkins",
        "product":      "Jenkins",
        "cvss3":        9.1,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.78300,
        "epss_pct":     0.99231,
        "kev":          False,
        "title":        "Jenkins Arbitrary File Read via CLI",
        "asset":        "app-server-01",
        "plugin_id":    209700,
    },
    {
        "cve_id":       "CVE-2023-44487",
        "vendor":       "IETF",
        "product":      "HTTP/2",
        "cvss3":        7.5,
        "severity_str": "high",
        "severity_int": 3,
        "qualys_sev":   4,
        "epss":         0.42100,
        "epss_pct":     0.97120,
        "kev":          True,
        "title":        "HTTP/2 Rapid Reset Attack",
        "asset":        "web-server-01",
        "plugin_id":    209001,
    },
    {
        "cve_id":       "CVE-2024-4040",
        "vendor":       "CrushFTP",
        "product":      "CrushFTP",
        "cvss3":        9.8,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.91200,
        "epss_pct":     0.99811,
        "kev":          True,
        "title":        "CrushFTP VFS Escape and Arbitrary File Read",
        "asset":        "web-server-01",
        "plugin_id":    204040,
    },
    {
        "cve_id":       "CVE-2024-27198",
        "vendor":       "JetBrains",
        "product":      "TeamCity",
        "cvss3":        9.8,
        "severity_str": "critical",
        "severity_int": 4,
        "qualys_sev":   5,
        "epss":         0.88010,
        "epss_pct":     0.99712,
        "kev":          False,
        "title":        "JetBrains TeamCity Authentication Bypass",
        "asset":        "k8s-node-01",
        "plugin_id":    207198,
    },
    {
        "cve_id":       "CVE-2024-6387",
        "vendor":       "OpenBSD",
        "product":      "OpenSSH",
        "cvss3":        8.1,
        "severity_str": "high",
        "severity_int": 3,
        "qualys_sev":   4,
        "epss":         0.24700,
        "epss_pct":     0.96400,
        "kev":          True,
        "title":        "OpenSSH Unauthenticated Remote Code Execution (regreSSHion)",
        "asset":        "db-server-01",
        "plugin_id":    206387,
    },
    {
        "cve_id":       "CVE-2024-38094",
        "vendor":       "Microsoft",
        "product":      "SharePoint",
        "cvss3":        7.2,
        "severity_str": "high",
        "severity_int": 3,
        "qualys_sev":   4,
        "epss":         0.36100,
        "epss_pct":     0.97001,
        "kev":          True,
        "title":        "Microsoft SharePoint Server Remote Code Execution",
        "asset":        "app-server-01",
        "plugin_id":    208094,
    },
    {
        "cve_id":       "CVE-2024-49138",
        "vendor":       "Microsoft",
        "product":      "Windows Common Log File System Driver",
        "cvss3":        7.8,
        "severity_str": "high",
        "severity_int": 3,
        "qualys_sev":   4,
        "epss":         0.15300,
        "epss_pct":     0.93200,
        "kev":          True,
        "title":        "Windows CLFS Driver Privilege Escalation",
        "asset":        "k8s-node-01",
        "plugin_id":    209138,
    },
]

# For Tenable export flow: track per-UUID state (PROCESSING → FINISHED)
_export_state: dict[str, int] = {}  # uuid → call_count


# ---------------------------------------------------------------------------
# Simulator status
# ---------------------------------------------------------------------------

@app.get("/simulator/status")
async def simulator_status():
    """Health/status for the simulator itself."""
    return {
        "status": "ok",
        "simulator": "Glasswatch External API Simulators",
        "version": "1.0.0",
        "services": [
            "tenable", "qualys", "rapid7",
            "slack", "teams", "jira", "servicenow",
            "cisa_kev", "nvd", "epss", "resend",
        ],
        "sample_cves": len(SAMPLE_CVES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ===========================================================================
# TENABLE.IO
# ===========================================================================

def _require_tenable_auth(x_apikeys: Optional[str]) -> None:
    """Validate Tenable X-ApiKeys header format."""
    if not x_apikeys:
        raise HTTPException(status_code=401, detail="Missing X-ApiKeys header")
    if "accessKey=" not in x_apikeys or "secretKey=" not in x_apikeys:
        raise HTTPException(
            status_code=401,
            detail="Invalid X-ApiKeys format. Expected: accessKey=<key>;secretKey=<secret>",
        )


@app.get("/tenable/workbenches/vulnerabilities")
async def tenable_workbenches_vulnerabilities(
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: List workbench vulnerabilities."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    vulns = []
    for v in SAMPLE_CVES:
        vulns.append({
            "plugin_id": v["plugin_id"],
            "plugin_name": v["title"],
            "severity": v["severity_int"],
            "severity_id": v["severity_int"],
            "cvss3_base_score": v["cvss3"],
            "vuln_count": random.randint(1, 5),
            "plugin_family": "Web Servers" if "web" in v["asset"] else "General",
            "counts": {
                "affected_assets": random.randint(1, 3),
            },
        })

    return {
        "vulnerabilities": vulns,
        "total": len(vulns),
    }


@app.get("/tenable/workbenches/assets")
async def tenable_workbenches_assets(
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: List workbench assets."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    assets = []
    for name in ["web-server-01", "db-server-01", "app-server-01", "k8s-node-01", "vpn-gateway-01"]:
        assets.append({
            "id": str(uuid.uuid4()),
            "has_plugin_results": True,
            "created_at": "2024-01-15T00:00:00Z",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "last_scan_target": f"10.0.0.{random.randint(10, 250)}",
            "network_id": "00000000-0000-0000-0000-000000000000",
            "ipv4": [f"10.0.0.{random.randint(10, 250)}"],
            "fqdn": [f"{name}.internal.example.com"],
            "hostnames": [name],
            "operating_system": ["Linux Kernel 5.15" if "k8s" not in name else "Ubuntu 22.04"],
            "agent_name": [name],
        })

    return {"assets": assets, "total": len(assets)}


@app.get("/tenable/scans")
async def tenable_scans(
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: List scans."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    return {
        "scans": [
            {
                "id": 1001,
                "uuid": str(uuid.uuid4()),
                "name": "Weekly Full Scan",
                "status": "completed",
                "enabled": True,
                "creation_date": 1704067200,
                "last_modification_date": int(time.time()),
                "starttime": "20240115-020000",
                "timezone": "UTC",
                "folder_id": 3,
                "type": "scheduled",
            },
            {
                "id": 1002,
                "uuid": str(uuid.uuid4()),
                "name": "Critical Assets Scan",
                "status": "completed",
                "enabled": True,
                "creation_date": 1704067200,
                "last_modification_date": int(time.time()),
                "starttime": "20240115-030000",
                "timezone": "UTC",
                "folder_id": 3,
                "type": "scheduled",
            },
        ],
        "timestamp": int(time.time()),
    }


@app.post("/tenable/vulns/export")
async def tenable_export_start(
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: Start vulnerability export."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    export_uuid = str(uuid.uuid4())
    _export_state[export_uuid] = 0

    return {"export_uuid": export_uuid}


@app.get("/tenable/vulns/export/{export_uuid}/status")
async def tenable_export_status(
    export_uuid: str,
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: Poll export status (first call PROCESSING, second FINISHED)."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    if export_uuid not in _export_state:
        raise HTTPException(status_code=404, detail="Export UUID not found")

    _export_state[export_uuid] += 1
    call_count = _export_state[export_uuid]

    if call_count == 1:
        return {"status": "PROCESSING", "chunks_available": 0}
    else:
        return {"status": "FINISHED", "chunks_available": 1}


@app.get("/tenable/vulns/export/{export_uuid}/chunks/{chunk_id}")
async def tenable_export_chunk(
    export_uuid: str,
    chunk_id: int,
    request: Request,
    simulate_error: bool = Query(False),
    x_apikeys: Optional[str] = Header(None),
):
    """Tenable.io: Download export chunk."""
    _log(request, bool(x_apikeys))
    _require_tenable_auth(x_apikeys)
    _maybe_error(simulate_error)

    if export_uuid not in _export_state:
        raise HTTPException(status_code=404, detail="Export UUID not found")

    vulns = []
    for v in SAMPLE_CVES:
        vulns.append({
            "asset": {
                "device_type": "general-purpose",
                "fqdn": f"{v['asset']}.internal.example.com",
                "hostname": v["asset"],
                "id": str(uuid.uuid4()),
                "ipv4": f"10.0.0.{random.randint(10, 250)}",
                "operating_system": "Linux",
            },
            "first_found": "2024-01-15T00:00:00Z",
            "last_found": datetime.now(timezone.utc).isoformat(),
            "plugin": {
                "cve": [v["cve_id"]],
                "cvss3_base_score": v["cvss3"],
                "description": f"Simulated vulnerability: {v['title']}",
                "family": "Web Servers",
                "id": v["plugin_id"],
                "name": v["title"],
                "risk_factor": v["severity_str"].capitalize(),
                "solution": "Apply vendor-provided patches.",
                "synopsis": f"{v['title']} allows remote attackers to execute arbitrary code.",
            },
            "port": {"port": 443, "protocol": "TCP", "service": "www"},
            "severity": v["severity_str"],
            "severity_id": v["severity_int"],
            "state": "OPEN",
        })

    return vulns


# ===========================================================================
# QUALYS VMPC (XML responses)
# ===========================================================================

def _require_basic_auth(authorization: Optional[str], service: str) -> None:
    """Validate Basic authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail=f"Missing Authorization header for {service}")
    if not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail=f"Invalid auth scheme for {service}. Expected: Basic <base64>",
        )
    try:
        decoded = base64.b64decode(authorization[6:]).decode()
        if ":" not in decoded:
            raise ValueError("No colon separator")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid base64 credentials")


def _xml_response(root: Element) -> Response:
    """Return XML response with correct Content-Type."""
    xml_bytes = tostring(root, encoding="unicode", xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes
    return Response(content=xml_str, media_type="application/xml")


@app.get("/qualys/api/2.0/fo/scan/")
async def qualys_list_scans(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Qualys VMPC: List scans (XML response)."""
    _log(request, bool(authorization))
    _require_basic_auth(authorization, "Qualys")
    _maybe_error(simulate_error)

    root = Element("SCAN_LIST_OUTPUT")
    resp = SubElement(root, "RESPONSE")
    SubElement(resp, "DATETIME").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scan_list = SubElement(resp, "SCAN_LIST")

    for i, name in enumerate(["Full Network Scan", "Critical Assets Scan"], 1):
        scan = SubElement(scan_list, "SCAN")
        SubElement(scan, "ID").text = str(1000 + i)
        SubElement(scan, "TITLE").text = name
        SubElement(scan, "REF").text = f"scan/{1000 + i}"
        SubElement(scan, "TYPE").text = "Scheduled"
        SubElement(scan, "STATUS").text = "Finished"
        SubElement(scan, "LAUNCH_DATETIME").text = "2024-01-15T02:00:00Z"
        SubElement(scan, "DURATION").text = "02:30:00"
        SubElement(scan, "PROCESSED").text = "1"

    return _xml_response(root)


@app.post("/qualys/api/2.0/fo/report/")
async def qualys_create_report(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Qualys VMPC: Create/download vulnerability report (XML response)."""
    _log(request, bool(authorization))
    _require_basic_auth(authorization, "Qualys")
    _maybe_error(simulate_error)

    root = Element("VULN_LIST")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    for idx, v in enumerate(SAMPLE_CVES, 1):
        vuln = SubElement(root, "VULN")
        SubElement(vuln, "ID").text = str(idx)
        SubElement(vuln, "QID").text = str(90000 + v["plugin_id"])
        SubElement(vuln, "TITLE").text = v["title"]
        SubElement(vuln, "CATEGORY").text = "General remote services"
        SubElement(vuln, "CVE_ID").text = v["cve_id"]
        SubElement(vuln, "SEVERITY").text = str(v["qualys_sev"])
        SubElement(vuln, "CVSS_BASE").text = str(v["cvss3"])
        SubElement(vuln, "CVSS3_BASE").text = str(v["cvss3"])
        SubElement(vuln, "VENDOR").text = v["vendor"]
        SubElement(vuln, "PRODUCT").text = v["product"]
        SubElement(vuln, "DIAGNOSIS").text = f"Detected: {v['title']}"
        SubElement(vuln, "SOLUTION").text = "Apply vendor-provided patch immediately."
        SubElement(vuln, "RESULT").text = "VULNERABLE"
        SubElement(vuln, "HOST").text = v["asset"]
        SubElement(vuln, "IP").text = f"10.0.0.{random.randint(10, 250)}"
        SubElement(vuln, "LAST_DETECTED").text = "2024-01-15T00:00:00Z"
        SubElement(vuln, "FIRST_DETECTED").text = "2024-01-01T00:00:00Z"

    return _xml_response(root)


@app.get("/qualys/msp/about.php")
async def qualys_health(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Qualys VMPC: Health check endpoint."""
    _log(request, bool(authorization))
    _require_basic_auth(authorization, "Qualys")
    root = Element("ABOUT")
    SubElement(root, "VERSION").text = "10.3"
    SubElement(root, "BUILD_DATE").text = "2024-01-01"
    return _xml_response(root)


# ===========================================================================
# RAPID7 INSIGHTVM
# ===========================================================================

def _require_rapid7_auth(authorization: Optional[str]) -> None:
    """Validate Rapid7 Basic auth (also allows X-Api-Key style in health check)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header for Rapid7")
    if not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=401,
            detail="Invalid auth scheme for Rapid7. Expected: Basic <base64(user:pass)>",
        )
    try:
        decoded = base64.b64decode(authorization[6:]).decode()
        if ":" not in decoded:
            raise ValueError
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid base64 credentials")


def _rapid7_hal_links(path: str, page: int, size: int, total: int) -> list:
    base = f"/api/3{path}"
    links = [
        {"href": f"{base}?page={page}&size={size}", "rel": "self"},
        {"href": f"{base}?page=0&size={size}", "rel": "first"},
        {"href": f"{base}?page={(total - 1) // size}&size={size}", "rel": "last"},
    ]
    if page > 0:
        links.append({"href": f"{base}?page={page - 1}&size={size}", "rel": "prev"})
    if (page + 1) * size < total:
        links.append({"href": f"{base}?page={page + 1}&size={size}", "rel": "next"})
    return links


@app.get("/rapid7/api/3/health")
async def rapid7_health(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """Rapid7 InsightVM: Health check."""
    _log(request, bool(authorization or x_api_key))
    if not (authorization or x_api_key):
        raise HTTPException(status_code=401, detail="Missing auth credentials")
    return {"status": "healthy"}


@app.get("/rapid7/api/3/vulnerabilities")
async def rapid7_vulnerabilities(
    request: Request,
    page: int = Query(0),
    size: int = Query(10),
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Rapid7 InsightVM: Paginated vulnerability list (HAL JSON)."""
    _log(request, bool(authorization))
    _require_rapid7_auth(authorization)
    _maybe_error(simulate_error)

    total = len(SAMPLE_CVES)
    start = page * size
    end = min(start + size, total)
    page_vulns = SAMPLE_CVES[start:end]

    resources = []
    for v in page_vulns:
        resources.append({
            "id": v["cve_id"].lower().replace("-", "_"),
            "title": v["title"],
            "description": f"Vulnerability: {v['title']}",
            "severity": v["severity_str"],
            "severityScore": v["cvss3"],
            "riskScore": round(v["cvss3"] * 100),
            "categories": ["Software", "Remote Exploit"],
            "cvss": {
                "v3": {
                    "score": v["cvss3"],
                    "vector": f"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                }
            },
            "cvssV3": {
                "score": v["cvss3"],
                "impactScore": v["cvss3"],
                "exploitabilityScore": min(v["cvss3"], 3.9),
                "attackVector": "NETWORK",
                "attackComplexity": "LOW",
            },
            "cve": {"ids": [v["cve_id"]]},
            "exploits": v["kev"],
            "malwareKits": 0,
            "published": "2024-01-15T00:00:00Z",
            "modified": datetime.now(timezone.utc).isoformat(),
            "links": [{"href": f"/api/3/vulnerabilities/{v['cve_id']}", "rel": "self"}],
        })

    return {
        "resources": resources,
        "page": {
            "number": page,
            "size": size,
            "totalPages": (total + size - 1) // size,
            "totalResources": total,
        },
        "links": _rapid7_hal_links("/vulnerabilities", page, size, total),
    }


@app.get("/rapid7/api/3/assets")
async def rapid7_assets(
    request: Request,
    page: int = Query(0),
    size: int = Query(10),
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Rapid7 InsightVM: Asset list (HAL JSON)."""
    _log(request, bool(authorization))
    _require_rapid7_auth(authorization)
    _maybe_error(simulate_error)

    asset_names = ["web-server-01", "db-server-01", "app-server-01", "k8s-node-01", "vpn-gateway-01"]
    total = len(asset_names)

    resources = [
        {
            "id": i + 1,
            "ip": f"10.0.0.{10 + i}",
            "hostName": f"{name}.internal.example.com",
            "hostNames": [{"name": name, "source": "dns"}],
            "osFingerprint": {"description": "Ubuntu Linux 22.04"},
            "os": "Ubuntu Linux 22.04",
            "osId": 1000 + i,
            "assessedForVulnerabilities": True,
            "vulnerabilities": {
                "critical": random.randint(1, 3),
                "severe": random.randint(1, 4),
                "moderate": random.randint(2, 8),
            },
            "riskScore": round(random.uniform(600, 950), 2),
            "addresses": [{"ip": f"10.0.0.{10 + i}", "mac": "00:00:00:00:00:0" + str(i)}],
            "links": [{"href": f"/api/3/assets/{i + 1}", "rel": "self"}],
        }
        for i, name in enumerate(asset_names)
    ]

    return {
        "resources": resources,
        "page": {
            "number": page,
            "size": size,
            "totalPages": 1,
            "totalResources": total,
        },
        "links": _rapid7_hal_links("/assets", page, size, total),
    }


@app.post("/rapid7/api/3/reports")
async def rapid7_create_report(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Rapid7 InsightVM: Create report."""
    _log(request, bool(authorization))
    _require_rapid7_auth(authorization)
    _maybe_error(simulate_error)

    report_id = random.randint(100, 999)
    return {
        "id": report_id,
        "status": "started",
        "links": [{"href": f"/api/3/reports/{report_id}", "rel": "self"}],
    }


# ===========================================================================
# SLACK
# ===========================================================================

def _require_slack_auth(authorization: Optional[str]) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer xoxb-"):
        raise HTTPException(
            status_code=401,
            detail='{"ok": false, "error": "invalid_auth"}',
        )


@app.post("/slack/api/chat.postMessage")
async def slack_post_message(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Slack: Post a message to a channel."""
    _log(request, bool(authorization))
    _require_slack_auth(authorization)
    _maybe_error(simulate_error)

    ts = f"{int(time.time())}.{random.randint(100000, 999999)}"
    channel_id = "C" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10))

    return {
        "ok": True,
        "channel": channel_id,
        "ts": ts,
        "message": {
            "type": "message",
            "subtype": "bot_message",
            "text": "Security alert posted",
            "ts": ts,
            "bot_id": "B" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10)),
        },
    }


@app.post("/slack/api/auth.test")
async def slack_auth_test(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Slack: Auth test."""
    _log(request, bool(authorization))
    _require_slack_auth(authorization)
    return {
        "ok": True,
        "url": "https://glasswatchdemo.slack.com/",
        "team": "Glasswatch Demo",
        "user": "glasswatch-bot",
        "team_id": "T" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10)),
        "user_id": "U" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10)),
        "bot_id": "B" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=10)),
        "is_enterprise_install": False,
    }


# ===========================================================================
# MICROSOFT TEAMS (Incoming Webhooks)
# ===========================================================================

@app.post("/teams/webhook")
async def teams_webhook(
    request: Request,
    simulate_error: bool = Query(False),
):
    """Microsoft Teams: Incoming webhook (no auth — URL is the secret)."""
    _log(request, False)
    _maybe_error(simulate_error)

    body = await request.json()
    # Validate either MessageCard or Adaptive Card format
    if "@type" not in body and "type" not in body:
        raise HTTPException(
            status_code=400,
            detail="Invalid Teams message format. Expected @type or type field.",
        )

    return PlainTextResponse("1", status_code=200)


# ===========================================================================
# JIRA
# ===========================================================================

def _require_jira_auth(authorization: Optional[str]) -> None:
    """Validate Jira Basic auth (email:api_token)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Invalid auth scheme. Expected Basic.")
    try:
        decoded = base64.b64decode(authorization[6:]).decode()
        if "@" not in decoded or ":" not in decoded:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials format. Expected Basic base64(email:api_token).",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid base64 credentials")


@app.post("/jira/rest/api/3/issue")
async def jira_create_issue(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Jira: Create a new issue."""
    _log(request, bool(authorization))
    _require_jira_auth(authorization)
    _maybe_error(simulate_error)

    body = await request.json()
    fields = body.get("fields", {})
    project_key = fields.get("project", {}).get("key", "SEC")
    issue_number = random.randint(100, 9999)
    issue_key = f"{project_key}-{issue_number}"
    issue_id = str(random.randint(10000, 99999))

    return {
        "id": issue_id,
        "key": issue_key,
        "self": f"https://glasswatchdemo.atlassian.net/rest/api/3/issue/{issue_id}",
        "transitions": [],
    }


@app.get("/jira/rest/api/3/project")
async def jira_list_projects(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Jira: List accessible projects."""
    _log(request, bool(authorization))
    _require_jira_auth(authorization)
    _maybe_error(simulate_error)

    return [
        {
            "id": "10001",
            "key": "SEC",
            "name": "Security",
            "projectTypeKey": "software",
            "self": "https://glasswatchdemo.atlassian.net/rest/api/3/project/10001",
        },
        {
            "id": "10002",
            "key": "OPS",
            "name": "Operations",
            "projectTypeKey": "service_desk",
            "self": "https://glasswatchdemo.atlassian.net/rest/api/3/project/10002",
        },
    ]


@app.get("/jira/rest/api/3/myself")
async def jira_myself(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Jira: Get current user (health check)."""
    _log(request, bool(authorization))
    _require_jira_auth(authorization)

    return {
        "accountId": "5f7b1234567890abcdef1234",
        "emailAddress": "glasswatch-bot@example.com",
        "displayName": "Glasswatch Bot",
        "active": True,
        "accountType": "atlassian",
    }


# ===========================================================================
# SERVICENOW
# ===========================================================================

def _require_servicenow_auth(authorization: Optional[str]) -> None:
    """Validate ServiceNow Basic auth."""
    _require_basic_auth(authorization, "ServiceNow")


@app.post("/servicenow/api/now/table/incident")
async def servicenow_create_incident(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """ServiceNow: Create an incident."""
    _log(request, bool(authorization))
    _require_servicenow_auth(authorization)
    _maybe_error(simulate_error)

    sys_id = str(uuid.uuid4()).replace("-", "")[:32]
    inc_number = f"INC{random.randint(1000000, 9999999)}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "result": {
            "sys_id": sys_id,
            "number": inc_number,
            "state": "1",
            "priority": "1",
            "urgency": "1",
            "impact": "1",
            "category": "security",
            "sys_created_on": now,
            "sys_updated_on": now,
            "opened_at": now,
            "short_description": "Security vulnerability detected by Glasswatch",
            "caller_id": {"value": "glasswatch-bot", "display_value": "Glasswatch Bot"},
            "assignment_group": {"value": "security_team", "display_value": "Security Team"},
        }
    }


@app.get("/servicenow/api/now/table/cmdb_ci_server")
async def servicenow_cmdb_servers(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """ServiceNow: Query CMDB server CIs."""
    _log(request, bool(authorization))
    _require_servicenow_auth(authorization)
    _maybe_error(simulate_error)

    result = []
    for i, name in enumerate(["web-server-01", "db-server-01", "app-server-01", "k8s-node-01", "vpn-gateway-01"]):
        sys_id = str(uuid.uuid4()).replace("-", "")[:32]
        result.append({
            "sys_id": sys_id,
            "name": name,
            "ip_address": f"10.0.0.{10 + i}",
            "fqdn": f"{name}.internal.example.com",
            "os": "Linux",
            "os_version": "Ubuntu 22.04",
            "classification": "Production",
            "environment": "production",
            "sys_class_name": "cmdb_ci_server",
            "install_status": "1",
        })

    return {"result": result}


@app.get("/servicenow/api/now/health")
async def servicenow_health(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """ServiceNow: Health check."""
    _log(request, bool(authorization))
    _require_servicenow_auth(authorization)
    return {"status": "healthy", "instance": "glasswatchdemo"}


# ===========================================================================
# CISA KEV
# ===========================================================================

@app.get("/cisa/kev")
async def cisa_kev(
    request: Request,
    simulate_error: bool = Query(False),
):
    """CISA Known Exploited Vulnerabilities Catalog."""
    _log(request, False)
    _maybe_error(simulate_error)

    kev_vulns = [v for v in SAMPLE_CVES if v["kev"]]
    vulns = []
    for v in kev_vulns:
        vulns.append({
            "cveID": v["cve_id"],
            "vendorProject": v["vendor"],
            "product": v["product"],
            "vulnerabilityName": v["title"],
            "dateAdded": "2024-01-15",
            "shortDescription": f"{v['title']} — exploited in the wild.",
            "requiredAction": "Apply mitigations per vendor instructions or discontinue use of the product if mitigations are unavailable.",
            "dueDate": "2024-02-05",
            "notes": "This vulnerability is actively exploited.",
            "cwes": [],
        })

    return {
        "title": "CISA Known Exploited Vulnerabilities Catalog (Simulated)",
        "catalogVersion": "2024.01.15",
        "dateReleased": "2024-01-15T00:00:00.0000Z",
        "count": len(vulns),
        "vulnerabilities": vulns,
    }


# ===========================================================================
# NVD (NIST)
# ===========================================================================

@app.get("/nvd/rest/json/cves/2.0")
async def nvd_cves(
    request: Request,
    cveId: Optional[str] = Query(None),
    keywordSearch: Optional[str] = Query(None),
    cvssV3Severity: Optional[str] = Query(None),
    startIndex: int = Query(0),
    resultsPerPage: int = Query(10),
    simulate_error: bool = Query(False),
):
    """NVD NIST: CVE lookup endpoint."""
    _log(request, False)
    _maybe_error(simulate_error)

    # Filter by CVE ID if requested
    if cveId:
        vulns = [v for v in SAMPLE_CVES if v["cve_id"].upper() == cveId.upper()]
    elif cvssV3Severity:
        sev_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_sev = sev_map.get(cvssV3Severity.upper(), 0)
        vulns = [v for v in SAMPLE_CVES if v["severity_int"] >= min_sev]
    else:
        vulns = SAMPLE_CVES[startIndex: startIndex + resultsPerPage]

    total = len(SAMPLE_CVES) if not cveId else len(vulns)

    vulnerabilities = []
    for v in vulns:
        vulnerabilities.append({
            "cve": {
                "id": v["cve_id"],
                "sourceIdentifier": "secure@microsoft.com",
                "published": "2024-01-15T00:00:00.000",
                "lastModified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000"),
                "vulnStatus": "Analyzed",
                "descriptions": [
                    {"lang": "en", "value": f"{v['title']} — simulated NVD entry."},
                    {"lang": "es", "value": f"[Simulado] {v['title']}"},
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "source": "nvd@nist.gov",
                            "type": "Primary",
                            "cvssData": {
                                "version": "3.1",
                                "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                "attackVector": "NETWORK",
                                "attackComplexity": "LOW",
                                "privilegesRequired": "NONE",
                                "userInteraction": "NONE",
                                "scope": "UNCHANGED",
                                "confidentialityImpact": "HIGH",
                                "integrityImpact": "HIGH",
                                "availabilityImpact": "HIGH",
                                "baseScore": v["cvss3"],
                                "baseSeverity": v["severity_str"].upper(),
                            },
                            "exploitabilityScore": 3.9,
                            "impactScore": 5.9,
                        }
                    ]
                },
                "weaknesses": [{"source": "nvd@nist.gov", "type": "Primary", "description": [{"lang": "en", "value": "CWE-78"}]}],
                "configurations": [],
                "references": [
                    {"url": f"https://www.cve.org/CVERecord?id={v['cve_id']}", "source": "nvd@nist.gov"},
                ],
            }
        })

    return {
        "resultsPerPage": resultsPerPage,
        "startIndex": startIndex,
        "totalResults": total,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000"),
        "vulnerabilities": vulnerabilities,
    }


# ===========================================================================
# EPSS
# ===========================================================================

@app.get("/epss/data/v1/epss")
async def epss_scores(
    request: Request,
    cve: Optional[str] = Query(None),
    simulate_error: bool = Query(False),
):
    """EPSS: Get exploit prediction scores."""
    _log(request, False)
    _maybe_error(simulate_error)

    if cve:
        vulns = [v for v in SAMPLE_CVES if v["cve_id"].upper() == cve.upper()]
    else:
        vulns = SAMPLE_CVES

    data = [
        {
            "cve": v["cve_id"],
            "epss": str(v["epss"]),
            "percentile": str(v["epss_pct"]),
            "date": "2024-03-01",
        }
        for v in vulns
    ]

    return {
        "status": "OK",
        "status-code": 200,
        "version": "1.0",
        "access": "public",
        "total": len(data),
        "offset": 0,
        "limit": 100,
        "data": data,
    }


# ===========================================================================
# RESEND (Email)
# ===========================================================================

def _require_resend_auth(authorization: Optional[str]) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer re_"):
        raise HTTPException(
            status_code=401,
            detail='{"name": "missing_required_fields", "message": "Missing API key", "statusCode": 401}',
        )


@app.post("/resend/emails")
async def resend_send_email(
    request: Request,
    simulate_error: bool = Query(False),
    authorization: Optional[str] = Header(None),
):
    """Resend: Send an email."""
    _log(request, bool(authorization))
    _require_resend_auth(authorization)
    _maybe_error(simulate_error)

    body = await request.json()
    if not body.get("to") or not body.get("from") or not body.get("subject"):
        raise HTTPException(
            status_code=422,
            detail='{"name": "missing_required_fields", "message": "Missing to, from, or subject"}',
        )

    email_id = "sim_" + uuid.uuid4().hex[:20]
    return {"id": email_id}


@app.get("/resend/emails/{email_id}")
async def resend_get_email(
    email_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Resend: Get email status."""
    _log(request, bool(authorization))
    _require_resend_auth(authorization)

    return {
        "id": email_id,
        "object": "email",
        "to": ["recipient@example.com"],
        "from": "snapper@updates.mckinleylabsllc.com",
        "subject": "Security Digest",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_event": "delivered",
    }

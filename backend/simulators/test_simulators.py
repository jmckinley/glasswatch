#!/usr/bin/env python3
"""
Glasswatch Simulator Test Script
=================================
Verifies all simulator endpoints return the correct format and status codes.
Also tests auth validation and error simulation.

Run:
    # Start the simulator first:
    uvicorn backend.simulators.external_apis:app --port 8099 &

    # Then run this script:
    python3 backend/simulators/test_simulators.py

    # Or against a custom host:
    SIMULATOR_BASE=http://localhost:9000 python3 backend/simulators/test_simulators.py
"""

import base64
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any

import httpx

BASE = os.getenv("SIMULATOR_BASE", "http://localhost:8099").rstrip("/")

# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------
TENABLE_HEADERS = {"X-ApiKeys": "accessKey=test-access-key;secretKey=test-secret-key"}
BASIC_CREDS = base64.b64encode(b"testuser:testpass").decode()
BASIC_HEADERS = {"Authorization": f"Basic {BASIC_CREDS}"}
JIRA_CREDS = base64.b64encode(b"user@example.com:jira-api-token-here").decode()
JIRA_HEADERS = {"Authorization": f"Basic {JIRA_CREDS}"}
SLACK_HEADERS = {"Authorization": "Bearer xoxb-fake-token-for-testing"}
RESEND_HEADERS = {"Authorization": "Bearer re_fake_key_for_testing"}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    msg = f"  [{status}] {name}"
    if detail and not condition:
        msg += f" — {detail}"
    print(msg)
    results.append((name, condition, detail))
    return condition


def test_group(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_status(client: httpx.Client) -> None:
    test_group("Simulator Status")
    r = client.get(f"{BASE}/simulator/status")
    check("GET /simulator/status → 200", r.status_code == 200)
    data = r.json()
    check("status field == 'ok'", data.get("status") == "ok")
    check("services list present", "services" in data and len(data["services"]) >= 11)


def test_tenable(client: httpx.Client) -> None:
    test_group("Tenable.io")

    # Auth validation
    r = client.get(f"{BASE}/tenable/workbenches/vulnerabilities")
    check("Missing auth → 401", r.status_code == 401)

    r = client.get(
        f"{BASE}/tenable/workbenches/vulnerabilities",
        headers={"X-ApiKeys": "wrongformat"},
    )
    check("Bad auth format → 401", r.status_code == 401)

    # Vulnerabilities
    r = client.get(f"{BASE}/tenable/workbenches/vulnerabilities", headers=TENABLE_HEADERS)
    check("GET /workbenches/vulnerabilities → 200", r.status_code == 200)
    data = r.json()
    check("vulnerabilities list present", "vulnerabilities" in data)
    check("total field present", "total" in data)
    vulns = data["vulnerabilities"]
    if vulns:
        v = vulns[0]
        check("plugin_id field", "plugin_id" in v)
        check("plugin_name field", "plugin_name" in v)
        check("severity field (int)", isinstance(v.get("severity"), int))
        check("cvss3_base_score field", "cvss3_base_score" in v)

    # Assets
    r = client.get(f"{BASE}/tenable/workbenches/assets", headers=TENABLE_HEADERS)
    check("GET /workbenches/assets → 200", r.status_code == 200)
    data = r.json()
    check("assets list present", "assets" in data)

    # Scans
    r = client.get(f"{BASE}/tenable/scans", headers=TENABLE_HEADERS)
    check("GET /scans → 200", r.status_code == 200)
    data = r.json()
    check("scans list present", "scans" in data)

    # Export flow
    r = client.post(f"{BASE}/tenable/vulns/export", headers=TENABLE_HEADERS)
    check("POST /vulns/export → 200", r.status_code == 200)
    export_uuid = r.json().get("export_uuid")
    check("export_uuid returned", bool(export_uuid))

    if export_uuid:
        r = client.get(f"{BASE}/tenable/vulns/export/{export_uuid}/status", headers=TENABLE_HEADERS)
        check("GET export status (1st) → 200", r.status_code == 200)
        check("1st status == PROCESSING", r.json().get("status") == "PROCESSING")

        r = client.get(f"{BASE}/tenable/vulns/export/{export_uuid}/status", headers=TENABLE_HEADERS)
        check("GET export status (2nd) → 200", r.status_code == 200)
        check("2nd status == FINISHED", r.json().get("status") == "FINISHED")
        check("chunks_available == 1", r.json().get("chunks_available") == 1)

        r = client.get(f"{BASE}/tenable/vulns/export/{export_uuid}/chunks/1", headers=TENABLE_HEADERS)
        check("GET export chunk → 200", r.status_code == 200)
        chunk = r.json()
        check("chunk is list", isinstance(chunk, list))
        if chunk:
            item = chunk[0]
            check("chunk item has plugin.cve", "plugin" in item and "cve" in item.get("plugin", {}))
            check("chunk item has severity", "severity" in item)

    # Error simulation
    r = client.get(
        f"{BASE}/tenable/workbenches/vulnerabilities?simulate_error=true",
        headers=TENABLE_HEADERS,
    )
    check("simulate_error → 4xx/5xx", r.status_code >= 400)


def test_qualys(client: httpx.Client) -> None:
    test_group("Qualys VMPC")

    # Auth validation
    r = client.get(f"{BASE}/qualys/api/2.0/fo/scan/")
    check("Missing auth → 401", r.status_code == 401)

    r = client.get(f"{BASE}/qualys/api/2.0/fo/scan/", headers={"Authorization": "Bearer bad"})
    check("Bearer (wrong scheme) → 401", r.status_code == 401)

    # Scan list
    r = client.get(f"{BASE}/qualys/api/2.0/fo/scan/", headers=BASIC_HEADERS)
    check("GET /api/2.0/fo/scan/ → 200", r.status_code == 200)
    check("Content-Type: application/xml", "xml" in r.headers.get("content-type", ""))
    try:
        root = ET.fromstring(r.text)
        check("XML root is SCAN_LIST_OUTPUT", root.tag == "SCAN_LIST_OUTPUT")
        scan_list = root.find(".//SCAN_LIST")
        check("SCAN_LIST present", scan_list is not None)
    except ET.ParseError as e:
        check("XML parses cleanly", False, str(e))

    # Report
    r = client.post(f"{BASE}/qualys/api/2.0/fo/report/", headers=BASIC_HEADERS)
    check("POST /api/2.0/fo/report/ → 200", r.status_code == 200)
    check("Report Content-Type: xml", "xml" in r.headers.get("content-type", ""))
    try:
        root = ET.fromstring(r.text)
        check("XML root is VULN_LIST", root.tag == "VULN_LIST")
        vulns = root.findall("VULN")
        check("VULN elements present", len(vulns) > 0)
        if vulns:
            v = vulns[0]
            check("QID field", v.find("QID") is not None)
            check("CVE_ID field", v.find("CVE_ID") is not None)
            check("SEVERITY field", v.find("SEVERITY") is not None)
            check("CVSS3_BASE field", v.find("CVSS3_BASE") is not None)
    except ET.ParseError as e:
        check("Report XML parses cleanly", False, str(e))

    # Health
    r = client.get(f"{BASE}/qualys/msp/about.php", headers=BASIC_HEADERS)
    check("GET /msp/about.php → 200", r.status_code == 200)


def test_rapid7(client: httpx.Client) -> None:
    test_group("Rapid7 InsightVM")

    # Auth validation
    r = client.get(f"{BASE}/rapid7/api/3/vulnerabilities")
    check("Missing auth → 401", r.status_code == 401)

    r = client.get(
        f"{BASE}/rapid7/api/3/vulnerabilities",
        headers={"Authorization": "Bearer bad_token"},
    )
    check("Bearer (wrong scheme) → 401", r.status_code == 401)

    # Health check
    r = client.get(f"{BASE}/rapid7/api/3/health", headers=BASIC_HEADERS)
    check("GET /api/3/health → 200", r.status_code == 200)

    # Vulnerabilities (paginated)
    r = client.get(f"{BASE}/rapid7/api/3/vulnerabilities", headers=BASIC_HEADERS)
    check("GET /api/3/vulnerabilities → 200", r.status_code == 200)
    data = r.json()
    check("resources list present", "resources" in data)
    check("page object present", "page" in data)
    check("links (HAL) present", "links" in data)
    if data.get("resources"):
        v = data["resources"][0]
        check("id field", "id" in v)
        check("title field", "title" in v)
        check("severity field (string)", isinstance(v.get("severity"), str))
        check("cvssV3 field", "cvssV3" in v)
        check("cve.ids field", "ids" in v.get("cve", {}))

    # Pagination
    r = client.get(f"{BASE}/rapid7/api/3/vulnerabilities?page=0&size=5", headers=BASIC_HEADERS)
    check("Pagination (size=5) → 200", r.status_code == 200)
    data = r.json()
    check("totalPages > 1 for size=5", data.get("page", {}).get("totalPages", 0) > 1)

    # Assets
    r = client.get(f"{BASE}/rapid7/api/3/assets", headers=BASIC_HEADERS)
    check("GET /api/3/assets → 200", r.status_code == 200)
    data = r.json()
    check("assets resources present", "resources" in data)

    # Create report
    r = client.post(
        f"{BASE}/rapid7/api/3/reports",
        json={"name": "Test Report", "format": "pdf-template"},
        headers=BASIC_HEADERS,
    )
    check("POST /api/3/reports → 200", r.status_code == 200)
    check("id returned", "id" in r.json())


def test_slack(client: httpx.Client) -> None:
    test_group("Slack")

    # Auth validation
    r = client.post(
        f"{BASE}/slack/api/chat.postMessage",
        json={"channel": "#test", "text": "hi"},
    )
    check("Missing auth → 401", r.status_code == 401)

    r = client.post(
        f"{BASE}/slack/api/chat.postMessage",
        json={"channel": "#test", "text": "hi"},
        headers={"Authorization": "Bearer xoxp-wrong-type"},
    )
    check("Wrong token type (xoxp) → 401", r.status_code == 401)

    # Post message
    r = client.post(
        f"{BASE}/slack/api/chat.postMessage",
        json={
            "channel": "#security-alerts",
            "text": "Critical vuln detected",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
        },
        headers=SLACK_HEADERS,
    )
    check("POST chat.postMessage → 200", r.status_code == 200)
    data = r.json()
    check("ok == true", data.get("ok") is True)
    check("channel returned", "channel" in data)
    check("ts returned", "ts" in data)

    # Auth test
    r = client.post(f"{BASE}/slack/api/auth.test", headers=SLACK_HEADERS)
    check("POST auth.test → 200", r.status_code == 200)
    data = r.json()
    check("auth.test ok == true", data.get("ok") is True)


def test_teams(client: httpx.Client) -> None:
    test_group("Microsoft Teams")

    # MessageCard format
    r = client.post(
        f"{BASE}/teams/webhook",
        json={
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "text": "Security alert",
            "sections": [],
        },
    )
    check("POST webhook (MessageCard) → 200", r.status_code == 200)
    check("Response body is '1'", r.text == "1")

    # Adaptive Card format
    r = client.post(
        f"{BASE}/teams/webhook",
        json={
            "type": "message",
            "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive"}],
        },
    )
    check("POST webhook (Adaptive Card) → 200", r.status_code == 200)

    # Invalid format
    r = client.post(f"{BASE}/teams/webhook", json={"text": "no type field"})
    check("Invalid format → 400", r.status_code == 400)


def test_jira(client: httpx.Client) -> None:
    test_group("Jira")

    # Auth validation
    r = client.post(
        f"{BASE}/jira/rest/api/3/issue",
        json={"fields": {"project": {"key": "SEC"}, "summary": "Test"}},
    )
    check("Missing auth → 401", r.status_code == 401)

    bad_creds = base64.b64encode(b"notanemail:token").decode()
    r = client.post(
        f"{BASE}/jira/rest/api/3/issue",
        json={"fields": {}},
        headers={"Authorization": f"Basic {bad_creds}"},
    )
    check("Non-email credentials → 401", r.status_code == 401)

    # Create issue
    r = client.post(
        f"{BASE}/jira/rest/api/3/issue",
        json={
            "fields": {
                "project": {"key": "SEC"},
                "summary": "CVE-2024-21887 detected on vpn-gateway-01",
                "description": {
                    "version": 1,
                    "type": "doc",
                    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Details..."}]}],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": "Highest"},
            }
        },
        headers=JIRA_HEADERS,
    )
    check("POST /rest/api/3/issue → 200/201", r.status_code in (200, 201))
    data = r.json()
    check("id returned", "id" in data)
    check("key returned", "key" in data)
    check("key format is PROJECT-NUM", "-" in data.get("key", ""))
    check("self link returned", "self" in data)

    # List projects
    r = client.get(f"{BASE}/jira/rest/api/3/project", headers=JIRA_HEADERS)
    check("GET /rest/api/3/project → 200", r.status_code == 200)
    check("project list is array", isinstance(r.json(), list))

    # Myself (health check)
    r = client.get(f"{BASE}/jira/rest/api/3/myself", headers=JIRA_HEADERS)
    check("GET /rest/api/3/myself → 200", r.status_code == 200)


def test_servicenow(client: httpx.Client) -> None:
    test_group("ServiceNow")

    # Auth validation
    r = client.post(f"{BASE}/servicenow/api/now/table/incident", json={})
    check("Missing auth → 401", r.status_code == 401)

    # Create incident
    r = client.post(
        f"{BASE}/servicenow/api/now/table/incident",
        json={
            "short_description": "CVE-2024-21887 on vpn-gateway-01",
            "description": "Critical vuln detected by Glasswatch",
            "priority": "1",
            "category": "security",
            "caller_id": "glasswatch-bot",
        },
        headers=BASIC_HEADERS,
    )
    check("POST /api/now/table/incident → 200/201", r.status_code in (200, 201))
    data = r.json()
    check("result object present", "result" in data)
    result = data.get("result", {})
    check("sys_id present", "sys_id" in result)
    check("number present (INC...)", "number" in result and result["number"].startswith("INC"))
    check("state present", "state" in result)

    # CMDB
    r = client.get(f"{BASE}/servicenow/api/now/table/cmdb_ci_server", headers=BASIC_HEADERS)
    check("GET /api/now/table/cmdb_ci_server → 200", r.status_code == 200)
    check("result list present", "result" in r.json())

    # Health
    r = client.get(f"{BASE}/servicenow/api/now/health", headers=BASIC_HEADERS)
    check("GET /api/now/health → 200", r.status_code == 200)


def test_cisa_kev(client: httpx.Client) -> None:
    test_group("CISA KEV")

    r = client.get(f"{BASE}/cisa/kev")
    check("GET /cisa/kev → 200", r.status_code == 200)
    data = r.json()
    check("title present", "title" in data)
    check("catalogVersion present", "catalogVersion" in data)
    check("count present", "count" in data)
    check("vulnerabilities list present", "vulnerabilities" in data)
    check("count matches list length", data.get("count") == len(data.get("vulnerabilities", [])))

    if data.get("vulnerabilities"):
        v = data["vulnerabilities"][0]
        check("cveID field", "cveID" in v)
        check("vendorProject field", "vendorProject" in v)
        check("product field", "product" in v)
        check("dateAdded field", "dateAdded" in v)
        check("requiredAction field", "requiredAction" in v)

    # Only KEV-marked CVEs returned
    cve_ids = [v["cveID"] for v in data.get("vulnerabilities", [])]
    check("CVE-2024-21887 in KEV (should be)", "CVE-2024-21887" in cve_ids)
    check("CVE-2024-23897 NOT in KEV (not KEV-marked)", "CVE-2024-23897" not in cve_ids)


def test_nvd(client: httpx.Client) -> None:
    test_group("NVD (NIST)")

    # All vulns
    r = client.get(f"{BASE}/nvd/rest/json/cves/2.0")
    check("GET /nvd/rest/json/cves/2.0 → 200", r.status_code == 200)
    data = r.json()
    check("resultsPerPage present", "resultsPerPage" in data)
    check("totalResults present", "totalResults" in data)
    check("vulnerabilities list present", "vulnerabilities" in data)

    if data.get("vulnerabilities"):
        v = data["vulnerabilities"][0]
        check("cve.id field", "id" in v.get("cve", {}))
        check("cve.descriptions field", "descriptions" in v.get("cve", {}))
        metrics = v.get("cve", {}).get("metrics", {})
        check("cvssMetricV31 present", "cvssMetricV31" in metrics)
        cvss = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
        check("baseScore field", "baseScore" in cvss)
        check("baseSeverity field", "baseSeverity" in cvss)

    # Single CVE lookup
    r = client.get(f"{BASE}/nvd/rest/json/cves/2.0?cveId=CVE-2024-21887")
    check("Single CVE lookup → 200", r.status_code == 200)
    data = r.json()
    check("Single CVE returns 1 result", len(data.get("vulnerabilities", [])) == 1)
    if data.get("vulnerabilities"):
        check(
            "Correct CVE returned",
            data["vulnerabilities"][0]["cve"]["id"] == "CVE-2024-21887",
        )


def test_epss(client: httpx.Client) -> None:
    test_group("EPSS")

    r = client.get(f"{BASE}/epss/data/v1/epss")
    check("GET /epss/data/v1/epss → 200", r.status_code == 200)
    data = r.json()
    check("status == OK", data.get("status") == "OK")
    check("data list present", "data" in data)
    check("total field present", "total" in data)

    if data.get("data"):
        item = data["data"][0]
        check("cve field", "cve" in item)
        check("epss score field", "epss" in item)
        check("percentile field", "percentile" in item)
        check("date field", "date" in item)

    # Single CVE lookup
    r = client.get(f"{BASE}/epss/data/v1/epss?cve=CVE-2024-3400")
    check("Single EPSS lookup → 200", r.status_code == 200)
    data = r.json()
    check("Single EPSS returns 1 result", data.get("total") == 1)
    if data.get("data"):
        check("Correct CVE", data["data"][0]["cve"] == "CVE-2024-3400")


def test_resend(client: httpx.Client) -> None:
    test_group("Resend (Email)")

    # Auth validation
    r = client.post(f"{BASE}/resend/emails", json={"to": ["test@example.com"]})
    check("Missing auth → 401", r.status_code == 401)

    r = client.post(
        f"{BASE}/resend/emails",
        json={"to": ["test@example.com"]},
        headers={"Authorization": "Bearer sk_wrong_prefix"},
    )
    check("Wrong prefix (not re_) → 401", r.status_code == 401)

    # Send email
    r = client.post(
        f"{BASE}/resend/emails",
        json={
            "from": "snapper@updates.mckinleylabsllc.com",
            "to": ["security@example.com"],
            "subject": "Critical Vulnerability Alert",
            "html": "<h1>CVE-2024-21887 Detected</h1>",
        },
        headers=RESEND_HEADERS,
    )
    check("POST /resend/emails → 200", r.status_code == 200)
    data = r.json()
    check("id returned", "id" in data)

    # Missing required fields
    r = client.post(
        f"{BASE}/resend/emails",
        json={"to": ["test@example.com"]},  # missing from and subject
        headers=RESEND_HEADERS,
    )
    check("Missing from/subject → 422", r.status_code == 422)

    # Error simulation
    r = client.post(
        f"{BASE}/resend/emails?simulate_error=true",
        json={
            "from": "snapper@updates.mckinleylabsllc.com",
            "to": ["test@example.com"],
            "subject": "Test",
            "html": "<p>test</p>",
        },
        headers=RESEND_HEADERS,
    )
    check("simulate_error → 4xx/5xx", r.status_code >= 400)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\nGlasswatch Simulator Tests")
    print(f"Base URL: {BASE}")
    print(f"Testing all endpoints...\n")

    # Check if simulator is running
    try:
        with httpx.Client(timeout=5.0) as probe:
            probe.get(f"{BASE}/simulator/status")
    except httpx.ConnectError:
        print(f"\n❌  Cannot connect to simulator at {BASE}")
        print("    Start it with: uvicorn backend.simulators.external_apis:app --port 8099")
        sys.exit(1)

    with httpx.Client(timeout=10.0) as client:
        test_status(client)
        test_tenable(client)
        test_qualys(client)
        test_rapid7(client)
        test_slack(client)
        test_teams(client)
        test_jira(client)
        test_servicenow(client)
        test_cisa_kev(client)
        test_nvd(client)
        test_epss(client)
        test_resend(client)

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed:
        print("\nFailed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}" + (f": {detail}" if detail else ""))
        sys.exit(1)
    else:
        print("\n✅  All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()

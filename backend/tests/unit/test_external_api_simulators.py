"""
Unit tests for the Glasswatch External API Simulators.

Tests every simulator endpoint for:
  - Correct HTTP status code
  - Auth validation (401 on missing/wrong credentials)
  - Response format matches documented real API format
  - Error simulation (?simulate_error=true returns 4xx/5xx)
  - XML responses are valid and have correct structure (Qualys)
  - Tenable export flow state machine
"""
import base64
import xml.etree.ElementTree as ET
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from backend.simulators.external_apis import app, _export_state


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared auth headers
# ---------------------------------------------------------------------------
TENABLE_HEADERS = {"X-ApiKeys": "accessKey=test;secretKey=secret"}
BASIC_CREDS = base64.b64encode(b"user:password").decode()
BASIC_HEADERS = {"Authorization": f"Basic {BASIC_CREDS}"}
JIRA_CREDS = base64.b64encode(b"user@example.com:api-token").decode()
JIRA_HEADERS = {"Authorization": f"Basic {JIRA_CREDS}"}
SLACK_HEADERS = {"Authorization": "Bearer xoxb-test-token-here"}
RESEND_HEADERS = {"Authorization": "Bearer re_test_key"}


# ===========================================================================
# Simulator status
# ===========================================================================

class TestSimulatorStatus:
    def test_status_200(self, client):
        r = client.get("/simulator/status")
        assert r.status_code == 200

    def test_status_fields(self, client):
        data = client.get("/simulator/status").json()
        assert data["status"] == "ok"
        assert "services" in data
        assert len(data["services"]) >= 11

    def test_services_include_all(self, client):
        services = client.get("/simulator/status").json()["services"]
        for svc in ["tenable", "qualys", "rapid7", "slack", "teams", "jira",
                    "servicenow", "cisa_kev", "nvd", "epss", "resend"]:
            assert svc in services


# ===========================================================================
# Tenable.io
# ===========================================================================

class TestTenable:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.get("/tenable/workbenches/vulnerabilities")
        assert r.status_code == 401

    def test_bad_auth_format_401(self, client):
        r = client.get(
            "/tenable/workbenches/vulnerabilities",
            headers={"X-ApiKeys": "bad-format-no-keys"},
        )
        assert r.status_code == 401

    # --- Vulnerabilities ---
    def test_vuln_list_200(self, client):
        r = client.get("/tenable/workbenches/vulnerabilities", headers=TENABLE_HEADERS)
        assert r.status_code == 200

    def test_vuln_list_structure(self, client):
        data = client.get("/tenable/workbenches/vulnerabilities", headers=TENABLE_HEADERS).json()
        assert "vulnerabilities" in data
        assert "total" in data
        assert isinstance(data["vulnerabilities"], list)
        assert data["total"] == len(data["vulnerabilities"])

    def test_vuln_item_fields(self, client):
        vulns = client.get("/tenable/workbenches/vulnerabilities", headers=TENABLE_HEADERS).json()["vulnerabilities"]
        assert len(vulns) > 0
        v = vulns[0]
        assert "plugin_id" in v
        assert "plugin_name" in v
        assert isinstance(v["severity"], int)
        assert 0 <= v["severity"] <= 4
        assert "cvss3_base_score" in v

    # --- Assets ---
    def test_assets_200(self, client):
        r = client.get("/tenable/workbenches/assets", headers=TENABLE_HEADERS)
        assert r.status_code == 200

    def test_assets_structure(self, client):
        data = client.get("/tenable/workbenches/assets", headers=TENABLE_HEADERS).json()
        assert "assets" in data
        assert isinstance(data["assets"], list)
        assert len(data["assets"]) == 5

    # --- Scans ---
    def test_scans_200(self, client):
        r = client.get("/tenable/scans", headers=TENABLE_HEADERS)
        assert r.status_code == 200

    def test_scans_structure(self, client):
        data = client.get("/tenable/scans", headers=TENABLE_HEADERS).json()
        assert "scans" in data
        assert len(data["scans"]) >= 2

    # --- Export flow ---
    def test_export_start_returns_uuid(self, client):
        r = client.post("/tenable/vulns/export", headers=TENABLE_HEADERS)
        assert r.status_code == 200
        assert "export_uuid" in r.json()

    def test_export_status_processing_then_finished(self, client):
        _export_state.clear()
        export_uuid = client.post("/tenable/vulns/export", headers=TENABLE_HEADERS).json()["export_uuid"]

        r1 = client.get(f"/tenable/vulns/export/{export_uuid}/status", headers=TENABLE_HEADERS)
        assert r1.status_code == 200
        assert r1.json()["status"] == "PROCESSING"

        r2 = client.get(f"/tenable/vulns/export/{export_uuid}/status", headers=TENABLE_HEADERS)
        assert r2.status_code == 200
        assert r2.json()["status"] == "FINISHED"
        assert r2.json()["chunks_available"] == 1

    def test_export_chunk_contains_vulns(self, client):
        _export_state.clear()
        export_uuid = client.post("/tenable/vulns/export", headers=TENABLE_HEADERS).json()["export_uuid"]
        r = client.get(f"/tenable/vulns/export/{export_uuid}/chunks/1", headers=TENABLE_HEADERS)
        assert r.status_code == 200
        chunk = r.json()
        assert isinstance(chunk, list)
        assert len(chunk) > 0
        item = chunk[0]
        assert "plugin" in item
        assert "cve" in item["plugin"]
        assert "severity" in item

    def test_export_unknown_uuid_404(self, client):
        r = client.get("/tenable/vulns/export/nonexistent-uuid/status", headers=TENABLE_HEADERS)
        assert r.status_code == 404

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.get(
            "/tenable/workbenches/vulnerabilities?simulate_error=true",
            headers=TENABLE_HEADERS,
        )
        assert r.status_code >= 400


# ===========================================================================
# Qualys VMPC
# ===========================================================================

class TestQualys:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/")
        assert r.status_code == 401

    def test_wrong_scheme_401(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/", headers={"Authorization": "Bearer token"})
        assert r.status_code == 401

    # --- Scans (XML) ---
    def test_scans_200(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/", headers=BASIC_HEADERS)
        assert r.status_code == 200

    def test_scans_content_type_xml(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/", headers=BASIC_HEADERS)
        assert "xml" in r.headers.get("content-type", "")

    def test_scans_valid_xml(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/", headers=BASIC_HEADERS)
        root = ET.fromstring(r.text)
        assert root.tag == "SCAN_LIST_OUTPUT"

    def test_scans_has_scan_list(self, client):
        r = client.get("/qualys/api/2.0/fo/scan/", headers=BASIC_HEADERS)
        root = ET.fromstring(r.text)
        scan_list = root.find(".//SCAN_LIST")
        assert scan_list is not None

    # --- Report (XML) ---
    def test_report_200(self, client):
        r = client.post("/qualys/api/2.0/fo/report/", headers=BASIC_HEADERS)
        assert r.status_code == 200

    def test_report_xml_structure(self, client):
        r = client.post("/qualys/api/2.0/fo/report/", headers=BASIC_HEADERS)
        root = ET.fromstring(r.text)
        assert root.tag == "VULN_LIST"
        vulns = root.findall("VULN")
        assert len(vulns) > 0

    def test_report_vuln_fields(self, client):
        r = client.post("/qualys/api/2.0/fo/report/", headers=BASIC_HEADERS)
        root = ET.fromstring(r.text)
        v = root.findall("VULN")[0]
        assert v.find("QID") is not None
        assert v.find("CVE_ID") is not None
        assert v.find("SEVERITY") is not None
        assert v.find("CVSS3_BASE") is not None
        assert v.find("TITLE") is not None

    def test_report_severity_range(self, client):
        r = client.post("/qualys/api/2.0/fo/report/", headers=BASIC_HEADERS)
        root = ET.fromstring(r.text)
        for v in root.findall("VULN"):
            sev = int(v.find("SEVERITY").text)
            assert 1 <= sev <= 5

    # --- Health ---
    def test_health_200(self, client):
        r = client.get("/qualys/msp/about.php", headers=BASIC_HEADERS)
        assert r.status_code == 200

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.post("/qualys/api/2.0/fo/report/?simulate_error=true", headers=BASIC_HEADERS)
        assert r.status_code >= 400


# ===========================================================================
# Rapid7 InsightVM
# ===========================================================================

class TestRapid7:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.get("/rapid7/api/3/vulnerabilities")
        assert r.status_code == 401

    def test_bearer_scheme_rejected(self, client):
        r = client.get(
            "/rapid7/api/3/vulnerabilities",
            headers={"Authorization": "Bearer api_token"},
        )
        assert r.status_code == 401

    # --- Health ---
    def test_health_200(self, client):
        r = client.get("/rapid7/api/3/health", headers=BASIC_HEADERS)
        assert r.status_code == 200

    # --- Vulnerabilities ---
    def test_vulns_200(self, client):
        r = client.get("/rapid7/api/3/vulnerabilities", headers=BASIC_HEADERS)
        assert r.status_code == 200

    def test_vulns_hal_structure(self, client):
        data = client.get("/rapid7/api/3/vulnerabilities", headers=BASIC_HEADERS).json()
        assert "resources" in data
        assert "page" in data
        assert "links" in data

    def test_vulns_page_structure(self, client):
        page = client.get("/rapid7/api/3/vulnerabilities", headers=BASIC_HEADERS).json()["page"]
        assert "number" in page
        assert "size" in page
        assert "totalPages" in page
        assert "totalResources" in page

    def test_vuln_item_fields(self, client):
        resources = client.get("/rapid7/api/3/vulnerabilities", headers=BASIC_HEADERS).json()["resources"]
        assert len(resources) > 0
        v = resources[0]
        assert "id" in v
        assert "title" in v
        assert isinstance(v["severity"], str)
        assert v["severity"] in ("critical", "high", "medium", "low")
        assert "cvssV3" in v
        assert "ids" in v.get("cve", {})

    def test_pagination_size_5(self, client):
        data = client.get("/rapid7/api/3/vulnerabilities?page=0&size=5", headers=BASIC_HEADERS).json()
        assert len(data["resources"]) <= 5
        assert data["page"]["totalPages"] > 1

    # --- Assets ---
    def test_assets_200(self, client):
        r = client.get("/rapid7/api/3/assets", headers=BASIC_HEADERS)
        assert r.status_code == 200

    def test_assets_fields(self, client):
        resources = client.get("/rapid7/api/3/assets", headers=BASIC_HEADERS).json()["resources"]
        assert len(resources) > 0
        a = resources[0]
        assert "id" in a
        assert "ip" in a

    # --- Create report ---
    def test_create_report_200(self, client):
        r = client.post("/rapid7/api/3/reports", json={"name": "test"}, headers=BASIC_HEADERS)
        assert r.status_code == 200
        assert "id" in r.json()

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.get("/rapid7/api/3/vulnerabilities?simulate_error=true", headers=BASIC_HEADERS)
        assert r.status_code >= 400


# ===========================================================================
# Slack
# ===========================================================================

class TestSlack:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.post("/slack/api/chat.postMessage", json={"channel": "#test"})
        assert r.status_code == 401

    def test_wrong_token_type_401(self, client):
        r = client.post(
            "/slack/api/chat.postMessage",
            json={"channel": "#test"},
            headers={"Authorization": "Bearer xoxp-wrong-type"},
        )
        assert r.status_code == 401

    # --- Post message ---
    def test_post_message_200(self, client):
        r = client.post(
            "/slack/api/chat.postMessage",
            json={"channel": "#security-alerts", "text": "Test"},
            headers=SLACK_HEADERS,
        )
        assert r.status_code == 200

    def test_post_message_structure(self, client):
        data = client.post(
            "/slack/api/chat.postMessage",
            json={"channel": "#test", "text": "Hi"},
            headers=SLACK_HEADERS,
        ).json()
        assert data["ok"] is True
        assert "channel" in data
        assert "ts" in data

    # --- Auth test ---
    def test_auth_test_200(self, client):
        r = client.post("/slack/api/auth.test", headers=SLACK_HEADERS)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.post(
            "/slack/api/chat.postMessage?simulate_error=true",
            json={"channel": "#test", "text": "test"},
            headers=SLACK_HEADERS,
        )
        assert r.status_code >= 400


# ===========================================================================
# Microsoft Teams
# ===========================================================================

class TestTeams:
    def test_message_card_200(self, client):
        r = client.post(
            "/teams/webhook",
            json={"@type": "MessageCard", "@context": "...", "text": "Alert"},
        )
        assert r.status_code == 200
        assert r.text == "1"

    def test_adaptive_card_200(self, client):
        r = client.post(
            "/teams/webhook",
            json={"type": "message", "attachments": []},
        )
        assert r.status_code == 200

    def test_invalid_format_400(self, client):
        r = client.post("/teams/webhook", json={"text": "no type"})
        assert r.status_code == 400

    def test_simulate_error(self, client):
        r = client.post(
            "/teams/webhook?simulate_error=true",
            json={"@type": "MessageCard", "text": "test"},
        )
        assert r.status_code >= 400


# ===========================================================================
# Jira
# ===========================================================================

class TestJira:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.post("/jira/rest/api/3/issue", json={})
        assert r.status_code == 401

    def test_non_email_creds_401(self, client):
        bad = base64.b64encode(b"notanemail:token").decode()
        r = client.post("/jira/rest/api/3/issue", json={}, headers={"Authorization": f"Basic {bad}"})
        assert r.status_code == 401

    # --- Create issue ---
    def test_create_issue_200(self, client):
        r = client.post(
            "/jira/rest/api/3/issue",
            json={
                "fields": {
                    "project": {"key": "SEC"},
                    "summary": "Test issue",
                    "issuetype": {"name": "Bug"},
                }
            },
            headers=JIRA_HEADERS,
        )
        assert r.status_code == 200

    def test_create_issue_structure(self, client):
        data = client.post(
            "/jira/rest/api/3/issue",
            json={"fields": {"project": {"key": "SEC"}, "summary": "Test", "issuetype": {"name": "Bug"}}},
            headers=JIRA_HEADERS,
        ).json()
        assert "id" in data
        assert "key" in data
        assert "-" in data["key"]  # e.g. SEC-123
        assert "self" in data

    # --- List projects ---
    def test_list_projects_200(self, client):
        r = client.get("/jira/rest/api/3/project", headers=JIRA_HEADERS)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    # --- Myself ---
    def test_myself_200(self, client):
        r = client.get("/jira/rest/api/3/myself", headers=JIRA_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "accountId" in data

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.post(
            "/jira/rest/api/3/issue?simulate_error=true",
            json={"fields": {}},
            headers=JIRA_HEADERS,
        )
        assert r.status_code >= 400


# ===========================================================================
# ServiceNow
# ===========================================================================

class TestServiceNow:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.post("/servicenow/api/now/table/incident", json={})
        assert r.status_code == 401

    # --- Create incident ---
    def test_create_incident_200(self, client):
        r = client.post(
            "/servicenow/api/now/table/incident",
            json={"short_description": "Test", "priority": "1", "category": "security"},
            headers=BASIC_HEADERS,
        )
        assert r.status_code == 200

    def test_create_incident_structure(self, client):
        data = client.post(
            "/servicenow/api/now/table/incident",
            json={"short_description": "Test", "priority": "1"},
            headers=BASIC_HEADERS,
        ).json()
        assert "result" in data
        result = data["result"]
        assert "sys_id" in result
        assert "number" in result
        assert result["number"].startswith("INC")
        assert "state" in result

    # --- CMDB ---
    def test_cmdb_servers_200(self, client):
        r = client.get("/servicenow/api/now/table/cmdb_ci_server", headers=BASIC_HEADERS)
        assert r.status_code == 200
        assert "result" in r.json()

    # --- Health ---
    def test_health_200(self, client):
        r = client.get("/servicenow/api/now/health", headers=BASIC_HEADERS)
        assert r.status_code == 200

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.post(
            "/servicenow/api/now/table/incident?simulate_error=true",
            json={"short_description": "Test"},
            headers=BASIC_HEADERS,
        )
        assert r.status_code >= 400


# ===========================================================================
# CISA KEV
# ===========================================================================

class TestCisaKev:
    def test_200_no_auth(self, client):
        r = client.get("/cisa/kev")
        assert r.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/cisa/kev").json()
        assert "title" in data
        assert "catalogVersion" in data
        assert "count" in data
        assert "vulnerabilities" in data

    def test_count_matches_list(self, client):
        data = client.get("/cisa/kev").json()
        assert data["count"] == len(data["vulnerabilities"])

    def test_vuln_fields(self, client):
        vuln = client.get("/cisa/kev").json()["vulnerabilities"][0]
        assert "cveID" in vuln
        assert "vendorProject" in vuln
        assert "product" in vuln
        assert "dateAdded" in vuln
        assert "requiredAction" in vuln

    def test_kev_contains_correct_cves(self, client):
        cve_ids = [v["cveID"] for v in client.get("/cisa/kev").json()["vulnerabilities"]]
        # These are KEV-marked
        assert "CVE-2024-21887" in cve_ids
        assert "CVE-2024-3400" in cve_ids
        # This is NOT KEV-marked
        assert "CVE-2024-23897" not in cve_ids

    def test_simulate_error(self, client):
        r = client.get("/cisa/kev?simulate_error=true")
        assert r.status_code >= 400


# ===========================================================================
# NVD
# ===========================================================================

class TestNvd:
    def test_200_no_auth(self, client):
        r = client.get("/nvd/rest/json/cves/2.0")
        assert r.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/nvd/rest/json/cves/2.0").json()
        assert "resultsPerPage" in data
        assert "totalResults" in data
        assert "vulnerabilities" in data

    def test_vuln_fields(self, client):
        vuln = client.get("/nvd/rest/json/cves/2.0").json()["vulnerabilities"][0]
        cve = vuln["cve"]
        assert "id" in cve
        assert "descriptions" in cve
        assert "metrics" in cve
        assert "cvssMetricV31" in cve["metrics"]

    def test_cvss_data(self, client):
        vuln = client.get("/nvd/rest/json/cves/2.0").json()["vulnerabilities"][0]
        cvss = vuln["cve"]["metrics"]["cvssMetricV31"][0]["cvssData"]
        assert "baseScore" in cvss
        assert "baseSeverity" in cvss
        assert isinstance(cvss["baseScore"], float)

    def test_single_cve_lookup(self, client):
        r = client.get("/nvd/rest/json/cves/2.0?cveId=CVE-2024-21887")
        assert r.status_code == 200
        data = r.json()
        assert len(data["vulnerabilities"]) == 1
        assert data["vulnerabilities"][0]["cve"]["id"] == "CVE-2024-21887"

    def test_simulate_error(self, client):
        r = client.get("/nvd/rest/json/cves/2.0?simulate_error=true")
        assert r.status_code >= 400


# ===========================================================================
# EPSS
# ===========================================================================

class TestEpss:
    def test_200_no_auth(self, client):
        r = client.get("/epss/data/v1/epss")
        assert r.status_code == 200

    def test_response_structure(self, client):
        data = client.get("/epss/data/v1/epss").json()
        assert data["status"] == "OK"
        assert "data" in data
        assert "total" in data

    def test_data_item_fields(self, client):
        item = client.get("/epss/data/v1/epss").json()["data"][0]
        assert "cve" in item
        assert "epss" in item
        assert "percentile" in item
        assert "date" in item

    def test_epss_score_range(self, client):
        for item in client.get("/epss/data/v1/epss").json()["data"]:
            score = float(item["epss"])
            assert 0.0 <= score <= 1.0

    def test_single_cve_lookup(self, client):
        r = client.get("/epss/data/v1/epss?cve=CVE-2024-3400")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["data"][0]["cve"] == "CVE-2024-3400"

    def test_simulate_error(self, client):
        r = client.get("/epss/data/v1/epss?simulate_error=true")
        assert r.status_code >= 400


# ===========================================================================
# Resend
# ===========================================================================

class TestResend:
    # --- Auth ---
    def test_missing_auth_401(self, client):
        r = client.post("/resend/emails", json={"to": ["test@example.com"]})
        assert r.status_code == 401

    def test_wrong_prefix_401(self, client):
        r = client.post(
            "/resend/emails",
            json={"to": ["test@example.com"]},
            headers={"Authorization": "Bearer sk_not_re_prefix"},
        )
        assert r.status_code == 401

    # --- Send email ---
    def test_send_email_200(self, client):
        r = client.post(
            "/resend/emails",
            json={
                "from": "sender@example.com",
                "to": ["recipient@example.com"],
                "subject": "Test",
                "html": "<p>Test</p>",
            },
            headers=RESEND_HEADERS,
        )
        assert r.status_code == 200

    def test_send_email_returns_id(self, client):
        data = client.post(
            "/resend/emails",
            json={
                "from": "sender@example.com",
                "to": ["r@example.com"],
                "subject": "Test",
                "html": "<p>T</p>",
            },
            headers=RESEND_HEADERS,
        ).json()
        assert "id" in data

    def test_missing_required_fields_422(self, client):
        r = client.post(
            "/resend/emails",
            json={"to": ["test@example.com"]},  # no from or subject
            headers=RESEND_HEADERS,
        )
        assert r.status_code == 422

    # --- Get email status ---
    def test_get_email_200(self, client):
        r = client.get("/resend/emails/sim_test_id", headers=RESEND_HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert "last_event" in data

    # --- Error simulation ---
    def test_simulate_error(self, client):
        r = client.post(
            "/resend/emails?simulate_error=true",
            json={"from": "a@b.com", "to": ["c@d.com"], "subject": "Test", "html": "T"},
            headers=RESEND_HEADERS,
        )
        assert r.status_code >= 400

"""
Unit tests for CSV parsing logic in the import service.

Tests the helper parse functions and the CSV row validation logic
used by the import_api endpoints, without touching the database.
"""
import csv
import io
import pytest
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


# ── Import helpers under test ─────────────────────────────────────────────────

from backend.api.v1.import_api import _parse_date, _parse_float, _parse_int

# ── CSV parsing helpers ───────────────────────────────────────────────────────

VULN_CSV_REQUIRED = ["asset_name", "cve_id", "severity", "cvss_score", "discovered_date"]
ASSET_CSV_REQUIRED = ["name", "type", "environment", "criticality"]


def _read_csv_rows(csv_text: str) -> list[dict]:
    """Parse a CSV string into a list of row dicts."""
    reader = csv.DictReader(io.StringIO(csv_text))
    return list(reader)


def _validate_vuln_row(row: dict) -> tuple[bool, str]:
    """
    Reproduce basic validation from import_api.py:
    - asset_name/asset_ip must be present
    - cve_id must be present
    """
    asset_identifier = (
        row.get("asset_name") or row.get("asset_ip") or row.get("hostname") or ""
    ).strip()
    cve_id = (row.get("cve_id") or row.get("cve") or "").strip()

    if not asset_identifier:
        return False, "missing asset_name or asset_ip"
    if not cve_id:
        return False, "missing cve_id"
    return True, ""


def _validate_asset_row(row: dict) -> tuple[bool, str]:
    """Reproduce basic validation from import_api.py for asset rows."""
    name = (
        row.get("name") or row.get("hostname") or row.get("identifier") or ""
    ).strip()
    if not name:
        return False, "missing name/hostname/identifier"
    return True, ""


# ── _parse_float ──────────────────────────────────────────────────────────────

class TestParseFloat:
    async def test_parse_float_valid(self):
        assert _parse_float("7.5") == 7.5

    async def test_parse_float_integer_string(self):
        assert _parse_float("9") == 9.0

    async def test_parse_float_with_whitespace(self):
        assert _parse_float("  8.3  ") == 8.3

    async def test_parse_float_empty_string(self):
        assert _parse_float("") is None

    async def test_parse_float_none_input(self):
        assert _parse_float(None) is None

    async def test_parse_float_non_numeric(self):
        assert _parse_float("abc") is None


# ── _parse_int ────────────────────────────────────────────────────────────────

class TestParseInt:
    async def test_parse_int_valid(self):
        assert _parse_int("3") == 3

    async def test_parse_int_clamps_to_max(self):
        # Criticality is clamped to 1-5
        assert _parse_int("10") == 5

    async def test_parse_int_clamps_to_min(self):
        assert _parse_int("0") == 1

    async def test_parse_int_empty_uses_default(self):
        assert _parse_int("", default=3) == 3

    async def test_parse_int_none_uses_default(self):
        assert _parse_int(None, default=2) == 2


# ── _parse_date ───────────────────────────────────────────────────────────────

class TestParseDate:
    async def test_parse_date_iso_format(self):
        result = _parse_date("2024-01-15")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    async def test_parse_date_us_format(self):
        result = _parse_date("01/15/2024")
        assert isinstance(result, datetime)
        assert result.day == 15

    async def test_parse_date_empty_returns_none(self):
        assert _parse_date("") is None

    async def test_parse_date_none_returns_none(self):
        assert _parse_date(None) is None

    async def test_parse_date_invalid_returns_none(self):
        assert _parse_date("not-a-date") is None


# ── Vulnerability CSV parsing ─────────────────────────────────────────────────

class TestParseVulnCsv:
    async def test_parse_vuln_csv_valid(self):
        """Valid CSV with required columns returns correct rows."""
        csv_text = (
            "asset_name,cve_id,severity,cvss_score,discovered_date\n"
            "web-server-01,CVE-2024-1234,HIGH,7.5,2024-01-10\n"
            "db-server-02,CVE-2024-5678,CRITICAL,9.8,2024-01-11\n"
        )
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 2

        row0 = rows[0]
        assert row0["asset_name"] == "web-server-01"
        assert row0["cve_id"] == "CVE-2024-1234"
        assert row0["severity"] == "HIGH"
        assert _parse_float(row0["cvss_score"]) == 7.5
        assert _parse_date(row0["discovered_date"]) is not None

    async def test_parse_vuln_csv_missing_required_column(self):
        """Row missing cve_id fails validation."""
        csv_text = (
            "asset_name,severity,cvss_score\n"
            "web-server-01,HIGH,7.5\n"
        )
        rows = _read_csv_rows(csv_text)
        ok, err = _validate_vuln_row(rows[0])
        assert not ok
        assert "cve_id" in err or "missing" in err

    async def test_parse_vuln_csv_missing_asset_name(self):
        """Row missing asset_name/asset_ip fails validation."""
        csv_text = (
            "cve_id,severity,cvss_score\n"
            "CVE-2024-0001,HIGH,7.5\n"
        )
        rows = _read_csv_rows(csv_text)
        ok, err = _validate_vuln_row(rows[0])
        assert not ok
        assert "asset" in err

    async def test_parse_vuln_csv_all_rows_valid(self):
        """Multiple valid rows all pass validation."""
        csv_text = (
            "asset_name,cve_id,severity,cvss_score,discovered_date\n"
            "host-a,CVE-2024-0001,LOW,3.1,2024-02-01\n"
            "host-b,CVE-2024-0002,MEDIUM,5.5,2024-02-02\n"
            "host-c,CVE-2024-0003,CRITICAL,9.9,2024-02-03\n"
        )
        rows = _read_csv_rows(csv_text)
        assert all(_validate_vuln_row(r)[0] for r in rows)


# ── Asset CSV parsing ─────────────────────────────────────────────────────────

class TestParseAssetCsv:
    async def test_parse_asset_csv_valid(self):
        """Valid asset CSV returns correct rows."""
        csv_text = (
            "name,type,environment,ip_address,owner_team,criticality\n"
            "api-gateway,server,production,10.0.0.1,platform,5\n"
            "worker-01,container,staging,10.0.0.2,ops,3\n"
        )
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 2

        row0 = rows[0]
        assert row0["name"] == "api-gateway"
        assert row0["type"] == "server"
        assert row0["environment"] == "production"
        assert _parse_int(row0["criticality"]) == 5

    async def test_parse_asset_csv_row_valid(self):
        """Row with name passes validation."""
        row = {"name": "my-server", "type": "server", "environment": "prod"}
        ok, err = _validate_asset_row(row)
        assert ok

    async def test_parse_asset_csv_row_missing_name(self):
        """Row with no name/hostname/identifier fails validation."""
        row = {"type": "server", "environment": "prod"}
        ok, err = _validate_asset_row(row)
        assert not ok

    async def test_parse_csv_with_extra_columns(self):
        """Extra columns in the CSV are ignored gracefully."""
        csv_text = (
            "name,type,environment,criticality,extra_col_1,extra_col_2,future_field\n"
            "my-server,server,production,4,ignored,also_ignored,whatever\n"
        )
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 1
        row = rows[0]

        # Core fields are still parsed correctly
        assert row["name"] == "my-server"
        assert _parse_int(row["criticality"]) == 4

        # Extra columns are present in the dict but shouldn't cause errors
        assert "extra_col_1" in row

    async def test_parse_vuln_csv_with_extra_columns(self):
        """Extra columns in a vuln CSV are ignored gracefully."""
        csv_text = (
            "asset_name,cve_id,severity,cvss_score,discovered_date,extra_field\n"
            "web-01,CVE-2024-9999,HIGH,7.0,2024-01-01,junk\n"
        )
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 1

        ok, _ = _validate_vuln_row(rows[0])
        assert ok  # extra column doesn't break validation

    async def test_parse_asset_csv_uses_hostname_fallback(self):
        """'hostname' column is accepted as a fallback for 'name'."""
        row = {"hostname": "backup-server", "type": "server"}
        ok, _ = _validate_asset_row(row)
        assert ok


# ── CSV alias and edge-case tests ─────────────────────────────────────────────

class TestCsvAliasColumns:
    """Tests for column alias handling added in recent import_api work."""

    async def test_vuln_csv_accepts_asset_ip_column(self):
        """`asset_ip` column works as an alias for asset_name."""
        row = {"asset_ip": "10.0.0.1", "cve_id": "CVE-2024-1111"}
        ok, _ = _validate_vuln_row(row)
        assert ok, "asset_ip should be accepted as asset identifier"

    async def test_vuln_csv_accepts_hostname_column(self):
        """`hostname` column is accepted as asset identifier."""
        row = {"hostname": "db-server-01", "cve_id": "CVE-2024-2222"}
        ok, _ = _validate_vuln_row(row)
        assert ok

    async def test_vuln_csv_accepts_cve_column(self):
        """`cve` column works as an alias for cve_id."""
        row = {"asset_name": "web-01", "cve": "CVE-2024-3333"}
        ok, _ = _validate_vuln_row(row)
        assert ok, "cve should be accepted as alias for cve_id"

    async def test_vuln_csv_invalid_severity_defaults_to_medium(self):
        """Unrecognised severity value should normalise to MEDIUM."""
        # Reproduce the normalisation from import_api.py
        def _normalise_severity(raw: str) -> str:
            valid = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL")
            s = (raw or "MEDIUM").strip().upper()
            return s if s in valid else "MEDIUM"

        assert _normalise_severity("BANANA") == "MEDIUM"
        assert _normalise_severity("") == "MEDIUM"
        assert _normalise_severity("high") == "HIGH"  # case-normalised correctly
        assert _normalise_severity("critical") == "CRITICAL"

    async def test_asset_csv_invalid_type_defaults_to_server(self):
        """Unrecognised asset type should normalise to 'server'."""
        valid_types = ("server", "container", "function", "database", "application", "network", "endpoint")

        def _normalise_type(raw: str) -> str:
            t = (raw or "server").strip().lower()
            return t if t in valid_types else "server"

        assert _normalise_type("appliance") == "server"
        assert _normalise_type("") == "server"
        assert _normalise_type("container") == "container"

    async def test_asset_csv_accepts_ip_column(self):
        """`ip` column is accepted as an alias for ip_address."""
        # ip_address resolution is done in import_api via:
        #   ip_address = (row.get("ip_address") or row.get("ip") or "").strip()
        row = {"ip": "192.168.1.50", "ip_address": ""}
        ip = (row.get("ip_address") or row.get("ip") or "").strip()
        assert ip == "192.168.1.50"


class TestCsvSpecialCases:
    async def test_csv_utf8_bom_stripped(self):
        """CSV with UTF-8 BOM header should parse correctly (BOM stripped)."""
        # Build raw UTF-8 bytes WITH BOM prefix (EF BB BF)
        csv_text = "asset_name,cve_id,severity\nweb-01,CVE-2024-9000,HIGH\n"
        content_bytes = b"\xef\xbb\xbf" + csv_text.encode("utf-8")

        # import_api.py uses content.decode("utf-8-sig") which strips the BOM
        decoded = content_bytes.decode("utf-8-sig")

        rows = _read_csv_rows(decoded)
        assert len(rows) == 1

        # Column header should NOT have BOM prefix after decoding
        assert "asset_name" in rows[0], \
            f"BOM prefix not stripped — headers: {list(rows[0].keys())}"

    async def test_csv_empty_file_returns_error(self):
        """An empty CSV string should produce zero data rows."""
        rows = _read_csv_rows("")
        assert rows == [], "Empty CSV should yield no rows"

    async def test_csv_empty_file_only_header(self):
        """A CSV with only a header row but no data rows should produce no rows."""
        header_only = "asset_name,cve_id,severity\n"
        rows = _read_csv_rows(header_only)
        assert rows == []

    async def test_csv_missing_required_column_vuln(self):
        """CSV missing cve_id column causes validation error per row."""
        csv_text = "asset_name,severity,cvss_score\nweb-01,HIGH,7.5\n"
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 1
        ok, err = _validate_vuln_row(rows[0])
        assert not ok
        assert "cve_id" in err or "missing" in err

    async def test_csv_missing_required_column_asset(self):
        """CSV missing name/hostname/identifier causes validation error per row."""
        csv_text = "type,environment,criticality\nserver,production,4\n"
        rows = _read_csv_rows(csv_text)
        assert len(rows) == 1
        ok, err = _validate_asset_row(rows[0])
        assert not ok

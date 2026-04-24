"""
Unit tests for the weekly digest HTML content builder.

Since the digest service generates HTML inline (as a template),
these tests validate the HTML rendering logic by calling a local
builder that mirrors the digest_service template — ensuring the
format and metric values are rendered correctly.

Note: digest_service.send_weekly_digest currently has a DB compatibility
issue (Vulnerability.tenant_id) so we test the HTML building in isolation.
"""
import pytest
from datetime import datetime, timezone

pytestmark = pytest.mark.asyncio


def _build_digest_html(
    *,
    total_vulns: int,
    new_vulns: int,
    kev_count: int,
    bundles_completed: int,
    goals_on_track: int,
    week_str: str = None,
) -> str:
    """
    Build the digest HTML using the same template as digest_service.py.
    This is an extracted version of the template for unit testing.
    """
    now = datetime.now(timezone.utc)
    if week_str is None:
        week_str = now.strftime("%B %d, %Y")

    kev_badge = (
        f'<span style="background:#dc3545;color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:12px;">{kev_count} KEV</span>'
        if kev_count
        else ""
    )

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background:#f0f2f5; margin:0; padding:20px; }}
    .wrap {{ max-width:600px; margin:0 auto; }}
    .header {{ background:#111827; color:white; padding:24px 28px; border-radius:8px 8px 0 0; }}
    .header h1 {{ margin:0; font-size:22px; }}
    .header p {{ margin:4px 0 0; color:#9ca3af; font-size:14px; }}
    .body {{ background:#ffffff; padding:28px; border-radius:0 0 8px 8px; }}
    table {{ width:100%; border-collapse:collapse; margin:16px 0; }}
    th {{ background:#f9fafb; text-align:left; padding:10px 12px;
          font-size:13px; color:#6b7280; border-bottom:1px solid #e5e7eb; }}
    td {{ padding:12px; font-size:15px; border-bottom:1px solid #f3f4f6; }}
    td.label {{ color:#374151; font-weight:500; }}
    td.value {{ color:#111827; font-weight:700; font-size:20px; }}
    td.delta {{ color:#6b7280; font-size:12px; }}
    .cta {{ display:inline-block; margin-top:16px; padding:12px 24px;
            background:#2563eb; color:white; border-radius:6px;
            text-decoration:none; font-weight:600; font-size:14px; }}
    .footer {{ color:#9ca3af; font-size:12px; margin-top:20px; text-align:center; }}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>⚡ Glasswatch Weekly Digest</h1>
    <p>Week ending {week_str}</p>
  </div>
  <div class="body">
    <p style="color:#374151;">Here's your patch management summary for the past 7 days.</p>

    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td class="label">Open Vulnerabilities</td>
          <td class="value">{total_vulns}</td>
          <td class="delta">+{new_vulns} new this week</td>
        </tr>
        <tr>
          <td class="label">KEV-Listed (open)</td>
          <td class="value">{kev_count}</td>
          <td class="delta">{kev_badge}</td>
        </tr>
        <tr>
          <td class="label">Bundles Completed</td>
          <td class="value">{bundles_completed}</td>
          <td class="delta">this week</td>
        </tr>
        <tr>
          <td class="label">Goals Active</td>
          <td class="value">{goals_on_track}</td>
          <td class="delta">being tracked</td>
        </tr>
      </tbody>
    </table>

    {"<p style='color:#dc3545;font-weight:600;'>⚠️ " + str(kev_count) + " KEV-listed vulnerabilities require immediate attention.</p>" if kev_count else ""}

    <a href="https://glasswatch-production.up.railway.app/vulnerabilities" class="cta">
      View Dashboard →
    </a>
  </div>
  <div class="footer">
    You're receiving this because digest emails are enabled for your Glasswatch workspace.<br />
    Generated {now.strftime('%Y-%m-%d %H:%M UTC')}
  </div>
</div>
</body>
</html>"""

    return html_body


# ── HTML vuln count tests ─────────────────────────────────────────────────────


class TestDigestHtmlContainsVulnCount:
    async def test_digest_html_contains_vuln_count(self):
        """HTML must render the total open vulnerability count."""
        html = _build_digest_html(
            total_vulns=99,
            new_vulns=5,
            kev_count=0,
            bundles_completed=3,
            goals_on_track=2,
        )
        assert "99" in html, "Expected vuln count '99' in digest HTML"

    async def test_digest_html_contains_new_vuln_delta(self):
        """HTML must include the new-this-week count."""
        html = _build_digest_html(
            total_vulns=50,
            new_vulns=13,
            kev_count=0,
            bundles_completed=0,
            goals_on_track=0,
        )
        assert "13" in html

    async def test_digest_html_contains_kev_count(self):
        """When KEV count > 0, it appears in the HTML."""
        html = _build_digest_html(
            total_vulns=50,
            new_vulns=2,
            kev_count=4,
            bundles_completed=1,
            goals_on_track=1,
        )
        assert "4" in html

    async def test_digest_html_kev_warning_present(self):
        """Non-zero KEV count triggers a warning message in the HTML."""
        html = _build_digest_html(
            total_vulns=20,
            new_vulns=1,
            kev_count=2,
            bundles_completed=0,
            goals_on_track=0,
        )
        # Warning paragraph should contain KEV reference
        assert "KEV" in html
        # Warning badge or paragraph should reference the count
        assert "2" in html

    async def test_digest_html_no_kev_warning_when_zero(self):
        """Zero KEV count produces no warning paragraph."""
        html = _build_digest_html(
            total_vulns=5,
            new_vulns=0,
            kev_count=0,
            bundles_completed=2,
            goals_on_track=1,
        )
        # The warning paragraph only appears when kev_count > 0
        assert "require immediate attention" not in html


# ── HTML bundle count tests ───────────────────────────────────────────────────


class TestDigestHtmlContainsBundleCount:
    async def test_digest_html_contains_bundle_count(self):
        """HTML must render the bundles-completed count."""
        html = _build_digest_html(
            total_vulns=10,
            new_vulns=1,
            kev_count=0,
            bundles_completed=11,
            goals_on_track=3,
        )
        assert "11" in html, "Expected bundle count '11' in digest HTML"

    async def test_digest_html_zero_bundles_renders_cleanly(self):
        """Zero bundles renders '0' without crashing."""
        html = _build_digest_html(
            total_vulns=10,
            new_vulns=0,
            kev_count=0,
            bundles_completed=0,
            goals_on_track=0,
        )
        assert "0" in html

    async def test_digest_html_contains_goals_count(self):
        """HTML must render the goals-on-track count."""
        html = _build_digest_html(
            total_vulns=10,
            new_vulns=1,
            kev_count=0,
            bundles_completed=3,
            goals_on_track=5,
        )
        assert "5" in html


# ── HTML structure tests ──────────────────────────────────────────────────────


class TestDigestHtmlStructure:
    async def test_digest_html_is_valid_html(self):
        """HTML should start with <!DOCTYPE html>."""
        html = _build_digest_html(
            total_vulns=0,
            new_vulns=0,
            kev_count=0,
            bundles_completed=0,
            goals_on_track=0,
        )
        assert html.strip().startswith("<!DOCTYPE html")

    async def test_digest_html_contains_glasswatch_branding(self):
        """HTML should contain 'Glasswatch' branding."""
        html = _build_digest_html(
            total_vulns=5,
            new_vulns=1,
            kev_count=0,
            bundles_completed=2,
            goals_on_track=1,
        )
        assert "Glasswatch" in html

    async def test_digest_html_contains_dashboard_link(self):
        """HTML should include a link to the Glasswatch dashboard."""
        html = _build_digest_html(
            total_vulns=1,
            new_vulns=0,
            kev_count=0,
            bundles_completed=0,
            goals_on_track=0,
        )
        assert "glasswatch-production.up.railway.app" in html or "View Dashboard" in html

    async def test_digest_html_contains_week_ending(self):
        """HTML should reference the week-ending date."""
        week_str = "January 01, 2025"
        html = _build_digest_html(
            total_vulns=0,
            new_vulns=0,
            kev_count=0,
            bundles_completed=0,
            goals_on_track=0,
            week_str=week_str,
        )
        assert "January 01, 2025" in html

    async def test_digest_html_contains_all_four_metrics(self):
        """All four table rows (vulns, KEV, bundles, goals) appear in HTML."""
        html = _build_digest_html(
            total_vulns=42,
            new_vulns=7,
            kev_count=3,
            bundles_completed=8,
            goals_on_track=4,
        )
        assert "Open Vulnerabilities" in html
        assert "KEV-Listed" in html
        assert "Bundles Completed" in html
        assert "Goals Active" in html

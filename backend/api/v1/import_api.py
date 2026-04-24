"""
CSV Import API endpoints.

Handles bulk import of vulnerabilities and assets from CSV files.
Note: named import_api.py because 'import' is a Python reserved word.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth_compat import get_current_tenant_compat as get_current_tenant
from backend.db.session import get_db
from backend.models.asset import Asset
from backend.models.asset_vulnerability import AssetVulnerability
from backend.models.tenant import Tenant
from backend.models.vulnerability import Vulnerability

router = APIRouter()

# Maximum file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


def _parse_date(value: str) -> Optional[datetime]:
    """Parse a date string in various formats."""
    if not value or not value.strip():
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_float(value: str) -> Optional[float]:
    """Parse a float value, returning None on failure."""
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None


def _parse_int(value: str, default: int = 3) -> int:
    """Parse an integer value, returning default on failure."""
    if not value or not value.strip():
        return default
    try:
        v = int(value.strip())
        return max(1, min(5, v))  # Clamp to 1-5 for criticality
    except (ValueError, TypeError):
        return default


@router.post("/vulnerabilities/csv")
async def import_vulnerabilities_csv(
    file: UploadFile = File(..., description="CSV file with vulnerability data"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Import vulnerabilities from a CSV file.

    Expected CSV columns:
      - asset_name (or asset_ip): Asset hostname or IP address
      - cve_id: CVE identifier (e.g. CVE-2024-1234)
      - severity: CRITICAL, HIGH, MEDIUM, LOW
      - cvss_score: 0.0-10.0
      - discovered_date: YYYY-MM-DD

    Returns a summary of rows processed, assets created, vulns created, and errors.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    try:
        text = content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    rows_processed = 0
    assets_created = 0
    vulns_created = 0
    links_created = 0
    errors: List[str] = []

    for row_num, row in enumerate(reader, start=2):
        try:
            # Resolve asset identifier (support both asset_name and asset_ip columns)
            asset_identifier = (
                row.get("asset_name") or row.get("asset_ip") or row.get("hostname") or ""
            ).strip()

            cve_id = (row.get("cve_id") or row.get("cve") or "").strip().upper()
            severity = (row.get("severity") or "MEDIUM").strip().upper()
            cvss_score = _parse_float(row.get("cvss_score", ""))
            discovered_date = _parse_date(row.get("discovered_date", ""))

            if not asset_identifier:
                errors.append(f"Row {row_num}: missing asset_name or asset_ip")
                continue
            if not cve_id:
                errors.append(f"Row {row_num}: missing cve_id")
                continue
            if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"):
                severity = "MEDIUM"

            # Upsert Asset
            asset_result = await db.execute(
                select(Asset).where(
                    and_(
                        Asset.tenant_id == tenant.id,
                        Asset.identifier == asset_identifier,
                    )
                )
            )
            asset = asset_result.scalar_one_or_none()
            if not asset:
                asset = Asset(
                    id=uuid4(),
                    tenant_id=tenant.id,
                    identifier=asset_identifier,
                    name=asset_identifier,
                    type="server",
                    environment="production",
                    criticality=3,
                )
                db.add(asset)
                await db.flush()
                assets_created += 1

            # Upsert Vulnerability (global, not tenant-scoped)
            vuln_result = await db.execute(
                select(Vulnerability).where(Vulnerability.identifier == cve_id)
            )
            vuln = vuln_result.scalar_one_or_none()
            if not vuln:
                vuln = Vulnerability(
                    id=uuid4(),
                    identifier=cve_id,
                    source="import",
                    title=f"Imported: {cve_id}",
                    description=f"Imported from CSV on {datetime.now(timezone.utc).date()}",
                    severity=severity,
                    cvss_score=cvss_score,
                    kev_listed=False,
                    exploit_available=False,
                    patch_available=False,
                    published_at=discovered_date or datetime.now(timezone.utc),
                    affected_products=[],
                )
                db.add(vuln)
                await db.flush()
                vulns_created += 1
            else:
                # Update severity/cvss if provided
                if severity and severity != vuln.severity:
                    vuln.severity = severity
                if cvss_score is not None and vuln.cvss_score is None:
                    vuln.cvss_score = cvss_score

            # Upsert AssetVulnerability link
            link_result = await db.execute(
                select(AssetVulnerability).where(
                    and_(
                        AssetVulnerability.asset_id == asset.id,
                        AssetVulnerability.vulnerability_id == vuln.id,
                    )
                )
            )
            link = link_result.scalar_one_or_none()
            if not link:
                link = AssetVulnerability(
                    id=uuid4(),
                    asset_id=asset.id,
                    vulnerability_id=vuln.id,
                    status="ACTIVE",
                    risk_score=cvss_score * 10 if cvss_score else 50.0,
                    discovered_at=discovered_date or datetime.now(timezone.utc),
                )
                db.add(link)
                links_created += 1

            rows_processed += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            if len(errors) >= 50:
                errors.append("Too many errors — stopping after 50")
                break

    await db.commit()

    return {
        "rows_processed": rows_processed,
        "assets_created": assets_created,
        "vulns_created": vulns_created,
        "links_created": links_created,
        "errors": errors,
    }


@router.post("/assets/csv")
async def import_assets_csv(
    file: UploadFile = File(..., description="CSV file with asset data"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> Dict[str, Any]:
    """
    Import assets from a CSV file.

    Expected CSV columns:
      - name: Asset name (required)
      - type: server, container, function, database, application
      - environment: production, staging, development, test
      - ip_address: Primary IP address
      - owner_team: Owning team name
      - criticality: 1-5 (5 = most critical)

    Returns a summary of rows processed and assets created/updated.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no headers")

    rows_processed = 0
    assets_created = 0
    assets_updated = 0
    errors: List[str] = []

    for row_num, row in enumerate(reader, start=2):
        try:
            name = (row.get("name") or row.get("hostname") or row.get("identifier") or "").strip()
            if not name:
                errors.append(f"Row {row_num}: missing name/hostname/identifier")
                continue

            asset_type = (row.get("type") or "server").strip().lower()
            environment = (row.get("environment") or "production").strip().lower()
            ip_address = (row.get("ip_address") or row.get("ip") or "").strip()
            owner_team = (row.get("owner_team") or row.get("team") or "").strip()
            criticality = _parse_int(row.get("criticality", "3"), default=3)

            # Validate asset type
            valid_types = ("server", "container", "function", "database", "application", "network", "endpoint")
            if asset_type not in valid_types:
                asset_type = "server"

            # Upsert Asset by identifier
            result = await db.execute(
                select(Asset).where(
                    and_(
                        Asset.tenant_id == tenant.id,
                        Asset.identifier == name,
                    )
                )
            )
            asset = result.scalar_one_or_none()

            if not asset:
                asset = Asset(
                    id=uuid4(),
                    tenant_id=tenant.id,
                    identifier=name,
                    name=name,
                    type=asset_type,
                    environment=environment,
                    criticality=criticality,
                    owner_team=owner_team or None,
                    ip_addresses=[ip_address] if ip_address else [],
                )
                db.add(asset)
                assets_created += 1
            else:
                # Update fields
                asset.type = asset_type
                asset.environment = environment
                asset.criticality = criticality
                if owner_team:
                    asset.owner_team = owner_team
                if ip_address:
                    existing_ips = asset.ip_addresses or []
                    if ip_address not in existing_ips:
                        asset.ip_addresses = existing_ips + [ip_address]
                assets_updated += 1

            rows_processed += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            if len(errors) >= 50:
                errors.append("Too many errors — stopping after 50")
                break

    await db.commit()

    return {
        "rows_processed": rows_processed,
        "assets_created": assets_created,
        "assets_updated": assets_updated,
        "errors": errors,
    }

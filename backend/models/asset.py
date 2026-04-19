"""
Asset model - represents infrastructure components that may have vulnerabilities.

Tracks servers, containers, applications, databases, and other infrastructure.
Includes criticality scoring and exposure assessment for prioritization.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, 
    Index, JSON, Float, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.db.base_class import Base


class Asset(Base):
    """
    Infrastructure asset that may be affected by vulnerabilities.
    
    Multi-tenant model with flexible metadata for different asset types.
    Criticality and exposure are key inputs to vulnerability scoring.
    """
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_asset_tenant_id", "tenant_id"),
        Index("ix_asset_identifier", "tenant_id", "identifier", unique=True),
        Index("ix_asset_type", "type"),
        Index("ix_asset_criticality", "criticality"),
        Index("ix_asset_exposure", "exposure"),
    )

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    identifier = Column(String(255), nullable=False)  # hostname, instance-id, container-id
    name = Column(String(255), nullable=False)  # Human-friendly name
    
    # Asset classification
    type = Column(String(50), nullable=False)  # server, container, function, database, application
    platform = Column(String(50))  # aws, azure, gcp, k8s, on-prem, vmware
    environment = Column(String(50))  # production, staging, development, test
    
    # Location and ownership
    location = Column(String(255))  # us-east-1, datacenter-1, cluster-prod
    owner_team = Column(String(255))  # engineering, devops, security
    owner_email = Column(String(255))
    business_unit = Column(String(255))
    
    # Criticality and exposure (key scoring inputs)
    criticality = Column(Integer, nullable=False, default=3)  # 1-5 scale (5 = most critical)
    exposure = Column(String(20), nullable=False, default="ISOLATED")  # INTERNET, INTRANET, ISOLATED
    
    # Technical details
    os_family = Column(String(50))  # linux, windows, macos
    os_version = Column(String(100))  # Ubuntu 22.04, Windows Server 2022
    ip_addresses = Column(JSON)  # ["10.0.1.5", "172.16.0.10"]
    fqdn = Column(String(255))  # server1.prod.example.com
    
    # Cloud-specific metadata
    cloud_account_id = Column(String(255))  # AWS account, Azure subscription
    cloud_region = Column(String(50))  # us-east-1, westeurope
    cloud_instance_type = Column(String(50))  # t3.medium, Standard_D4s_v3
    cloud_tags = Column(JSON)  # {"Environment": "Prod", "CostCenter": "Engineering"}
    
    # Software inventory (simplified - full SBOM in separate table)
    installed_packages = Column(JSON)  # [{"name": "openssl", "version": "1.1.1k"}]
    running_services = Column(JSON)  # ["nginx", "postgresql", "redis"]
    open_ports = Column(JSON)  # [22, 80, 443, 5432]
    
    # Compliance and controls
    compliance_frameworks = Column(JSON)  # ["PCI-DSS", "HIPAA", "SOC2"]
    compensating_controls = Column(JSON)  # ["WAF", "IPS", "Network Isolation"]
    patch_group = Column(String(100))  # patch-group-web-prod, patch-group-db
    maintenance_window = Column(String(100))  # tuesday-2am-6am, saturday-midnight
    
    # Operational metadata
    last_scanned_at = Column(DateTime(timezone=True))
    last_patched_at = Column(DateTime(timezone=True))
    uptime_days = Column(Integer)
    
    # Integration references
    cmdb_id = Column(String(255))  # ServiceNow CI ID
    monitoring_id = Column(String(255))  # Datadog, New Relic ID
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="assets")
    asset_vulnerabilities = relationship("AssetVulnerability", back_populates="asset")
    
    def __repr__(self):
        return f"<Asset {self.identifier}: {self.type}/{self.platform}>"
    
    @property
    def risk_score(self) -> int:
        """Calculate base risk score for the asset (0-100)."""
        score = 0
        
        # Criticality contributes up to 50 points
        score += self.criticality * 10
        
        # Exposure contributes up to 30 points
        exposure_scores = {
            "INTERNET": 30,
            "INTRANET": 15,
            "ISOLATED": 0
        }
        score += exposure_scores.get(self.exposure.upper(), 0)
        
        # Environment contributes up to 20 points
        if self.environment and self.environment.lower() == "production":
            score += 20
        elif self.environment and self.environment.lower() == "staging":
            score += 10
        
        return min(score, 100)
    
    @property
    def is_internet_facing(self) -> bool:
        """Check if asset is exposed to the internet."""
        return self.exposure.upper() == "INTERNET"
    
    @property
    def has_compensating_controls(self) -> bool:
        """Check if asset has any compensating security controls."""
        return bool(self.compensating_controls)
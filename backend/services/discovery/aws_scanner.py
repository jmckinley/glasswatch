"""
AWS asset discovery scanner.

Discovers EC2 instances, ECS containers, Lambda functions, RDS databases,
EKS clusters, and other AWS resources.
"""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from backend.services.discovery.base import (
    BaseScanner, ScanResult, DiscoveredAsset,
    ScannerType, AssetType
)


class AWSScanner(BaseScanner):
    """
    AWS infrastructure discovery scanner.
    
    Requires: boto3, configured AWS credentials
    Discovers: EC2, ECS, Lambda, RDS, EKS
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.scanner_type = ScannerType.CLOUD
        self.scanner_name = "aws"
        
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for AWS scanning. Install: pip install boto3")
        
        # AWS credentials from config or environment
        self.session = boto3.Session(
            aws_access_key_id=config.get("aws_access_key_id") if config else None,
            aws_secret_access_key=config.get("aws_secret_access_key") if config else None,
            region_name=config.get("region", "us-east-1") if config else "us-east-1"
        )
        
        self.default_region = config.get("region", "us-east-1") if config else "us-east-1"
        self.scan_regions = config.get("regions", [self.default_region]) if config else [self.default_region]
    
    async def scan(self, target: Optional[str] = None, **kwargs) -> ScanResult:
        """
        Discover AWS assets across regions.
        
        Args:
            target: Optional region name to scan (overrides config)
            **kwargs: Additional options (resource_types, tags, etc.)
            
        Returns:
            ScanResult with discovered AWS assets
        """
        start_time = time.time()
        assets = []
        errors = []
        
        regions = [target] if target else self.scan_regions
        
        for region in regions:
            try:
                # EC2 instances
                ec2_assets = await self._discover_ec2(region, errors)
                assets.extend(ec2_assets)
                
                # RDS databases
                rds_assets = await self._discover_rds(region, errors)
                assets.extend(rds_assets)
                
                # Lambda functions
                lambda_assets = await self._discover_lambda(region, errors)
                assets.extend(lambda_assets)
                
                # ECS containers
                ecs_assets = await self._discover_ecs(region, errors)
                assets.extend(ecs_assets)
                
                # EKS clusters
                eks_assets = await self._discover_eks(region, errors)
                assets.extend(eks_assets)
                
            except Exception as e:
                errors.append(f"Failed to scan region {region}: {str(e)}")
        
        duration = time.time() - start_time
        
        return ScanResult(
            scanner_name=self.scanner_name,
            scanner_type=self.scanner_type,
            assets=assets,
            scan_duration_seconds=duration,
            errors=errors,
            metadata={
                "regions_scanned": regions,
                "resource_types": ["ec2", "rds", "lambda", "ecs", "eks"]
            }
        )
    
    async def _discover_ec2(self, region: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover EC2 instances."""
        assets = []
        
        try:
            ec2 = self.session.client("ec2", region_name=region)
            response = ec2.describe_instances()
            
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId")
                    state = instance.get("State", {}).get("Name")
                    
                    # Skip terminated instances
                    if state == "terminated":
                        continue
                    
                    # Extract tags
                    tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                    name = tags.get("Name", instance_id)
                    environment = tags.get("Environment", "unknown").lower()
                    
                    # Determine exposure (heuristic based on public IP)
                    has_public_ip = bool(instance.get("PublicIpAddress"))
                    exposure = "INTERNET" if has_public_ip else "INTRANET"
                    
                    # Determine criticality from tags
                    criticality_map = {
                        "critical": 5,
                        "high": 4,
                        "medium": 3,
                        "low": 2,
                        "dev": 1
                    }
                    criticality = criticality_map.get(
                        tags.get("Criticality", "medium").lower(),
                        3
                    )
                    
                    # Build IP list
                    ip_addresses = []
                    if instance.get("PrivateIpAddress"):
                        ip_addresses.append(instance["PrivateIpAddress"])
                    if instance.get("PublicIpAddress"):
                        ip_addresses.append(instance["PublicIpAddress"])
                    
                    # Get OS info from platform
                    platform_details = instance.get("PlatformDetails", "")
                    os_family = "linux"
                    if "Windows" in platform_details:
                        os_family = "windows"
                    
                    asset = DiscoveredAsset(
                        identifier=instance_id,
                        name=name,
                        type=AssetType.SERVER.value,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="aws",
                        environment=environment,
                        location=region,
                        criticality=criticality,
                        exposure=exposure,
                        os_family=os_family,
                        ip_addresses=ip_addresses,
                        cloud_account_id=instance.get("OwnerId"),
                        cloud_region=region,
                        cloud_instance_type=instance.get("InstanceType"),
                        cloud_tags=tags,
                        owner_team=tags.get("Owner"),
                        raw_data=instance
                    )
                    
                    assets.append(asset)
        
        except (ClientError, NoCredentialsError) as e:
            errors.append(f"EC2 discovery failed in {region}: {str(e)}")
        
        return assets
    
    async def _discover_rds(self, region: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover RDS database instances."""
        assets = []
        
        try:
            rds = self.session.client("rds", region_name=region)
            response = rds.describe_db_instances()
            
            for db in response.get("DBInstances", []):
                db_id = db.get("DBInstanceIdentifier")
                
                # Determine exposure (public accessibility)
                is_public = db.get("PubliclyAccessible", False)
                exposure = "INTERNET" if is_public else "INTRANET"
                
                # Extract tags
                arn = db.get("DBInstanceArn")
                tags = {}
                try:
                    tags_response = rds.list_tags_for_resource(ResourceName=arn)
                    tags = {tag["Key"]: tag["Value"] for tag in tags_response.get("TagList", [])}
                except Exception:
                    pass
                
                environment = tags.get("Environment", "unknown").lower()
                
                # Databases are typically critical
                criticality = 4
                
                asset = DiscoveredAsset(
                    identifier=db_id,
                    name=db_id,
                    type=AssetType.DATABASE.value,
                    scanner_type=self.scanner_type.value,
                    source=self.scanner_name,
                    platform="aws",
                    environment=environment,
                    location=region,
                    criticality=criticality,
                    exposure=exposure,
                    cloud_account_id=arn.split(":")[4] if arn else None,
                    cloud_region=region,
                    cloud_instance_type=db.get("DBInstanceClass"),
                    cloud_tags=tags,
                    owner_team=tags.get("Owner"),
                    running_services=[db.get("Engine", "unknown")],
                    raw_data=db
                )
                
                assets.append(asset)
        
        except (ClientError, NoCredentialsError) as e:
            errors.append(f"RDS discovery failed in {region}: {str(e)}")
        
        return assets
    
    async def _discover_lambda(self, region: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover Lambda functions."""
        assets = []
        
        try:
            lambda_client = self.session.client("lambda", region_name=region)
            paginator = lambda_client.get_paginator("list_functions")
            
            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    func_name = func.get("FunctionName")
                    
                    # Get tags
                    arn = func.get("FunctionArn")
                    tags = {}
                    try:
                        tags_response = lambda_client.list_tags(Resource=arn)
                        tags = tags_response.get("Tags", {})
                    except Exception:
                        pass
                    
                    environment_vars = func.get("Environment", {}).get("Variables", {})
                    environment = tags.get("Environment", "unknown").lower()
                    
                    # Lambda exposure depends on trigger (default isolated)
                    exposure = "ISOLATED"
                    
                    asset = DiscoveredAsset(
                        identifier=func_name,
                        name=func_name,
                        type=AssetType.LAMBDA.value,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="aws",
                        environment=environment,
                        location=region,
                        criticality=3,
                        exposure=exposure,
                        cloud_account_id=arn.split(":")[4] if arn else None,
                        cloud_region=region,
                        cloud_tags=tags,
                        owner_team=tags.get("Owner"),
                        raw_data=func
                    )
                    
                    assets.append(asset)
        
        except (ClientError, NoCredentialsError) as e:
            errors.append(f"Lambda discovery failed in {region}: {str(e)}")
        
        return assets
    
    async def _discover_ecs(self, region: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover ECS tasks and services."""
        assets = []
        
        try:
            ecs = self.session.client("ecs", region_name=region)
            
            # List clusters
            clusters_response = ecs.list_clusters()
            
            for cluster_arn in clusters_response.get("clusterArns", []):
                cluster_name = cluster_arn.split("/")[-1]
                
                # List services in cluster
                services_response = ecs.list_services(cluster=cluster_arn)
                
                for service_arn in services_response.get("serviceArns", []):
                    service_name = service_arn.split("/")[-1]
                    
                    asset = DiscoveredAsset(
                        identifier=f"ecs:{cluster_name}/{service_name}",
                        name=service_name,
                        type=AssetType.CONTAINER.value,
                        scanner_type=self.scanner_type.value,
                        source=self.scanner_name,
                        platform="aws",
                        location=f"{region}/{cluster_name}",
                        criticality=3,
                        exposure="INTRANET",
                        cloud_region=region,
                        cloud_tags={"cluster": cluster_name},
                        raw_data={"service_arn": service_arn, "cluster_arn": cluster_arn}
                    )
                    
                    assets.append(asset)
        
        except (ClientError, NoCredentialsError) as e:
            errors.append(f"ECS discovery failed in {region}: {str(e)}")
        
        return assets
    
    async def _discover_eks(self, region: str, errors: List[str]) -> List[DiscoveredAsset]:
        """Discover EKS clusters."""
        assets = []
        
        try:
            eks = self.session.client("eks", region_name=region)
            response = eks.list_clusters()
            
            for cluster_name in response.get("clusters", []):
                # Get cluster details
                cluster_info = eks.describe_cluster(name=cluster_name)
                cluster = cluster_info.get("cluster", {})
                
                asset = DiscoveredAsset(
                    identifier=f"eks:{cluster_name}",
                    name=cluster_name,
                    type=AssetType.APPLICATION.value,
                    scanner_type=ScannerType.KUBERNETES.value,
                    source=self.scanner_name,
                    platform="aws",
                    location=region,
                    criticality=4,
                    exposure="INTRANET",
                    cloud_region=region,
                    cloud_tags=cluster.get("tags", {}),
                    raw_data=cluster
                )
                
                assets.append(asset)
        
        except (ClientError, NoCredentialsError) as e:
            errors.append(f"EKS discovery failed in {region}: {str(e)}")
        
        return assets
    
    async def test_connection(self) -> bool:
        """Test AWS credentials and connectivity."""
        try:
            sts = self.session.client("sts")
            sts.get_caller_identity()
            return True
        except Exception:
            return False
    
    def get_required_config(self) -> List[str]:
        """AWS scanner can use environment credentials or explicit config."""
        return []  # Optional: aws_access_key_id, aws_secret_access_key

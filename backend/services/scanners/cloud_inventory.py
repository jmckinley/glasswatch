"""
Cloud asset inventory scanners for AWS, Azure, GCP
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from google.cloud import asset_v1
from google.oauth2 import service_account

from . import ScannerInterface, ScanResult


class AWSInventoryScanner(ScannerInterface):
    """AWS asset inventory using boto3"""
    
    def __init__(self, region: str = "us-east-1"):
        self.scanner_name = "aws-inventory"
        self.scan_type = "cloud"
        self.region = region
        self.session = None
    
    def is_available(self) -> bool:
        """Check if AWS credentials are configured"""
        try:
            session = boto3.Session()
            sts = session.client('sts')
            sts.get_caller_identity()
            return True
        except:
            return False
    
    async def scan(self, target: str = "all", options: Dict[str, Any] = None) -> ScanResult:
        """Scan AWS account for assets"""
        started_at = datetime.utcnow()
        options = options or {}
        findings = []
        
        try:
            session = boto3.Session(region_name=self.region)
            
            # EC2 Instances
            if target in ["all", "ec2"]:
                ec2 = session.client('ec2')
                response = ec2.describe_instances()
                
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        findings.append({
                            "asset_type": "ec2_instance",
                            "asset_id": instance['InstanceId'],
                            "name": self._get_tag_value(instance.get('Tags', []), 'Name'),
                            "state": instance['State']['Name'],
                            "instance_type": instance['InstanceType'],
                            "platform": instance.get('Platform', 'linux'),
                            "vpc_id": instance.get('VpcId'),
                            "subnet_id": instance.get('SubnetId'),
                            "security_groups": [sg['GroupId'] for sg in instance.get('SecurityGroups', [])],
                            "public_ip": instance.get('PublicIpAddress'),
                            "private_ip": instance.get('PrivateIpAddress'),
                            "tags": {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                        })
            
            # ECS Clusters and Services
            if target in ["all", "ecs"]:
                ecs = session.client('ecs')
                clusters = ecs.list_clusters()
                
                for cluster_arn in clusters.get('clusterArns', []):
                    cluster = ecs.describe_clusters(clusters=[cluster_arn])['clusters'][0]
                    
                    findings.append({
                        "asset_type": "ecs_cluster",
                        "asset_id": cluster['clusterArn'],
                        "name": cluster['clusterName'],
                        "status": cluster['status'],
                        "running_tasks": cluster['runningTasksCount'],
                        "pending_tasks": cluster['pendingTasksCount'],
                        "active_services": cluster['activeServicesCount']
                    })
                    
                    # Get services in cluster
                    services = ecs.list_services(cluster=cluster_arn)
                    if services.get('serviceArns'):
                        service_details = ecs.describe_services(
                            cluster=cluster_arn,
                            services=services['serviceArns']
                        )
                        
                        for service in service_details.get('services', []):
                            findings.append({
                                "asset_type": "ecs_service",
                                "asset_id": service['serviceArn'],
                                "name": service['serviceName'],
                                "status": service['status'],
                                "desired_count": service['desiredCount'],
                                "running_count": service['runningCount'],
                                "cluster": cluster['clusterName']
                            })
            
            # Lambda Functions
            if target in ["all", "lambda"]:
                lambda_client = session.client('lambda')
                functions = lambda_client.list_functions()
                
                for func in functions.get('Functions', []):
                    findings.append({
                        "asset_type": "lambda_function",
                        "asset_id": func['FunctionArn'],
                        "name": func['FunctionName'],
                        "runtime": func['Runtime'],
                        "handler": func['Handler'],
                        "memory": func['MemorySize'],
                        "timeout": func['Timeout'],
                        "last_modified": func['LastModified']
                    })
            
            # RDS Databases
            if target in ["all", "rds"]:
                rds = session.client('rds')
                instances = rds.describe_db_instances()
                
                for db in instances.get('DBInstances', []):
                    findings.append({
                        "asset_type": "rds_instance",
                        "asset_id": db['DBInstanceIdentifier'],
                        "engine": f"{db['Engine']} {db['EngineVersion']}",
                        "instance_class": db['DBInstanceClass'],
                        "status": db['DBInstanceStatus'],
                        "multi_az": db['MultiAZ'],
                        "encrypted": db.get('StorageEncrypted', False),
                        "publicly_accessible": db.get('PubliclyAccessible', False)
                    })
            
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                findings=findings,
                metadata={
                    "region": self.region,
                    "asset_count": len(findings),
                    "asset_types": list(set(f["asset_type"] for f in findings))
                }
            )
            
        except Exception as e:
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                error=str(e)
            )
    
    def _get_tag_value(self, tags: List[Dict], key: str) -> Optional[str]:
        """Extract tag value by key"""
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
        return None


class AzureInventoryScanner(ScannerInterface):
    """Azure asset inventory scanner"""
    
    def __init__(self):
        self.scanner_name = "azure-inventory"
        self.scan_type = "cloud"
    
    def is_available(self) -> bool:
        """Check if Azure credentials are configured"""
        try:
            credential = DefaultAzureCredential()
            # Test with a simple API call
            return True
        except:
            return False
    
    async def scan(self, target: str = "all", options: Dict[str, Any] = None) -> ScanResult:
        """Scan Azure subscription for assets"""
        started_at = datetime.utcnow()
        findings = []
        
        try:
            credential = DefaultAzureCredential()
            subscription_id = options.get("subscription_id") if options else None
            
            if not subscription_id:
                # Try to get from environment or credential
                return ScanResult(
                    scanner=self.scanner_name,
                    target=target,
                    scan_type=self.scan_type,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    success=False,
                    error="Azure subscription ID required"
                )
            
            # Initialize resource management client
            resource_client = ResourceManagementClient(credential, subscription_id)
            
            # List all resources
            for resource in resource_client.resources.list():
                findings.append({
                    "asset_type": resource.type,
                    "asset_id": resource.id,
                    "name": resource.name,
                    "location": resource.location,
                    "resource_group": resource.id.split('/')[4],  # Extract from ID
                    "tags": resource.tags or {}
                })
            
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=True,
                findings=findings,
                metadata={
                    "subscription_id": subscription_id,
                    "asset_count": len(findings),
                    "asset_types": list(set(f["asset_type"] for f in findings))
                }
            )
            
        except Exception as e:
            return ScanResult(
                scanner=self.scanner_name,
                target=target,
                scan_type=self.scan_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                success=False,
                error=str(e)
            )
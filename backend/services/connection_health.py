"""
Connection health check service.

Provides health checks for various provider types.
"""
from typing import Dict, Any, Tuple
import httpx
from datetime import datetime, timezone


class ConnectionHealthService:
    """
    Health check service for external connections.
    
    Implements provider-specific health checks.
    """
    
    async def check_health(self, provider: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check health of a connection.
        
        Args:
            provider: Provider type
            config: Connection configuration
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Route to provider-specific check
        if provider == "aws":
            return await self._check_aws(config)
        elif provider == "azure":
            return await self._check_azure(config)
        elif provider == "gcp":
            return await self._check_gcp(config)
        elif provider == "slack":
            return await self._check_slack(config)
        elif provider == "jira":
            return await self._check_jira(config)
        elif provider == "servicenow":
            return await self._check_servicenow(config)
        elif provider == "webhook":
            return await self._check_webhook(config)
        else:
            return False, f"Unknown provider: {provider}"
    
    async def _check_aws(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check AWS connection using STS GetCallerIdentity.
        
        Args:
            config: AWS configuration (access_key, secret_key, region)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            access_key = config.get("access_key_id")
            secret_key = config.get("secret_access_key")
            region = config.get("region", "us-east-1")
            
            if not access_key or not secret_key:
                return False, "Missing AWS credentials"
            
            # Try using boto3 if available
            try:
                import boto3
                from botocore.exceptions import ClientError, BotoCoreError
                
                # Create STS client
                sts = boto3.client(
                    'sts',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
                
                # Call GetCallerIdentity to verify credentials
                response = sts.get_caller_identity()
                account = response.get('Account', 'unknown')
                arn = response.get('Arn', 'unknown')
                
                return True, f"AWS credentials valid for account {account}"
                
            except ImportError:
                # boto3 not available - fall back to format validation
                if len(access_key) < 16 or len(secret_key) < 20:
                    return False, "Invalid AWS credential format"
                
                return True, "AWS credentials format valid (install boto3 for full verification)"
            
            except (ClientError, BotoCoreError) as e:
                return False, f"AWS authentication failed: {str(e)}"
        
        except Exception as e:
            return False, f"AWS health check failed: {str(e)}"
    
    async def _check_azure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check Azure connection using OAuth2 token endpoint.
        
        Args:
            config: Azure configuration (tenant_id, client_id, client_secret)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            tenant_id = config.get("tenant_id")
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
            
            if not all([tenant_id, client_id, client_secret]):
                return False, "Missing Azure credentials"
            
            # Use client credentials grant to get a token
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": "https://management.azure.com/.default"
                    },
                    timeout=10.0,
                )
                
                if response.status_code != 200:
                    data = response.json()
                    error_description = data.get("error_description", "Authentication failed")
                    return False, f"Azure authentication failed: {error_description}"
                
                data = response.json()
                token_type = data.get("token_type", "unknown")
                
                return True, f"Azure credentials valid (token type: {token_type})"
        
        except Exception as e:
            return False, f"Azure health check failed: {str(e)}"
    
    async def _check_gcp(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check GCP connection by validating service account JSON.
        
        Args:
            config: GCP configuration (service_account_json or credentials)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            import json
            
            credentials = config.get("service_account_json") or config.get("credentials")
            
            if not credentials:
                return False, "Missing GCP credentials"
            
            # Parse the service account JSON
            if isinstance(credentials, str):
                try:
                    creds_dict = json.loads(credentials)
                except json.JSONDecodeError:
                    return False, "Invalid JSON format for service account credentials"
            elif isinstance(credentials, dict):
                creds_dict = credentials
            else:
                return False, "Credentials must be a JSON string or dict"
            
            # Validate required fields
            required_fields = ["client_email", "private_key", "project_id", "type"]
            missing_fields = [f for f in required_fields if f not in creds_dict]
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            if creds_dict.get("type") != "service_account":
                return False, f"Invalid credential type: {creds_dict.get('type')} (expected 'service_account')"
            
            # Try using google-auth if available for token exchange
            try:
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request
                
                # Create credentials object
                credentials_obj = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]
                )
                
                # Note: We're not actually making a request here, just validating the credentials can be created
                # A full check would refresh the token, but that requires sync code
                project_id = creds_dict.get("project_id")
                client_email = creds_dict.get("client_email")
                
                return True, f"GCP service account valid: {client_email} (project: {project_id})"
                
            except ImportError:
                # google-auth not available - return format validation success
                project_id = creds_dict.get("project_id")
                client_email = creds_dict.get("client_email")
                
                return True, f"GCP credentials format valid: {client_email} (project: {project_id}, install google-auth for full verification)"
            
            except Exception as e:
                return False, f"GCP credential validation failed: {str(e)}"
        
        except Exception as e:
            return False, f"GCP health check failed: {str(e)}"
    
    async def _check_slack(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check Slack connection using auth.test.
        
        Args:
            config: Slack configuration (access_token)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            access_token = config.get("access_token")
            
            if not access_token:
                return False, "Missing Slack access token"
            
            # Call Slack auth.test
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                
                if response.status_code != 200:
                    return False, f"Slack API returned {response.status_code}"
                
                data = response.json()
                
                if not data.get("ok"):
                    error = data.get("error", "unknown")
                    return False, f"Slack auth failed: {error}"
                
                team_name = data.get("team", "unknown")
                return True, f"Connected to Slack workspace: {team_name}"
        
        except Exception as e:
            return False, f"Slack health check failed: {str(e)}"
    
    async def _check_jira(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check Jira connection.
        
        Args:
            config: Jira configuration (url, email, api_token)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            url = config.get("url")
            email = config.get("email")
            api_token = config.get("api_token")
            
            if not all([url, email, api_token]):
                return False, "Missing Jira credentials"
            
            # Call Jira API to get current user
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}/rest/api/2/myself",
                    auth=(email, api_token),
                    timeout=10.0,
                )
                
                if response.status_code == 401:
                    return False, "Jira authentication failed"
                
                if response.status_code != 200:
                    return False, f"Jira API returned {response.status_code}"
                
                data = response.json()
                display_name = data.get("displayName", "unknown")
                return True, f"Connected to Jira as {display_name}"
        
        except Exception as e:
            return False, f"Jira health check failed: {str(e)}"
    
    async def _check_servicenow(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check ServiceNow connection.
        
        Args:
            config: ServiceNow configuration (instance_url, username, password)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            instance_url = config.get("instance_url")
            username = config.get("username")
            password = config.get("password")
            
            if not all([instance_url, username, password]):
                return False, "Missing ServiceNow credentials"
            
            # Call ServiceNow API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{instance_url}/api/now/table/sys_user",
                    params={"sysparm_limit": 1},
                    auth=(username, password),
                    timeout=10.0,
                )
                
                if response.status_code == 401:
                    return False, "ServiceNow authentication failed"
                
                if response.status_code != 200:
                    return False, f"ServiceNow API returned {response.status_code}"
                
                return True, f"Connected to ServiceNow instance"
        
        except Exception as e:
            return False, f"ServiceNow health check failed: {str(e)}"
    
    async def _check_webhook(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check generic webhook connection.
        
        Args:
            config: Webhook configuration (url)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            url = config.get("url")
            
            if not url:
                return False, "Missing webhook URL"
            
            # Send HEAD request
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=10.0)
                
                if response.status_code >= 500:
                    return False, f"Webhook returned server error: {response.status_code}"
                
                return True, f"Webhook endpoint reachable (status {response.status_code})"
        
        except Exception as e:
            return False, f"Webhook health check failed: {str(e)}"


# Global service instance
connection_health_service = ConnectionHealthService()

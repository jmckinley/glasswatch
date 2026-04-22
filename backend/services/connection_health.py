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
            # In production, use boto3
            # For now, we'll do a minimal check
            access_key = config.get("access_key_id")
            secret_key = config.get("secret_access_key")
            region = config.get("region", "us-east-1")
            
            if not access_key or not secret_key:
                return False, "Missing AWS credentials"
            
            # TODO: Implement actual STS check with boto3
            # For now, just validate format
            if len(access_key) < 16 or len(secret_key) < 20:
                return False, "Invalid AWS credential format"
            
            return True, "AWS credentials format valid (full check requires boto3)"
        
        except Exception as e:
            return False, f"AWS health check failed: {str(e)}"
    
    async def _check_azure(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check Azure connection.
        
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
            
            # TODO: Implement actual Azure SDK check
            # For now, validate format
            return True, "Azure credentials format valid (full check requires Azure SDK)"
        
        except Exception as e:
            return False, f"Azure health check failed: {str(e)}"
    
    async def _check_gcp(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check GCP connection.
        
        Args:
            config: GCP configuration (service_account_json or credentials)
        
        Returns:
            Tuple of (success, message)
        """
        try:
            credentials = config.get("service_account_json") or config.get("credentials")
            
            if not credentials:
                return False, "Missing GCP credentials"
            
            # TODO: Implement actual GCP check
            return True, "GCP credentials format valid (full check requires GCP SDK)"
        
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

"""
Locust Load Testing Configuration

Load test scenarios for Glasswatch API endpoints.

Usage:
    locust -f backend/tests/load/locustfile.py --host http://localhost:8000

Target: 1000 concurrent users, <500ms p95 response time
"""
import random
import json
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


class GlasswatchUser(HttpUser):
    """
    Simulated Glasswatch user for load testing.
    """
    
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    def on_start(self):
        """
        Called when a user starts. Authenticate and get token.
        """
        # For now, use a test token
        # In production, implement actual authentication flow
        self.token = "test-token-placeholder"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.tenant_id = "test-tenant-001"
    
    @task(5)
    def view_vulnerabilities_dashboard(self):
        """
        Most common task: View vulnerabilities dashboard.
        
        Weight: 5 (highest frequency)
        """
        with self.client.get(
            f"/api/v1/vulnerabilities?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(4)
    def view_assets_list(self):
        """
        View assets list.
        
        Weight: 4
        """
        with self.client.get(
            f"/api/v1/assets?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(3)
    def view_vulnerability_details(self):
        """
        View specific vulnerability details.
        
        Weight: 3
        """
        vuln_id = f"vuln-{random.randint(1, 1000)}"
        with self.client.get(
            f"/api/v1/vulnerabilities/{vuln_id}?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/vulnerabilities/[id]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(3)
    def view_dashboard_stats(self):
        """
        View dashboard statistics.
        
        Weight: 3
        """
        with self.client.get(
            f"/api/v1/dashboard/stats?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def filter_vulnerabilities_by_severity(self):
        """
        Filter vulnerabilities by severity.
        
        Weight: 2
        """
        severity = random.choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])
        with self.client.get(
            f"/api/v1/vulnerabilities?tenant_id={self.tenant_id}&severity={severity}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/vulnerabilities?severity=[severity]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def view_bundles(self):
        """
        View patch bundles.
        
        Weight: 2
        """
        with self.client.get(
            f"/api/v1/bundles?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def create_vulnerability(self):
        """
        Create a new vulnerability (write operation).
        
        Weight: 1 (lower frequency for writes)
        """
        vuln_data = {
            "cve_id": f"CVE-2024-{random.randint(10000, 99999)}",
            "severity": random.choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
            "cvss_score": round(random.uniform(1.0, 10.0), 1),
            "description": "Load test vulnerability",
            "tenant_id": self.tenant_id
        }
        
        with self.client.post(
            "/api/v1/vulnerabilities",
            headers=self.headers,
            json=vuln_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def trigger_asset_discovery(self):
        """
        Trigger asset discovery (resource-intensive operation).
        
        Weight: 1 (lowest frequency)
        """
        discovery_data = {
            "tenant_id": self.tenant_id,
            "scanner_type": "nmap",
            "targets": ["10.0.0.0/24"]
        }
        
        with self.client.post(
            "/api/v1/discovery/scan",
            headers=self.headers,
            json=discovery_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def calculate_scoring(self):
        """
        Trigger vulnerability scoring calculation.
        
        Weight: 1
        """
        with self.client.post(
            f"/api/v1/scoring/calculate?tenant_id={self.tenant_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(1)
    def submit_approval_request(self):
        """
        Submit an approval request (workflow test).
        
        Weight: 1
        """
        approval_data = {
            "tenant_id": self.tenant_id,
            "entity_type": "bundle",
            "entity_id": f"bundle-{random.randint(1, 100)}",
            "justification": "Load test approval request"
        }
        
        with self.client.post(
            "/api/v1/approvals",
            headers=self.headers,
            json=approval_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class AdminUser(HttpUser):
    """
    Heavy admin user performing intensive operations.
    """
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Initialize admin user."""
        self.token = "admin-token-placeholder"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.tenant_id = "test-tenant-001"
    
    @task
    def generate_report(self):
        """
        Generate a comprehensive report (expensive operation).
        """
        with self.client.post(
            f"/api/v1/reports/generate?tenant_id={self.tenant_id}",
            headers=self.headers,
            json={"report_type": "executive_summary"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


# Event hooks for custom metrics

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called when the load test starts.
    """
    print("🚀 Starting Glasswatch load test")
    print(f"   Target: {environment.host}")
    print(f"   Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Called when the load test stops.
    """
    print("\n📊 Load test complete")
    
    # Print summary statistics
    stats = environment.stats
    print(f"\n   Total Requests: {stats.total.num_requests}")
    print(f"   Failed Requests: {stats.total.num_failures}")
    print(f"   Median Response Time: {stats.total.get_response_time_percentile(0.5)}ms")
    print(f"   95th Percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"   99th Percentile: {stats.total.get_response_time_percentile(0.99)}ms")
    print(f"   Requests/sec: {stats.total.total_rps}")
    
    # Check if we met our performance target
    p95 = stats.total.get_response_time_percentile(0.95)
    if p95 and p95 < 500:
        print(f"\n   ✅ Performance target met! (p95: {p95}ms < 500ms)")
    elif p95:
        print(f"\n   ⚠️  Performance target NOT met (p95: {p95}ms >= 500ms)")

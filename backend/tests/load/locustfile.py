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
        Called when a user starts. Authenticate via demo-login and get real token.
        """
        # Use the demo login endpoint to get a real access token
        with self.client.get(
            "/api/v1/auth/demo-login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token", "")
                response.success()
            else:
                self.token = ""
                response.failure(f"Demo login failed: {response.status_code}")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(5)
    def view_vulnerabilities_dashboard(self):
        """
        Most common task: View vulnerabilities dashboard.
        Weight: 5 (highest frequency)
        """
        with self.client.get(
            "/api/v1/vulnerabilities",
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
            "/api/v1/assets",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def view_bundles_list(self):
        """
        View patch bundles list.
        Weight: 3
        """
        with self.client.get(
            "/api/v1/bundles",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def view_goals_list(self):
        """
        View remediation goals.
        Weight: 3
        """
        with self.client.get(
            "/api/v1/goals",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def view_maintenance_windows(self):
        """
        View maintenance windows.
        Weight: 2
        """
        with self.client.get(
            "/api/v1/maintenance-windows",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def view_rules(self):
        """
        View automation rules.
        Weight: 2
        """
        with self.client.get(
            "/api/v1/rules",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def view_dashboard(self):
        """
        View dashboard metrics.
        Weight: 2
        """
        with self.client.get(
            "/api/v1/dashboard",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def view_single_vulnerability(self):
        """
        View a specific vulnerability.
        Weight: 1
        """
        vuln_id = f"CVE-2024-{random.randint(1000, 9999)}"
        with self.client.get(
            f"/api/v1/vulnerabilities/{vuln_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/vulnerabilities/[id]"
        ) as response:
            if response.status_code in [200, 404]:
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
            "entity_type": "bundle",
            "entity_id": str(random.randint(1, 100)),
            "justification": "Load test approval request"
        }

        with self.client.post(
            "/api/v1/approvals",
            headers=self.headers,
            json=approval_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 422]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class AdminUser(HttpUser):
    """
    Heavy admin user performing intensive operations.
    """

    wait_time = between(5, 10)

    def on_start(self):
        """Initialize admin user via demo login."""
        with self.client.get(
            "/api/v1/auth/demo-login",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token", "")
                response.success()
            else:
                self.token = ""
                response.failure(f"Demo login failed: {response.status_code}")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task
    def generate_report(self):
        """
        Generate a comprehensive report (expensive operation).
        """
        with self.client.get(
            "/api/v1/dashboard",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task
    def view_all_bundles(self):
        """Admin views all bundles."""
        with self.client.get(
            "/api/v1/bundles?limit=50",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
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
    p50 = stats.total.get_response_time_percentile(0.5)
    p95 = stats.total.get_response_time_percentile(0.95)
    p99 = stats.total.get_response_time_percentile(0.99)
    print(f"   Median Response Time: {p50}ms")
    print(f"   95th Percentile: {p95}ms")
    print(f"   99th Percentile: {p99}ms")
    print(f"   Requests/sec: {stats.total.total_rps}")

    # Check if we met our performance target
    if p95 and p95 < 500:
        print(f"\n   ✅ Performance target met! (p95: {p95}ms < 500ms)")
    elif p95:
        print(f"\n   ⚠️  Performance target NOT met (p95: {p95}ms >= 500ms)")

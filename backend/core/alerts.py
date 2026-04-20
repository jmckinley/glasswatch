"""
Alert configuration and notification system.

Defines alert rules, channels, and routing logic for system monitoring.
"""
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert notification channels."""
    SLACK = "slack"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    CONSOLE = "console"  # For development/testing


@dataclass
class AlertRule:
    """
    Alert rule definition.
    
    Defines when and how to trigger an alert.
    """
    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    operator: str  # ">", "<", ">=", "<=", "=="
    window_seconds: int = 300  # 5 minutes
    channels: List[AlertChannel] = None
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes between alerts
    
    def __post_init__(self):
        """Set default channels based on severity."""
        if self.channels is None:
            if self.severity == AlertSeverity.CRITICAL:
                self.channels = [AlertChannel.SLACK, AlertChannel.PAGERDUTY]
            elif self.severity == AlertSeverity.WARNING:
                self.channels = [AlertChannel.SLACK, AlertChannel.EMAIL]
            else:
                self.channels = [AlertChannel.CONSOLE]
    
    def evaluate(self, current_value: float) -> bool:
        """
        Evaluate if the alert should trigger.
        
        Args:
            current_value: Current metric value
        
        Returns:
            True if alert should trigger
        """
        if not self.enabled:
            return False
        
        if self.operator == ">":
            return current_value > self.threshold
        elif self.operator == "<":
            return current_value < self.threshold
        elif self.operator == ">=":
            return current_value >= self.threshold
        elif self.operator == "<=":
            return current_value <= self.threshold
        elif self.operator == "==":
            return current_value == self.threshold
        
        return False


# Default alert rules
DEFAULT_ALERT_RULES = [
    # Error rate alerts
    AlertRule(
        name="high_error_rate_warning",
        description="Error rate exceeds 5% threshold",
        severity=AlertSeverity.WARNING,
        metric_name="error_rate",
        threshold=0.05,
        operator=">",
        window_seconds=300,
    ),
    AlertRule(
        name="high_error_rate_critical",
        description="Error rate exceeds 15% threshold",
        severity=AlertSeverity.CRITICAL,
        metric_name="error_rate",
        threshold=0.15,
        operator=">",
        window_seconds=300,
    ),
    
    # Latency alerts
    AlertRule(
        name="high_latency_p95_warning",
        description="P95 latency exceeds 2 seconds",
        severity=AlertSeverity.WARNING,
        metric_name="latency_p95",
        threshold=2.0,
        operator=">",
        window_seconds=300,
    ),
    AlertRule(
        name="high_latency_p95_critical",
        description="P95 latency exceeds 5 seconds",
        severity=AlertSeverity.CRITICAL,
        metric_name="latency_p95",
        threshold=5.0,
        operator=">",
        window_seconds=300,
    ),
    
    # Database alerts
    AlertRule(
        name="db_connections_high",
        description="Database connections exceed 80% of pool",
        severity=AlertSeverity.WARNING,
        metric_name="db_connection_utilization",
        threshold=0.80,
        operator=">",
        window_seconds=60,
    ),
    AlertRule(
        name="db_query_slow",
        description="Database query time exceeds 1 second",
        severity=AlertSeverity.WARNING,
        metric_name="db_query_time",
        threshold=1.0,
        operator=">",
        window_seconds=60,
    ),
    
    # System resource alerts
    AlertRule(
        name="disk_space_critical",
        description="Disk usage exceeds 90%",
        severity=AlertSeverity.CRITICAL,
        metric_name="disk_usage_percent",
        threshold=90.0,
        operator=">",
        window_seconds=300,
    ),
    AlertRule(
        name="memory_high",
        description="Memory usage exceeds 85%",
        severity=AlertSeverity.WARNING,
        metric_name="memory_usage_percent",
        threshold=85.0,
        operator=">",
        window_seconds=300,
    ),
    AlertRule(
        name="cpu_high",
        description="CPU usage exceeds 90%",
        severity=AlertSeverity.WARNING,
        metric_name="cpu_usage_percent",
        threshold=90.0,
        operator=">",
        window_seconds=300,
    ),
]


class AlertManager:
    """
    Alert management system.
    
    Handles:
    - Alert rule evaluation
    - Alert deduplication
    - Alert routing to channels
    - Cooldown management
    - Escalation rules
    """
    
    def __init__(self, rules: Optional[List[AlertRule]] = None):
        """
        Initialize alert manager.
        
        Args:
            rules: List of alert rules (uses defaults if not provided)
        """
        self.rules = rules or DEFAULT_ALERT_RULES
        self.last_alert_time: Dict[str, float] = {}
        self.alert_counts: Dict[str, int] = {}
        self.notification_handlers: Dict[AlertChannel, Callable] = {}
        
        # Register default handlers
        self.register_handler(AlertChannel.CONSOLE, self._console_handler)
    
    def register_handler(self, channel: AlertChannel, handler: Callable):
        """
        Register a notification handler for a channel.
        
        Args:
            channel: Alert channel
            handler: Async handler function
        """
        self.notification_handlers[channel] = handler
    
    def add_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule by name."""
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """Get an alert rule by name."""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None
    
    def enable_rule(self, rule_name: str):
        """Enable an alert rule."""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = True
    
    def disable_rule(self, rule_name: str):
        """Disable an alert rule."""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = False
    
    async def evaluate_rules(self, metrics: Dict[str, float]):
        """
        Evaluate all alert rules against current metrics.
        
        Args:
            metrics: Dictionary of metric_name -> value
        """
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Check if metric is available
            if rule.metric_name not in metrics:
                continue
            
            current_value = metrics[rule.metric_name]
            
            # Evaluate rule
            if rule.evaluate(current_value):
                await self._trigger_alert(rule, current_value)
    
    async def _trigger_alert(self, rule: AlertRule, current_value: float):
        """
        Trigger an alert.
        
        Args:
            rule: Alert rule that triggered
            current_value: Current metric value
        """
        now = time.time()
        
        # Check cooldown
        last_alert = self.last_alert_time.get(rule.name, 0)
        if now - last_alert < rule.cooldown_seconds:
            return  # Still in cooldown period
        
        # Check for escalation
        should_escalate = await self._check_escalation(rule, current_value)
        
        # Build alert message
        alert = {
            "rule_name": rule.name,
            "description": rule.description,
            "severity": rule.severity.value,
            "metric_name": rule.metric_name,
            "current_value": current_value,
            "threshold": rule.threshold,
            "operator": rule.operator,
            "timestamp": datetime.utcnow().isoformat(),
            "escalated": should_escalate,
        }
        
        # Route to channels
        for channel in rule.channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await handler(alert)
                except Exception as e:
                    print(f"⚠️  Failed to send alert to {channel}: {e}")
        
        # Update tracking
        self.last_alert_time[rule.name] = now
        self.alert_counts[rule.name] = self.alert_counts.get(rule.name, 0) + 1
    
    async def _check_escalation(self, rule: AlertRule, current_value: float) -> bool:
        """
        Check if alert should be escalated.
        
        Escalation conditions:
        - Alert has triggered multiple times
        - Value is significantly above threshold
        
        Args:
            rule: Alert rule
            current_value: Current metric value
        
        Returns:
            True if alert should be escalated
        """
        # Check alert frequency
        count = self.alert_counts.get(rule.name, 0)
        if count >= 3:  # Third occurrence
            return True
        
        # Check if value is critically high
        if rule.operator in [">", ">="]:
            if current_value > rule.threshold * 2:  # 2x threshold
                return True
        
        return False
    
    async def _console_handler(self, alert: Dict[str, Any]):
        """
        Console alert handler (for development).
        
        Args:
            alert: Alert data
        """
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
        }
        
        emoji = severity_emoji.get(alert["severity"], "📢")
        escalated = " [ESCALATED]" if alert.get("escalated") else ""
        
        print(
            f"\n{emoji} ALERT{escalated}: {alert['description']}\n"
            f"   Rule: {alert['rule_name']}\n"
            f"   Metric: {alert['metric_name']}\n"
            f"   Current: {alert['current_value']:.2f} {alert['operator']} {alert['threshold']:.2f}\n"
            f"   Time: {alert['timestamp']}\n"
        )
    
    async def _slack_handler(self, alert: Dict[str, Any]):
        """
        Slack webhook handler.
        
        TODO: Implement Slack webhook integration
        
        Args:
            alert: Alert data
        """
        # TODO: Send to Slack webhook
        pass
    
    async def _email_handler(self, alert: Dict[str, Any]):
        """
        Email handler.
        
        TODO: Implement email integration
        
        Args:
            alert: Alert data
        """
        # TODO: Send email
        pass
    
    async def _pagerduty_handler(self, alert: Dict[str, Any]):
        """
        PagerDuty handler.
        
        TODO: Implement PagerDuty integration
        
        Args:
            alert: Alert data
        """
        # TODO: Send to PagerDuty
        pass


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager

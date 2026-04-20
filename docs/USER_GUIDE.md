# Glasswatch User Guide

**Transform vulnerability chaos into organized patch operations.**

Welcome to Glasswatch, the AI-powered patch decision platform that converts business objectives into optimized patch schedules.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Managing Vulnerabilities](#managing-vulnerabilities)
4. [Asset Management](#asset-management)
5. [Creating Goals](#creating-goals)
6. [Patch Bundles](#patch-bundles)
7. [Approval Workflows](#approval-workflows)
8. [Patch Simulator](#patch-simulator)
9. [Team Collaboration](#team-collaboration)
10. [Activity Feed & Notifications](#activity-feed--notifications)
11. [Best Practices](#best-practices)

---

## Getting Started

### First Login

#### Production (SSO)
1. Navigate to your organization's Glasswatch URL
2. Click "Login with SSO"
3. Enter your organization domain or ID
4. Authenticate through your identity provider (WorkOS SSO)
5. Grant necessary permissions
6. You'll be redirected to the Glasswatch dashboard

#### Demo Mode (Development/Testing)
1. Navigate to the Glasswatch instance
2. Click "Demo Login" (appears when WorkOS is not configured)
3. Automatically logged in as demo user with full access
4. Explore all features with sample data

### User Roles

| Role | Permissions |
|------|-------------|
| **Viewer** | Read-only access to dashboards and reports |
| **Analyst** | View + Comment + Create goals/bundles (no execution) |
| **Operator** | Analyst + Execute bundles + Manage assets |
| **Admin** | Full access including user management and configuration |

### Initial Setup Checklist

- [ ] Complete your user profile
- [ ] Set notification preferences
- [ ] Review existing assets (or import your infrastructure)
- [ ] Familiarize yourself with the dashboard
- [ ] Explore sample vulnerabilities and their risk scores
- [ ] Try creating a simple goal

---

## Dashboard Overview

The dashboard provides a real-time view of your patch management status.

### Key Widgets

#### Vulnerability Overview
- **Total Vulnerabilities**: All known vulnerabilities across your assets
- **Severity Distribution**: Breakdown by CRITICAL, HIGH, MEDIUM, LOW
- **KEV Listed**: CISA Known Exploited Vulnerabilities
- **Exploits Available**: Vulnerabilities with public exploits
- **Recent (7 days)**: Newly published vulnerabilities

#### Asset Health
- **Total Assets**: All infrastructure assets under management
- **By Environment**: Production, Staging, Development breakdown
- **Risk Score Distribution**: Assets by risk level
- **Internet-Facing**: Public-facing assets requiring priority

#### Patch Bundles
- **Pending Approval**: Bundles awaiting approval
- **Scheduled**: Approved bundles with future execution dates
- **In Progress**: Currently executing bundles
- **Completed (30 days)**: Recently completed patches

#### Active Goals
- **Goal Progress**: Percentage completion for each active goal
- **Target Dates**: Upcoming compliance deadlines
- **Risk Reduction**: Total risk points reduced

### Quick Actions
- Create new goal
- Import assets
- Trigger discovery scan
- Review pending approvals
- Generate compliance report

---

## Managing Vulnerabilities

Glasswatch aggregates vulnerability data from multiple sources (NVD, GHSA, vendor advisories) and enriches it with runtime context from Snapper.

### Viewing Vulnerabilities

1. Navigate to **Vulnerabilities** in the main menu
2. Use filters to narrow results:
   - **Severity**: CRITICAL, HIGH, MEDIUM, LOW
   - **KEV Status**: Show only CISA KEV-listed
   - **Exploit Availability**: Filter by exploit status
   - **Source**: NVD, GHSA, vendor-specific
   - **Search**: Find by CVE ID, title, or description

### Understanding Risk Scores

Glasswatch uses an **8-factor scoring algorithm** that goes beyond CVSS:

| Factor | Weight | Description |
|--------|--------|-------------|
| **CVSS Score** | 40% | Base severity (0-10) |
| **EPSS Score** | 20% | Exploit prediction probability |
| **KEV Listed** | +15 pts | CISA Known Exploited Vulnerabilities |
| **Exploit Available** | +10 pts | Public exploit code exists |
| **Asset Criticality** | 15% | Importance of affected assets (1-5) |
| **Asset Exposure** | 10% | Internet-facing, internal, or isolated |
| **Snapper Runtime** | ±25 pts | **Actual code execution detected** |
| **Patch Availability** | 5% | Vendor patch released |

**Total Risk Score**: 0-100 (higher = more urgent)

### Snapper Runtime Integration

**What is Snapper?**
Snapper is a runtime monitoring system that tracks actual code execution in your applications.

**Why it matters:**
- Traditional scoring assumes all vulnerabilities are equally exploitable
- Snapper shows which vulnerable code paths **actually run**
- **+25 points** if vulnerability code is executed regularly
- **-25 points** if vulnerable code is never executed
- This makes prioritization dramatically more accurate

**Example:**
```
CVE-2024-1234 in Apache Commons
- CVSS: 9.8 (Critical)
- Base Score: 78
- Snapper detects: Code NEVER executed
- Final Score: 53 (Medium priority)
→ Deprioritized for patching
```

### Vulnerability Detail Page

Click any vulnerability to view:
- **Full Description**: Technical details and impact
- **CVSS Vector**: Breakdown of attack complexity, privileges, etc.
- **Affected Assets**: List of your assets with this vulnerability
- **Patch Information**: Vendor advisory, patch release date, download links
- **Exploit Details**: Maturity level, POC availability
- **Patch Weather**: Community success rate for this patch
- **Snapper Data**: Runtime execution status per asset
- **Comments**: Team discussion and notes

### Adding Vulnerabilities Manually

While Glasswatch automatically discovers vulnerabilities through scanning, you can also add them manually:

1. Click **Add Vulnerability**
2. Enter CVE/GHSA identifier or fill form manually:
   - Identifier (e.g., CVE-2024-1234)
   - Title and description
   - Severity and CVSS score
   - Affected products
3. Select affected assets
4. Click **Save**

The system will automatically enrich the data with:
- NVD information (if available)
- EPSS score
- KEV status
- Patch availability

---

## Asset Management

Assets are your infrastructure components: servers, containers, cloud instances, databases, etc.

### Viewing Assets

1. Navigate to **Assets**
2. Filter by:
   - **Type**: Server, Container, Cloud Instance, Database, Application
   - **Platform**: Linux, Windows, Kubernetes, AWS, Azure, GCP
   - **Environment**: Production, Staging, Development
   - **Criticality**: 1 (Low) to 5 (Critical)
   - **Exposure**: Internet-facing, Internal, Isolated
   - **Search**: Name, identifier, FQDN, IP address

### Understanding Asset Criticality

| Level | Description | Example |
|-------|-------------|---------|
| **5 - Critical** | Revenue-generating, customer-facing | Payment API, E-commerce frontend |
| **4 - High** | Core business operations | Internal CRM, Email server |
| **3 - Medium** | Supporting systems | CI/CD, Monitoring |
| **2 - Low** | Development/testing | Dev servers, QA environments |
| **1 - Minimal** | Non-operational | Decommissioned, archived |

### Adding Assets Manually

1. Click **Add Asset**
2. Fill in required fields:
   - **Identifier**: Unique ID (hostname, instance ID, etc.)
   - **Name**: Human-readable name
   - **Type**: Asset type
   - **Platform**: Operating system or platform
   - **Environment**: Deployment environment
3. Fill optional fields:
   - Criticality (1-5)
   - Exposure level
   - Location/region
   - Owner team and email
   - IP addresses, FQDN
   - Cloud metadata (account ID, tags, etc.)
   - Compliance frameworks
   - Maintenance window
4. Click **Save**

### Bulk Import

For large-scale asset management:

1. Click **Import Assets**
2. Choose format: **JSON** or **CSV**
3. Download template
4. Fill in asset data
5. Upload file
6. Review import results:
   - Created: New assets added
   - Updated: Existing assets modified
   - Errors: Validation failures

**CSV Template:**
```csv
identifier,name,type,platform,environment,criticality,exposure,owner_team
prod-web-01,Production Web 01,server,linux,production,5,internet,platform
prod-db-01,Production DB 01,database,postgresql,production,5,internal,database
```

**JSON Template:**
```json
[
  {
    "identifier": "prod-web-01",
    "name": "Production Web 01",
    "type": "server",
    "platform": "linux",
    "environment": "production",
    "criticality": 5,
    "exposure": "internet",
    "owner_team": "platform"
  }
]
```

### Asset Vulnerabilities

View all vulnerabilities affecting an asset:

1. Click on an asset
2. **Vulnerabilities Tab** shows:
   - Active vulnerabilities
   - Risk score for each
   - Snapper runtime data (code executed, library loaded)
   - Recommended action
   - Patch status
3. Filter by:
   - Risk score threshold
   - Patch availability
   - Status (Active, Patched, Accepted Risk)

### Discovery Scanning

Automate asset and vulnerability discovery:

1. Navigate to **Discovery** > **Scans**
2. Click **New Scan**
3. Configure scan:
   - **Name**: Descriptive name
   - **Type**: Network scan, Cloud account scan, Container registry scan
   - **Targets**: IP ranges, cloud accounts, registries
   - **Options**: Port scan, service detection, vulnerability detection
4. Click **Run Scan**
5. Monitor progress in the scan list
6. Review discovered assets and vulnerabilities
7. Approve or merge new findings

**Scheduled Scans:**
- Set up recurring scans (daily, weekly, monthly)
- Automatically import new assets
- Alert on new critical vulnerabilities

---

## Creating Goals

**Goals are the heart of Glasswatch** - they convert business objectives into optimized patch schedules.

### Goal Types

| Type | Description | Example |
|------|-------------|---------|
| **Compliance Deadline** | Meet audit requirements by date | "SOC 2 ready by June 30" |
| **Risk Reduction** | Reduce overall risk by X% | "Cut risk score by 50%" |
| **Zero Critical** | Eliminate all critical vulnerabilities | "Zero critical on production" |
| **KEV Elimination** | Patch all CISA KEV vulnerabilities | "KEV-free by Q2" |
| **Custom** | Custom metrics and targets | Advanced use cases |

### Creating a Goal

1. Navigate to **Goals**
2. Click **Create Goal**
3. Fill in basic information:
   - **Name**: Clear, descriptive name
   - **Type**: Select goal type
   - **Description**: What you're trying to achieve
   - **Target Date**: Deadline for completion
4. Set target metrics (varies by type):
   - Compliance Deadline: Frameworks to satisfy
   - Risk Reduction: % or point reduction
   - Zero Critical: Target count (usually 0)
   - KEV Elimination: Specific KEV list
5. Configure constraints:
   - **Risk Tolerance**: Conservative, Balanced, Aggressive
   - **Max Vulnerabilities per Window**: Limit patches per maintenance window
   - **Max Downtime**: Maximum acceptable downtime per window (hours)
   - **Require Vendor Approval**: Wait for official vendor patches only
   - **Min Patch Weather Score**: Minimum community success rate (0-100)
6. Scope the goal:
   - **Asset Filters**: Which assets to include
     - Environment (production, staging, etc.)
     - Exposure (internet-facing, internal)
     - Criticality level
     - Owner team
   - **Vulnerability Filters**: Which vulnerabilities to address
     - Severity levels
     - KEV-listed only
     - Exploit availability
     - Published date range
7. Click **Create & Optimize**

### Understanding Risk Tolerance

| Setting | Approach | Best For |
|---------|----------|----------|
| **Conservative** | Slow, cautious patching | Critical production systems |
| **Balanced** | Moderate pace, best trade-off | Most environments |
| **Aggressive** | Fast patching, accepts some risk | Development, non-critical systems |

**What it affects:**
- Patches per maintenance window
- Acceptable downtime
- Testing requirements
- Rollback planning

### Running Optimization

After creating a goal, Glasswatch's constraint solver generates optimal patch bundles:

1. Click **Optimize** on your goal
2. Configure optimization:
   - **Maintenance Windows**: Number of windows to schedule
   - **Start Date**: When to begin patching
   - **Force Re-optimize**: Regenerate even if bundles exist
3. Click **Run Optimization**
4. Wait 10-30 seconds (shows progress)
5. Review generated bundles:
   - Bundle count
   - Vulnerabilities addressed
   - Estimated risk reduction
   - Total downtime required

**Optimization Algorithm:**
- Uses Google OR-Tools constraint solver
- Balances risk reduction vs. operational impact
- Respects maintenance windows
- Groups related patches for efficiency
- Minimizes downtime
- Considers dependencies

### Goal Progress Tracking

Monitor goal progress in real-time:
- **Progress Bar**: % of vulnerabilities resolved
- **Bundles Created**: Patch bundles generated
- **Bundles Completed**: Successfully executed bundles
- **Risk Reduction**: Total risk points reduced
- **Timeline**: Execution schedule vs. target date

### Previewing Before Creating Bundles

Want to see the plan before committing?

1. Navigate to your goal
2. Click **Preview Optimization**
3. Adjust parameters
4. See projected bundles without creating them
5. Iterate until satisfied
6. Click **Create Bundles** when ready

---

## Patch Bundles

Bundles are optimized groups of patches created by the goal engine.

### Bundle Lifecycle

```
Draft → Scheduled → Approved → In Progress → Completed
  ↓         ↓           ↓            ↓
Cancelled ←─────────────┘            ↓
                                   Failed
```

### Viewing Bundles

1. Navigate to **Bundles**
2. Filter by:
   - **Status**: Draft, Scheduled, Approved, In Progress, Completed, Failed
   - **Goal**: Parent goal
   - **Schedule**: Upcoming, past
3. Sort by:
   - Scheduled date
   - Risk score
   - Creation date

### Bundle Details

Click a bundle to view:
- **Overview**: Name, status, schedule, downtime estimate
- **Items**: Individual vulnerability + asset pairs
  - Vulnerability details
  - Asset details
  - Risk score
  - Patch time estimate
  - Snapper runtime data
- **Impact Summary**: Affected services, dependencies
- **Approval Status**: Who approved, when
- **Execution Log**: Real-time progress (if in progress)
- **Comments**: Team discussion

### Requesting Approval

If a bundle requires approval:

1. Open the bundle
2. Click **Request Approval**
3. Fill in request:
   - **Title**: Summary for approvers
   - **Description**: Details and justification
   - **Risk Level**: Your assessment
   - **Impact Summary**: Services affected, downtime estimate
4. Click **Submit**
5. Approvers will be notified
6. Track approval status in bundle details

### Executing a Bundle

Once approved:

1. Open the approved bundle
2. Verify:
   - Maintenance window is open
   - No change freezes active
   - Required resources available
3. Click **Execute**
4. Monitor real-time progress
5. Review completion status
6. Verify patches applied successfully

**Note**: Execution integrates with your patch deployment tools (Ansible, SCCM, AWS Systems Manager, etc.). Contact your admin for integration setup.

### Rollback

If something goes wrong:

1. Navigate to the bundle
2. Click **Rollback**
3. Confirm rollback action
4. System reverts changes
5. Bundle status changes to "Failed" with rollback note

---

## Approval Workflows

Glasswatch supports multi-level approval workflows for patch bundles.

### Approval Policies

Admins configure policies that determine when approval is required:

**Example Policy:**
```
Name: Production Critical Patches
Required Approvals: 2
Auto-Approve Threshold: null
Timeout: 48 hours
Conditions:
  - Environment: production
  - Risk Level: high OR critical
Approver Roles: admin, security_lead
```

### Requesting Approval (Detailed)

1. Navigate to **Approvals** > **Requests**
2. Click **New Request**
3. Select the bundle
4. Fill in request details:
   - Title (concise summary)
   - Description (full context)
   - Risk level assessment
   - Impact summary:
     - Assets affected
     - Services impacted
     - Estimated downtime
     - Rollback plan
5. Click **Submit**
6. Request is routed to appropriate approvers

### Approving a Request

If you're an approver:

1. Navigate to **Approvals** > **Pending**
2. Review request:
   - Bundle details
   - Affected assets and vulnerabilities
   - Risk assessment
   - Impact summary
   - Simulation results (if available)
3. Click **Approve** or **Reject**
4. Add comment explaining your decision
5. Click **Confirm**

**Approval Tips:**
- Review simulation results before approving
- Check for maintenance window availability
- Verify no change freezes are active
- Ensure rollback plan is documented
- Consider business impact timing

### Rejecting a Request

1. Open the approval request
2. Click **Reject**
3. **Required**: Add comment explaining why:
   - Insufficient testing
   - Missing rollback plan
   - Timing concerns
   - Risk too high
   - Better alternatives exist
4. Click **Confirm**
5. Requester is notified with your feedback

### Auto-Approval

Some policies support auto-approval for low-risk bundles:
- Risk score below threshold
- Only affects non-production environments
- All patches have high Patch Weather scores
- No critical services impacted

---

## Patch Simulator

The simulator predicts patch impact before execution.

### Running Impact Prediction

1. Open a bundle
2. Click **Simulate Impact**
3. Wait 10-15 seconds for analysis
4. Review results:
   - **Risk Score**: Overall execution risk (0-100)
   - **Risk Level**: Low, Medium, High, Critical
   - **Assets Affected**: Count and list
   - **Services Impacted**: Which services will be affected
   - **Estimated Downtime**: Total downtime in minutes
   - **Dependencies**: Related services and systems
   - **Rollback Plan**: Automated or manual
5. **Is Safe to Proceed?**: Green/yellow/red indicator

### Running Dry-Run Simulation

Full pre-flight validation:

1. Open a bundle
2. Click **Dry-Run**
3. System performs:
   - ✓ Package availability check
   - ✓ Disk space validation
   - ✓ Network connectivity test
   - ✓ Maintenance window verification
   - ✓ Change freeze check
   - ✓ Dependency analysis
   - ✓ Rollback plan validation
4. Review detailed results:
   - All checks passed?
   - Any warnings or blockers?
   - Recommended actions
5. Make go/no-go decision

### Interpreting Results

**Risk Levels:**
- **Low (0-30)**: Safe to proceed, minimal risk
- **Medium (31-60)**: Acceptable with proper planning
- **High (61-80)**: Requires careful consideration and rollback plan
- **Critical (81-100)**: High risk, consider alternatives

**Common Warnings:**
- "Maintenance window conflict detected"
- "Insufficient disk space on target"
- "Package not available in repository"
- "Change freeze active"
- "Low Patch Weather score"

---

## Team Collaboration

### Comments

Add comments to any resource (vulnerability, asset, bundle, goal):

1. Navigate to the resource
2. Scroll to **Comments** section
3. Type your comment
4. **@mention** teammates for notifications:
   - Type `@` and select from list
   - They'll receive notification
5. Click **Post**

**Formatting:**
- Basic markdown supported
- Code blocks with triple backticks
- Links auto-detected

### Mentions & Notifications

**Getting notified:**
- In-app notification bell
- Email digest (configure in preferences)
- Real-time browser notifications (if enabled)

**Notification types:**
- @mentions in comments
- Approval requests
- Bundle execution status changes
- Goal milestones reached
- Critical vulnerability discovered
- Scheduled bundle reminders

### Configuring Notifications

1. Click your avatar → **Preferences**
2. Navigate to **Notifications**
3. Choose preferences:
   - Email digest: Realtime, Hourly, Daily, Weekly, Off
   - Browser notifications: On/Off
   - Notification types to receive
4. Click **Save**

---

## Activity Feed & Notifications

### Activity Feed

Real-time timeline of all tenant actions:

1. Navigate to **Activity**
2. View chronological feed:
   - User actions
   - System events
   - Status changes
   - Approvals
   - Executions
3. Filter by:
   - User
   - Action type
   - Resource type
   - Date range
4. Search activities

**Example Activities:**
- "Alice approved Bundle #42"
- "System discovered 12 new vulnerabilities"
- "Bob created goal 'Q2 Compliance'"
- "Bundle #40 execution completed successfully"

### Real-Time Updates

Enable live updates:

1. Activity feed auto-refreshes
2. WebSocket connection for instant updates
3. Toast notifications for important events
4. Update badge counts on navigation items

---

## Best Practices

### Vulnerability Prioritization

**DO:**
- ✓ Trust Glasswatch's risk scores (they're smarter than CVSS alone)
- ✓ Pay attention to Snapper runtime data
- ✓ Prioritize KEV-listed vulnerabilities
- ✓ Consider asset criticality and exposure
- ✓ Use Patch Weather scores to avoid problematic patches

**DON'T:**
- ✗ Ignore CVSS scores entirely (they're part of the picture)
- ✗ Patch everything at once (increases risk)
- ✗ Skip testing because a patch looks "safe"
- ✗ Ignore vulnerabilities on internal assets

### Goal Creation

**DO:**
- ✓ Start with clear business objectives
- ✓ Set realistic target dates
- ✓ Use appropriate risk tolerance for each environment
- ✓ Scope goals narrowly at first (iterate and expand)
- ✓ Run preview before creating bundles

**DON'T:**
- ✗ Create overlapping goals (confuses optimization)
- ✗ Set impossible deadlines
- ✗ Use aggressive risk tolerance for production
- ✗ Ignore maintenance window constraints

### Patch Execution

**DO:**
- ✓ Always run simulation before approval
- ✓ Verify maintenance windows are clear
- ✓ Have rollback plans documented
- ✓ Monitor execution in real-time
- ✓ Verify success after completion
- ✓ Update runbooks based on experience

**DON'T:**
- ✗ Skip dry-run for production bundles
- ✗ Execute during business hours (unless emergency)
- ✗ Ignore warnings from simulator
- ✗ Assume success without verification
- ✗ Execute during change freezes

### Team Collaboration

**DO:**
- ✓ Use comments to document decisions
- ✓ @mention relevant team members
- ✓ Provide context in approval requests
- ✓ Share lessons learned
- ✓ Document exceptions and workarounds

**DON'T:**
- ✗ Approve without reviewing details
- ✗ Make unilateral decisions for shared assets
- ✗ Ignore approval rejection feedback
- ✗ Skip communication during incidents

### Asset Management

**DO:**
- ✓ Keep asset metadata up-to-date
- ✓ Set accurate criticality levels
- ✓ Document owner teams and contacts
- ✓ Use discovery scans regularly
- ✓ Tag assets consistently

**DON'T:**
- ✗ Leave assets without owners
- ✗ Overstate criticality (dilutes meaning)
- ✗ Ignore discovered assets
- ✗ Skip decommissioned asset cleanup

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `g d` | Go to Dashboard |
| `g v` | Go to Vulnerabilities |
| `g a` | Go to Assets |
| `g b` | Go to Bundles |
| `g o` | Go to Goals |
| `/` | Focus search |
| `c` | Create (context-sensitive) |
| `?` | Show keyboard shortcuts |
| `Esc` | Close modal |

---

## Getting Help

- **In-App Help**: Click `?` icon in top navigation
- **Documentation**: [docs.glasswatch.ai](https://docs.glasswatch.ai)
- **Support Email**: support@glasswatch.ai
- **Status Page**: [status.glasswatch.ai](https://status.glasswatch.ai)
- **Community Forum**: [community.glasswatch.ai](https://community.glasswatch.ai)

---

**Happy patching! 🎯**

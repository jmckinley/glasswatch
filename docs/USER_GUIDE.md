# Glasswatch User Guide

**Version:** Alpha · **Last updated:** April 2026 (Sprint 10 — Audit Log, API Simulators)

---

Glasswatch is a patch decision platform for security and IT operations teams. It takes vulnerability data from your scanners and converts it into a prioritized, scheduled patching plan — one grounded in business objectives rather than raw CVE counts.

This guide covers every major feature. It assumes you have access to Glasswatch and are comfortable with basic security concepts (CVEs, CVSS scores, patch management). It does not assume any developer knowledge.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Vulnerabilities](#vulnerabilities)
4. [Assets](#assets)
5. [Goals](#goals)
6. [Patch Bundles](#patch-bundles)
7. [Maintenance Windows](#maintenance-windows)
8. [Rules](#rules)
9. [AI Assistant](#ai-assistant)
10. [Notifications](#notifications)
11. [Compliance & Reporting](#compliance--reporting)
12. [Settings](#settings)
13. [Importing Data](#importing-data)
14. [Testing Integrations](#testing-integrations-simulator-mode)
15. [Audit Log](#audit-log)

---

## Getting Started

### Trying the Demo

If you're evaluating Glasswatch or just getting oriented, the fastest way in is the demo.

Go to [https://frontend-production-ef3e.up.railway.app](https://frontend-production-ef3e.up.railway.app) and click **Try Demo**. No sign-up required. You'll land in a fully functional environment loaded with synthetic assets, vulnerabilities, goals, and bundles. Every feature works — create goals, approve bundles, write rules, ask the AI assistant questions. Demo data resets periodically.

### Logging In to a Real Deployment

If your organization has deployed Glasswatch, navigate to your instance URL. You'll see options for:

- **Email and password** — works out of the box, no additional configuration needed
- **Google or GitHub OAuth** — available if your admin has configured those integrations
- **SSO (WorkOS)** — for enterprise deployments with a configured identity provider; click "Login with SSO" and enter your organization domain

### Key Concepts

Before diving into the interface, a few terms worth knowing:

**Vulnerability** — A specific CVE (or similar identifier) that affects one or more of your assets. Glasswatch ingests these from scanner webhooks or CSV imports and scores each one using 8 factors.

**Asset** — A system in your infrastructure: a server, container, database, cloud instance, or application. Assets have metadata like environment (production vs. staging), criticality, and exposure level (internet-facing vs. internal).

**Goal** — A business-level objective that drives patching. "Patch all CISA KEV vulnerabilities on production systems by June 30" is a goal. Glasswatch uses goals to automatically generate a patching plan.

**Bundle** — A group of patches scheduled for deployment in a single maintenance window. Bundles are the output of the goal optimizer. They move through a lifecycle: Draft → Pending Approval → Approved → In Progress → Completed.

**Rule** — A governance policy that controls when and how patches can be deployed. "No deployments in production on Fridays after 3pm" is a rule. You write these in plain English.

**Maintenance Window** — An approved time slot for running patches. Bundles are scheduled to run within windows.

---

## Dashboard

The dashboard is your starting point. It surfaces the information that matters most — where your biggest risks are, what's in flight, and what needs your attention today.

### Focus Mode and Full Mode

The dashboard has two display modes. **Focus Mode** strips away lower-priority information and shows only what requires action: critical unpatched vulnerabilities, bundles awaiting approval, and overdue SLA items. It's useful for a quick morning check.

**Full Mode** shows the complete picture: all vulnerability counts by severity, asset health across environments, goal progress, and recent bundle activity. Toggle between modes using the view selector at the top right.

### Reading the Panels

**Vulnerability Overview** shows your total vulnerability count broken down by severity (Critical, High, Medium, Low). It also calls out how many are in the CISA Known Exploited Vulnerabilities (KEV) catalog — these are confirmed exploits in the wild and should be treated as the highest priority regardless of CVSS score.

**Asset Health** shows your asset inventory by environment. The risk score distribution tells you how many assets have elevated risk — not just because of the number of vulnerabilities they carry, but weighted by severity and business criticality.

**Patch Bundles** summarizes what's in motion: bundles pending approval, scheduled for upcoming windows, currently in progress, and completed in the last 30 days.

**Active Goals** shows progress toward your current goals — percentage complete, days until the target date, and projected risk reduction.

### The Risk Score

The tenant-wide risk score is the number at the top of the dashboard. It's a 0–100 aggregate that reflects the severity and breadth of your unpatched vulnerability exposure. As you complete bundles, the score goes down. Tracking it over time tells you whether your patching program is making real progress.

### "Patch These Now"

This button appears on the dashboard when Glasswatch has identified a short list of vulnerabilities that combine high risk scores with available patches and no active bundle assignment. Clicking it creates a draft bundle with those items pre-populated, ready for your review.

---

## Vulnerabilities

### Viewing the Vulnerability List

Navigate to **Vulnerabilities** in the sidebar. By default you'll see all open vulnerabilities sorted by risk score, highest first. The list shows the CVE ID, a short description, the number of affected assets, severity, whether it's KEV-listed, and the risk score.

Use the filters at the top to narrow the list:

- **KEV only** — shows only CISA Known Exploited Vulnerabilities. These have confirmed active exploitation and should be your first priority in almost every case.
- **Critical** — shows only Critical severity (CVSS 9.0+).
- **By asset** — filter to vulnerabilities affecting a specific asset or asset group.
- **Patch available** — useful when you're building a bundle; you can filter to only vulnerabilities where a vendor patch exists.

Search the list by CVE ID or keyword to find a specific vulnerability quickly.

### Understanding the Risk Score

Glasswatch scores every vulnerability on a 0–100 scale using 8 factors. This goes well beyond CVSS, which only captures the severity of the vulnerability in isolation. The 8 factors are:

**CVSS Score (40%)** — The base severity rating from the National Vulnerability Database. High CVSS still matters.

**EPSS Score (20%)** — The Exploit Prediction Scoring System, published by FIRST.org. This is a probability (0–100%) that the vulnerability will be exploited in the next 30 days based on actual threat intelligence. A high EPSS score means the attacker community has noticed this one.

**KEV Listing (+15 points)** — If CISA has added the vulnerability to its Known Exploited Vulnerabilities catalog, it's confirmed active exploitation. This adds a flat 15 points regardless of other factors.

**Exploit Available (+10 points)** — Public proof-of-concept or working exploit code exists in the wild. Not as severe as confirmed exploitation, but meaningfully more dangerous than a theoretical vulnerability.

**Asset Criticality (15%)** — How important is the affected asset to your business? Criticality is set per asset (1–5 scale). A CVSS 7.0 vulnerability on your payment API (criticality 5) is more urgent than the same vulnerability on a dev server (criticality 2).

**Asset Exposure (10%)** — Internet-facing assets score higher than internal systems, which score higher than isolated ones. An internet-facing asset is one click away from an attacker.

**Patch Availability (5%)** — Whether a vendor patch exists. Unpatched CVEs score slightly lower because there's nothing you can do yet — but only slightly.

**Snapper Runtime Data (±25 points)** — If your deployment includes Snapper, runtime reachability data is factored in. If the vulnerable code path is actively executing, the score increases by 25 points. If it's never called, it decreases by 25. This is the most powerful differentiator: a CVSS 9.8 vulnerability in a library you use but never invoke is genuinely lower priority than a CVSS 7.0 in code that runs thousands of times per hour.

Example: CVE-2024-1234 in Apache Commons, CVSS 9.8. Without Snapper, it scores 78. With Snapper confirming the code never runs, it drops to 53 — still medium priority, but no longer a fire drill.

### CVE Detail Page

Click any vulnerability to open its detail view. This shows:

- Full technical description and impact analysis
- CVSS vector breakdown (attack complexity, privileges required, etc.)
- EPSS score and historical trend
- KEV status with the CISA advisory link
- All assets affected, with per-asset risk scores
- Patch information: vendor advisory, patch release date, fix version
- Exploit details: maturity level, proof-of-concept availability
- Snapper runtime data per asset (if configured)
- SLA deadline: based on your organization's SLA settings, when this should be resolved

### SLA Deadlines

Glasswatch tracks SLA compliance for every open vulnerability. The default SLAs follow industry-standard timelines (Critical: 15 days, High: 30 days, Medium: 60 days) but your admin can configure custom targets in Settings. Vulnerabilities approaching or past their SLA deadline are flagged in the list and on the compliance dashboard.

---

## Assets

### Asset List Overview

Navigate to **Assets** to see your full inventory. Each asset shows its name, type, environment, criticality, exposure level, and current risk score. The risk score for an asset is derived from the vulnerabilities affecting it.

Filter by environment (Production, Staging, Development), criticality level, exposure, asset type, or owner team. Use search to find a specific host by name or IP.

### Asset Detail Page

Click an asset to see everything about it:

**Risk Breakdown** — A visual breakdown of the asset's overall risk, showing which vulnerabilities are driving it. The top-contributing vulnerabilities are listed with their individual scores.

**Vulnerability List** — All open vulnerabilities affecting this asset, sorted by risk score. You can filter this list by severity, KEV status, or patch availability. Each row shows the CVE, risk score, SLA status, and whether it's already assigned to a bundle.

**Patch History** — A log of every patch that has been applied to this asset through Glasswatch, including when it ran, who approved it, and whether it succeeded.

**"Patch This Asset"** — Creates a new draft bundle containing all unpatched vulnerabilities for this asset. Good for targeted remediation when an asset is high-risk and you want to address it immediately outside the normal goal cycle.

### Asset Groups

Asset groups let you organize assets by environment, team, or criticality tier. Groups are useful for scoping goals ("patch all internet-facing production assets") and for reporting ("show compliance posture for the payments team").

To create a group, go to Assets → Groups → New Group. Define the name and add assets individually or use a filter rule (e.g., "all assets with environment=production and criticality ≥ 4").

### Patch Coverage View

The patch coverage view shows a matrix of CVEs versus assets, letting you see at a glance which vulnerabilities affect which systems and where coverage gaps exist. This is particularly useful for compliance work — for example, verifying that a specific KEV CVE has been patched across all internet-facing hosts.

### Stale Asset Detection

If an asset has not received new scan data in more than 30 days, Glasswatch flags it as stale. A stale asset might mean your scanner isn't reaching it, it's been decommissioned without being removed, or there's a gap in your coverage. Stale assets appear with a warning indicator in the asset list.

---

## Goals

### What Goals Are

Goals are the reason Glasswatch exists. Instead of working through a CVE queue manually, you define an outcome — what you want to achieve and by when — and Glasswatch builds the patching plan to get there.

A goal might be: "Eliminate all KEV vulnerabilities on internet-facing production systems by June 15." Or: "Reduce our overall risk score by 40% before the SOC 2 audit." Or simply: "Zero critical vulnerabilities on the payments infrastructure by end of quarter."

Goals are not just tracking tools. When you create a goal and run the optimizer, Glasswatch generates the actual patch bundles, scheduled across your maintenance windows, that will achieve the goal. The plan is concrete and executable, not aspirational.

### Creating a Goal

Navigate to **Goals** and click **New Goal**. Fill in:

**Name** — Something descriptive that will make sense to your team. "Q2 KEV Elimination" or "Glasswing Compliance Sprint" are better than "Goal 1."

**Target Date** — The deadline. Be realistic — the optimizer will tell you if the goal can't be achieved in time given your maintenance window capacity.

**Risk Threshold** — The minimum acceptable risk score for vulnerabilities in scope. For example, setting this to 50 means the goal will only include vulnerabilities scoring 50 or above. Lower thresholds create more work but achieve more complete remediation.

**CVE Filter** — Optionally restrict the goal to specific CVE types: KEV-listed only, critical severity only, a specific asset group, or vulnerabilities matching a custom filter.

**Risk Tolerance** — Conservative, Balanced, or Aggressive. This controls how many patches get scheduled per maintenance window and how much downtime is acceptable. Use Conservative for production systems, Aggressive for dev and staging.

Click **Create and Optimize** to generate the bundle schedule immediately, or **Create** to save the goal and optimize later.

### Goal Progress Tracking

The goal detail page shows:

- Overall progress as a percentage of vulnerabilities resolved
- A timeline comparing projected completion vs. your target date
- Bundles generated: how many are complete, in progress, pending, or draft
- Risk reduction achieved so far

If the goal is falling behind — bundles are delayed, windows are missed — the optimizer can be re-run to rebalance the remaining work across available windows.

### How Goals Generate Bundles

When you run the optimizer, Glasswatch:

1. Identifies all vulnerabilities and assets in scope based on your goal's filters
2. Ranks them by risk score, highest first
3. Distributes them across your available maintenance windows, respecting window capacity constraints (max patches per window, max downtime)
4. Evaluates all active rules to ensure no governance policies are violated
5. Groups related patches where possible to reduce total deployment events
6. Outputs a set of bundles, each scheduled to a specific maintenance window

The optimizer uses Google OR-Tools, a constraint solver. If OR-Tools can't find an optimal solution within the time limit (which can happen with very large datasets), it falls back to a fast heuristic. You'll see a note in the optimization results if this happens — the plan is still good, just not provably optimal. This is expected behavior.

---

## Patch Bundles

### What Bundles Are

A bundle is a scheduled unit of patch deployment. It contains a list of vulnerability-asset pairs (e.g., "patch CVE-2024-1234 on prod-web-01") assigned to a specific maintenance window. Think of it as a change ticket with a concrete scope, schedule, and approval chain.

Bundles are typically generated by the goal optimizer, but you can also create them manually for urgent or one-off situations.

### Bundle Lifecycle

A bundle moves through these states:

**Draft** — Created but not yet submitted for approval. You can freely edit the scope, add or remove items, and adjust the scheduled window.

**Pending Approval** — Submitted to approvers. The bundle is locked for editing until it's approved or rejected.

**Approved** — Cleared for execution. The bundle will run during its scheduled maintenance window.

**In Progress** — Execution is underway. Patch items are being applied to assets in sequence.

**Completed** — All patch items ran successfully. The bundle is closed and its items are marked resolved.

**Failed** — One or more patch items failed during execution, or the bundle was rolled back. The detail page will show which items failed and why.

If a bundle is rejected or needs to be abandoned, it can be cancelled from Draft or Pending Approval states.

### Bundle Detail Page

Click a bundle to see its full view. The detail page has several sections:

**Timeline Stepper** — A visual progress indicator showing where the bundle is in its lifecycle. Each stage shows who performed the action and when.

**Pre-Flight Checklist** — Automatically populated before execution. Checks include: maintenance window is open, no change freeze is active, required packages are available, disk space is sufficient, and all bundle items are still valid (the vulnerabilities haven't already been patched).

**Patch Items** — The list of specific patches to apply: CVE, affected asset, estimated downtime, and current status. Each item shows the patch command or procedure that will be run.

**Execution Log** — Available once the bundle is in progress or completed. Shows the real-time (or historical) output of each patch operation, with timestamps and success/failure status for each item.

### Approving a Bundle

If you have approver permissions, bundles in Pending Approval state will appear in your queue. Open the bundle, review the scope and impact, and click **Approve** or **Reject**.

When approving, you're confirming that:
- The scope is correct
- The scheduled window is appropriate
- Rollback procedures are in place
- No business events conflict with the timing

When rejecting, you must provide a reason. The requester will be notified with your feedback.

### Executing a Bundle

Once a bundle is Approved, it will execute automatically when its scheduled maintenance window opens — provided automated execution is configured. If manual execution is required, you'll see an **Execute** button in the bundle detail page. Click it to start the run.

During execution, the execution log updates in real time. You can monitor progress without refreshing.

### Rolling Back

If something goes wrong during or after execution, navigate to the bundle and click **Roll Back**. Glasswatch will attempt to revert the changes applied by this bundle. The bundle status will change to Failed, and a rollback entry will be added to the execution log. The affected vulnerabilities will be re-opened and re-queued for future scheduling.

### Edit/Tweak Mode

Approved bundles are normally locked to prevent scope changes after sign-off. However, if you need to make minor adjustments (removing a single asset that just went into a freeze, for example), you can enter **Edit/Tweak Mode** from the bundle detail page.

Important: entering Edit/Tweak Mode resets the bundle to Draft status and clears the approval. You will need to go through the approval process again. This is by design — changes to an approved bundle must be re-reviewed.

---

## Maintenance Windows

### What Maintenance Windows Do

Maintenance windows tell Glasswatch when it's acceptable to apply patches to your systems. The optimizer will only schedule bundles inside valid windows. Windows prevent patches from being scheduled at inappropriate times — during business hours, major product launches, or regulatory blackout periods.

### Creating a Window

Navigate to **Settings → Maintenance Windows** and click **New Window**. Configure:

- **Name** — e.g., "Production Saturday nights" or "Dev weekday evenings"
- **Day and Time** — Day of week and start time
- **Duration** — How many hours the window lasts
- **Environment** — Which environments this window applies to (Production, Staging, Development, or All)
- **Recurrence** — One-time or recurring (weekly, biweekly, monthly)

Once created, the window will appear in the optimizer's scheduling constraints. Bundles scoped to matching environments will be assigned to available windows.

You can also blackout specific dates — useful for holidays, company events, or audit periods when you don't want any changes running.

---

## Rules

### What Rules Are

Rules are governance policies that Glasswatch evaluates at deployment time. They can block a bundle from running, require additional approvals, send notifications, or constrain scheduling.

Rules are how your change management policy gets encoded into Glasswatch. Instead of relying on people to remember "we don't deploy on Fridays," you write the rule once and it's enforced automatically.

### Creating Rules via NLP

Navigate to **Rules** and click **New Rule**. Type your rule in plain English in the text box. Glasswatch (using Claude if an API key is configured, or pattern matching otherwise) parses it and generates a structured rule. You'll see a preview of what was understood before saving.

Examples of rules you can write:

- "Block all deployments in production on Fridays after 3pm"
- "Require two approvals for any bundle affecting internet-facing assets"
- "Notify the security team when a bundle is scheduled that includes KEV vulnerabilities"
- "Block deployments in the last three days of any quarter"
- "Warn if a single bundle contains more than 50 patch items"

After the rule is created, review the parsed version and click **Save** to activate it.

### Rule Types

**Block** — Prevents bundle execution. The bundle cannot proceed until the condition is resolved (e.g., change the scheduled time to a permitted window).

**Require** — Adds a mandatory gate. For example, "require CISO approval for critical production bundles" adds a specific approver requirement to matching bundles.

**Notify** — Sends an alert when the rule condition is met, but does not block. Useful for visibility without friction.

**Schedule** — Automatically constrains when bundles matching the rule can be scheduled. Similar to maintenance windows but expressed as a policy.

---

## AI Assistant

### Opening the Assistant

The AI assistant is available from any page in Glasswatch. Click the sparkle icon (✨) in the bottom-right corner to open it. It's a floating chat interface connected to your live data.

### What It Can Do

The assistant is most useful for things that would otherwise require navigating to several different pages. Some examples of what you can ask:

**Situation awareness:**
- "What needs my attention right now?" — Returns your highest-priority items: critical KEV vulnerabilities without a bundle, bundles awaiting your approval, and goals at risk of missing their deadline.
- "How many KEV vulnerabilities do we have open?" — Queries live data and returns the count with a breakdown.

**Looking things up:**
- "What is the risk score for CVE-2021-44228?" — Fetches the scoring details and explains why it scored that way.
- "Which assets are affected by critical vulnerabilities with no patch available?" — Runs a live query and lists results.

**Taking action:**
- "Create a rule blocking deployments on the last Friday of every month in production" — Creates the rule directly, then shows you a preview to confirm.
- "Approve bundle #42" — Triggers the approval action if you have the required permissions.
- "Show me all bundles pending approval" — Lists them with links.

### Prompts to Try

If you're not sure where to start, these tend to be useful:

- "What's the status of our Q2 compliance goal?"
- "Which goal is furthest behind schedule?"
- "What are the top 5 vulnerabilities I should address today?"
- "Create a new goal: patch all KEV vulnerabilities on internet-facing assets by June 30"
- "Show me the riskiest assets in production"

The assistant uses your actual data, not synthetic examples. If the answer depends on something Glasswatch doesn't have (like scanner data that hasn't been ingested), it will say so.

---

## Notifications

### The Notification Bell

The bell icon in the top navigation shows real-time alerts. Glasswatch polls for new events every 30 seconds and updates the count badge automatically. Click the bell to see the full notification list.

### Alert Types

**KEV Alerts** — Triggered when CISA adds a new CVE to the Known Exploited Vulnerabilities catalog that affects one or more of your assets. These are high-signal, high-urgency — a KEV addition means active exploitation has been confirmed.

**Bundle Events** — Status changes on your bundles: approval requested, approved, rejected, execution started, execution completed, execution failed.

**SLA Warnings** — When a vulnerability's SLA deadline is approaching (configurable: 7 days, 3 days, day-of) or has been breached, you'll receive an alert.

**Goal Milestones** — When a goal reaches 25%, 50%, 75%, or 100% completion, or when a goal is at risk of missing its target date.

### Configuring Alert Rules

Navigate to **Settings → Alert Rules** to configure which events trigger notifications and where they're delivered.

Each rule has:
- **Trigger** — The event type (KEV alert, bundle status change, SLA warning, etc.)
- **Filter** — Conditions that must be true for the alert to fire (e.g., only for production assets, only for Critical severity)
- **Channels** — Where to send the alert: In-App, Slack, Microsoft Teams, or Email

You can create multiple rules with different filters and channels. For example: send all KEV alerts to Slack immediately, send weekly SLA summaries by email, and send bundle approvals in-app only.

### Delivery Channels

**In-App** — The notification bell. Always available, no configuration needed.

**Slack** — Requires a Slack webhook URL configured in Settings → Integrations. Notifications are sent as formatted messages to the configured channel.

**Microsoft Teams** — Requires a Teams incoming webhook URL. Format and setup are similar to Slack.

**Email** — Requires Resend API configuration (Settings → Integrations). Alerts are sent from your configured sender address.

---

## Compliance & Reporting

### Compliance Dashboard

Navigate to **Compliance** to see your posture against common frameworks. The dashboard shows cards for:

- **BOD 22-01** — CISA's Binding Operational Directive requiring federal agencies to patch KEV vulnerabilities within defined timelines. Even if you're not a federal agency, this is a useful benchmark: KEV with patch = patch it fast.
- **SOC 2** — Tracks your patch SLA adherence, which is a supporting control for SOC 2 CC7.1 (vulnerability and patch management).
- **PCI DSS** — Tracks patching of systems in scope for PCI, with attention to the required monthly scanning and timely critical patch requirements.

Each card shows current pass/fail status, the number of items in or out of compliance, and a trend line.

### MTTP Metrics

Mean Time to Patch (MTTP) is the core metric for patch program effectiveness. The reporting view shows MTTP:

- By severity (Critical, High, Medium, Low)
- By environment (Production, Staging, Dev)
- By team (based on asset owner_team)
- Trend over time

Drilling into any metric shows the individual vulnerability-asset pairs contributing to it.

### SLA Tracking Table

The SLA table lists all open vulnerabilities with their SLA deadlines, current status (on track, at risk, breached), and the assigned bundle (if any). Filter by status to quickly find breached items.

### Exporting a PDF Report

From the Compliance page, click **Export Report**. Choose a date range and which sections to include (executive summary, compliance posture, MTTP metrics, SLA status, detailed vulnerability list). The report generates in your browser and downloads as a PDF. Reports are formatted for presentation to leadership or auditors.

### SIEM and CMDB Integration

Glasswatch exposes export endpoints for feeding data into your SIEM or CMDB:

```
GET /api/v1/export/vulnerabilities
GET /api/v1/export/assets
```

Both endpoints support `?format=json` (default) and `?format=csv`. Add filters via query parameters: `?severity=critical`, `?environment=production`, `?kev_only=true`.

Authenticate with an API key (generate one in Settings → API Keys). These endpoints are designed to be called by scheduled scripts or your SIEM's connector.

---

## Audit Log

The Audit Log is a complete, tamper-evident record of every action taken in your Glasswatch workspace. It is available to admin users and is designed to support compliance reviews, security investigations, and accountability requirements.

### What is recorded

Every meaningful action generates an audit event:

| Category | Examples |
|---|---|
| Bundle actions | Created, approved, status changed, executed |
| Vulnerability data | CSV imported (with count), webhook ingestion |
| User actions | Login, login failed, invited, invite accepted |
| Maintenance windows | Created, deleted |
| Goals | Created, updated |
| System events | Configuration changes, integration events |

Each entry records: timestamp, user (or "System" for automated events), action type, the resource affected (type + name), full context details, client IP address, and whether the action succeeded or failed.

### Navigating the Audit Log

Go to **Audit Log** in the sidebar (below Settings). The page shows the most recent events first, 50 per page.

**Filters available:**
- **Action Type** — narrow to a specific event class (e.g. "bundle.approved" or "user.invited")
- **Resource Type** — show only bundle events, or only user events, etc.
- **Date From / Date To** — restrict to a time window

Apply active filters using the Apply button. Each active filter appears as a pill below the filter bar — click the × on a pill to remove it individually, or "Clear all" to reset.

**Reading the table:**

- **Timestamp** — relative time ("2 min ago") with the full ISO datetime visible on hover
- **User** — colored avatar with initials for user actions; a "SYS" badge for system/automated events
- **Action** — color-coded badge indicating the category:
  - 📦 Indigo — bundle events
  - 🛡️ Amber — vulnerability events
  - 👤 Emerald — user events
  - 🗓️ Blue — maintenance window events
  - 🎯 Purple — goal events
  - ⚙️ Gray — system events
- **Resource** — the type and name of the affected object (e.g. "Bundle: KEV Emergency Response")
- **Status** — ✓ green for success, ✗ red for failure (e.g. failed login attempt)

**Expanding a row:** Click any row to expand it and see the full structured details. Fields vary by event type — for example, a `bundle.status_changed` event shows the old and new status; a `vulnerability.imported` event shows the count of CVEs imported.

### Exporting for auditors

Click **Export CSV** (top-right of the page) to download a CSV file containing all audit events matching the current filters. The CSV includes all columns including the full details JSON serialized as a string.

This export is suitable for:
- SOC 2 audit evidence packages
- PCI DSS compliance reviews
- Internal security investigations
- Legal/eDiscovery requests

### Failed login attempts

Failed logins appear with a ✗ red status and the action `user.login_failed`. The IP address column shows where the attempt originated. This is useful for detecting brute-force attempts or compromised credentials.

### Retention

Audit log entries are retained indefinitely and are never automatically deleted. Entries cannot be modified after creation.

---

## Settings

### Integrations

**Settings → Integrations** is where you connect Glasswatch to your scanner infrastructure and notification services.

For each scanner (Tenable, Qualys, Rapid7), you'll configure a webhook secret. Glasswatch then provides you with a webhook URL to paste into your scanner's notification settings. Once configured, the scanner will POST new findings to Glasswatch in real time as scans complete.

For Slack and Teams, paste in the incoming webhook URL from your messaging platform. Glasswatch will use it to deliver alerts.

For email, enter your Resend API key. Glasswatch uses Resend for reliable transactional delivery.

### Alert Rules

Described in the [Notifications](#notifications) section above. This is where you configure which events trigger alerts and where they go.

### Connections

**Settings → Connections** shows the health status of each configured integration. A green indicator means the last test was successful. A red indicator means something needs attention — click it to see the error details and troubleshooting suggestions.

Use the **Test** button on each connection to send a test payload and confirm the integration is working end-to-end.

---

## Importing Data

### CSV Import

If you don't have a scanner configured yet, or if you're migrating from another tool, you can import vulnerability and asset data via CSV.

Navigate to **Import** in the sidebar. Select the data type (Vulnerabilities or Assets) and download the template CSV to see the expected format.

**Vulnerability CSV columns:**

| Column | Required | Description |
|--------|----------|-------------|
| `asset_name` | Yes | Name of the affected asset (must match an existing asset) |
| `cve_id` | Yes | CVE identifier, e.g. `CVE-2024-1234` |
| `severity` | Yes | `critical`, `high`, `medium`, or `low` |
| `cvss_score` | Yes | CVSS base score (0.0–10.0) |
| `discovered_date` | Yes | ISO 8601 date, e.g. `2024-03-15` |
| `description` | No | Short description of the vulnerability |
| `patch_available` | No | `true` or `false` |

**Asset CSV columns:**

| Column | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Asset name |
| `type` | Yes | `server`, `container`, `database`, `cloud_instance`, or `application` |
| `environment` | Yes | `production`, `staging`, or `development` |
| `ip_address` | No | Primary IP address |
| `owner_team` | No | Team responsible for this asset |
| `criticality` | No | Integer 1–5 (default: 3) |

### What Happens After Import

After you upload a CSV, Glasswatch shows a summary: rows created, rows updated (if the identifier already exists), and any validation errors. Errors are listed with row numbers and descriptions so you can fix and re-upload.

Imported vulnerabilities are immediately scored using the same 8-factor algorithm as scanner-ingested data. They'll appear in the vulnerability list and contribute to asset risk scores within a few seconds of import completing.

---

## Testing Integrations (Simulator Mode)

Glasswatch ships with a built-in simulator server that mimics all 11 external APIs — Tenable, Qualys, Rapid7, Slack, Teams, Jira, ServiceNow, Resend, CISA KEV, NVD, and EPSS — with exact auth validation and realistic vulnerability data.

This lets you test the full integration flow without real credentials.

### Starting the simulator

```bash
uvicorn backend.simulators.external_apis:app --port 8099
```

### Enabling simulator mode

Set the environment variable before starting Glasswatch backend:

```bash
SIMULATOR_MODE=true uvicorn backend.main:app --port 8000
```

When `SIMULATOR_MODE=true`, all scanner health checks and integration calls route to `localhost:8099` instead of the real vendor APIs.

### What the simulator provides

- **10 real CVEs** (CVE-2024-21887, CVE-2024-3400, CVE-2024-1709, etc.) spread across 5 named assets
- **Exact auth validation** — pass the wrong Tenable `X-ApiKeys` format and you get a real 401
- **Tenable export state machine** — POST export → PROCESSING → FINISHED → chunk download, just like production
- **Qualys XML responses** — proper `Content-Type: application/xml` with `VULN_LIST` structure
- **Rapid7 HAL pagination** — `resources` + `page` + `links` structure
- **Error simulation** — append `?simulate_error=true` to any endpoint to get a random 429, 500, or 503

### Running the test suite against simulators

```bash
python3 backend/simulators/test_simulators.py
```

Prints PASS/FAIL for every simulated endpoint. All 11 systems should pass.

See `docs/SIMULATORS.md` for full developer reference.

---

*For deployment and integration setup, see the [Implementation Guide](IMPLEMENTATION_GUIDE.md). For API reference, see the [interactive API docs](https://glasswatch-production.up.railway.app/docs).*

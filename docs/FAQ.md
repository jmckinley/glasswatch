# Glasswatch — FAQ

---

**Q: What is Glasswatch?**

Glasswatch is an AI-driven patch management platform for enterprise security teams. It converts vulnerability data from scanners into organized, prioritized patch plans — with the goal being outcomes ("patch all KEV vulns by July 1") rather than just lists of CVEs. It handles scoring, scheduling, approval workflows, and deployment tracking in one place.

---

**Q: How is this different from Qualys or Tenable?**

Qualys and Tenable are scanners — they find and report vulnerabilities. Glasswatch is what comes after: it takes scanner output and helps you decide what to patch, when, and in what order. It integrates directly with Tenable, Qualys, and Rapid7 via webhooks. Think of it as the decision and execution layer that scanners lack.

---

**Q: What scanners does Glasswatch integrate with?**

Glasswatch accepts inbound webhooks from:
- Tenable (Nessus/Tenable.io)
- Qualys
- Rapid7 InsightVM

You can also import vulnerabilities manually or via the bulk import API. Support for additional scanners is planned.

---

**Q: How does AI scoring work?**

Each vulnerability is scored using 8 factors:

1. **CVSS score** — Base severity
2. **EPSS score** — Probability of exploitation in the next 30 days
3. **KEV listing** — Is it in CISA's Known Exploited Vulnerabilities catalog?
4. **Asset exposure** — Internet-facing assets score higher
5. **Asset criticality** — Business-defined criticality tier
6. **Patch age** — How long since a patch was available
7. **Exploit availability** — Public PoC or active exploitation?
8. **Runtime data (Snapper)** — Is the vulnerable code actually reachable at runtime?

The final risk score drives prioritization across all dashboards and the optimizer.

---

**Q: What is a bundle?**

A bundle is a group of patches scheduled for deployment in a single maintenance window. Bundles are the output of the optimization engine — when you create a goal ("patch all critical KEV vulns by July 1"), Glasswatch generates one or more bundles with the right patches, scheduled in your approved maintenance windows. Bundles go through a draft → approved → in_progress → completed lifecycle.

---

**Q: What is a maintenance window?**

A maintenance window is an approved time slot for applying patches to production systems. It has a start and end time, an optional environment scope (e.g., "production only"), and capacity constraints (max assets, max risk score). Bundles are scheduled within windows.

---

**Q: How do NLP rules work?**

You write deployment rules in plain English — for example:

- "Block all deployments on Fridays after 3pm"
- "Require approval for production changes in the last 3 days of the month"
- "Warn if more than 50 patches are in a single bundle"

Glasswatch parses the text using Claude (if an API key is configured) or falls back to pattern matching. Rules evaluate at deployment time and can allow, warn, or block.

---

**Q: Can I self-host Glasswatch?**

Yes. The backend is a standard FastAPI app with a PostgreSQL database. A `docker-compose.yml` is included for local development. For production, any host that supports Docker containers works. See [docs/ARCHITECTURE.md](ARCHITECTURE.md) for environment variables and setup.

---

**Q: What data does Glasswatch store?**

Glasswatch stores:
- Vulnerability metadata (CVE IDs, CVSS scores, descriptions, KEV status)
- Asset inventory (hostnames, IPs, OS, exposure, criticality)
- Patch history (what was applied, when, by whom)
- Goal definitions and progress
- Bundle schedules and approvals
- Deployment rules
- Audit logs (who did what and when)

Glasswatch does not store vulnerability scan credentials, raw scan files, or source code.

---

**Q: How does the demo work?**

The demo runs against a shared demo tenant pre-populated with synthetic assets, vulnerabilities, and goals. No signup required — click "Try Demo" on the login page. All actions (creating goals, approving bundles, editing rules) work in demo mode. Demo data resets periodically.

---

**Q: What does "SOC 2 readiness" mean?**

Glasswatch is designed with SOC 2 requirements in mind:
- Immutable audit logs for every action (who, what, when)
- Role-based access control (admin, analyst, viewer)
- JWT authentication with short-lived tokens
- TLS-only communication
- Tenant isolation (data is scoped per organization)

Glasswatch is not itself SOC 2 certified (yet), but using it supports your own SOC 2 audit by maintaining a verifiable patch history.

---

**Q: How does the goal optimizer work?**

When you create a goal (e.g., "eliminate all KEV vulns on internet-facing assets by July 1"), Glasswatch:
1. Identifies all vulnerabilities and assets in scope
2. Calculates the optimal patching order by risk score
3. Distributes patches across your available maintenance windows
4. Generates bundles respecting constraints (max patches per window, blackout periods, rules)
5. Shows a projected timeline and risk reduction curve

You can adjust constraints and re-optimize as many times as needed.

---

**Q: What approval workflows does Glasswatch support?**

Bundles go through a configurable approval chain before deployment. You can require:
- Single approver (any authorized user)
- Specific role approval (must be an admin)
- Multi-stage (analyst approval → admin sign-off)
- Automatic approval for low-risk bundles below a threshold

Approval actions are logged to the audit trail.

---

**Q: How does Glasswatch integrate with Jira/ServiceNow?**

Glasswatch can create Jira tickets or ServiceNow change requests when a bundle is approved for deployment. Inbound webhooks from Jira can update bundle status when tickets are resolved. Configure credentials in Settings → Connections.

---

**Q: What is the AI assistant?**

The AI assistant (bottom-right floating button) accepts plain English questions and commands:
- "What needs my attention right now?" → pulls live KEV + overdue bundle data
- "Create a rule blocking Friday deployments" → creates the rule directly
- "What is the risk score for CVE-2021-44228?" → looks it up and explains it
- "Show me pending approvals" → lists bundles awaiting approval

It uses your live data — not hardcoded examples.

---

**Q: Does Glasswatch support multi-tenancy?**

Yes. Every object (assets, vulnerabilities, goals, bundles, rules) is scoped to a tenant. Tenants are completely isolated at the database level. Each tenant can have multiple users with different roles.

---

**Q: What are the system requirements?**

Backend: Python 3.11+, PostgreSQL 14+, 512MB RAM minimum (2GB recommended for production).
Frontend: Node.js 18+, any modern browser.
No special hardware required. Runs fine on a small VM or Railway free tier for evaluation.

---

**Q: How are vulnerability scores kept up to date?**

The scoring engine recalculates scores when:
- New scanner data arrives via webhook
- EPSS scores are refreshed (daily feed)
- KEV catalog is updated (CISA publishes updates periodically)
- Asset metadata changes (exposure or criticality update)
- Snapper runtime data refreshes

Manual rescore is available from the vulnerability detail page.

---

**Q: What's new in Sprint 10?**

Sprint 10 delivered:
- **Audit Log** — every action in Glasswatch is now recorded with full details (user, resource, IP, timestamp). Accessible via sidebar nav and exportable to CSV for compliance.
- **External API Simulators** — 11 simulated systems (Tenable, Qualys, Rapid7, and more) that let you test integrations without real credentials. Enable with `SIMULATOR_MODE=true`.
- **UX overhaul** — improved navigation, sidebar audit log access, and refined data tables across all major views.
- **516 automated tests** — 479 backend + 37 frontend, covering audit log hooks, simulator endpoints, and all existing features.

---

**Q: How does the audit log work?**

Every action taken in Glasswatch — creating a goal, approving a bundle, changing a user's role, editing a rule — is written to an immutable audit log entry. Each entry records: who did it (user + IP address), what they did (action + resource), when it happened, and whether it succeeded. Access the audit log via **Audit Log** in the sidebar. You can filter by user, action type, resource type, or date range, and export to CSV for compliance reporting. Audit log data is scoped per tenant.

---

**Q: Can I test integrations without real scanner credentials?**

Yes. Set `SIMULATOR_MODE=true` in your environment and Glasswatch will start the External API Simulators on port 8099. The simulators mimic the real Tenable, Qualys, and Rapid7 webhook APIs and can push synthetic scan payloads into Glasswatch without any external accounts or credentials. This is designed for development and integration testing. See [docs/SIMULATORS.md](SIMULATORS.md) for the full list of simulated systems and usage.

---

**Q: What authentication methods are supported?**

Glasswatch supports:
- **Email/password** — standard login with a Glasswatch account
- **Demo login** — one-click access to a shared demo tenant (no credentials needed; available when WorkOS is not configured)
- **Google OAuth** — built in, requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars to activate
- **GitHub OAuth** — built in, requires `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` env vars to activate
- **WorkOS SSO** — enterprise SAML/OIDC via WorkOS; requires `WORKOS_API_KEY` and `WORKOS_CLIENT_ID` env vars; activates automatically when set

Demo login is disabled when WorkOS is configured.

---

**Q: How many automated tests does Glasswatch have?**

516 total: 479 backend (Python/pytest) and 37 frontend (React Testing Library). Backend tests cover unit tests for scoring, approval, simulation, audit, and integration tests for all API endpoints. Frontend tests cover key UI flows including login, vulnerability list, bundle workflow, and the audit log view.

---

**Q: What's on the roadmap?**

Near-term priorities:
- Async worker queue for large-scale scoring jobs
- Additional scanner integrations (Wiz, Crowdstrike, Lacework)
- Reporting and executive dashboards
- Mobile-responsive UI improvements
- Read-only API scopes for CI/CD integrations

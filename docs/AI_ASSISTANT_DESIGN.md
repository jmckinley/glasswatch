# Glasswatch AI Assistant Design

## Core Concept
An AI assistant that makes vulnerability management accessible to non-security experts while providing power features for professionals.

## Key Personas

### 1. The CISO
**Needs**: High-level risk visibility, compliance status, board-ready reports
**AI Helps**: 
- "What's our security posture this month?"
- "Generate executive summary for the board"
- "Are we on track for SOC 2 audit?"

### 2. The Security Engineer  
**Needs**: Detailed vulnerability data, patch coordination, technical deep-dives
**AI Helps**:
- "Show me all OpenSSL vulnerabilities in production"
- "Why is CVE-2024-1234 scored so high?"
- "Create a zero-downtime patch plan for web servers"

### 3. The IT Operations Manager
**Needs**: Maintenance scheduling, change management, resource planning
**AI Helps**:
- "What's in Tuesday's maintenance window?"
- "Can we defer these patches to next month?"
- "How many engineer-hours for this quarter's patches?"

## Conversation Examples

### Example 1: Onboarding
```
AI: Welcome to Glasswatch! I'll help you get started. First, let's connect your infrastructure. What are you using?

User: We have AWS and ServiceNow

AI: Great! I'll guide you through connecting both. For AWS, I'll need read-only access to EC2, ECS, and Lambda. [Connect AWS →]

[After connection]

AI: Perfect! I found 847 assets across 3 regions. Now, what's your biggest concern right now?

User: The Glasswing disclosure in July

AI: Understood. I'll create a goal to make you Glasswing-ready by July 1st. Based on your infrastructure, here's what I recommend:
- Conservative approach: 6 maintenance windows, minimal risk
- Balanced approach: 4 maintenance windows, moderate risk  
- Aggressive approach: 2 maintenance windows, higher risk

Which fits your risk tolerance?
```

### Example 2: Daily Operations
```
User: What needs my attention today?

AI: Here are your priorities:

1. **URGENT**: 3 new KEV-listed vulnerabilities affect your internet-facing assets
   - CVE-2024-5521 (Apache): 12 production servers
   - CVE-2024-5522 (nginx): 8 load balancers
   - CVE-2024-5523 (OpenSSL): 156 assets total
   
2. **Bundle Ready**: Tuesday's maintenance bundle is prepared
   - 23 patches for staging environment
   - Estimated downtime: 45 minutes
   - [Review Bundle →] [Approve →]

3. **Goal Progress**: You're 67% toward "Glasswing-ready"
   - On track for July 1 target
   - Next milestone: Patch production databases (scheduled May 15)

User: Tell me more about the OpenSSL vulnerability

AI: CVE-2024-5523 is a critical memory corruption vulnerability in OpenSSL 3.0.x:

**Risk Score: 84/100** (Critical)
- CVSS: 9.8 (Remote code execution)
- EPSS: 76% (High exploit probability)
- ✅ Patch available since yesterday

**Your exposure**:
- 156 assets affected (42 in production)
- 18 are internet-facing 🔴
- Snapper shows vulnerable code executing on 12 assets

**My recommendation**: Emergency patch for the 18 internet-facing assets tonight, remainder in Tuesday's window. Want me to create an emergency bundle?
```

### Example 3: Strategic Planning
```
User: We're acquiring a company next month. How do I plan for their infrastructure?

AI: I'll help you prepare for the acquisition. Let me ask a few questions:

1. Do you have their asset inventory or SBOM?
2. What's their current patch management maturity?
3. Any compliance requirements to maintain?

User: They sent an Excel file with 2000 servers. No idea about their patching. They need to maintain PCI compliance.

AI: I can work with that. Here's my recommended approach:

**Phase 1 - Discovery (Week 1-2)**
- Import their asset list
- I'll identify critical vulnerabilities
- Estimate remediation effort

**Phase 2 - Risk Assessment (Week 3)**
- PCI compliance gap analysis
- Critical vulnerability report
- Integration plan with your maintenance windows

**Phase 3 - Integration (Week 4+)**
- Gradually add their assets to your patch cycles
- Maintain separate PCI-compliant bundles
- Track progress with new goal: "Acquisition Integration"

Would you like me to create this phased plan as a goal?
```

## Technical Implementation

### AI Capabilities Needed

1. **Context Awareness**
   - Current vulnerabilities
   - Asset inventory
   - Patch history
   - Goal progress
   - User's role/preferences

2. **Action Execution**
   ```typescript
   // AI can execute these actions with confirmation
   actions = {
     createGoal: (params) => POST /api/v1/goals,
     generateBundle: (params) => POST /api/v1/bundles/generate,
     approveBundle: (bundleId) => PUT /api/v1/bundles/{id}/approve,
     runReport: (type) => GET /api/v1/reports/{type},
     updateRiskProfile: (profile) => PUT /api/v1/settings/risk-profile
   }
   ```

3. **Proactive Notifications**
   - New critical vulnerabilities
   - Goals at risk
   - Upcoming maintenance windows
   - Compliance deadlines

## UI Components

### Chat Interface
```
┌─────────────────────────────────────────────┐
│ Glasswatch AI Assistant                   ⚡│
├─────────────────────────────────────────────┤
│                                             │
│ AI: Good morning! You have 3 urgent items  │
│     requiring attention:                    │
│                                             │
│     1. New KEV vulnerability affects 23     │
│        production servers                   │
│     2. Tomorrow's maintenance window has    │
│        conflicts                            │
│     3. Compliance report due Friday         │
│                                             │
│     What would you like to tackle first?   │
│                                             │
│ ┌─────────────────────────────────────┐    │
│ │ Let's look at the KEV vulnerability │    │
│ └─────────────────────────────────────┘    │
│                                             │
│ [📎 Upload SBOM] [🎯 Create Goal] [📊 Status]│
└─────────────────────────────────────────────┘
```

### Quick Actions
- Suggested responses
- One-click actions
- File uploads (SBOM, CSV)
- Visual data (charts, timelines)

## Success Metrics

1. **Onboarding Completion**: 80%+ finish setup
2. **Daily Active Usage**: 60%+ use AI daily  
3. **Goal Achievement**: 90%+ meet target dates
4. **Natural Language Success**: 85%+ queries understood
5. **Action Automation**: 50%+ approvals via AI

## Implementation Priority

1. **MVP** (Sprint 2)
   - Basic chat interface
   - Status queries
   - Simple goal creation

2. **Enhanced** (Sprint 4)  
   - Proactive insights
   - Complex planning
   - Visual responses

3. **Advanced** (Post-launch)
   - Learning from user patterns
   - Predictive maintenance windows
   - Cross-tenant insights (anonymized)
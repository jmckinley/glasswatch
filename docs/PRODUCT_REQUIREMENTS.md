# Glasswatch Product Requirements

## Core UX Principles

### 1. Great Defaults
- Pre-configured risk profiles (Conservative, Balanced, Aggressive)
- Smart maintenance window detection from existing patterns
- Sensible default scoring weights
- Auto-detect common platforms and environments
- Pre-built goal templates:
  - "Glasswing-ready by July 1"
  - "Zero KEV exposure in 30 days"
  - "Patch critical systems monthly"
  - "Minimize downtime for production"

### 2. Exceptional Onboarding
- **Step 1**: Connect data sources (one-click for major platforms)
  - Auto-discover from AWS/Azure/GCP
  - ServiceNow/Jira OAuth flow
  - Upload SBOM/inventory CSV

- **Step 2**: Set your first goal
  - Guided goal creation wizard
  - Visual preview of patch timeline
  - Clear trade-off explanations

- **Step 3**: Review first bundle
  - AI explains why these patches together
  - Show risk reduction visualization
  - One-click approval to ITSM

### 3. Integrated AI Assistant

**Capabilities:**
- **Advisory Mode**
  - "What's my biggest risk right now?"
  - "Should I patch this CVE immediately?"
  - "What would happen if I delay this bundle?"
  
- **Status Intelligence**
  - Natural language status reports
  - Proactive alerts on emerging threats
  - Progress tracking against goals
  
- **Goal Shaping**
  - Convert business needs to technical goals
  - "I need 99.9% uptime" → Specific patch strategy
  - Trade-off analysis and recommendations
  
- **System Operation**
  - "Create a goal to be ready for audit by May"
  - "Show me all internet-facing critical vulnerabilities"
  - "Approve this bundle and schedule for Tuesday"
  - "Generate compliance report for Q1"

## Implementation Approach

### AI Chat Interface
```typescript
interface AIChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  actions?: SystemAction[]  // Executable actions
  visualizations?: DataViz[] // Charts, graphs
}

interface SystemAction {
  type: 'create_goal' | 'approve_bundle' | 'run_report' | 'update_settings'
  parameters: Record<string, any>
  confirmation_required: boolean
}
```

### Natural Language Examples
```
User: "We have a board meeting next month. Make sure we're secure."
# Glasswatch Demo Walkthrough

## 🚀 Starting the Application

```bash
# Start the full stack
docker compose up

# Or run services individually:
docker compose up -d postgres redis
cd backend && uvicorn main:app --reload
cd frontend && pnpm dev
```

## 📱 What You'll See

### 1. Dashboard (http://localhost:3000)
- **Risk Score Hero**: Total risk score with 7-day trend
- **Critical Vulnerabilities**: Count with KEV highlighting  
- **Internet Exposed Assets**: High-risk asset monitoring
- **Active Goals**: Progress tracking with at-risk indicators
- **Scheduled Bundles**: Next maintenance window info

### 2. Goals Page (/goals)
- **Create New Goal**: Business objective → patch schedule
- **Goal Types**: 
  - Compliance Deadline (e.g., "SOC 2 by July 1")
  - Risk Reduction (e.g., "Reduce risk by 80%")
  - Zero Critical (eliminate all critical vulns)
  - KEV Elimination (patch all CISA KEV listed)
- **Risk Tolerance**: Conservative, Balanced, Aggressive
- **Optimize Button**: Triggers constraint solver

### 3. Vulnerabilities Page (/vulnerabilities)
- **Stats Bar**: Total, Critical, High, KEV, Patches Available
- **Filter Options**: Severity, KEV-only, search
- **Table View**: 
  - CVE identifier with KEV badges
  - CVSS and EPSS scores
  - Affected asset count
  - Published date
- **Pagination**: 20 per page

### 4. Schedule Page (/schedule)
- **Maintenance Windows**: Weekly scheduled times
- **Bundle Details**: What patches go in each window
- **Window Utilization**: How full each window is
- **Approval Status**: Which windows need approval

## 🎯 Demo Flow

### Quick Win Demo (5 minutes)
1. Show dashboard - highlight total risk score
2. Go to Goals → Create "Glasswing Readiness" goal
3. Click Optimize - show how it creates bundles
4. Go to Schedule - show the generated patch plan
5. Explain: "Business goal → Optimized technical plan"

### Technical Deep Dive (15 minutes)
1. **Scoring Algorithm**
   - Show a vulnerability detail
   - Explain 8-factor scoring
   - Highlight Snapper runtime ±25 points
   
2. **Constraint Solver**
   - Create goal with constraints
   - Show optimization in action
   - Explain OR-Tools magic
   
3. **Multi-Tenant Architecture**
   - Show tenant header in requests
   - Explain row-level security
   - Future WorkOS integration

### Executive Pitch (3 minutes)
1. "20,000 CVEs per year - which ones matter?"
2. "Tell Glasswatch your business goal"
3. "Get an optimized patch schedule"
4. "No competitor does actual optimization"
5. "Snapper tells us if code actually runs"

## 💡 Key Differentiators to Highlight

1. **Not Just Prioritization**: True mathematical optimization
2. **Business-First**: Goals drive technical decisions  
3. **Runtime Intelligence**: Snapper integration is unique
4. **Patch Weather™**: Community success data (future)
5. **Dark Theme**: Built for ops teams who work at night

## 🔧 Technical Talking Points

- **FastAPI + Async**: Modern Python, great performance
- **Next.js 15**: Latest React with server components
- **PostgreSQL**: Battle-tested, supports row-level security
- **OR-Tools**: Google's constraint solver
- **Multi-Cloud Ready**: Kubernetes native from day one

## 📊 Metrics That Matter

Show these on the dashboard:
- Risk reduction over time
- Mean time to patch (MTTP)
- Compliance deadline tracking
- Patch success rate
- Window utilization

## 🎬 The "Aha!" Moment

When you click "Optimize" on a goal and see:
- Vulnerabilities automatically grouped
- Maintenance windows efficiently packed
- Risk reduced systematically over time
- Business deadline will be met

**"This is what every CISO wants but nobody else can deliver."**
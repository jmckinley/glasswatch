# Glasswatch Beta Testing Program

**Version:** 1.0  
**Launch Date:** June 2026  
**GA Target:** July 2026 (Glasswing disclosure window)  
**Last Updated:** 2026-04-20

---

## Overview

The Glasswatch beta program is a structured approach to validate product-market fit, identify bugs, and collect feedback before general availability. We'll run a phased beta program: **Closed Beta** (5 users) → **Open Beta** (50 users) → **General Availability**.

**Goals:**
1. Validate core workflows (asset discovery, scoring, optimization, approvals)
2. Identify and fix critical bugs before GA
3. Collect user feedback for UX improvements
4. Build early customer relationships and testimonials
5. Stress-test infrastructure at scale

---

## Beta Phases

### Phase 1: Closed Beta (2 weeks)

**Dates:** June 1-14, 2026  
**Participants:** 5 carefully selected organizations  
**Focus:** Core functionality validation, critical bug identification

**Participant Selection Criteria:**
- **Diverse environments:** Mix of AWS, Azure, GCP; different asset scales (100-10k assets)
- **Technical expertise:** Teams comfortable with beta software and providing detailed feedback
- **Relationship:** Existing contacts, warm introductions, or engaged mailing list subscribers
- **Time commitment:** Willing to dedicate 5+ hours/week to testing and feedback

**Ideal Participant Profile:**
- Security Engineer or Manager at a tech company (50-500 employees)
- Managing 500-5000 IT assets
- Current pain: Manual patch prioritization, spreadsheet-based tracking
- Tech stack: Cloud-native (AWS/GCP/Azure), containerized workloads
- Regulatory compliance needs (SOC 2, PCI-DSS, HIPAA)

**Deliverables:**
- [ ] 5 beta accounts provisioned
- [ ] Onboarding sessions scheduled (1-on-1, 30 min)
- [ ] Feedback form sent (Google Form)
- [ ] Weekly check-in calls scheduled
- [ ] Bug reports triaged and fixed within 48h

### Phase 2: Open Beta (2 weeks)

**Dates:** June 15-28, 2026  
**Participants:** 50 organizations (includes Closed Beta participants)  
**Focus:** Scale testing, edge case discovery, UX refinement

**Participant Recruitment:**
- **Landing page:** Beta signup form (email, company, # of assets)
- **Email outreach:** Targeted outreach to security mailing lists
- **Social media:** Twitter, LinkedIn, Reddit (r/netsec, r/sysadmin)
- **Product Hunt:** "Coming Soon" page with beta signup
- **Partnerships:** Reach out to cloud security communities (Cloud Security Alliance, OWASP)

**Acceptance Criteria:**
- [ ] Complete beta signup form
- [ ] Provide valid work email (no personal emails)
- [ ] Agree to beta user agreement (see below)
- [ ] Attend onboarding webinar or watch recording

**Deliverables:**
- [ ] 50 beta accounts provisioned
- [ ] Group onboarding webinar (weekly, 1 hour)
- [ ] Self-service knowledge base (docs.glasswatch.io)
- [ ] Beta Slack/Discord community for peer support
- [ ] Bug reports triaged and fixed within 72h

### Phase 3: General Availability

**Date:** July 1, 2026 (Glasswing disclosure window)  
**Participants:** Open to all  
**Focus:** Public launch, marketing, customer acquisition

**Transition Plan:**
- [ ] Beta users automatically upgraded to GA (free trial or discounted pricing)
- [ ] Launch announcement sent to beta users first (24h early access)
- [ ] Beta user testimonials collected for marketing
- [ ] Beta feedback incorporated into product roadmap

---

## User Onboarding Flow

### Step 1: Welcome Email (T+0, automated)

**Subject:** Welcome to the Glasswatch Beta! 🚀

**Content:**
- Thank you for joining the beta
- What to expect (timeline, support, feedback expectations)
- Next steps: Schedule onboarding call or watch video
- Link to beta user agreement
- Link to Slack/Discord community
- Contact for questions: beta@glasswatch.io

### Step 2: Onboarding Session (T+1-3 days, scheduled or recorded)

**Format:** Live video call (1-on-1 for Closed Beta, group webinar for Open Beta)

**Agenda (30 min):**
1. **Introduction (5 min):** Product overview, beta goals, feedback expectations
2. **Account Setup (5 min):** Login, team invitation, multi-tenant setup
3. **Asset Discovery (10 min):** Connect cloud accounts, run first scan, review results
4. **Vulnerability Scoring (5 min):** Review scoring algorithm, filter by priority
5. **Goal Creation (3 min):** Set first goal ("Patch top 10 critical vulns in 30 days")
6. **Q&A (2 min):** Answer questions, troubleshoot issues

**Deliverables:**
- [ ] Onboarding video recording (for self-service)
- [ ] Onboarding checklist (PDF or interactive)
- [ ] Sample data set (optional, for testing without real assets)

### Step 3: First Week Check-In (T+7 days, manual)

**Format:** Email or Slack message

**Content:**
- How's it going? Any blockers?
- Reminder to complete feedback form
- Highlight 2-3 features to try (e.g., approval workflows, rollback tracking)
- Share tips from other beta users
- Invite to office hours (weekly open Q&A session)

### Step 4: Exit Survey (End of beta phase, automated)

**Format:** Google Form or Typeform

**Questions:** (See "Feedback Collection" section below)

---

## Feedback Collection

### In-App Feedback

**Feedback Widget:**
- Floating "Feedback" button (bottom-right corner)
- Clicking opens modal: "What's on your mind?" (text + screenshot capture)
- Submit → creates GitHub Issue (tagged `beta-feedback`)
- User receives confirmation: "Thanks! We'll review within 48h."

**Feature Flagging:**
- New features released behind feature flags (enabled for beta users first)
- Collect feedback on new features before GA release

### Surveys

**Weekly Pulse Survey (1 question, 1 min):**
- "How satisfied are you with Glasswatch this week?" (1-5 scale)
- Optional: "What's one thing we could improve?"

**Mid-Beta Survey (5 min):**
- Product-market fit question: "How would you feel if you could no longer use Glasswatch?" (Very disappointed / Somewhat disappointed / Not disappointed)
- Feature usage: "Which features have you used?" (checklist)
- Feature satisfaction: "How satisfied are you with [feature]?" (1-5 scale)
- Missing features: "What's missing that you need?" (open text)
- NPS: "How likely are you to recommend Glasswatch?" (0-10 scale)

**Exit Survey (10 min):**
- Overall satisfaction: "How satisfied are you with Glasswatch?" (1-5 scale)
- Feature deep-dive: Detailed feedback on each major feature
- Comparison: "How does Glasswatch compare to your current solution?" (Better/Same/Worse)
- Pricing: "What would you expect to pay for Glasswatch?" (open text or multiple choice)
- Willingness to pay: "Would you pay for Glasswatch at GA?" (Yes/No/Maybe)
- Testimonial: "Can we quote you for marketing?" (Yes/No, with quote)
- Referral: "Do you know anyone else who would benefit?" (email addresses)

### User Interviews

**Cadence:** 1-2 interviews per week during beta (5-10 total)

**Format:** 1-on-1 video call, 30-45 min

**Goals:**
- Deep-dive into user workflows and pain points
- Understand decision-making process (Why Glasswatch? Why not competitors?)
- Identify "aha moments" and friction points
- Collect stories for case studies and testimonials

**Interview Guide:**
1. **Background (5 min):** Tell me about your role and team.
2. **Current Process (10 min):** How do you manage patches today? What are the biggest pain points?
3. **Glasswatch Usage (15 min):** Walk me through how you've been using Glasswatch. What do you love? What's frustrating?
4. **Feature Requests (5 min):** If you could add one feature, what would it be?
5. **Pricing & Value (5 min):** What would you expect to pay? What ROI do you see?
6. **Wrap-Up (5 min):** Any other feedback? Can we quote you?

**Deliverables:**
- [ ] Interview notes (shared with product team)
- [ ] Themes and insights document (updated after each batch of 3-5 interviews)
- [ ] User quotes for marketing (with permission)

---

## Bug Reporting Process

### How Users Report Bugs

**Channels:**
1. **In-app feedback widget** (preferred, includes screenshot + context)
2. **Email:** beta@glasswatch.io
3. **Slack/Discord:** #beta-bugs channel
4. **GitHub Issues:** Direct submission (for technical users)

**Required Information:**
- **What happened?** (description of the bug)
- **What did you expect?** (expected behavior)
- **How to reproduce?** (steps to reproduce)
- **Environment:** Browser, OS, account details
- **Screenshot or video** (if applicable)

### Bug Triage Process

**SLA:**
- **Critical:** Response within 4 hours, fix within 24 hours
- **High:** Response within 24 hours, fix within 3 days
- **Medium:** Response within 48 hours, fix within 1 week
- **Low:** Response within 1 week, fix in next sprint

**Priority Definitions:**
- **Critical:** Data loss, security vulnerability, complete feature failure, affects >50% of users
- **High:** Major feature broken, affects 10-50% of users, workaround exists
- **Medium:** Minor feature issue, affects <10% of users, workaround exists
- **Low:** Cosmetic issue, nice-to-have, no functional impact

**Workflow:**
1. Bug reported → GitHub Issue created (auto-labeled `beta-bug`)
2. Engineer triages within SLA (assigns priority, assigns owner)
3. Engineer investigates and responds to reporter (acknowledge, ask for details, or provide workaround)
4. Fix implemented → PR created → Code review → Merge
5. Fix deployed to beta environment
6. Reporter notified: "Fixed in latest version, please verify"
7. Reporter verifies → Issue closed, or reopened if not fixed

**Communication:**
- All bug reports acknowledged within SLA
- Weekly "Bug Squash Update" email to beta users (bugs fixed, known issues, workarounds)

---

## Success Metrics

### Product Metrics

| Metric | Target | How We Measure |
|--------|--------|----------------|
| **Activation Rate** | >80% | % of beta users who complete first scan |
| **Weekly Active Users (WAU)** | >60% | % of beta users active in past 7 days |
| **Feature Adoption** | >50% | % of users who use key features (discovery, scoring, goals, approvals) |
| **Task Completion Rate** | >90% | % of users who complete core workflows (end-to-end) |
| **Time to First Value** | <15 min | Time from signup to first scan completion |

### Feedback Metrics

| Metric | Target | How We Measure |
|--------|--------|----------------|
| **NPS (Net Promoter Score)** | >40 | "How likely are you to recommend Glasswatch?" (0-10 scale) |
| **Product-Market Fit** | >40% | % of users who say "Very disappointed" if product goes away |
| **Feature Satisfaction** | >4.0/5 | Average satisfaction rating across all features |
| **Bug Severity** | 0 critical | # of critical bugs reported and unresolved |
| **Response Time** | <24h | Average time to first response on bug reports |

### Business Metrics

| Metric | Target | How We Measure |
|--------|--------|----------------|
| **Conversion Intent** | >50% | % of beta users who say "Yes" or "Maybe" to "Would you pay?" |
| **Referrals** | >20% | % of beta users who refer others |
| **Testimonials** | >10 | # of beta users who agree to be quoted |
| **Case Studies** | >2 | # of detailed case studies written |

---

## Known Limitations (Beta)

Communicate these upfront to set expectations:

**Features Not Yet Implemented:**
- [ ] WorkOS SSO integration (coming in GA)
- [ ] Mobile app (roadmap for Q3 2026)
- [ ] Advanced RBAC (custom roles - roadmap)
- [ ] White-label branding (enterprise feature)

**Performance Limitations:**
- [ ] Asset discovery may take longer for very large environments (>10k assets)
- [ ] Optimization solver may timeout for complex goals (>1000 patches, >100 windows)
- [ ] Real-time updates may lag for high-frequency activity (>100 events/min)

**Support Limitations:**
- [ ] Beta support via email and Slack only (no phone support)
- [ ] Response time: 24 hours (not 24/7 coverage)
- [ ] Known issues documented in changelog (check before reporting bugs)

**Data & Security:**
- [ ] Beta environment is separate from production (data will not migrate automatically)
- [ ] Data retention: 90 days (after beta ends, accounts may be deleted or archived)
- [ ] No SLA or uptime guarantee during beta
- [ ] No SOC 2 certification yet (in progress, expected Q3 2026)

---

## Beta User Agreement

### Terms & Conditions

**By participating in the Glasswatch beta program, you agree to:**

1. **Test and Provide Feedback:** Actively use the product and provide feedback via surveys, interviews, and bug reports.

2. **Confidentiality:** Beta features and performance are confidential. Do not publicly disclose beta-only features without written permission.

3. **No SLA:** Glasswatch is provided "as-is" during beta. No uptime or performance guarantees. We may deploy updates without notice.

4. **Data:** Your data is stored securely, but we cannot guarantee data retention beyond the beta period. Export your data before beta ends.

5. **Pricing:** Beta access is free. GA pricing will be announced before beta ends. Beta users will receive a discount or extended trial.

6. **Support:** Best-effort support via email and Slack. Critical bugs prioritized, but no 24/7 support.

7. **Termination:** We may terminate beta access at any time. You may leave the beta program at any time.

8. **Intellectual Property:** All feedback, suggestions, and bug reports become property of Glasswatch. We may use your testimonials and quotes for marketing (with permission).

**Questions?** Contact beta@glasswatch.io

---

## Beta Timeline

### Pre-Beta (May 2026)

- [ ] **Week 1-2:** Finalize beta program plan (this document)
- [ ] **Week 3:** Set up beta environment (separate from production)
- [ ] **Week 3:** Create beta landing page and signup form
- [ ] **Week 4:** Recruit Closed Beta participants (5 organizations)
- [ ] **Week 4:** Prepare onboarding materials (video, checklist, docs)

### Closed Beta (June 1-14, 2026)

- [ ] **Week 1 (June 1-7):**
  - [ ] Send welcome emails to 5 participants
  - [ ] Conduct 1-on-1 onboarding sessions
  - [ ] Monitor usage and errors (daily dashboard review)
  - [ ] Triage and fix critical bugs (within 24h)
  - [ ] Send weekly pulse survey
- [ ] **Week 2 (June 8-14):**
  - [ ] First-week check-in with each participant
  - [ ] Conduct 2-3 user interviews
  - [ ] Mid-beta survey sent
  - [ ] Bug squash sprint (fix top 10 issues)
  - [ ] Prepare for Open Beta expansion

### Open Beta (June 15-28, 2026)

- [ ] **Week 3 (June 15-21):**
  - [ ] Open beta signups (target: 50 total participants)
  - [ ] Send welcome emails to new participants
  - [ ] Group onboarding webinar (June 16 and 18)
  - [ ] Monitor usage and errors (daily dashboard review)
  - [ ] Triage and fix bugs (within 72h SLA)
  - [ ] Weekly pulse survey
- [ ] **Week 4 (June 22-28):**
  - [ ] Mid-Open Beta check-in (email or Slack)
  - [ ] Conduct 3-5 user interviews
  - [ ] Exit survey sent (June 26)
  - [ ] Final bug squash sprint
  - [ ] Prepare launch announcement

### GA Transition (June 29 - July 1, 2026)

- [ ] **June 29:** Beta program ends, exit survey closes
- [ ] **June 30:** Analyze feedback, finalize launch plan
- [ ] **July 1:** General Availability launch (Glasswing window)
  - [ ] Beta users receive early access email (24h before public launch)
  - [ ] Pricing announced (beta users get discount or extended trial)
  - [ ] Beta user testimonials published on website
  - [ ] Thank you email to all beta participants (swag, credits, or discounts)

---

## Resources

### Documentation

- **Beta User Guide:** docs.glasswatch.io/beta
- **FAQ:** docs.glasswatch.io/beta/faq
- **Known Issues:** docs.glasswatch.io/beta/known-issues
- **Changelog:** docs.glasswatch.io/changelog

### Support

- **Email:** beta@glasswatch.io (response time: 24h)
- **Slack/Discord:** Join beta community (invite in welcome email)
- **Office Hours:** Weekly open Q&A session (Wednesdays 2-3 PM ET)

### Feedback

- **In-app widget:** Click "Feedback" button (bottom-right)
- **Surveys:** Sent via email (weekly pulse, mid-beta, exit)
- **Interviews:** Schedule via Calendly link (in welcome email)

---

## Post-Beta Action Plan

After beta ends, analyze feedback and prioritize improvements:

### Immediate Fixes (Pre-Launch)

- [ ] Fix all critical bugs (0 tolerance)
- [ ] Fix high-priority bugs (or document workarounds)
- [ ] Address top 3 UX pain points from feedback

### Post-Launch Roadmap (Q3 2026)

- [ ] Implement top 5 feature requests (based on frequency and impact)
- [ ] Improve onboarding based on "time to first value" data
- [ ] Optimize performance based on load testing and beta usage patterns
- [ ] Build integrations based on beta user requests (Jira, PagerDuty, etc.)

### Marketing & Sales

- [ ] Write 2-3 case studies from beta users (with permission)
- [ ] Collect and publish testimonials (website, social proof)
- [ ] Create video testimonials (optional, high-impact)
- [ ] Use beta feedback to refine messaging and positioning
- [ ] Beta user referral program (discounts for referrals)

---

## Contact

**Beta Program Manager:** [Your Name]  
**Email:** beta@glasswatch.io  
**Slack/Discord:** Join #beta channel  
**Office Hours:** Wednesdays 2-3 PM ET  

---

**Last Updated:** 2026-04-20  
**Version:** 1.0  
**Status:** Ready to Launch  
**Next Review:** Post-Beta (July 2026)

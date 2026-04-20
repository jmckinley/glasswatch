# Sprint 10 Frontend - Route Map

## Public Routes

### `/auth/login`
**Login Page**
- SSO login button (POST /api/v1/auth/login)
- Demo login button (GET /api/v1/auth/demo-login)
- Dark themed, centered card layout
- Handles OAuth callback with token
- Auto-redirects to `/` after successful login

## Protected Routes (require authentication)

All protected routes use `DashboardLayout` which includes:
- Header with navigation
- NotificationBell in top-right
- User avatar/menu dropdown
- Auto-redirects to `/auth/login` if not authenticated

### `/` (existing)
**Main Dashboard**
- Overview stats and cards
- Risk score trending
- Vulnerability summaries
- Uses existing DashboardPage component

### `/dashboard/approvals`
**Approvals Inbox**
- Tabs: Pending | Approved | Rejected | All
- Risk-color-coded approval cards
- Quick Approve/Reject buttons
- Comment modal for actions
- Requester, timestamp, approval progress

### `/dashboard/activities`
**Activity Feed (Full Page)**
- Chronological activity stream
- All activity types with icons/colors
- Unread indicators
- Mark as read / Mark all as read
- Click to navigate (future enhancement)

## Components (can be embedded anywhere)

### `<NotificationBell />`
**Location:** Header (top-right)
- Bell icon with unread badge
- Dropdown shows recent 10 activities
- Polls every 30s for updates
- Click to mark activities as read

### `<ActivityFeed mode="sidebar" />`
**Location:** Sidebar of any page
- Recent activities in compact view
- Unread count badge
- Used with `<DashboardLayout showActivitySidebar={true}>`

### `<CommentThread entityType="..." entityId="..." />`
**Location:** Any detail page
- Full threaded comment system
- @mention autocomplete
- Emoji reactions
- Edit/delete own comments
- Reply to any comment

### `<ApprovalRequestModal />`
**Location:** Modal overlay
- Create new approval request
- Bundle selection
- Risk assessment display
- Title + description form

## Navigation Flow

```
                  ┌──────────────┐
                  │ /auth/login  │
                  └──────┬───────┘
                         │
                    (JWT token)
                         │
        ┌────────────────┴────────────────┐
        │                                  │
        ▼                                  ▼
┌───────────────┐                 ┌──────────────────────┐
│      /        │                 │ /dashboard/approvals │
│  Dashboard    │◄────────────────┤   Approvals Inbox    │
└───────┬───────┘                 └──────────────────────┘
        │
        │
        ▼
┌───────────────────────┐
│ /dashboard/activities │
│    Activity Feed      │
└───────────────────────┘
```

## Header Navigation (always visible on protected routes)

```
┌─────────────────────────────────────────────────────────────┐
│ [Glasswatch]  Dashboard  Approvals  Vulns  Goals   🔔 [User]│
└─────────────────────────────────────────────────────────────┘
                                                       ▲    ▲
                                                       │    │
                                          NotificationBell  UserMenu
                                               (dropdown)   (dropdown)
```

## Activity Icons Reference

| Type | Icon | Color |
|------|------|-------|
| approval_request | 📋 | blue |
| approval_approved | ✅ | green |
| approval_rejected | ❌ | red |
| comment_added | 💬 | purple |
| bundle_created | 📦 | yellow |
| bundle_deployed | 🚀 | cyan |
| goal_created | 🎯 | indigo |
| goal_completed | 🏆 | green |
| vulnerability_discovered | 🔒 | orange |

## Risk Level Colors

| Level | Badge | Color |
|-------|-------|-------|
| Low | 🟢 LOW | green |
| Medium | 🟡 MEDIUM | yellow |
| High | 🟠 HIGH | orange |
| Critical | 🔴 CRITICAL | red |

---

**Quick Start:**
1. Navigate to `/auth/login`
2. Click "Demo Login"
3. Redirects to `/` (Dashboard)
4. Click "Approvals" in header → `/dashboard/approvals`
5. Click bell icon 🔔 → see recent activities
6. Click "View all activity →" → `/dashboard/activities`

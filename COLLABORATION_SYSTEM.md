# Team Collaboration System - Sprint 10

## Overview
Built a comprehensive team collaboration system for Glasswatch with comments, @mentions, reactions, and activity feed.

## Components Created

### 1. Models (`backend/models/`)

#### `comment.py`
- **Comment model**: Threaded comments with soft delete
  - Polymorphic entity references (asset, vulnerability, bundle, goal, approval)
  - Parent-child threading via `parent_id`
  - @mention tracking in JSON field
  - Edit and delete tracking
- **Reaction model**: Emoji reactions on comments
  - Unique constraint: one emoji per user per comment
  - Toggle behavior (add/remove)

#### `activity.py`
- **Activity model**: System-wide activity tracking
  - 13 activity types (comment_added, approval_requested, etc.)
  - Entity references for polymorphic tracking
  - Read/unread state for notifications
  - Supports both user and system actions

### 2. Service Layer (`backend/services/`)

#### `collaboration_service.py`
Core collaboration logic:
- **add_comment()**: Parse @mentions, create comment, notify users, create activity
- **edit_comment()**: Edit own comments only
- **delete_comment()**: Soft delete with permission check
- **get_comments()**: Retrieve threaded comments with replies
- **add_reaction()**: Toggle emoji reactions
- **record_activity()**: Create activity entries
- **get_activity_feed()**: Paginated feed with filtering
- **get_unread_count()**: Notification badge count
- **mark_as_read()**: Mark activities as read

### 3. API Endpoints (`backend/api/v1/`)

#### `comments.py`
- `POST /comments` - Add comment with @mentions
- `GET /comments` - List comments for entity (with replies)
- `GET /comments/{id}` - Get specific comment
- `PATCH /comments/{id}` - Edit comment (author only)
- `DELETE /comments/{id}` - Soft delete (author or admin)
- `POST /comments/{id}/reactions` - Toggle reaction
- `GET /comments/{id}/reactions` - List reactions (grouped by emoji)

#### `activities.py`
- `GET /activities` - Tenant-wide activity feed
- `GET /activities/my` - Current user's activities
- `GET /activities/unread-count` - Notification badge count
- `POST /activities/mark-read` - Mark activities as read

### 4. Database Migration

#### `006_add_collaboration.py`
- Creates `entitytype` enum (asset, vulnerability, bundle, goal, approval)
- Creates `activitytype` enum (13 types)
- Creates `comments` table with indexes
- Creates `reactions` table with unique constraint
- Creates `activities` table with indexes
- Optimized indexes for common queries

## Features

### @Mentions
- Regex parsing: `@username` or `@email@domain.com`
- Resolves to user UUIDs
- Creates USER_MENTIONED activities for notifications
- Stores mentions in JSON array

### Threading
- Top-level comments and nested replies
- Self-referential via `parent_id`
- Recursive loading with SQLAlchemy `selectinload`

### Reactions
- Emoji reactions (e.g., "thumbsup", "rocket", "eyes")
- Toggle behavior: add if missing, remove if exists
- Grouped by emoji with counts in API response

### Activity Feed
- System-wide feed for transparency
- Per-user feed for personalized notifications
- Read/unread tracking
- Paginated and filterable

### Soft Delete
- Comments marked `is_deleted` instead of removed
- Preserves conversation history
- Content replaced with "[deleted]" in API responses

## Security

- Tenant isolation on all queries
- Permission checks:
  - Edit: author only
  - Delete: author or admin
  - Read: tenant members
- @mention validation against tenant users
- Activity permissions via user_id

## Next Steps

1. **Frontend Integration**
   - Comment threads UI
   - @mention autocomplete
   - Reaction picker
   - Activity feed notifications

2. **Real-time Updates**
   - WebSocket support for live comments
   - Push notifications for mentions

3. **Testing**
   - Unit tests for service layer
   - API integration tests
   - Permission boundary tests

4. **Enhanced Features**
   - Rich text formatting
   - File attachments on comments
   - Email notifications for mentions
   - Comment search

## Database Schema

```sql
-- Comments (threaded, with mentions)
comments
  id UUID PK
  tenant_id UUID FK
  entity_type ENUM
  entity_id UUID
  user_id UUID FK
  parent_id UUID FK (self-referential)
  content TEXT
  mentions JSON
  is_edited BOOLEAN
  is_deleted BOOLEAN
  created_at TIMESTAMP
  updated_at TIMESTAMP

-- Reactions (emoji on comments)
reactions
  id UUID PK
  comment_id UUID FK
  user_id UUID FK
  emoji VARCHAR(20)
  created_at TIMESTAMP
  UNIQUE (comment_id, user_id, emoji)

-- Activities (feed and notifications)
activities
  id UUID PK
  tenant_id UUID FK
  user_id UUID FK (nullable for system actions)
  activity_type ENUM
  entity_type VARCHAR(50)
  entity_id UUID
  title VARCHAR(255)
  details JSON
  is_read BOOLEAN
  created_at TIMESTAMP
```

## Commit
```
feat(collab): Add comments, @mentions, reactions, and activity feed

- Comment model with threading and soft delete
- Reaction model with toggle behavior
- Activity model for feed and notifications
- CollaborationService with @mention parsing
- Comments API (CRUD, reactions)
- Activities API (feed, unread count, mark read)
- Migration 006 with optimized indexes
```

## Verification

All files passed syntax validation:
- ✓ comment.py
- ✓ activity.py
- ✓ collaboration_service.py
- ✓ comments.py
- ✓ activities.py
- ✓ __init__.py
- ✓ base.py
- ✓ 006_add_collaboration.py

Committed: 5f4bcb2

# Contributing to Glasswatch

Thank you for your interest in contributing to Glasswatch! This guide will help you get started with development, code style, testing, and the pull request process.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Messages](#commit-messages)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Code Review Checklist](#code-review-checklist)
- [Release Process](#release-process)

---

## Getting Started

### Prerequisites

**Backend:**
- Python 3.11+ (3.12 recommended)
- PostgreSQL 15+
- Redis 7+
- pip or uv (package manager)

**Frontend:**
- Node.js 20+ (LTS recommended)
- pnpm 8+ (preferred over npm/yarn)

**Tools:**
- Git 2.30+
- Docker & Docker Compose (for local development)
- A code editor (VS Code recommended with Python, ESLint, Prettier extensions)

### First-Time Setup

1. **Fork the repository** (if external contributor)
2. **Clone the repository:**
   ```bash
   git clone https://github.com/jmckinley/glasswatch.git
   cd glasswatch
   ```

3. **Set up backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Dev dependencies
   ```

4. **Set up frontend:**
   ```bash
   cd frontend
   pnpm install
   ```

5. **Set up database (Docker Compose):**
   ```bash
   cd ..  # Back to project root
   docker-compose up -d postgres redis
   ```

6. **Run database migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

7. **Verify setup:**
   ```bash
   # Backend (from backend/)
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   # Visit: http://localhost:8000/docs (Swagger UI)

   # Frontend (from frontend/)
   pnpm dev
   # Visit: http://localhost:3000
   ```

---

## Development Setup

### Environment Variables

Create `.env` files in `backend/` and `frontend/`:

**backend/.env:**
```bash
DATABASE_URL=postgresql+asyncpg://glasswatch:password@localhost:5432/glasswatch
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-key-change-in-production
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

**frontend/.env.local:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENV=development
```

### Running Locally

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
pnpm dev
```

**Full Stack (Docker Compose):**
```bash
docker-compose up
```

### Database Migrations

**Create a new migration:**
```bash
cd backend
alembic revision --autogenerate -m "Add new column to assets table"
```

**Review the migration file** (in `backend/alembic/versions/`) before applying.

**Apply migrations:**
```bash
alembic upgrade head
```

**Rollback migrations:**
```bash
alembic downgrade -1  # Rollback one version
alembic downgrade <revision_id>  # Rollback to specific version
```

---

## Code Style

We use automated formatters and linters to maintain consistent code style.

### Python (Backend)

**Formatter:** [Black](https://github.com/psf/black)  
**Import Sorter:** [isort](https://pycqa.github.io/isort/)  
**Linter:** [Ruff](https://github.com/astral-sh/ruff) (replaces flake8, pylint)

**Configuration:** See `backend/pyproject.toml`

**Run formatters:**
```bash
cd backend
black .
isort .
```

**Run linter:**
```bash
ruff check .
```

**Fix auto-fixable issues:**
```bash
ruff check --fix .
```

**Pre-commit hook** (recommended):
```bash
pip install pre-commit
pre-commit install
```

**Style Guidelines:**
- **Line length:** 100 characters (Black default: 88, we extend to 100)
- **Imports:** Sorted alphabetically, grouped (stdlib → third-party → local)
- **Type hints:** Required for all function signatures
- **Docstrings:** Google style for public APIs, classes, and complex functions
- **Naming:**
  - Variables/functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`

**Example:**
```python
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Vulnerability


async def get_vulnerabilities(
    db: AsyncSession,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Vulnerability]:
    """
    Fetch vulnerabilities for a tenant.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        limit: Max number of results
        offset: Pagination offset

    Returns:
        List of Vulnerability objects
    """
    result = await db.execute(
        select(Vulnerability)
        .filter(Vulnerability.tenant_id == tenant_id)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
```

### TypeScript (Frontend)

**Formatter:** [Prettier](https://prettier.io/)  
**Linter:** [ESLint](https://eslint.org/)

**Configuration:** See `frontend/.prettierrc` and `frontend/.eslintrc.json`

**Run formatter:**
```bash
cd frontend
pnpm format
```

**Run linter:**
```bash
pnpm lint
```

**Fix auto-fixable issues:**
```bash
pnpm lint --fix
```

**Style Guidelines:**
- **Line length:** 100 characters
- **Quotes:** Single quotes for strings (Prettier default)
- **Semicolons:** Always
- **Trailing commas:** ES5 (arrays, objects)
- **Naming:**
  - Components: `PascalCase` (e.g., `AssetList.tsx`)
  - Variables/functions: `camelCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Interfaces/Types: `PascalCase` (prefix with `I` optional)

**Example:**
```typescript
import { useState, useEffect } from 'react';
import { Asset } from '@/types';

interface AssetListProps {
  tenantId: string;
  limit?: number;
}

export default function AssetList({ tenantId, limit = 100 }: AssetListProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAssets();
  }, [tenantId]);

  const fetchAssets = async () => {
    setLoading(true);
    const response = await fetch(`/api/assets?tenant_id=${tenantId}&limit=${limit}`);
    const data = await response.json();
    setAssets(data);
    setLoading(false);
  };

  if (loading) return <div>Loading...</div>;

  return (
    <ul>
      {assets.map((asset) => (
        <li key={asset.id}>{asset.name}</li>
      ))}
    </ul>
  );
}
```

---

## Branch Naming Convention

Use descriptive branch names with prefixes:

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New feature or enhancement | `feature/asset-discovery` |
| `fix/` | Bug fix | `fix/scoring-null-pointer` |
| `refactor/` | Code refactoring (no functional change) | `refactor/optimize-queries` |
| `docs/` | Documentation only | `docs/update-readme` |
| `test/` | Test-only changes | `test/add-integration-tests` |
| `chore/` | Tooling, dependencies, config | `chore/update-dependencies` |

**Examples:**
```bash
git checkout -b feature/approval-workflows
git checkout -b fix/login-session-timeout
git checkout -b docs/api-documentation
```

**Main branches:**
- `main` - Production-ready code (protected)
- `develop` - Integration branch (if using GitFlow, otherwise merge to `main`)

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style changes (formatting, no functional change)
- `refactor` - Code refactoring
- `test` - Adding or updating tests
- `chore` - Tooling, dependencies, config
- `perf` - Performance improvement
- `security` - Security fix

**Scope:** Optional, indicates area of change (e.g., `auth`, `api`, `frontend`, `db`)

**Examples:**
```bash
feat(auth): Add JWT token refresh endpoint

Implements automatic token refresh to improve UX.
Tokens expire after 1 hour, refresh extends by 24h.

Closes #123

fix(scoring): Handle null EPSS values gracefully

Previously crashed when EPSS data was missing.
Now defaults to 0 and logs a warning.

Fixes #456

docs(readme): Update installation instructions

Added Docker Compose setup and environment variables.

test(api): Add integration tests for approval workflows

Covers create, approve, reject, and escalation flows.
87 tests now pass.
```

**Best Practices:**
- **Subject line:** 50 characters or less, imperative mood ("Add feature" not "Added feature")
- **Body:** Wrap at 72 characters, explain what and why (not how)
- **Footer:** Reference issues/PRs (`Closes #123`, `Fixes #456`, `Related to #789`)

---

## Testing Requirements

All code changes must include tests. We aim for **70%+ code coverage**.

### Backend Tests (pytest)

**Run all tests:**
```bash
cd backend
pytest
```

**Run with coverage:**
```bash
pytest --cov=app --cov-report=term-missing
```

**Run specific test file:**
```bash
pytest tests/test_auth.py
```

**Run specific test:**
```bash
pytest tests/test_auth.py::test_login_success
```

**Test Structure:**
- `tests/unit/` - Unit tests (isolated, fast, mock external dependencies)
- `tests/integration/` - Integration tests (test API endpoints, database, etc.)

**Example Unit Test:**
```python
import pytest
from app.services.scoring import calculate_score

def test_calculate_score_critical_kev():
    """Test scoring for critical vulnerability in KEV."""
    score = calculate_score(
        cvss_score=9.8,
        epss_score=0.9,
        in_kev=True,
        asset_criticality="critical",
        internet_facing=True,
        patch_available=True,
        compensating_controls=False,
        runtime_detection=True,
    )
    # Expected: 30 (CVSS) + 13.5 (EPSS) + 20 (KEV) + 15 (criticality) + 10 (exposure) + 25 (runtime) = 113.5
    assert score >= 110  # Allow some rounding
```

**Example Integration Test:**
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_get_vulnerabilities():
    """Test GET /api/vulnerabilities endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/vulnerabilities", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Frontend Tests (Jest + React Testing Library)

**Run all tests:**
```bash
cd frontend
pnpm test
```

**Run with coverage:**
```bash
pnpm test --coverage
```

**Run in watch mode (during development):**
```bash
pnpm test --watch
```

**Test Structure:**
- `__tests__/` - Test files (colocated with components)
- `*.test.tsx` - Component tests
- `*.test.ts` - Utility/logic tests

**Example Component Test:**
```typescript
import { render, screen } from '@testing-library/react';
import AssetList from './AssetList';

test('renders asset list', async () => {
  render(<AssetList tenantId="test-tenant" />);
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
  // Add assertions for loaded state
});
```

---

## Pull Request Process

### Before Opening a PR

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes** and commit frequently (atomic commits preferred)

3. **Run tests locally:**
   ```bash
   # Backend
   cd backend
   pytest --cov=app
   black .
   isort .
   ruff check .

   # Frontend
   cd frontend
   pnpm lint
   pnpm test
   pnpm build  # Verify build succeeds
   ```

4. **Pull latest changes** from `main` and resolve conflicts:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

5. **Push your branch:**
   ```bash
   git push origin feature/my-new-feature
   ```

### Opening a PR

1. **Go to GitHub** and open a Pull Request
2. **Fill out the PR template:**
   - **Title:** Concise, descriptive (e.g., "Add approval workflow feature")
   - **Description:**
     - What does this PR do?
     - Why is this change needed?
     - How was it tested?
     - Screenshots (for UI changes)
     - Related issues (`Closes #123`)
   - **Checklist:**
     - [ ] Tests added/updated
     - [ ] Code follows style guide
     - [ ] Documentation updated (if needed)
     - [ ] No breaking changes (or documented)

3. **Request reviewers** (1-2 team members)

4. **Wait for CI checks** to pass (tests, linting, build)

### During Review

- **Respond to feedback** promptly
- **Make requested changes** in new commits (don't force-push during review)
- **Mark conversations as resolved** once addressed
- **Re-request review** after addressing all feedback

### Merging

- **Squash and merge** (preferred for feature branches) - creates a single commit on `main`
- **Merge commit** (for long-lived branches or when commit history is important)
- **Rebase and merge** (for linear history, but avoid if there are many commits)

**After merging:**
- **Delete the feature branch** (GitHub will prompt)
- **Verify in staging/production** (if applicable)

---

## Code Review Checklist

Use this checklist when reviewing PRs:

### Functionality
- [ ] Code does what the PR description says
- [ ] No breaking changes (or documented with migration guide)
- [ ] Edge cases handled (null values, empty arrays, errors)
- [ ] Error messages are user-friendly

### Code Quality
- [ ] Code is readable and well-structured
- [ ] No obvious performance issues (N+1 queries, unnecessary loops)
- [ ] No code duplication (DRY principle)
- [ ] Functions are small and focused (single responsibility)
- [ ] Complex logic has explanatory comments

### Testing
- [ ] Tests added for new functionality
- [ ] Tests cover happy path and edge cases
- [ ] Tests are readable and maintainable
- [ ] Coverage increased or maintained (70%+ target)

### Security
- [ ] No sensitive data in logs or error messages
- [ ] Input validation for user-provided data
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized output)
- [ ] Authentication/authorization checks in place

### Documentation
- [ ] Docstrings added for public APIs
- [ ] README updated (if installation/usage changed)
- [ ] API docs updated (if endpoints added/changed)
- [ ] CHANGELOG updated (if user-facing change)

### Style
- [ ] Code follows style guide (Black, isort, Ruff for Python; Prettier, ESLint for TypeScript)
- [ ] No linting errors or warnings
- [ ] Commit messages follow Conventional Commits

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features (backward-compatible)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (backward-compatible)

### Release Checklist

1. **Update version:**
   - `backend/pyproject.toml` (version field)
   - `frontend/package.json` (version field)

2. **Update CHANGELOG.md:**
   - Add new version section with date
   - List all changes (features, fixes, breaking changes)
   - Link to PRs and issues

3. **Create a git tag:**
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

4. **GitHub Release:**
   - Create a new release on GitHub
   - Copy CHANGELOG section into release notes
   - Upload any artifacts (binaries, Docker images, etc.)

5. **Deploy to production:**
   - Follow deployment guide
   - Monitor errors and metrics
   - Send release announcement (email, blog, social media)

---

## Questions?

- **Slack/Discord:** Join #dev channel
- **Email:** dev@glasswatch.io
- **GitHub Discussions:** https://github.com/jmckinley/glasswatch/discussions

Thank you for contributing to Glasswatch! 🚀

---

**Last Updated:** 2026-04-20  
**Version:** 1.0

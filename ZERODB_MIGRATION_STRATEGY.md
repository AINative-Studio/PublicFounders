# ZeroDB Migration Strategy

**Date:** December 13, 2025
**Decision:** Replace PostgreSQL with ZeroDB for ALL database operations
**Rationale:** Single platform, semantic intelligence native, enterprise features built-in

---

## 🎯 Migration Overview

### Current Architecture (Dual-Layer)
- **Relational Layer:** PostgreSQL (9 tables)
- **Vector Layer:** ZeroDB (embeddings only)
- **Problem:** Complexity, two systems to maintain

### New Architecture (ZeroDB-Only)
- **NoSQL Tables:** Replace PostgreSQL tables
- **Vector Storage:** Continue embeddings
- **Events:** Built-in event stream
- **Files:** Built-in file storage
- **RLHF:** Built-in feedback system

---

## 📊 Migration Mapping

### Table 1: Users → ZeroDB NoSQL

**PostgreSQL Schema:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    linkedin_id VARCHAR UNIQUE,
    email VARCHAR,
    name VARCHAR,
    headline VARCHAR,
    profile_picture_url VARCHAR,
    location VARCHAR,
    phone_number VARCHAR,
    phone_verified BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**ZeroDB NoSQL Schema:**
```python
await zerodb_create_table(
    table_name="users",
    schema={
        "fields": {
            "id": "string",           # UUID as string
            "linkedin_id": "string",
            "email": "string",
            "name": "string",
            "headline": "string",
            "profile_picture_url": "string",
            "location": "string",
            "phone_number": "string",
            "phone_verified": "boolean",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["linkedin_id", "email", "id"]
    }
)
```

**Migration Code:**
```python
# Insert user
await zerodb_insert_rows(
    table_id="users",
    rows=[{
        "id": str(user_id),
        "linkedin_id": "abc123",
        "email": "founder@example.com",
        "name": "Jane Founder",
        "headline": "Building the future",
        "profile_picture_url": "https://...",
        "location": "San Francisco, CA",
        "phone_number": "+14155551234",
        "phone_verified": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }]
)

# Query user
results = await zerodb_query_rows(
    table_id="users",
    filter={"linkedin_id": "abc123"},
    limit=1
)
```

---

### Table 2: Founder Profiles → ZeroDB NoSQL

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="founder_profiles",
    schema={
        "fields": {
            "id": "string",
            "user_id": "string",
            "bio": "string",
            "current_focus": "string",
            "autonomy_mode": "string",      # suggest, confirm, auto
            "public_visibility": "boolean",
            "embedding_id": "string",       # Reference to vector
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["user_id", "id", "public_visibility"]
    }
)
```

---

### Table 3: Goals → ZeroDB NoSQL + Vectors

**ZeroDB NoSQL (Relational Data):**
```python
await zerodb_create_table(
    table_name="goals",
    schema={
        "fields": {
            "id": "string",
            "user_id": "string",
            "type": "string",           # fundraising, hiring, growth, partnerships, learning
            "description": "string",
            "priority": "integer",
            "is_active": "boolean",
            "embedding_id": "string",   # Reference to vector
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["user_id", "type", "is_active", "priority"]
    }
)
```

**ZeroDB Vectors (Semantic Data):**
```python
# Already implemented via embedding_service.py
await embedding_service.create_goal_embedding(
    goal_id=goal_id,
    user_id=user_id,
    goal_type=goal_type,
    description=description,
    priority=priority
)
```

---

### Table 4: Asks → ZeroDB NoSQL + Vectors

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="asks",
    schema={
        "fields": {
            "id": "string",
            "user_id": "string",
            "description": "string",
            "urgency": "string",        # low, medium, high
            "status": "string",         # open, in_progress, closed
            "goal_id": "string",        # Optional link
            "fulfilled_at": "datetime",
            "embedding_id": "string",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["user_id", "urgency", "status", "goal_id"]
    }
)
```

---

### Table 5: Posts → ZeroDB NoSQL + Vectors

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="posts",
    schema={
        "fields": {
            "id": "string",
            "user_id": "string",
            "type": "string",           # milestone, learning, question, update
            "content": "string",
            "visibility": "string",     # public, connections, private
            "embedding_id": "string",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["user_id", "type", "visibility", "created_at"]
    }
)
```

---

### Table 6: Companies → ZeroDB NoSQL

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="companies",
    schema={
        "fields": {
            "id": "string",
            "name": "string",
            "website": "string",
            "industry": "string",
            "stage": "string",          # idea, pre-seed, seed, series-a, etc.
            "founded_year": "integer",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["name", "industry", "stage"]
    }
)
```

---

### Table 7: Company Roles → ZeroDB NoSQL

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="company_roles",
    schema={
        "fields": {
            "id": "string",
            "user_id": "string",
            "company_id": "string",
            "role": "string",           # founder, co-founder, employee
            "is_current": "boolean",
            "start_date": "date",
            "end_date": "date",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["user_id", "company_id", "is_current"]
    }
)
```

---

### Table 8: Introductions → ZeroDB NoSQL

**ZeroDB Schema:**
```python
await zerodb_create_table(
    table_name="introductions",
    schema={
        "fields": {
            "id": "string",
            "requester_id": "string",
            "target_id": "string",
            "connector_id": "string",   # User making intro
            "status": "string",         # pending, accepted, declined, completed
            "context": "string",        # Why this intro
            "message": "string",
            "created_at": "datetime",
            "responded_at": "datetime",
            "completed_at": "datetime"
        },
        "indexes": ["requester_id", "target_id", "connector_id", "status"]
    }
)
```

---

### Table 9: Interaction Outcomes → ZeroDB RLHF System

**Use ZeroDB Built-in RLHF Instead:**
```python
# Track introduction outcome
await zerodb_rlhf_interaction(
    agent_id="introduction_matcher",
    prompt=f"Match request: {requester_goal}",
    response=f"Suggested: {target_founder}",
    feedback=1.0 if accepted else -0.5,
    context={
        "requester_id": str(requester_id),
        "target_id": str(target_id),
        "goal_type": goal_type,
        "outcome": outcome_type
    }
)
```

---

## 🔄 Migration Phases

### Phase 1: Create ZeroDB Project ✅
```python
# Already done via MCP - just need PROJECT_ID
project = await zerodb_create_project(
    project_name="publicfounders-production",
    description="PublicFounders semantic founder network"
)
# Add PROJECT_ID to .env
```

### Phase 2: Create All Tables
```python
# Create all 8 NoSQL tables
tables = [
    "users",
    "founder_profiles",
    "goals",
    "asks",
    "posts",
    "companies",
    "company_roles",
    "introductions"
]

for table in tables:
    await create_table_with_schema(table)
```

### Phase 3: Update Service Layer
**Replace SQLAlchemy with ZeroDB MCP calls:**

**Before (SQLAlchemy):**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.goal import Goal

async def create_goal(db: AsyncSession, goal_data: GoalCreate):
    goal = Goal(**goal_data.dict())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal
```

**After (ZeroDB MCP):**
```python
from app.services.zerodb_client import zerodb_client

async def create_goal(goal_data: GoalCreate):
    goal_id = str(uuid.uuid4())

    # Insert into NoSQL table
    await zerodb_client.insert_rows(
        table_id="goals",
        rows=[{
            "id": goal_id,
            "user_id": str(goal_data.user_id),
            "type": goal_data.type,
            "description": goal_data.description,
            "priority": goal_data.priority,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }]
    )

    # Create embedding (already using ZeroDB vectors)
    embedding_id = await embedding_service.create_goal_embedding(
        goal_id=UUID(goal_id),
        user_id=goal_data.user_id,
        goal_type=goal_data.type,
        description=goal_data.description,
        priority=goal_data.priority
    )

    # Update with embedding reference
    await zerodb_client.update_rows(
        table_id="goals",
        filter={"id": goal_id},
        update={"$set": {"embedding_id": embedding_id}}
    )

    return goal_id
```

### Phase 4: Update API Endpoints
**No changes needed** - endpoints use service layer

### Phase 5: Migrate Tests
```python
# Replace database fixtures with ZeroDB fixtures
@pytest.fixture
async def test_db():
    # Create test tables
    await zerodb_create_table(...)
    yield
    # Cleanup
    await zerodb_delete_table(...)
```

---

## 💡 Key Benefits

### 1. **Single Platform**
- No PostgreSQL to maintain
- No separate Redis instance
- All data in ZeroDB

### 2. **Semantic Native**
- NoSQL + Vectors in same system
- No sync issues
- Consistent queries

### 3. **Enterprise Features Built-in**
- **RLHF:** Track all interactions for learning
- **Events:** Built-in event stream for analytics
- **Files:** Store profile images, logos
- **Quantum:** Future quantum compression

### 4. **Simplified Architecture**
```
Before:
  FastAPI → PostgreSQL (relational)
         → ZeroDB (vectors)
         → Redis (caching)

After:
  FastAPI → ZeroDB (NoSQL + vectors + cache + events + files + RLHF)
```

### 5. **Cost Reduction**
- No PostgreSQL hosting
- No Redis hosting
- Single AINative bill

---

## 🛠️ Implementation Files

### Create ZeroDB Client Service
**File:** `backend/app/services/zerodb_client.py`

```python
"""
ZeroDB Client - Wrapper around ZeroDB MCP tools
Provides async methods for NoSQL operations
"""
import httpx
from typing import Any, Dict, List, Optional
from app.core.config import settings

class ZeroDBClient:
    """Client for ZeroDB NoSQL operations."""

    def __init__(self):
        self.project_id = settings.ZERODB_PROJECT_ID
        self.api_key = settings.ZERODB_API_KEY
        self.base_url = "https://api.zerodb.ai/v1"

    async def insert_rows(self, table_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Insert rows into ZeroDB table."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tables/{table_id}/rows",
                headers={
                    "X-Project-ID": self.project_id,
                    "X-API-Key": self.api_key
                },
                json={"rows": rows}
            )
            response.raise_for_status()
            return response.json()

    async def query_rows(
        self,
        table_id: str,
        filter: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query rows from ZeroDB table."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tables/{table_id}/query",
                headers={
                    "X-Project-ID": self.project_id,
                    "X-API-Key": self.api_key
                },
                json={
                    "filter": filter or {},
                    "limit": limit,
                    "offset": offset
                }
            )
            response.raise_for_status()
            return response.json().get("rows", [])

# Singleton
zerodb_client = ZeroDBClient()
```

---

## 📋 Migration Checklist

### Setup
- [x] LinkedIn credentials added to .env
- [ ] Create ZeroDB project and get PROJECT_ID
- [ ] Add PROJECT_ID to .env
- [ ] Create zerodb_client.py service

### Tables
- [ ] Create users table
- [ ] Create founder_profiles table
- [ ] Create goals table
- [ ] Create asks table
- [ ] Create posts table
- [ ] Create companies table
- [ ] Create company_roles table
- [ ] Create introductions table

### Services
- [ ] Update auth_service.py to use ZeroDB
- [ ] Update profile_service.py to use ZeroDB
- [ ] Keep embedding_service.py (already using ZeroDB vectors)
- [ ] Remove database.py (no longer needed)

### Models
- [ ] Keep models for type hints/validation (Pydantic)
- [ ] Remove SQLAlchemy Base and relationships
- [ ] Keep enums (GoalType, PostType, etc.)

### Tests
- [ ] Update test fixtures for ZeroDB
- [ ] Remove Alembic migrations
- [ ] Update conftest.py

### Deployment
- [ ] Remove PostgreSQL from infrastructure
- [ ] Remove Alembic from requirements.txt
- [ ] Update README.md
- [ ] Update ARCHITECTURE.md

---

## 🚀 Agent Tasks

### Agent 1: ZeroDB Setup & Table Creation
- Create ZeroDB project
- Create all 8 NoSQL tables
- Create zerodb_client.py service
- Update .env with PROJECT_ID

### Agent 2: Service Layer Migration
- Update auth_service.py
- Update profile_service.py
- Create new CRUD services for goals/asks/posts using ZeroDB
- Remove SQLAlchemy dependencies

### Agent 3: Test Migration
- Update test fixtures
- Update conftest.py
- Migrate all 50+ tests to use ZeroDB
- Achieve 80% coverage

---

**Status:** Ready for parallel agent execution
**Estimated Time:** 2-3 days with 3 agents
**Impact:** Simplified architecture, single platform, enterprise features

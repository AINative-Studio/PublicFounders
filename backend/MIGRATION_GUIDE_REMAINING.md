# ZeroDB Migration Guide - Remaining Endpoints

**For:** Goals, Asks, and Posts endpoints
**Pattern:** Follow the same migration approach used for auth and profile

---

## Migration Pattern (Proven)

### Step 1: Update the Service/Endpoint File

**Before (PostgreSQL/SQLAlchemy):**
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.goal import Goal

@router.post("/")
async def create_goal(
    goal_data: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = Goal(**goal_data.dict())
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal
```

**After (ZeroDB NoSQL):**
```python
from app.services.zerodb_client import zerodb_client
from uuid import uuid4
from datetime import datetime

@router.post("/")
async def create_goal(
    goal_data: GoalCreate,
    current_user: dict = Depends(get_current_user)  # Now returns dict
):
    goal_dict = zerodb_client.prepare_insert_data(
        data={
            "user_id": current_user["id"],
            "type": goal_data.type,
            "description": goal_data.description,
            "priority": goal_data.priority,
            "is_active": True
        }
    )

    await zerodb_client.insert_rows(
        table_name="goals",
        rows=[goal_dict]
    )

    return goal_dict
```

---

## Endpoint-Specific Migration Instructions

### 1. Goals Endpoint (`app/api/v1/endpoints/goals.py`)

**Tables Used:** `goals`

**Operations to Migrate:**

1. **Create Goal:**
```python
goal_dict = zerodb_client.prepare_insert_data({
    "user_id": str(user_id),
    "type": goal_data.type,
    "description": goal_data.description,
    "priority": goal_data.priority,
    "is_active": True
})
await zerodb_client.insert_rows("goals", [goal_dict])
```

2. **List Goals:**
```python
goals = await zerodb_client.query_rows(
    table_name="goals",
    filter={"user_id": str(user_id), "is_active": True},
    limit=limit,
    offset=offset,
    sort={"priority": -1}  # Descending
)
```

3. **Update Goal:**
```python
await zerodb_client.update_rows(
    table_name="goals",
    filter={"id": str(goal_id), "user_id": str(user_id)},
    update=zerodb_client.prepare_update_data({
        "description": goal_data.description,
        "priority": goal_data.priority
    })
)
```

4. **Delete Goal (Soft):**
```python
await zerodb_client.update_rows(
    table_name="goals",
    filter={"id": str(goal_id)},
    update={"$set": {"is_active": False, "updated_at": datetime.utcnow().isoformat()}}
)
```

5. **Delete Goal (Hard):**
```python
await zerodb_client.delete_rows(
    table_name="goals",
    filter={"id": str(goal_id)}
)
```

---

### 2. Asks Endpoint (`app/api/v1/endpoints/asks.py`)

**Tables Used:** `asks`

**Operations to Migrate:**

1. **Create Ask:**
```python
ask_dict = zerodb_client.prepare_insert_data({
    "user_id": str(user_id),
    "description": ask_data.description,
    "urgency": ask_data.urgency,
    "status": "open",
    "goal_id": str(ask_data.goal_id) if ask_data.goal_id else None
})
await zerodb_client.insert_rows("asks", [ask_dict])
```

2. **List Asks:**
```python
# All asks
asks = await zerodb_client.query_rows(
    table_name="asks",
    filter={"user_id": str(user_id)},
    limit=limit,
    offset=offset
)

# Filter by status
asks = await zerodb_client.query_rows(
    table_name="asks",
    filter={"user_id": str(user_id), "status": "open"},
    limit=limit
)

# Filter by urgency
asks = await zerodb_client.query_rows(
    table_name="asks",
    filter={"urgency": "high"},
    limit=limit
)
```

3. **Update Ask Status:**
```python
await zerodb_client.update_rows(
    table_name="asks",
    filter={"id": str(ask_id)},
    update={"$set": {
        "status": "in_progress",
        "updated_at": datetime.utcnow().isoformat()
    }}
)
```

4. **Mark Ask as Fulfilled:**
```python
await zerodb_client.update_rows(
    table_name="asks",
    filter={"id": str(ask_id)},
    update={"$set": {
        "status": "closed",
        "fulfilled_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }}
)
```

---

### 3. Posts Endpoint (`app/api/v1/endpoints/posts.py`)

**Tables Used:** `posts`

**Operations to Migrate:**

1. **Create Post:**
```python
post_dict = zerodb_client.prepare_insert_data({
    "user_id": str(user_id),
    "type": post_data.type,  # milestone, learning, question, update
    "content": post_data.content,
    "visibility": post_data.visibility  # public, connections, private
})
await zerodb_client.insert_rows("posts", [post_dict])
```

2. **List Posts (Feed):**
```python
# Public posts
posts = await zerodb_client.query_rows(
    table_name="posts",
    filter={"visibility": "public"},
    limit=limit,
    offset=offset,
    sort={"created_at": -1}  # Most recent first
)

# User's posts
posts = await zerodb_client.query_rows(
    table_name="posts",
    filter={"user_id": str(user_id)},
    limit=limit,
    sort={"created_at": -1}
)
```

3. **Update Post:**
```python
await zerodb_client.update_rows(
    table_name="posts",
    filter={"id": str(post_id), "user_id": str(user_id)},
    update=zerodb_client.prepare_update_data({
        "content": post_data.content,
        "visibility": post_data.visibility
    })
)
```

4. **Delete Post:**
```python
await zerodb_client.delete_rows(
    table_name="posts",
    filter={"id": str(post_id), "user_id": str(user_id)}
)
```

---

## Common Patterns

### 1. Remove Database Session Dependencies

**Find:**
```python
async def endpoint(
    db: AsyncSession = Depends(get_db)
):
```

**Replace:**
```python
async def endpoint(
    # No db parameter
):
```

### 2. Update User Authentication

**Find:**
```python
current_user: User = Depends(get_current_user)
user_id = current_user.id
```

**Replace:**
```python
current_user: dict = Depends(get_current_user)
user_id = current_user["id"]
```

### 3. Remove SQLAlchemy Imports

**Remove:**
```python
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.goal import Goal
```

**Add:**
```python
from app.services.zerodb_client import zerodb_client
from datetime import datetime
from uuid import uuid4
```

### 4. Convert ORM Operations to NoSQL

**ORM Query:**
```python
stmt = select(Goal).where(Goal.user_id == user_id, Goal.is_active == True)
result = await db.execute(stmt)
goals = result.scalars().all()
```

**NoSQL Query:**
```python
goals = await zerodb_client.query_rows(
    table_name="goals",
    filter={"user_id": str(user_id), "is_active": True}
)
```

### 5. Handle Relationships

**Before (SQLAlchemy Relationships):**
```python
goal = await db.get(Goal, goal_id)
user = goal.user  # Lazy loaded
```

**After (Manual Joins):**
```python
goal = await zerodb_client.get_by_id("goals", str(goal_id))
user = await zerodb_client.get_by_id("users", goal["user_id"])
```

---

## Testing Changes

### Update Test Fixtures

**Before:**
```python
@pytest.fixture
async def test_goal(db: AsyncSession, test_user: User):
    goal = Goal(
        user_id=test_user.id,
        type="fundraising",
        description="Raise seed round"
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal
```

**After:**
```python
@pytest.fixture
async def test_goal(test_user: dict):
    goal_data = zerodb_client.prepare_insert_data({
        "user_id": test_user["id"],
        "type": "fundraising",
        "description": "Raise seed round",
        "priority": 5,
        "is_active": True
    })
    await zerodb_client.insert_rows("goals", [goal_data])
    return goal_data
```

### Update Assertions

**Before:**
```python
assert isinstance(goal, Goal)
assert goal.user_id == user.id
```

**After:**
```python
assert isinstance(goal, dict)
assert goal["user_id"] == user["id"]
```

---

## Validation Checklist

For each migrated endpoint, verify:

- [ ] No SQLAlchemy imports remain
- [ ] No `Depends(get_db)` in function signatures
- [ ] All queries use `zerodb_client`
- [ ] All UUIDs converted to strings
- [ ] All timestamps use ISO format strings
- [ ] All responses return dicts (not ORM objects)
- [ ] Pydantic schemas still validate input/output
- [ ] Tests updated to use dicts instead of ORM objects

---

## Example: Complete Endpoint Migration

**File:** `app/api/v1/endpoints/goals.py`

```python
"""
Goals API Endpoints - ZeroDB Edition
"""
from typing import List
from uuid import uuid4
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends

from app.services.zerodb_client import zerodb_client
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from app.api.dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new goal"""
    goal_dict = zerodb_client.prepare_insert_data({
        "user_id": current_user["id"],
        "type": goal_data.type,
        "description": goal_data.description,
        "priority": goal_data.priority,
        "is_active": True,
        "embedding_id": None
    })

    await zerodb_client.insert_rows("goals", [goal_dict])

    # TODO: Generate embedding asynchronously
    # await embedding_service.create_goal_embedding(goal_dict)

    return goal_dict


@router.get("/", response_model=List[GoalResponse])
async def list_goals(
    current_user: dict = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0,
    is_active: bool = True
):
    """List user's goals"""
    goals = await zerodb_client.query_rows(
        table_name="goals",
        filter={
            "user_id": current_user["id"],
            "is_active": is_active
        },
        limit=limit,
        offset=offset,
        sort={"priority": -1}
    )
    return goals


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific goal"""
    goal = await zerodb_client.get_by_id("goals", goal_id)

    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    if goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this goal"
        )

    return goal


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    goal_data: GoalUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a goal"""
    # Verify ownership
    goal = await zerodb_client.get_by_id("goals", goal_id)
    if not goal or goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    # Update fields
    update_dict = goal_data.model_dump(exclude_unset=True)

    await zerodb_client.update_rows(
        table_name="goals",
        filter={"id": goal_id},
        update=zerodb_client.prepare_update_data(update_dict)
    )

    # Fetch updated goal
    updated_goal = await zerodb_client.get_by_id("goals", goal_id)
    return updated_goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a goal (soft delete)"""
    goal = await zerodb_client.get_by_id("goals", goal_id)
    if not goal or goal["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )

    await zerodb_client.update_rows(
        table_name="goals",
        filter={"id": goal_id},
        update={"$set": {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
```

---

## Quick Command Reference

### ZeroDB Client Operations

```python
# INSERT
await zerodb_client.insert_rows("table_name", [row_dict])

# QUERY
rows = await zerodb_client.query_rows(
    table_name="table_name",
    filter={"field": "value"},
    limit=10,
    offset=0,
    sort={"field": -1}
)

# UPDATE
await zerodb_client.update_rows(
    table_name="table_name",
    filter={"id": "uuid"},
    update={"$set": {"field": "value"}}
)

# DELETE
await zerodb_client.delete_rows(
    table_name="table_name",
    filter={"id": "uuid"}
)

# GET BY ID
row = await zerodb_client.get_by_id("table_name", "uuid")

# GET BY FIELD
row = await zerodb_client.get_by_field("table_name", "field", "value")
```

---

## Next Steps

1. Migrate `app/api/v1/endpoints/goals.py` using this pattern
2. Migrate `app/api/v1/endpoints/asks.py` using this pattern
3. Migrate `app/api/v1/endpoints/posts.py` using this pattern
4. Update tests for each endpoint
5. Run full test suite
6. Document any edge cases or issues

**Time Estimate:** 2-3 hours per endpoint (including tests)

---

**This guide provides everything needed to complete the ZeroDB migration!**

# Sprint 2 API Endpoints Reference

Quick reference guide for Goals, Asks, and Posts endpoints.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require JWT Bearer token:
```
Authorization: Bearer {your_jwt_token}
```

---

## Goals Endpoints

### Create Goal
```http
POST /goals
Content-Type: application/json

{
  "type": "fundraising" | "hiring" | "growth" | "partnerships" | "learning",
  "description": "string (10-2000 chars)",
  "priority": 1-10,
  "is_active": true
}

→ 201 Created
{
  "id": "uuid",
  "user_id": "uuid",
  "type": "fundraising",
  "description": "Raise $2M seed round",
  "priority": 10,
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### List Goals
```http
GET /goals?page=1&page_size=20&is_active=true&goal_type=fundraising

→ 200 OK
{
  "goals": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

**Query Parameters:**
- `page` (default: 1) - Page number
- `page_size` (default: 20, max: 100) - Items per page
- `is_active` (optional) - Filter by active status
- `goal_type` (optional) - Filter by type

### Get Goal
```http
GET /goals/{goal_id}

→ 200 OK
→ 404 Not Found
```

### Update Goal
```http
PUT /goals/{goal_id}
Content-Type: application/json

{
  "description": "Updated description",
  "priority": 5,
  "is_active": false
}

→ 200 OK
```

### Delete Goal
```http
DELETE /goals/{goal_id}

→ 204 No Content
→ 404 Not Found
```

---

## Asks Endpoints

### Create Ask
```http
POST /asks
Content-Type: application/json

{
  "description": "string (10-2000 chars)",
  "urgency": "low" | "medium" | "high",
  "goal_id": "uuid" (optional)
}

→ 201 Created
{
  "id": "uuid",
  "user_id": "uuid",
  "goal_id": "uuid",
  "description": "Need warm intros to VCs",
  "urgency": "high",
  "status": "open",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "fulfilled_at": null
}
```

### List Asks
```http
GET /asks?page=1&page_size=20&mine_only=true&status_filter=open&urgency_filter=high

→ 200 OK
{
  "asks": [...],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

**Query Parameters:**
- `page` (default: 1) - Page number
- `page_size` (default: 20, max: 100) - Items per page
- `mine_only` (default: true) - Show only my asks
- `status_filter` (optional) - Filter by status (open/fulfilled/closed)
- `urgency_filter` (optional) - Filter by urgency (low/medium/high)
- `goal_id` (optional) - Filter by linked goal

### Get Ask
```http
GET /asks/{ask_id}

→ 200 OK
→ 404 Not Found
```

### Update Ask
```http
PUT /asks/{ask_id}
Content-Type: application/json

{
  "description": "Updated description",
  "urgency": "low",
  "goal_id": "new-goal-uuid"
}

→ 200 OK
```

### Update Ask Status
```http
PATCH /asks/{ask_id}/status
Content-Type: application/json

{
  "status": "fulfilled" | "closed" | "open"
}

→ 200 OK
```

### Delete Ask
```http
DELETE /asks/{ask_id}

→ 204 No Content
→ 404 Not Found
```

---

## Posts Endpoints

### Create Post
```http
POST /posts
Content-Type: application/json

{
  "type": "progress" | "learning" | "milestone" | "ask",
  "content": "string (10-5000 chars)",
  "is_cross_posted": false
}

→ 201 Created
{
  "id": "uuid",
  "user_id": "uuid",
  "type": "milestone",
  "content": "Just closed our first customer!",
  "is_cross_posted": true,
  "embedding_status": "pending",
  "embedding_created_at": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Note:** Embedding created asynchronously. Check `embedding_status`:
- `pending` - Queued for embedding
- `processing` - Embedding in progress
- `completed` - Embedding created successfully
- `failed` - Embedding creation failed (see `embedding_error`)

### List Posts (Chronological)
```http
GET /posts?page=1&page_size=20&user_id={uuid}&post_type=milestone

→ 200 OK
{
  "posts": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

**Query Parameters:**
- `page` (default: 1) - Page number
- `page_size` (default: 20, max: 100) - Items per page
- `user_id` (optional) - Filter by user
- `post_type` (optional) - Filter by type

### Discover Posts (Semantic)
```http
GET /posts/discover?limit=20&min_similarity=0.7&recency_weight=0.3

→ 200 OK
{
  "posts": [
    {
      "id": "uuid",
      "type": "milestone",
      "content": "Just raised our seed round!",
      ...
    },
    ...
  ],
  "similarity_scores": [0.95, 0.87, 0.82, ...],
  "total": 15
}
```

**Query Parameters:**
- `limit` (default: 20, max: 100) - Number of posts to return
- `min_similarity` (default: 0.7, range: 0-1) - Minimum similarity threshold
- `recency_weight` (default: 0.3, range: 0-1) - Weight for recency in ranking

**Algorithm:**
```
combined_score = similarity × (1 - recency_weight) + recency × recency_weight
```

**How it works:**
1. Fetches your active goals
2. Combines goal descriptions as query
3. Searches post embeddings semantically
4. Ranks by similarity + recency
5. Returns top N posts with scores

### Get Post
```http
GET /posts/{post_id}

→ 200 OK
→ 404 Not Found
```

### Update Post
```http
PUT /posts/{post_id}
Content-Type: application/json

{
  "content": "Updated content",
  "is_cross_posted": true
}

→ 200 OK
```

**Note:** Content updates trigger async embedding regeneration.

### Delete Post
```http
DELETE /posts/{post_id}

→ 204 No Content
→ 404 Not Found
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Goal does not belong to you"
}
```

### 404 Not Found
```json
{
  "detail": "Goal {id} not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "ensure this value has at least 10 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### 503 Service Unavailable
```json
{
  "detail": "Semantic search temporarily unavailable"
}
```

---

## Example Workflows

### Create a Fundraising Goal with Ask
```bash
# 1. Create goal
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "fundraising",
    "description": "Raise $2M seed round by Q2 2025",
    "priority": 10
  }'
# → Returns goal with id: goal-uuid

# 2. Create ask linked to goal
curl -X POST http://localhost:8000/api/v1/asks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Need warm intros to tier 1 VCs in fintech space",
    "urgency": "high",
    "goal_id": "goal-uuid"
  }'
```

### Post Progress and Discover Similar Posts
```bash
# 1. Post your update
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "milestone",
    "content": "Just closed our first enterprise customer! $50k ARR. This validates our B2B SaaS pricing model.",
    "is_cross_posted": true
  }'

# 2. Discover relevant posts from others
curl -X GET "http://localhost:8000/api/v1/posts/discover?limit=10&recency_weight=0.3" \
  -H "Authorization: Bearer $TOKEN"
```

### Mark Ask as Fulfilled
```bash
# 1. Create ask
curl -X POST http://localhost:8000/api/v1/asks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Looking for beta testers for our MVP",
    "urgency": "medium"
  }'
# → Returns ask with id: ask-uuid

# 2. Later, mark as fulfilled
curl -X PATCH http://localhost:8000/api/v1/asks/ask-uuid/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "fulfilled"
  }'
# → fulfilled_at timestamp is automatically set
```

---

## Testing Endpoints

### Using HTTPie
```bash
# Create goal
http POST localhost:8000/api/v1/goals \
  Authorization:"Bearer $TOKEN" \
  type=fundraising \
  description="Raise $2M seed round" \
  priority:=10

# List goals
http GET localhost:8000/api/v1/goals \
  Authorization:"Bearer $TOKEN" \
  page==1 \
  page_size==20

# Discover posts
http GET "localhost:8000/api/v1/posts/discover?limit=10" \
  Authorization:"Bearer $TOKEN"
```

### Using Python Requests
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "your-jwt-token"
headers = {"Authorization": f"Bearer {TOKEN}"}

# Create goal
goal_data = {
    "type": "fundraising",
    "description": "Raise $2M seed round",
    "priority": 10
}
response = requests.post(f"{BASE_URL}/goals", json=goal_data, headers=headers)
goal = response.json()

# Discover posts
params = {"limit": 10, "recency_weight": 0.3}
response = requests.get(f"{BASE_URL}/posts/discover", params=params, headers=headers)
posts = response.json()
```

---

## Rate Limits & Performance

### Expected Response Times
- **Create Goal/Ask:** <200ms (includes sync embedding)
- **Create Post:** <50ms (async embedding)
- **List Endpoints:** <100ms
- **Discover Feed:** <500ms

### Embedding Status
- **Goals/Asks:** Synchronous (embedding created before response)
- **Posts:** Asynchronous (embedding created in background)

### Pagination Limits
- Default: 20 items
- Maximum: 100 items per page

---

## OpenAPI/Swagger Documentation

Interactive API documentation available at:
```
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

---

**Last Updated:** December 13, 2025
**Sprint:** Sprint 2

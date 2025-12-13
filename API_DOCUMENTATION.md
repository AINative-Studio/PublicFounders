# PublicFounders API Documentation

Complete API reference for the PublicFounders semantic founder network platform.

**Base URL**: `https://api.publicfounders.com/api/v1` (or `http://localhost:8000/api/v1` for development)

**Version**: 1.0
**Last Updated**: December 2025

---

## Table of Contents

1. [Authentication](#authentication)
2. [Profile Management](#profile-management)
3. [Goals](#goals)
4. [Asks](#asks)
5. [Posts](#posts)
6. [Semantic Search](#semantic-search)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

All authenticated endpoints require a JWT Bearer token in the `Authorization` header:

```http
Authorization: Bearer <your_jwt_token>
```

### LinkedIn OAuth Flow

#### 1. Initiate OAuth

```http
GET /api/v1/auth/linkedin/initiate
```

**Description**: Redirects user to LinkedIn authorization page.

**Response**: `302 Redirect` to LinkedIn OAuth page

**Example**:
```bash
curl -X GET https://api.publicfounders.com/api/v1/auth/linkedin/initiate
```

---

#### 2. OAuth Callback

```http
GET /api/v1/auth/linkedin/callback?code={authorization_code}
```

**Description**: Handles LinkedIn OAuth callback and creates/authenticates user.

**Query Parameters**:
- `code` (required): Authorization code from LinkedIn

**Response**: `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "founder@example.com",
    "name": "Jane Founder",
    "linkedin_id": "linkedin-user-123",
    "created_at": "2025-12-13T10:00:00Z"
  },
  "profile": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "bio": null,
    "current_focus": null,
    "autonomy_mode": "suggest",
    "created_at": "2025-12-13T10:00:00Z"
  },
  "is_new_user": true
}
```

**Errors**:
- `400 Bad Request`: Missing authorization code
- `500 Internal Server Error`: LinkedIn OAuth not configured or token exchange failed

---

### Phone Verification (Optional)

#### Request Verification Code

```http
POST /api/v1/auth/phone/request-verification
```

**Description**: Request SMS verification code for phone number.

**Request Body**:
```json
{
  "phone": "+1234567890"
}
```

**Response**: `200 OK`

```json
{
  "message": "Verification code sent",
  "verification_id": "verify-123",
  "expires_at": "2025-12-13T10:15:00Z"
}
```

---

#### Confirm Verification Code

```http
POST /api/v1/auth/phone/confirm-verification
```

**Description**: Confirm phone number with verification code.

**Request Body**:
```json
{
  "verification_id": "verify-123",
  "code": "123456"
}
```

**Response**: `200 OK`

```json
{
  "verified": true,
  "phone": "+1234567890"
}
```

**Errors**:
- `400 Bad Request`: Invalid or expired verification code
- `404 Not Found`: Verification ID not found

---

## Profile Management

### Get Current User Profile

```http
GET /api/v1/profile/me
```

**Description**: Get the authenticated user's profile.

**Headers**:
```http
Authorization: Bearer <token>
```

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "bio": "Serial entrepreneur passionate about AI and sustainability",
  "current_focus": "Building AI-powered climate solutions",
  "location": "San Francisco, CA",
  "website": "https://example.com",
  "autonomy_mode": "suggest",
  "public_visibility": true,
  "intro_preferences": {
    "channels": ["linkedin", "email"],
    "availability": "open"
  },
  "embedding_id": "emb-123",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T10:00:00Z"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or missing token
- `404 Not Found`: Profile not found

---

### Update Profile

```http
PATCH /api/v1/profile/me
```

**Description**: Update the authenticated user's profile. Automatically generates new embeddings for semantic search.

**Headers**:
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body** (all fields optional):
```json
{
  "bio": "Updated bio with new information",
  "current_focus": "Raising Series A for AI startup",
  "location": "New York, NY",
  "website": "https://newsite.com",
  "autonomy_mode": "auto",
  "public_visibility": true,
  "intro_preferences": {
    "channels": ["linkedin", "email", "twitter"],
    "availability": "selective"
  }
}
```

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "bio": "Updated bio with new information",
  "current_focus": "Raising Series A for AI startup",
  "location": "New York, NY",
  "website": "https://newsite.com",
  "autonomy_mode": "auto",
  "public_visibility": true,
  "intro_preferences": {
    "channels": ["linkedin", "email", "twitter"],
    "availability": "selective"
  },
  "embedding_id": "emb-456",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T12:00:00Z"
}
```

**Autonomy Modes**:
- `suggest`: Agent suggests introductions, user must approve each one
- `approve`: Agent makes introductions, user has 24h to veto
- `auto`: Agent makes introductions automatically with full autonomy

**Errors**:
- `401 Unauthorized`: Invalid or missing token
- `422 Unprocessable Entity`: Validation error (e.g., invalid autonomy_mode)

---

### Get Public Profiles

```http
GET /api/v1/profile/public
```

**Description**: Get paginated list of public founder profiles.

**Query Parameters**:
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response**: `200 OK`

```json
{
  "profiles": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "bio": "Serial entrepreneur passionate about AI",
      "current_focus": "Building AI solutions",
      "location": "San Francisco, CA",
      "website": "https://example.com",
      "created_at": "2025-12-13T10:00:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

---

### Get Profile by ID

```http
GET /api/v1/profile/{user_id}
```

**Description**: Get a specific user's public profile.

**Path Parameters**:
- `user_id`: UUID of the user

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "bio": "Serial entrepreneur passionate about AI",
  "current_focus": "Building AI solutions",
  "location": "San Francisco, CA",
  "website": "https://example.com",
  "created_at": "2025-12-13T10:00:00Z"
}
```

**Errors**:
- `404 Not Found`: User not found or profile is private

---

## Goals

### Create Goal

```http
POST /api/v1/goals
```

**Description**: Create a new goal. Automatically generates semantic embeddings for intelligent matching.

**Headers**:
```http
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "type": "fundraising",
  "description": "Raise $2M seed round for AI-powered climate tech startup",
  "priority": 8,
  "is_active": true,
  "target_date": "2026-06-01T00:00:00Z"
}
```

**Goal Types**:
- `fundraising`: Seeking investment
- `hiring`: Looking for team members
- `partnerships`: Strategic partnerships
- `customers`: Customer acquisition
- `advisors`: Seeking mentorship/advice
- `learning`: Skill development
- `other`: Other objectives

**Response**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "fundraising",
  "description": "Raise $2M seed round for AI-powered climate tech startup",
  "priority": 8,
  "is_active": true,
  "target_date": "2026-06-01T00:00:00Z",
  "embedding_id": "emb-goal-123",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T10:00:00Z"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or missing token
- `422 Unprocessable Entity`: Validation error

---

### List Goals

```http
GET /api/v1/goals
```

**Description**: Get the authenticated user's goals.

**Query Parameters**:
- `is_active` (optional): Filter by active status (true/false)
- `type` (optional): Filter by goal type
- `limit` (optional): Number of results (default: 20)
- `offset` (optional): Pagination offset

**Response**: `200 OK`

```json
{
  "goals": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "fundraising",
      "description": "Raise $2M seed round",
      "priority": 8,
      "is_active": true,
      "embedding_id": "emb-goal-123",
      "created_at": "2025-12-13T10:00:00Z"
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

### Update Goal

```http
PATCH /api/v1/goals/{goal_id}
```

**Description**: Update a goal. Re-generates embeddings if description changes.

**Request Body** (all fields optional):
```json
{
  "description": "Updated goal description",
  "priority": 9,
  "is_active": false
}
```

**Response**: `200 OK`

---

### Delete Goal

```http
DELETE /api/v1/goals/{goal_id}
```

**Description**: Delete a goal and its embeddings.

**Response**: `204 No Content`

**Errors**:
- `403 Forbidden`: Not authorized to delete this goal
- `404 Not Found`: Goal not found

---

## Asks

### Create Ask

```http
POST /api/v1/asks
```

**Description**: Create a help request. Automatically generates embeddings for semantic matching.

**Request Body**:
```json
{
  "goal_id": "550e8400-e29b-41d4-a716-446655440002",
  "description": "Looking for intros to seed-stage climate tech investors",
  "urgency": 8,
  "status": "open",
  "tags": ["fundraising", "climate", "seed"]
}
```

**Response**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal_id": "550e8400-e29b-41d4-a716-446655440002",
  "description": "Looking for intros to seed-stage climate tech investors",
  "urgency": 8,
  "status": "open",
  "tags": ["fundraising", "climate", "seed"],
  "embedding_id": "emb-ask-123",
  "created_at": "2025-12-13T10:00:00Z"
}
```

**Ask Statuses**:
- `open`: Actively seeking help
- `in_progress`: Someone is helping
- `fulfilled`: Request completed
- `closed`: No longer needed

---

### List Asks

```http
GET /api/v1/asks
```

**Description**: Get the authenticated user's asks.

**Query Parameters**:
- `status` (optional): Filter by status
- `goal_id` (optional): Filter by goal
- `limit` (optional): Number of results
- `offset` (optional): Pagination offset

**Response**: `200 OK`

---

### Update Ask Status

```http
PATCH /api/v1/asks/{ask_id}
```

**Request Body**:
```json
{
  "status": "fulfilled"
}
```

**Response**: `200 OK`

---

## Posts

### Create Post

```http
POST /api/v1/posts
```

**Description**: Create a build-in-public post. Generates embeddings for content discovery.

**Request Body**:
```json
{
  "type": "update",
  "title": "Launching our MVP next week!",
  "content": "After 3 months of development, we're launching our AI climate platform...",
  "tags": ["launch", "mvp", "climate"],
  "is_public": true,
  "cross_post_linkedin": false
}
```

**Post Types**:
- `update`: General update
- `milestone`: Achievement or milestone
- `learning`: Lesson learned
- `ask`: Public ask for help
- `offer`: Offering help/resources

**Response**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "update",
  "title": "Launching our MVP next week!",
  "content": "After 3 months of development...",
  "tags": ["launch", "mvp", "climate"],
  "is_public": true,
  "embedding_id": "emb-post-123",
  "view_count": 0,
  "created_at": "2025-12-13T10:00:00Z"
}
```

---

### Get Feed

```http
GET /api/v1/posts/feed
```

**Description**: Get personalized feed of posts using semantic matching.

**Query Parameters**:
- `limit` (optional): Number of posts (default: 20, max: 100)
- `offset` (optional): Pagination offset
- `type` (optional): Filter by post type

**Response**: `200 OK`

```json
{
  "posts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440004",
      "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Jane Founder",
        "bio": "Serial entrepreneur..."
      },
      "type": "update",
      "title": "Launching our MVP!",
      "content": "After 3 months...",
      "tags": ["launch", "mvp"],
      "view_count": 127,
      "created_at": "2025-12-13T10:00:00Z",
      "relevance_score": 0.87
    }
  ],
  "total": 450,
  "limit": 20,
  "offset": 0
}
```

**Note**: Posts are ranked by semantic relevance to your profile and goals.

---

## Semantic Search

### Search Founders

```http
GET /api/v1/search/founders
```

**Description**: Semantic search for founders based on natural language query.

**Query Parameters**:
- `q` (required): Search query
- `limit` (optional): Number of results (default: 10, max: 50)
- `threshold` (optional): Minimum similarity score (0.0-1.0, default: 0.7)

**Example**:
```bash
curl -X GET "https://api.publicfounders.com/api/v1/search/founders?q=climate%20tech%20founders%20raising%20seed&limit=5" \
  -H "Authorization: Bearer <token>"
```

**Response**: `200 OK`

```json
{
  "results": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Jane Founder",
      "bio": "Building AI-powered climate solutions",
      "current_focus": "Raising seed round",
      "similarity_score": 0.92,
      "matched_fields": ["bio", "current_focus"]
    }
  ],
  "query": "climate tech founders raising seed",
  "total": 15,
  "threshold": 0.7
}
```

---

### Search Goals

```http
GET /api/v1/search/goals
```

**Description**: Find goals similar to your query for potential collaboration.

**Query Parameters**:
- `q` (required): Search query
- `limit` (optional): Number of results
- `threshold` (optional): Minimum similarity

**Response**: `200 OK`

```json
{
  "results": [
    {
      "goal_id": "550e8400-e29b-41d4-a716-446655440002",
      "type": "fundraising",
      "description": "Raise $2M seed for climate tech",
      "user": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Jane Founder"
      },
      "similarity_score": 0.88
    }
  ]
}
```

---

### Search Posts

```http
GET /api/v1/search/posts
```

**Description**: Semantic search through build-in-public posts.

**Response**: Similar to Search Founders

---

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "detail": "Human-readable error message",
  "type": "error_type",
  "code": "ERROR_CODE",
  "timestamp": "2025-12-13T10:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | OK | Successful GET/PATCH |
| `201` | Created | Successful POST |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid request data |
| `401` | Unauthorized | Missing or invalid token |
| `403` | Forbidden | No permission for resource |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error |

### Common Error Examples

#### Invalid Token
```json
{
  "detail": "Invalid or expired token",
  "type": "authentication_error"
}
```

#### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "priority"],
      "msg": "value must be between 1 and 10",
      "type": "value_error"
    }
  ],
  "type": "validation_error"
}
```

#### Not Found
```json
{
  "detail": "Goal not found",
  "type": "not_found_error"
}
```

---

## Rate Limiting

### Default Limits

- **Authenticated requests**: 1000 requests/hour
- **Public endpoints**: 100 requests/hour
- **Search endpoints**: 50 requests/hour
- **Embedding generation**: 20 requests/minute

### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1702467600
```

### Exceeded Rate Limit

```http
HTTP/1.1 429 Too Many Requests
```

```json
{
  "detail": "Rate limit exceeded. Try again in 45 minutes.",
  "retry_after": 2700
}
```

---

## Caching

### Built-in Caching

ZeroDB provides automatic caching for:
- User profiles (5 minutes)
- Goal embeddings (15 minutes)
- Search results (10 minutes)

### Cache Control Headers

```http
Cache-Control: public, max-age=300
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
```

---

## Webhook Events (Future)

Coming soon: Real-time webhooks for:
- New introduction suggestions
- Goal matches found
- Ask fulfillment offers
- Post engagement

---

## SDKs & Tools

### Official SDKs
- Python SDK (coming soon)
- JavaScript/TypeScript SDK (planned)

### API Testing
- **Interactive Docs**: `https://api.publicfounders.com/api/docs`
- **Postman Collection**: Available in repository
- **OpenAPI Spec**: `https://api.publicfounders.com/openapi.json`

---

## Support

- **API Issues**: https://github.com/AINative-Studio/PublicFounders/issues
- **Email**: api-support@ainative.studio
- **Status Page**: https://status.publicfounders.com

---

**Document Version**: 1.0
**Last Updated**: December 2025
**API Version**: v1

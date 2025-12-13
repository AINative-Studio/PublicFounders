# Sprint 1 API Examples

Sample API requests and responses for testing Sprint 1 endpoints.

## Authentication Flow

### 1. LinkedIn OAuth Sign-Up

**Step 1: Initiate OAuth**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/linkedin/initiate"
```

**Response**:
```
HTTP/1.1 307 Temporary Redirect
Location: https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=...
```

**Step 2: OAuth Callback** (after LinkedIn redirects)
```bash
curl -X GET "http://localhost:8000/api/v1/auth/linkedin/callback?code=AUTHORIZATION_CODE"
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibGlua2VkaW5faWQiOiJsaW5rZWRpbl8xMjM0NSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6MTcwNDEwMjQwMCwiaWF0IjoxNzAzNDk3NjAwfQ.SIGNATURE",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "linkedin_id": "linkedin_12345",
    "name": "John Doe",
    "headline": "Founder & CEO at TechStartup",
    "profile_photo_url": "https://media.licdn.com/dms/image/abc123",
    "location": "San Francisco, CA",
    "email": "john.doe@example.com",
    "phone_number": null,
    "phone_verified": false,
    "is_active": true,
    "created_at": "2025-12-13T10:00:00Z",
    "updated_at": "2025-12-13T10:00:00Z",
    "last_login_at": "2025-12-13T10:00:00Z"
  },
  "created": true
}
```

---

## Phone Verification

### Send Verification Code

```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-phone?user_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234"
  }'
```

**Response**:
```json
{
  "message": "Verification code sent successfully",
  "phone_number": "+14155551234",
  "expires_in_minutes": 5
}
```

### Confirm Verification Code

```bash
curl -X POST "http://localhost:8000/api/v1/auth/confirm-phone?user_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234",
    "verification_code": "123456"
  }'
```

**Success Response**:
```json
{
  "message": "Phone verified successfully",
  "phone_number": "+14155551234",
  "verified": true
}
```

**Error Response** (invalid code):
```json
{
  "detail": "Invalid or expired verification code"
}
```

---

## Profile Management

### Get Current User Profile

```bash
curl -X GET "http://localhost:8000/api/v1/profile/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response**:
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "linkedin_id": "linkedin_12345",
    "name": "John Doe",
    "headline": "Founder & CEO at TechStartup",
    "profile_photo_url": "https://media.licdn.com/dms/image/abc123",
    "location": "San Francisco, CA",
    "email": "john.doe@example.com",
    "phone_number": "+14155551234",
    "phone_verified": true,
    "is_active": true,
    "created_at": "2025-12-13T10:00:00Z",
    "updated_at": "2025-12-13T10:05:00Z",
    "last_login_at": "2025-12-13T10:00:00Z"
  },
  "profile": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "bio": "Building the future of AI-powered networking for founders. 5+ years in B2B SaaS.",
    "current_focus": "Raising seed round for our semantic networking platform",
    "autonomy_mode": "suggest",
    "public_visibility": true,
    "embedding_id": "vec_550e8400-e29b-41d4-a716-446655440000",
    "embedding_updated_at": "2025-12-13T10:05:00Z",
    "created_at": "2025-12-13T10:00:00Z",
    "updated_at": "2025-12-13T10:05:00Z"
  }
}
```

### Update Profile

```bash
curl -X PUT "http://localhost:8000/api/v1/profile/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Passionate founder building AI tools for the founder community. Previously scaled two B2B SaaS companies to Series A.",
    "current_focus": "Scaling to 1,000 active founders while maintaining product quality",
    "autonomy_mode": "approve",
    "public_visibility": true
  }'
```

**Response**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "bio": "Passionate founder building AI tools for the founder community. Previously scaled two B2B SaaS companies to Series A.",
  "current_focus": "Scaling to 1,000 active founders while maintaining product quality",
  "autonomy_mode": "approve",
  "public_visibility": true,
  "embedding_id": "vec_550e8400-e29b-41d4-a716-446655440000",
  "embedding_updated_at": "2025-12-13T10:10:00Z",
  "created_at": "2025-12-13T10:00:00Z",
  "updated_at": "2025-12-13T10:10:00Z"
}
```

### Get Another User's Profile (Public)

```bash
curl -X GET "http://localhost:8000/api/v1/profile/660e8400-e29b-41d4-a716-446655440001"
```

**Response** (public profile):
```json
{
  "user": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "linkedin_id": "linkedin_67890",
    "name": "Jane Smith",
    "headline": "Serial Entrepreneur | AI Enthusiast",
    "profile_photo_url": "https://media.licdn.com/dms/image/xyz789",
    "location": "New York, NY",
    "email": "jane.smith@example.com",
    "phone_number": null,
    "phone_verified": false,
    "is_active": true,
    "created_at": "2025-12-12T15:00:00Z",
    "updated_at": "2025-12-12T15:00:00Z",
    "last_login_at": "2025-12-13T09:00:00Z"
  },
  "profile": {
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "bio": "Third-time founder focused on democratizing AI for SMBs",
    "current_focus": "Building team for Series A push",
    "autonomy_mode": "suggest",
    "public_visibility": true,
    "embedding_id": "vec_660e8400-e29b-41d4-a716-446655440001",
    "embedding_updated_at": "2025-12-12T15:00:00Z",
    "created_at": "2025-12-12T15:00:00Z",
    "updated_at": "2025-12-12T15:00:00Z"
  }
}
```

**Error Response** (private profile):
```json
{
  "detail": "This profile is private"
}
```

### List Public Profiles

```bash
curl -X GET "http://localhost:8000/api/v1/profile/?limit=10&offset=0"
```

**Response**:
```json
[
  {
    "user": { ... },
    "profile": { ... }
  },
  {
    "user": { ... },
    "profile": { ... }
  },
  ...
]
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid or expired verification code"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "This profile is private"
}
```

### 404 Not Found
```json
{
  "detail": "Profile not found"
}
```

### 422 Unprocessable Entity (Validation Error)
```json
{
  "detail": [
    {
      "loc": ["body", "phone_number"],
      "msg": "Phone number must be in E.164 format (e.g., +1234567890)",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to update profile: Database connection error"
}
```

---

## Testing with httpie

If you have `httpie` installed:

```bash
# LinkedIn OAuth
http GET localhost:8000/api/v1/auth/linkedin/initiate

# Send verification code
http POST localhost:8000/api/v1/auth/verify-phone user_id==550e8400-e29b-41d4-a716-446655440000 phone_number="+14155551234"

# Get profile
http GET localhost:8000/api/v1/profile/me Authorization:"Bearer YOUR_JWT_TOKEN"

# Update profile
http PUT localhost:8000/api/v1/profile/me Authorization:"Bearer YOUR_JWT_TOKEN" bio="New bio" current_focus="New focus"

# List profiles
http GET localhost:8000/api/v1/profile/ limit==10 offset==0
```

---

## Testing with Postman

1. **Import Collection**: Create a new collection in Postman
2. **Set Environment Variables**:
   - `base_url`: `http://localhost:8000/api/v1`
   - `jwt_token`: (set after login)
   - `user_id`: (set after login)

3. **Example Requests**:
   - GET `{{base_url}}/auth/linkedin/initiate`
   - POST `{{base_url}}/auth/verify-phone?user_id={{user_id}}`
   - GET `{{base_url}}/profile/me` (with Bearer token)
   - PUT `{{base_url}}/profile/me` (with Bearer token)

---

## Complete User Journey Example

```bash
# 1. Sign up with LinkedIn (mocked for testing)
# This would normally redirect to LinkedIn, but in tests we mock it

# 2. Send phone verification
curl -X POST "http://localhost:8000/api/v1/auth/verify-phone?user_id=YOUR_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+14155551234"}'

# 3. Confirm phone (use code from database in development)
curl -X POST "http://localhost:8000/api/v1/auth/confirm-phone?user_id=YOUR_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234",
    "verification_code": "123456"
  }'

# 4. Get my profile
curl -X GET "http://localhost:8000/api/v1/profile/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 5. Update profile
curl -X PUT "http://localhost:8000/api/v1/profile/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bio": "Building in public!",
    "current_focus": "Raising pre-seed"
  }'

# 6. View another founder's profile
curl -X GET "http://localhost:8000/api/v1/profile/ANOTHER_USER_ID"

# 7. Browse public profiles
curl -X GET "http://localhost:8000/api/v1/profile/?limit=20&offset=0"
```

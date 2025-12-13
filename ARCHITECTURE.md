# PublicFounders System Architecture

## Executive Summary

PublicFounders is a semantic AI-powered founder network that intelligently connects entrepreneurs through LinkedIn data, vector embeddings, and autonomous AI agents. The system implements a **unified platform architecture** using ZeroDB for all data operations - both relational NoSQL tables and semantic vector embeddings in a single database.

**Key Architectural Decisions:**

1. **Tech Stack**: Python/FastAPI for rapid development, type safety, and async capabilities
2. **Unified Storage**: ZeroDB for all data - NoSQL tables + vector embeddings in one platform
3. **Testing Strategy**: TDD with 80% minimum coverage enforcement
4. **Agent Architecture**: Autonomous modes with full audit trails
5. **Embedding Pipeline**: OpenAI text-embedding-3-small (1536 dimensions)
6. **No ORM**: Direct HTTP API calls for simplicity and performance

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│  (LinkedIn OAuth, Web App, Mobile Future)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway                              │
│              FastAPI + Pydantic Validation                   │
│         Health Check, CORS, Rate Limiting, JWT Auth          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Business Logic      │
           │   - Auth Service      │
           │   - Profile Service   │
           │   - Embedding Service │
           │   - Matching Engine   │
           │   - Agent Reasoning   │
           └───────────┬───────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │  ZeroDB Client        │
           │  (HTTP/REST API)      │
           │  - CRUD Operations    │
           │  - Query Filtering    │
           │  - Pagination/Sort    │
           └───────────┬───────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      ZeroDB Platform                         │
├─────────────────────────────────────────────────────────────┤
│  NoSQL Tables (8):                                          │
│  - users, founder_profiles, goals, asks, posts              │
│  - companies, company_roles, introductions                  │
├─────────────────────────────────────────────────────────────┤
│  Vector Store:                                              │
│  - Founder embeddings, Goal embeddings                      │
│  - Ask embeddings, Post embeddings                          │
│  - 1536-dim semantic search built-in                        │
├─────────────────────────────────────────────────────────────┤
│  Enterprise Features (Future):                              │
│  - Event Streams (RLHF), File Storage, Caching             │
│  - Quantum capabilities, Agent memory                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack Rationale

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Python 3.9+ FastAPI | - Async/await for high concurrency<br>- Type hints for safety<br>- Auto-generated OpenAPI docs<br>- Excellent ecosystem for AI/ML |
| **Database** | ZeroDB (unified) | - NoSQL + vector storage in one platform<br>- No sync issues between systems<br>- Built-in semantic search<br>- RLHF + event streams<br>- Cost-effective single platform |
| **Embeddings** | OpenAI text-embedding-3-small | - Cost-effective ($0.02/1M tokens)<br>- 1536 dimensions<br>- High quality semantic understanding |
| **Data Access** | Direct HTTP API | - No ORM overhead<br>- Simple MongoDB-style queries<br>- Fast JSON serialization<br>- Easy to test and debug |
| **Testing** | pytest + coverage | - Async test support<br>- Rich fixture system<br>- 80% coverage enforcement |
| **CI/CD** | GitHub Actions | - Native GitHub integration<br>- Free for open source<br>- Excellent ecosystem |

---

## 2. Data Architecture

### 2.1 Unified Platform Philosophy

**ZeroDB Platform** provides both:

**NoSQL Tables** answer: *"What is true?"*
- Flexible schema for rapid development
- Audit trail for compliance (created_at, updated_at)
- Source of truth for all entities
- MongoDB-style queries for familiarity

**Vector Embeddings** answer: *"What is relevant?"*
- Probabilistic, semantic matching
- Intent-aware search built-in
- Continuously learning from outcomes
- No synchronization needed - same database!

### 2.2 ZeroDB NoSQL Schema

All 8 tables use flexible JSON documents with automatic indexing:

```python
# Core Identity
users = {
    "id": "uuid-string",
    "linkedin_id": "string",
    "email": "string",
    "name": "string",
    "phone": "string",
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601"
}

founder_profiles = {
    "id": "uuid-string",
    "user_id": "uuid-string",
    "bio": "text",
    "current_focus": "string",
    "autonomy_mode": "suggest|approve|auto",
    "embedding_id": "vector-uuid",
    "created_at": "ISO-8601"
}

# Company Context
companies = {"id": "uuid", "name": "string", "stage": "string", "industry": "string"}
company_roles = {"user_id": "uuid", "company_id": "uuid", "role": "string", "is_current": bool}

# Intent Capture
goals = {"user_id": "uuid", "type": "string", "description": "text", "priority": int, "is_active": bool}
asks = {"user_id": "uuid", "goal_id": "uuid", "description": "text", "urgency": int, "status": "string"}

# Content & Discovery
posts = {"user_id": "uuid", "type": "string", "content": "text", "is_cross_posted": bool}

# AI Actions
introductions = {"requester_id": "uuid", "target_id": "uuid", "channel": "string", "rationale": "text"}
```

**No migrations needed!** Schema evolves automatically as you add fields.

### 2.3 Vector Schema (ZeroDB)

Each entity type has corresponding embeddings:

```json
{
  "id": "uuid",
  "entity_type": "goal|ask|post|introduction|...",
  "source_id": "relational_uuid",
  "embedding": [float × 1536],
  "metadata": {
    "user_id": "uuid",
    "timestamp": "ISO-8601",
    "priority": 8,
    "stage": "seed",
    ...
  }
}
```

**Embedding Collections:**
1. `founder_embeddings`: Composite of bio + experience + goals
2. `goal_embeddings`: Intent vectors for matching
3. `ask_embeddings`: Help requests with urgency weighting
4. `post_embeddings`: Content for discovery
5. `introduction_embeddings`: Connection rationale
6. `interaction_embeddings`: Outcome patterns for RLHF
7. `agent_memory_embeddings`: Long-term agent learning

### 2.4 Data Flow (Simplified with ZeroDB)

```
User Input → Pydantic Validation
                ↓
        ZeroDB Client (HTTP)
                ↓
        ┌───────┴────────┐
        ▼                ▼
   NoSQL Insert    Embedding Pipeline
        ▼                ▼
   Audit Trail    Vector Upsert
        │                │
        └────────┬───────┘
                 ▼
        ZeroDB Platform
                 ▼
        Semantic Search
                 ▼
        AI Agent Decision
                 ▼
        RLHF Feedback Loop
```

**Key Benefit**: Single database transaction, no cross-system synchronization!

---

## 3. API Design

### 3.1 API Structure

```
/
├── /health                    # Health check
├── /api/
│   ├── /docs                  # OpenAPI documentation
│   ├── /v1/
│   │   ├── /auth/             # Authentication
│   │   │   ├── /linkedin      # LinkedIn OAuth
│   │   │   └── /phone         # Phone verification
│   │   ├── /profile/          # Profile management
│   │   ├── /goals/            # Goal CRUD
│   │   ├── /asks/             # Ask CRUD
│   │   ├── /posts/            # Content posting
│   │   ├── /introductions/    # Intro workflow
│   │   ├── /feed/             # Discovery feed
│   │   └── /analytics/        # KPI tracking
```

### 3.2 Authentication Flow

```
User → LinkedIn OAuth → JWT Token → API Requests
   ↓
Phone Verification (Optional)
   ↓
Founder Profile Creation
   ↓
Initial Embeddings Generated
```

### 3.3 Error Handling

All API errors follow RFC 7807 Problem Details:

```json
{
  "type": "/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Goal description must be at least 20 characters",
  "instance": "/api/v1/goals"
}
```

---

## 4. Embedding & Semantic Architecture

### 4.1 Embedding Generation Pipeline (ZeroDB)

```python
from app.services.embedding_service import EmbeddingService
from app.services.zerodb_client import zerodb_client

# Create entity and embedding in same workflow
async def create_goal_with_embedding(goal_data: dict):
    # 1. Insert into NoSQL table
    result = await zerodb_client.insert_rows("goals", [goal_data])
    goal_id = result["inserted_ids"][0]

    # 2. Generate embedding
    embedding_service = EmbeddingService()
    content = f"{goal_data['type']}: {goal_data['description']}"

    # 3. Store in same ZeroDB platform (vector store)
    vector_id = await embedding_service.create_goal_embedding(
        goal_id=goal_id,
        content=content,
        metadata={"priority": goal_data["priority"]}
    )

    # 4. Update goal with embedding reference
    await zerodb_client.update_rows(
        "goals",
        filter={"id": goal_id},
        update={"$set": {"embedding_id": vector_id}}
    )

    return goal_id

# No database commits needed - HTTP API handles transactions!
```

### 4.2 Semantic Search Strategy

```python
# Multi-stage ranking
async def find_relevant_connections(founder):
    # 1. Vector similarity search
    similar = await zerodb.search(
        query_embedding=founder.embedding,
        entity_type="founder",
        limit=50,
        threshold=0.7
    )

    # 2. Relational filtering
    candidates = filter_by_stage_compatibility(similar)
    candidates = filter_by_visibility_settings(candidates)
    candidates = exclude_existing_connections(candidates)

    # 3. Re-ranking with context
    ranked = rank_by_combined_score(
        candidates,
        goal_alignment=0.4,
        experience_match=0.3,
        geographic_proximity=0.2,
        recency=0.1
    )

    return ranked[:10]
```

### 4.3 Embedding Lifecycle

```
Creation → Initial Embedding
    ↓
Interactions → Outcome Recording
    ↓
RLHF Feedback → Weight Updates
    ↓
Periodic Re-embedding (30 days)
```

---

## 5. AI Agent Architecture

### 5.1 Agent Autonomy Modes

| Mode | Description | User Control |
|------|-------------|--------------|
| **suggest** | Agent proposes, user approves | Full review required |
| **approve** | Agent acts, user can veto | Notification + 24h window |
| **auto** | Agent acts autonomously | Audit trail only |

### 5.2 Agent Decision Flow

```python
class VirtualAdvisor:
    async def suggest_introduction(self, founder):
        # 1. Analyze current goals
        active_goals = await get_active_goals(founder)

        # 2. Semantic search for matches
        candidates = await find_relevant_connections(founder, active_goals)

        # 3. Generate rationale
        for candidate in candidates:
            rationale = await explain_match(founder, candidate, active_goals)

            # 4. Respect autonomy mode
            if founder.autonomy_mode == "suggest":
                await propose_intro(founder, candidate, rationale)
            elif founder.autonomy_mode == "approve":
                intro = await create_intro(founder, candidate, rationale, status="pending_approval")
                await notify_founder(intro)
            elif founder.autonomy_mode == "auto":
                intro = await create_and_send_intro(founder, candidate, rationale)
                await log_agent_action(intro)
```

### 5.3 RLHF Feedback Loop

```
Introduction Suggested → User Response → Outcome Recorded
         ↓                     ↓                ↓
   Agent Memory         Preference Update    Embedding Refresh
         ↓                     ↓                ↓
   Future Suggestions ← Improved Matching ← Updated Vectors
```

---

## 6. Testing Strategy

### 6.1 Test Pyramid

```
           ┌─────────┐
           │   E2E   │  10% - Full user workflows
           └─────────┘
         ┌─────────────┐
         │ Integration │  30% - API + DB interactions
         └─────────────┘
       ┌─────────────────┐
       │  Unit Tests     │  60% - Model logic, utilities
       └─────────────────┘
```

### 6.2 Coverage Requirements

- **Minimum**: 80% overall
- **Models**: 90% (business logic critical)
- **API Endpoints**: 85% (user-facing)
- **Services**: 80% (agent logic)
- **Utils**: 70% (helpers)

### 6.3 Test Types

```python
# Unit Test
@pytest.mark.unit
async def test_goal_embedding_content():
    goal = Goal(type=GoalType.FUNDRAISING, description="Raise $2M")
    content = goal.embedding_content
    assert "fundraising" in content.lower()

# Integration Test
@pytest.mark.integration
async def test_create_goal_endpoint(client):
    response = await client.post("/api/v1/goals", json={...})
    assert response.status_code == 201

# E2E Test
@pytest.mark.e2e
async def test_full_intro_workflow(client):
    # Sign up → Create goal → Get suggestion → Accept → Outcome
    ...
```

---

## 7. Scalability & Performance

### 7.1 Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| API Response Time | p95 < 200ms | Good UX |
| Embedding Generation | < 2s | OpenAI latency |
| Semantic Search | < 500ms | ZeroDB performance |
| Database Queries | p95 < 100ms | Indexed lookups |

### 7.2 Scaling Strategy

**Horizontal Scaling:**
- FastAPI workers via uvicorn/gunicorn
- PostgreSQL read replicas for queries
- ZeroDB inherently distributed

**Caching Strategy:**
- Redis for hot embeddings (future)
- CDN for static assets
- Application-level caching for rankings

**Database Optimization:**
- Compound indexes on frequent queries
- Partitioning for time-series data (posts, events)
- Connection pooling (10-20 connections)

### 7.3 Monitoring Plan

```
Application Metrics:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Active connections
- Background task queue depth

Business Metrics:
- Intro acceptance rate
- Outcome success rate
- Embedding generation lag
- Agent decision accuracy

Infrastructure:
- CPU/Memory utilization
- Database query performance
- Vector search latency
- API gateway throughput
```

---

## 8. Security & Compliance

### 8.1 Authentication Security

- LinkedIn OAuth 2.0 with PKCE
- JWT tokens with 7-day expiry
- Refresh token rotation
- Rate limiting per user/IP

### 8.2 Data Privacy

- User consent for AI agent actions
- Public visibility controls
- Data export capability (GDPR)
- Right to deletion (CCPA)

### 8.3 AI Safety

- Audit trail for all agent actions
- Explainable AI via rationale storage
- User override capability
- Bias monitoring in matching

---

## 9. Future Architecture Considerations

### 9.1 Next 6 Months

1. **Real-time Updates**: WebSockets for live notifications
2. **Mobile App**: React Native with shared API
3. **Email Integration**: Gmail/Outlook for intro delivery
4. **Advanced Analytics**: Cohort analysis, funnel tracking

### 9.2 Next 12 Months

1. **Multi-tenant Architecture**: Enterprise customers
2. **Quantum-enhanced Search**: ZeroDB quantum features
3. **Fine-tuned LLM**: Custom model for intro writing
4. **Federated Learning**: Privacy-preserving RLHF

---

## 10. Decision Records

### ADR-001: Why Python/FastAPI over Node.js/TypeScript?

**Context**: Need to choose backend framework

**Decision**: Python 3.9+ with FastAPI

**Rationale**:
- Superior AI/ML ecosystem (OpenAI, sentence-transformers)
- Type hints provide similar safety to TypeScript
- Async/await pattern well-established
- Better for data science team collaboration
- FastAPI auto-generates OpenAPI docs

**Consequences**:
- Positive: Faster AI feature development
- Positive: Better ZeroDB/embedding integration
- Negative: Slightly larger Docker images
- Negative: Less familiarity for frontend-first teams

### ADR-002: Why 80% Coverage Minimum?

**Context**: Balance between quality and velocity

**Decision**: Enforce 80% minimum test coverage

**Rationale**:
- Industry standard for production systems
- Catches most critical bugs
- Allows pragmatism for trivial code
- Higher (90%+) slows down experimentation

**Consequences**:
- Positive: High confidence in deployments
- Positive: Regression protection
- Negative: Slower initial development
- Mitigation: Focus coverage on business logic

### ADR-003: Why ZeroDB for Everything (NoSQL + Vectors)?

**Context**: Originally planned PostgreSQL + ZeroDB dual-layer architecture

**Decision**: Use ZeroDB for ALL data - NoSQL tables + vector embeddings

**Rationale**:
- **Simplified Architecture**: One database instead of two
- **No Sync Issues**: Relational data and vectors always consistent
- **Cost Reduction**: Single platform subscription vs. PostgreSQL + ZeroDB
- **Developer Experience**: No ORM, no migrations, simple HTTP API
- **Performance**: Direct API calls faster than SQLAlchemy
- **AI Features**: RLHF, event streams, file storage all built-in
- **Future-Ready**: Quantum capabilities when needed

**Consequences**:
- Positive: 50% reduction in infrastructure complexity
- Positive: Faster development (no schema migrations)
- Positive: Better for AI-native features
- Positive: Lower operational costs
- Negative: Less familiar than PostgreSQL for traditional developers
- Mitigation: MongoDB-style queries are widely understood

---

## Conclusion

This unified ZeroDB architecture provides a solid foundation for PublicFounders with significantly reduced complexity compared to traditional dual-database approaches. By combining NoSQL tables and vector embeddings in a single platform, we achieve:

1. **Simplicity**: One database, one API, one platform to learn
2. **Performance**: Direct HTTP API calls, no ORM overhead
3. **Consistency**: NoSQL data and vectors always in sync
4. **AI-Native**: Semantic search, RLHF, and agent memory built-in
5. **Cost-Effective**: Single subscription vs. multiple database services

**Migration Status (December 2025)**:
- ✅ Core services migrated (auth, profile, phone verification)
- ✅ All PostgreSQL/SQLAlchemy code removed
- ✅ 8 NoSQL tables operational
- ✅ Vector embeddings integrated
- ✅ Production endpoints cleaned of database dependencies
- Remaining: Test suite migration (in progress by separate agent)

**Next Steps**:
1. Complete test suite migration to ZeroDB
2. Finalize remaining endpoint migrations (goals/asks/posts)
3. Production deployment validation
4. Performance benchmarking

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Author**: System Architect Agent
**Status**: Approved for Sprint 0 Completion

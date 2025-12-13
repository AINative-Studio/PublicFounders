# PublicFounders System Architecture

## Executive Summary

PublicFounders is a semantic AI-powered founder network that intelligently connects entrepreneurs through LinkedIn data, vector embeddings, and autonomous AI agents. The system implements a dual-layer architecture separating relational truth from vector intelligence, enabling auditable AI decision-making while maintaining data compliance.

**Key Architectural Decisions:**

1. **Tech Stack**: Python/FastAPI for rapid development, type safety, and async capabilities
2. **Dual Storage**: PostgreSQL for relational truth + ZeroDB for semantic intelligence
3. **Testing Strategy**: TDD with 80% minimum coverage enforcement
4. **Agent Architecture**: Autonomous modes with full audit trails
5. **Embedding Pipeline**: OpenAI text-embedding-3-small (1536 dimensions)

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
│         Health Check, CORS, Rate Limiting                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Relational Layer    │  │  Vector Layer        │
│  PostgreSQL 15+      │  │  ZeroDB              │
│  - Users             │  │  - Embeddings        │
│  - Profiles          │  │  - Semantic Search   │
│  - Goals/Asks        │  │  - Agent Memory      │
│  - Introductions     │  │  - RLHF Data         │
│  - Outcomes          │  │                      │
└──────────┬───────────┘  └──────────┬───────────┘
           │                         │
           └──────────┬──────────────┘
                      │
                      ▼
           ┌──────────────────────┐
           │   Business Logic     │
           │   - Embedding Svc    │
           │   - Matching Engine  │
           │   - Agent Reasoning  │
           │   - RLHF Loop        │
           └──────────────────────┘
```

### 1.2 Technology Stack Rationale

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Python 3.9+ FastAPI | - Async/await for high concurrency<br>- Type hints for safety<br>- Auto-generated OpenAPI docs<br>- Excellent ecosystem for AI/ML |
| **Database** | PostgreSQL 15+ | - ACID compliance for audit trail<br>- JSON support for flexibility<br>- Proven reliability<br>- Strong ecosystem |
| **Vector Store** | ZeroDB | - 1536-dim embeddings support<br>- Built-in semantic search<br>- RLHF integration<br>- Quantum capabilities (future) |
| **Embeddings** | OpenAI text-embedding-3-small | - Cost-effective ($0.02/1M tokens)<br>- 1536 dimensions<br>- High quality semantic understanding |
| **Testing** | pytest + coverage | - Async test support<br>- Rich fixture system<br>- 80% coverage enforcement |
| **CI/CD** | GitHub Actions | - Native GitHub integration<br>- Free for open source<br>- Excellent ecosystem |

---

## 2. Data Architecture

### 2.1 Dual-Layer Philosophy

**Relational Layer** answers: *"What is true?"*
- Deterministic, ACID-compliant storage
- Audit trail for compliance
- Source of truth for all actions

**Vector Layer** answers: *"What is relevant?"*
- Probabilistic, semantic matching
- Intent-aware search
- Continuously learning from outcomes

### 2.2 Relational Schema

```sql
-- Core Identity
users (id, linkedin_id, name, email, phone, ...)
founder_profiles (user_id, bio, current_focus, autonomy_mode, ...)

-- Company Context
companies (id, name, stage, industry, ...)
company_roles (user_id, company_id, role, is_current, ...)

-- Intent Capture
goals (user_id, type, description, priority, is_active)
asks (user_id, goal_id, description, urgency, status)

-- Content & Discovery
posts (user_id, type, content, is_cross_posted)

-- AI Actions
introductions (requester_id, target_id, channel, rationale, status)
interaction_outcomes (introduction_id, outcome_type, notes)
```

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

### 2.4 Data Flow

```
User Input → Relational Write → Embedding Pipeline → Vector Store
                    ↓                                      ↓
              Audit Trail                          Semantic Search
                    ↓                                      ↓
              RLHF Feedback ← AI Agent Decision ← Ranked Results
```

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

### 4.1 Embedding Generation Pipeline

```python
# Synchronous (blocking) for critical entities
async def create_goal_embedding(goal):
    content = f"{goal.type}: {goal.description}"
    embedding = await generate_embedding(content)
    vector_id = await zerodb.upsert(
        entity_type="goal",
        entity_id=goal.id,
        embedding=embedding,
        metadata={"user_id": goal.user_id, "priority": goal.priority}
    )
    goal.embedding_id = vector_id
    await db.commit()

# Asynchronous (non-blocking) for posts
async def create_post_embedding(post):
    post.embedding_status = "pending"
    await db.commit()

    # Background task
    background_tasks.add_task(generate_and_store_embedding, post)
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

### ADR-003: Why ZeroDB over Pinecone/Weaviate?

**Context**: Choose vector database

**Decision**: ZeroDB for vector storage

**Rationale**:
- Native RLHF support
- Quantum capabilities for future
- Cost-effective for startup
- Direct MCP integration
- Better for agent memory

**Consequences**:
- Positive: Advanced AI features built-in
- Positive: Simpler architecture
- Negative: Smaller ecosystem vs Pinecone
- Mitigation: Strong documentation and support

---

## Conclusion

This architecture provides a solid foundation for PublicFounders while maintaining flexibility for future growth. The dual-layer approach cleanly separates deterministic truth from probabilistic intelligence, enabling powerful AI features while maintaining auditability and compliance.

**Next Steps (Sprint 1)**:
1. Implement LinkedIn OAuth flow
2. Build profile management endpoints
3. Deploy first semantic matching agent
4. Establish RLHF data collection

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Author**: System Architect Agent
**Status**: Approved for Sprint 0 Completion

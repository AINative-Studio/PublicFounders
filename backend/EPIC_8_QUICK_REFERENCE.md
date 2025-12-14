# Epic 8: Outcomes & Learning - Quick Reference

## Overview
Track introduction outcomes and use RLHF to improve matching quality over time.

## Key Components

### 1. Database Schema
```
introduction_outcomes (ZeroDB NoSQL)
├── id (UUID)
├── introduction_id (UUID, unique)
├── recorded_by_user_id (UUID)
├── outcome_type (successful|unsuccessful|no_response|not_relevant)
├── rating (1-5 stars, optional)
├── feedback_text (encrypted, optional)
├── tags (array, optional)
├── rlhf_score (-1.0 to 1.0)
├── rlhf_interaction_id (ZeroDB RLHF)
├── match_context (JSON)
└── timestamps (recorded_at, created_at, updated_at)
```

### 2. API Endpoints
```
POST   /api/v1/introductions/{id}/outcome      - Record outcome
GET    /api/v1/introductions/{id}/outcome      - Get outcome
PATCH  /api/v1/introductions/{id}/outcome      - Update outcome
GET    /api/v1/analytics/outcomes              - Aggregated analytics
GET    /api/v1/analytics/rlhf-insights         - ML insights
```

### 3. Services

**OutcomeService** (`outcome_service.py`)
- `record_outcome()` - Create outcome record
- `update_outcome()` - Update existing outcome
- `get_outcome()` - Retrieve outcome
- `get_outcome_analytics()` - Analytics queries
- `_calculate_rlhf_score()` - Map outcome to feedback score
- `_gather_match_context()` - Extract match metadata
- `_track_rlhf_async()` - Send to RLHF system

**RLHFService** (updated)
- `track_introduction_outcome_detailed()` - Enhanced RLHF tracking
- Includes match context, user context, goal context

**IntroductionService** (updated)
- `complete_introduction()` - Now records outcome directly
- `get_introduction_with_outcome()` - Include outcome data

### 4. RLHF Score Mapping

| Outcome Type | Base Score | +5 Stars | +1 Star |
|--------------|-----------|----------|---------|
| successful | +1.0 | +1.0 (clamped) | +0.8 |
| unsuccessful | -0.5 | -0.3 | -0.7 |
| no_response | -0.3 | -0.1 | -0.5 |
| not_relevant | -0.7 | -0.5 | -0.9 |

Rating adjustments: 1★(-0.2), 2★(-0.1), 3★(0.0), 4★(+0.1), 5★(+0.2)

### 5. Data Flow

```
User → POST /outcome
  ↓
Validate permission (must be involved in intro)
  ↓
Calculate RLHF score (outcome_type + rating)
  ↓
Gather match context (scores, goals, asks)
  ↓
Store in ZeroDB (introduction_outcomes table)
  ↓
Update introduction status (has_outcome = true)
  ↓
Track in RLHF system (async, non-blocking)
  ↓
Return outcome record
```

### 6. Implementation Phases

**Phase 1: Foundation (Week 1)**
- Create outcomes table
- Implement OutcomeService
- Build API endpoints
- Unit tests (>85% coverage)

**Phase 2: RLHF Integration (Week 2)**
- Match context extraction
- RLHF tracking pipeline
- Background task execution
- Integration tests

**Phase 3: Analytics (Week 3)**
- Outcome updates (PATCH)
- Analytics endpoints
- Aggregation queries
- Caching optimization

**Phase 4: ML Loop (Week 4)**
- Pattern analysis
- Weight adjustments
- A/B testing
- Performance monitoring

### 7. Key Metrics

**Success Criteria:**
- Outcome recording rate: >60%
- RLHF data collection: 100%
- API latency: <200ms (p95)
- Match quality improvement: >5%

**Business KPIs:**
- Average rating: >4.0
- Successful outcome rate: >60%
- Time to outcome: <5 days avg
- User satisfaction trend: ↗

### 8. Security & Privacy

**Data Protection:**
- Feedback text: Encrypted at rest
- User IDs: Anonymized after 90 days in RLHF
- Tags: Predefined set (no PII)
- Access control: Only involved users

**GDPR Compliance:**
- Right to be forgotten: Delete user outcomes
- Data minimization: Only necessary fields
- Purpose limitation: RLHF learning only
- Retention: 2 years for training data

### 9. Quick Start Commands

**Create Outcomes Table:**
```bash
cd /Users/aideveloper/Desktop/PublicFounders-main/backend
python3 -c "from migrations.create_outcomes_table import create_outcomes_table; import asyncio; asyncio.run(create_outcomes_table())"
```

**Run Tests:**
```bash
pytest tests/unit/test_outcome_service.py -v
pytest tests/integration/test_outcome_flow.py -v
```

**Deploy:**
```bash
# 1. Deploy code
git push origin feat/epic-8-outcomes

# 2. Create table (production)
python3 manage.py create_outcomes_table

# 3. Enable feature flag
export ENABLE_OUTCOME_TRACKING=true

# 4. Restart services
systemctl restart publicfounders-api
```

### 10. Example Usage

**Record Successful Outcome:**
```bash
curl -X POST https://api.publicfounders.com/api/v1/introductions/{intro_id}/outcome \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "outcome_type": "successful",
    "rating": 5,
    "feedback_text": "Great connection! We had a productive call.",
    "tags": ["helpful", "great_connection", "led_to_meeting"]
  }'
```

**Get Analytics:**
```bash
curl -X GET "https://api.publicfounders.com/api/v1/analytics/outcomes?time_range=week" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 11. Troubleshooting

**Issue: RLHF tracking fails**
- Check: ZeroDB API key valid?
- Check: Network connectivity to ZeroDB
- Impact: Non-critical, outcome still saved
- Fix: Retry background task

**Issue: Duplicate outcome error**
- Check: Outcome already exists?
- Fix: Use PATCH to update instead of POST

**Issue: Permission denied**
- Check: User involved in introduction?
- Check: User is requester or target?
- Fix: Verify introduction_id and user_id

### 12. File Locations

```
backend/
├── app/
│   ├── services/
│   │   ├── outcome_service.py          # NEW: Core outcome logic
│   │   ├── rlhf_service.py             # UPDATED: Enhanced tracking
│   │   └── introduction_service.py     # UPDATED: Integration
│   ├── models/
│   │   └── interaction_outcome.py      # EXISTING: Reference model
│   ├── schemas/
│   │   └── outcome.py                  # NEW: Pydantic schemas
│   └── api/v1/endpoints/
│       └── introductions.py            # UPDATED: Outcome endpoints
├── tests/
│   ├── unit/
│   │   └── test_outcome_service.py     # NEW: Unit tests
│   └── integration/
│       └── test_outcome_flow.py        # NEW: Integration tests
├── EPIC_8_ARCHITECTURE.md              # THIS DOCUMENT (detailed)
└── EPIC_8_QUICK_REFERENCE.md           # THIS FILE (quick ref)
```

### 13. Related Documentation

- **Full Architecture:** `EPIC_8_ARCHITECTURE.md`
- **Epic 7 Intros:** Introduction service implementation
- **Epic 4 Caching:** `EPIC_4_CACHING_IMPLEMENTATION.md`
- **ZeroDB Docs:** `ZERODB_MIGRATION_STRATEGY.md`

---

**Quick Links:**
- [Full Architecture Doc](./EPIC_8_ARCHITECTURE.md)
- [ZeroDB RLHF Docs](https://docs.zerodb.ai/rlhf)
- [API Reference](./API_REFERENCE.md)

**Last Updated:** December 13, 2025
**Version:** 1.0

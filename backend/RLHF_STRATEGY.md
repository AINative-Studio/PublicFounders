# RLHF Data Collection Strategy for Epic 8: Outcomes & Learning

## Overview

This document outlines the Reinforcement Learning from Human Feedback (RLHF) strategy for tracking introduction outcomes and continuously improving PublicFounders' intelligent matching algorithm.

## Goals

1. **Track Introduction Lifecycle**: Capture every stage from request → response → outcome
2. **Link Outcomes to Match Factors**: Connect success/failure back to the original relevance, trust, and reciprocity scores
3. **Identify Success Patterns**: Determine which factors and combinations predict successful introductions
4. **Enable Continuous Learning**: Provide data infrastructure for ML model training and A/B testing

## Data Points to Collect

### 1. Introduction Request Data
Tracked when a user requests an introduction:

```python
{
    "intro_id": "uuid",
    "timestamp": "ISO-8601",
    "requester_id": "uuid",
    "target_id": "uuid",
    "match_scores": {
        "relevance": 0.85,      # Semantic similarity (0-1)
        "trust": 0.72,          # Profile quality (0-1)
        "reciprocity": 0.80,    # Mutual value potential (0-1)
        "overall": 0.81         # Weighted: 50% relevance, 25% trust, 25% reciprocity
    },
    "matching_context": {
        "goal_matches": ["goal_id_1", "goal_id_2"],
        "ask_matches": ["ask_id_1"],
        "top_similarity": 0.89,
        "match_type": "goal_based | ask_based | hybrid",
        "goal_types": ["fundraising", "hiring"],
        "industry_match": true,
        "location_match": false
    },
    "feedback_score": 0.0  # Neutral initially
}
```

### 2. Introduction Response Data
Tracked when the target responds (accept/decline):

```python
{
    "intro_id": "uuid",
    "timestamp": "ISO-8601",
    "outcome": "accepted | declined",
    "time_to_response_hours": 24.5,
    "feedback_score": 1.0 | -0.5  # +1.0 for accept, -0.5 for decline
}
```

### 3. Introduction Completion Data
Tracked when either party marks the introduction complete:

```python
{
    "intro_id": "uuid",
    "timestamp": "ISO-8601",
    "outcome_type": "meeting_scheduled | email_exchanged | no_response | not_relevant",
    "outcome_notes": "User-provided feedback text",
    "rating": 1-5,  # Optional star rating
    "tags": ["helpful", "timing-off", "not-relevant"],  # Optional outcome tags
    "time_to_completion_days": 7.2,
    "feedback_score": 0.0-1.0  # Based on outcome type and rating
}
```

### 4. Implicit Signals
Tracked automatically without user input:

```python
{
    "intro_id": "uuid",
    "timestamp": "ISO-8601",
    "time_to_response": "Time from request to accept/decline",
    "time_to_completion": "Time from accept to completion",
    "no_response": true | false,  # Target never responded
    "expired": true | false,  # Request expired after 7 days
    "engagement_score": 0.0-1.0  # Based on speed and completion
}
```

## Linking Outcomes to Match Factors

### Primary Objective
Determine which match score components (relevance, trust, reciprocity) are most predictive of successful outcomes.

### Analysis Approach

1. **Correlation Analysis**
   - Calculate Pearson correlation between each score component and success
   - Identify which factor has strongest correlation with positive outcomes
   - Example: `correlation(relevance_score, success_rate) = 0.78`

2. **Score Range Analysis**
   - Bucket introductions by score ranges (0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)
   - Calculate success rate for each bucket
   - Identify optimal score thresholds

3. **Multi-variate Analysis**
   - Use logistic regression: `P(success) = f(relevance, trust, reciprocity, context)`
   - Determine optimal weight combinations
   - Current: 50/25/25 → Optimal: may be 60/20/20 or 55/30/15

### Success Metrics Hierarchy

#### Tier 1: High Success (score = 1.0)
- `outcome_type = "meeting_scheduled"` with 5-star rating
- `outcome_type = "email_exchanged"` with 4-5 star rating
- Tags include: "helpful", "valuable", "great-match"

#### Tier 2: Moderate Success (score = 0.7)
- `outcome_type = "meeting_scheduled"` with 3-4 star rating
- `outcome_type = "email_exchanged"` with 3 star rating
- Accepted but slow to complete (5-7 days)

#### Tier 3: Low Success (score = 0.4)
- `outcome_type = "email_exchanged"` with no rating
- `outcome_type = "no_response"` after initial accept
- Tags include: "timing-off", "too-busy"

#### Tier 4: Failure (score = 0.0)
- `status = "declined"` (immediate rejection)
- `status = "expired"` (no response within 7 days)
- `outcome_type = "not_relevant"` with 1-2 star rating
- Tags include: "not-relevant", "bad-match", "spam"

## What Makes a Successful Introduction?

### Explicit Success Indicators (Strong Signals)

1. **High Rating + Positive Outcome**
   - Rating: 4-5 stars
   - Outcome: meeting_scheduled OR email_exchanged
   - Weight: 1.0 (strongest signal)

2. **Fast Response + Acceptance**
   - Response time: < 24 hours
   - Status: accepted
   - Weight: 0.8

3. **Positive Tags**
   - Tags: helpful, valuable, great-match, timely
   - Weight: 0.7

### Implicit Success Indicators (Weak Signals)

1. **Moderate Response Time**
   - Response time: 24-72 hours
   - Status: accepted
   - Weight: 0.6

2. **Completion Without Rating**
   - Outcome: meeting_scheduled OR email_exchanged
   - No rating provided
   - Weight: 0.5 (cautious optimism)

### Failure Indicators

1. **Decline or No Response**
   - Status: declined OR expired
   - Weight: 0.0

2. **Negative Outcome**
   - Outcome: not_relevant
   - Rating: 1-2 stars
   - Tags: bad-match, spam, not-relevant
   - Weight: 0.0

3. **No Response After Accept**
   - Status: accepted but no completion after 14 days
   - Weight: 0.2 (borderline failure)

## How to Weight Different Signals

### Signal Priority (Descending Order)

1. **Explicit Feedback** (Rating + Outcome Type)
   - Weight: 60% of final score
   - Most reliable signal of actual value

2. **Behavioral Signals** (Response Time + Completion Time)
   - Weight: 25% of final score
   - Fast response indicates relevance and interest

3. **Contextual Signals** (Tags + Notes)
   - Weight: 15% of final score
   - Provides qualitative insights

### Composite Success Score Formula

```python
def calculate_success_score(outcome_data):
    # Explicit feedback (60%)
    rating_score = (outcome_data.get("rating", 3) - 1) / 4  # Normalize 1-5 to 0-1
    outcome_score = OUTCOME_TYPE_WEIGHTS[outcome_data["outcome_type"]]
    explicit_score = (rating_score * 0.5 + outcome_score * 0.5) * 0.6

    # Behavioral signals (25%)
    response_score = calculate_response_speed_score(outcome_data["time_to_response_hours"])
    completion_score = calculate_completion_speed_score(outcome_data["time_to_completion_days"])
    behavioral_score = (response_score * 0.6 + completion_score * 0.4) * 0.25

    # Contextual signals (15%)
    tag_score = calculate_tag_sentiment_score(outcome_data.get("tags", []))
    notes_score = calculate_notes_sentiment_score(outcome_data.get("notes", ""))
    contextual_score = (tag_score * 0.7 + notes_score * 0.3) * 0.15

    # Final composite score
    return explicit_score + behavioral_score + contextual_score

OUTCOME_TYPE_WEIGHTS = {
    "meeting_scheduled": 1.0,
    "email_exchanged": 0.8,
    "no_response": 0.2,
    "not_relevant": 0.0
}
```

## What Predicts Success?

### Hypothesis 1: High Overall Match Score
**Question**: Do introductions with overall_score > 0.8 succeed more often?

**Analysis**:
```python
success_by_score_range = {
    "0.9-1.0": calculate_success_rate(filter(overall_score >= 0.9)),
    "0.8-0.9": calculate_success_rate(filter(0.8 <= overall_score < 0.9)),
    "0.7-0.8": calculate_success_rate(filter(0.7 <= overall_score < 0.8)),
    "0.6-0.7": calculate_success_rate(filter(0.6 <= overall_score < 0.7))
}
```

**Expected Result**: Success rate increases with higher overall scores

### Hypothesis 2: Relevance Score is Most Important
**Question**: Does relevance_score predict success better than trust or reciprocity?

**Analysis**:
```python
# Calculate partial correlation while controlling for other factors
relevance_correlation = pearson_correlation(relevance_score, success_score)
trust_correlation = pearson_correlation(trust_score, success_score)
reciprocity_correlation = pearson_correlation(reciprocity_score, success_score)

# Determine which has highest correlation
dominant_factor = max(relevance_correlation, trust_correlation, reciprocity_correlation)
```

**Expected Result**: Relevance likely strongest, but trust may matter for high-value intros

### Hypothesis 3: Goal Type Alignment Matters
**Question**: Do certain goal type combinations succeed more?

**Analysis**:
```python
success_by_goal_pair = {
    ("fundraising", "fundraising"): calculate_success_rate(filter(both_fundraising)),
    ("fundraising", "hiring"): calculate_success_rate(filter(fundraising_hiring)),
    ("hiring", "hiring"): calculate_success_rate(filter(both_hiring)),
    ("cofounder", "cofounder"): calculate_success_rate(filter(both_cofounder))
}
```

**Expected Result**: Similar goal types may succeed more (mutual understanding)

### Hypothesis 4: Industry Match Boosts Success
**Question**: Do same-industry introductions succeed more?

**Analysis**:
```python
success_with_industry_match = calculate_success_rate(filter(industry_match == true))
success_without_industry_match = calculate_success_rate(filter(industry_match == false))

lift = (success_with_industry_match - success_without_industry_match) / success_without_industry_match
```

**Expected Result**: Industry match provides 10-20% lift in success rate

### Hypothesis 5: Match Type Affects Success
**Question**: Are goal-based matches more successful than ask-based?

**Analysis**:
```python
success_by_match_type = {
    "goal_based": calculate_success_rate(filter(match_type == "goal_based")),
    "ask_based": calculate_success_rate(filter(match_type == "ask_based")),
    "hybrid": calculate_success_rate(filter(match_type == "hybrid"))
}
```

**Expected Result**: Hybrid matches may have highest success (multiple signals)

## How to Improve Over Time

### Phase 1: Data Collection (Weeks 1-4)
**Objective**: Establish baseline metrics and collect sufficient data

**Actions**:
1. Deploy RLHF tracking to all introduction flows
2. Collect minimum 100 completed introductions
3. Calculate baseline success rate
4. Identify data quality issues

**Success Criteria**:
- 100+ introductions with outcomes
- < 5% missing data rate
- Baseline success rate established

### Phase 2: Analysis & Insights (Weeks 5-6)
**Objective**: Identify patterns and validate hypotheses

**Actions**:
1. Run correlation analysis on match factors
2. Test all hypotheses listed above
3. Identify high-success and low-success patterns
4. Generate insights report

**Success Criteria**:
- Hypotheses validated or rejected with statistical significance
- Identified top 3 predictive factors
- Found optimal score thresholds

### Phase 3: Algorithm Tuning (Weeks 7-8)
**Objective**: Adjust matching algorithm based on insights

**Potential Adjustments**:

1. **Adjust Factor Weights**
   ```python
   # Current
   RELEVANCE_WEIGHT = 0.5
   TRUST_WEIGHT = 0.25
   RECIPROCITY_WEIGHT = 0.25

   # If relevance is most predictive
   RELEVANCE_WEIGHT = 0.6
   TRUST_WEIGHT = 0.2
   RECIPROCITY_WEIGHT = 0.2

   # If trust matters more than expected
   RELEVANCE_WEIGHT = 0.5
   TRUST_WEIGHT = 0.35
   RECIPROCITY_WEIGHT = 0.15
   ```

2. **Increase Minimum Thresholds**
   ```python
   # Current
   MIN_OVERALL_SCORE = 0.6

   # If low-score intros fail often
   MIN_OVERALL_SCORE = 0.7
   ```

3. **Add New Factors**
   ```python
   # Industry match bonus
   if industry_match:
       overall_score *= 1.1

   # Goal type alignment bonus
   if goal_types_compatible:
       overall_score *= 1.05

   # Location proximity bonus
   if same_metro_area:
       overall_score *= 1.05
   ```

4. **Filter Low-Quality Suggestions**
   ```python
   # Don't suggest if relevance is too low
   if relevance_score < 0.65:
       skip_suggestion = True

   # Don't suggest if trust is too low
   if trust_score < 0.4:
       skip_suggestion = True
   ```

### Phase 4: A/B Testing (Weeks 9-12)
**Objective**: Validate improvements with controlled experiments

**Test Design**:
- Control Group (50%): Current algorithm (50/25/25 weights)
- Treatment Group (50%): New algorithm (optimized weights)

**Metrics**:
- Primary: Overall success rate
- Secondary: Response rate, completion rate, time to outcome
- Guardrail: Total suggestion volume (ensure not too restrictive)

**Success Criteria**:
- Treatment group shows 10%+ improvement in success rate
- Statistical significance (p < 0.05)
- No significant drop in suggestion volume

### Phase 5: Continuous Monitoring (Ongoing)
**Objective**: Monitor performance and detect drift

**Actions**:
1. Daily success rate tracking
2. Weekly performance reports
3. Monthly algorithm reviews
4. Quarterly retraining of ML models

**Alerts**:
- Success rate drops below baseline
- Response rate declines
- Data quality issues detected

## Edge Cases to Handle

### 1. No Response from Target
**Scenario**: Target never responds to introduction request

**Handling**:
- Auto-expire after 7 days
- Track as `status = "expired"`
- Feedback score: 0.0 (neutral failure)
- Don't penalize match scores too heavily (may be timing issue)

**Data Collection**:
```python
{
    "intro_id": "uuid",
    "outcome": "expired",
    "time_to_expiration_days": 7,
    "feedback_score": 0.0,
    "notes": "Auto-expired due to no response"
}
```

### 2. Partial Outcomes (Accept but No Completion)
**Scenario**: Target accepts but never marks intro as complete

**Handling**:
- After 14 days, prompt for outcome
- If no response after 30 days, mark as `incomplete`
- Feedback score: 0.3 (cautious negative)

**Data Collection**:
```python
{
    "intro_id": "uuid",
    "outcome": "incomplete",
    "status": "accepted",
    "responded_at": "...",
    "days_since_accept": 30,
    "feedback_score": 0.3
}
```

### 3. Negative Outcome After Accept
**Scenario**: Target accepts but later marks as "not relevant"

**Handling**:
- Track as valid data point
- Feedback score: 0.1 (acknowledge attempt)
- Analyze: Was accept too hasty? Score too low?

**Data Collection**:
```python
{
    "intro_id": "uuid",
    "outcome": "not_relevant",
    "status": "accepted_then_failed",
    "time_to_completion_days": 5,
    "feedback_score": 0.1,
    "notes": "Accepted initially but turned out not relevant"
}
```

### 4. Missing Feedback Data
**Scenario**: User completes intro but doesn't provide rating or notes

**Handling**:
- Use outcome_type as primary signal
- Infer success from completion alone
- Feedback score: 0.6 for meeting_scheduled, 0.5 for email_exchanged

**Data Collection**:
```python
{
    "intro_id": "uuid",
    "outcome": "meeting_scheduled",
    "rating": null,
    "notes": null,
    "feedback_score": 0.6,  # Inferred from outcome type
    "data_quality": "partial"
}
```

### 5. Conflicting Signals
**Scenario**: High rating but negative tags, or vice versa

**Handling**:
- Prioritize explicit rating over tags
- Flag for manual review if conflict is severe
- Use weighted average favoring rating

**Resolution Logic**:
```python
if rating >= 4 and "bad-match" in tags:
    # Rating wins but reduce confidence
    feedback_score = (rating / 5) * 0.8
    flag_for_review = True
elif rating <= 2 and "helpful" in tags:
    # Tags might indicate sarcasm or misclick
    feedback_score = (rating / 5) * 1.2
    flag_for_review = True
```

## Data Quality Assurance

### Validation Rules

1. **Completeness Checks**
   - All introductions must have: intro_id, requester_id, target_id, match_scores
   - At least one of: rating, outcome_type, or tags
   - Timestamps must be chronological

2. **Range Checks**
   - Scores: 0.0 ≤ score ≤ 1.0
   - Rating: 1 ≤ rating ≤ 5
   - Time ranges: 0 ≤ time_to_response_hours ≤ 168 (7 days)

3. **Consistency Checks**
   - If status = "declined", outcome should not be "meeting_scheduled"
   - If status = "expired", responded_at should be null
   - time_to_completion > time_to_response

### Data Cleaning Pipeline

```python
def clean_outcome_data(raw_data):
    """Clean and validate outcome data before RLHF tracking."""

    # Remove invalid scores
    for score in ["relevance", "trust", "reciprocity", "overall"]:
        if score not in raw_data["match_scores"]:
            raise ValueError(f"Missing score: {score}")
        if not (0.0 <= raw_data["match_scores"][score] <= 1.0):
            raise ValueError(f"Invalid score range: {score}")

    # Validate rating if present
    if "rating" in raw_data and raw_data["rating"]:
        if not (1 <= raw_data["rating"] <= 5):
            raw_data["rating"] = None  # Discard invalid rating

    # Ensure timestamps are chronological
    if raw_data.get("responded_at") and raw_data.get("requested_at"):
        if raw_data["responded_at"] < raw_data["requested_at"]:
            raise ValueError("responded_at before requested_at")

    # Calculate derived metrics
    if raw_data.get("responded_at"):
        raw_data["time_to_response_hours"] = calculate_time_diff_hours(
            raw_data["requested_at"],
            raw_data["responded_at"]
        )

    return raw_data
```

## Privacy and Ethics

### Data Collection Consent
- Users informed that introduction outcomes are tracked for improvement
- Opt-out option available in settings
- Notes/feedback anonymized before ML training

### Data Retention
- Raw RLHF data: 2 years
- Aggregated metrics: Indefinite
- User-identifiable feedback: Deleted on account closure

### Bias Mitigation
- Monitor success rates across user segments (geography, industry, gender)
- Flag if any segment shows < 50% of average success rate
- Regularly audit for algorithmic bias

## Success Metrics for RLHF System

### Primary KPIs

1. **Introduction Success Rate**
   - Baseline: TBD (establish in first 30 days)
   - Target: 60%+ of accepted introductions complete successfully
   - Excellent: 75%+ success rate

2. **Response Rate**
   - Baseline: TBD
   - Target: 50%+ of requests get accepted
   - Excellent: 65%+ acceptance rate

3. **Data Collection Rate**
   - Target: 80%+ of completed intros have outcome data
   - Excellent: 90%+ outcome data capture

### Secondary KPIs

1. **Time to Outcome**
   - Target: < 7 days average from request to completion
   - Excellent: < 5 days

2. **Algorithm Improvement Rate**
   - Target: 5% improvement in success rate per quarter
   - Excellent: 10%+ improvement per quarter

3. **User Satisfaction**
   - Target: 4.0+ average rating for completed intros
   - Excellent: 4.3+ average rating

## Next Steps

1. Implement RLHF tracking in `rlhf_service.py` (enhanced version)
2. Create analytics dashboard in `analytics_service.py`
3. Set up monitoring and alerts in `monitoring_service.py`
4. Deploy to production with feature flag
5. Collect baseline data for 30 days
6. Begin weekly analysis and optimization cycles

---

**Document Version**: 1.0
**Last Updated**: 2025-12-13
**Owner**: ML Engineering Team
**Review Cycle**: Quarterly

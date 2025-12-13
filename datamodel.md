# Data Model Specification

**Aligned to:** PRD v2 – Semantic AI Founder Network
**Purpose:** Define a production-ready data model that cleanly separates **relational truth**, **vector intelligence**, and **agent memory**, while allowing fast iteration and auditability.

---

## 1. Modeling Philosophy

PublicFounders uses a **dual-layer data model**:

1. **Relational Layer (Source of Truth)**

   * Deterministic
   * Auditable
   * Compliance-friendly

2. **Vector / Semantic Layer (Intelligence Layer)**

   * Probabilistic
   * Intent-aware
   * Continuously learning

> Relational data answers *“what is true?”*
> Vector data answers *“what is relevant?”*

Agents read from **both**, but only **write actions** through controlled relational endpoints.

---

## 2. High-Level Architecture

```
[ LinkedIn / User Input ]
            ↓
     Relational Store
            ↓
   Embedding Pipeline
            ↓
   ZeroDB Vector Store
            ↓
   Semantic Search APIs
            ↓
      AI Agents
            ↓
   Actions → Relational Store
```

---

## 3. Relational Data Model (SQL / Postgres)

### 3.1 Users

```sql
users (
  id UUID PK,
  linkedin_id TEXT UNIQUE,
  name TEXT,
  headline TEXT,
  profile_photo_url TEXT,
  location TEXT,
  phone_number TEXT NULL,
  email TEXT NULL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

---

### 3.2 Founder Profiles

```sql
founder_profiles (
  user_id UUID PK FK → users.id,
  bio TEXT,
  current_focus TEXT,
  autonomy_mode ENUM('suggest','approve','auto'),
  public_visibility BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

---

### 3.3 Companies

```sql
companies (
  id UUID PK,
  name TEXT,
  description TEXT,
  stage ENUM('idea','pre-seed','seed','series-a','series-b+'),
  industry TEXT,
  website TEXT,
  created_at TIMESTAMP
)
```

---

### 3.4 Founder ↔ Company Roles

```sql
company_roles (
  id UUID PK,
  user_id UUID FK → users.id,
  company_id UUID FK → companies.id,
  role TEXT,
  is_current BOOLEAN,
  start_date DATE,
  end_date DATE NULL
)
```

---

### 3.5 Goals

```sql
goals (
  id UUID PK,
  user_id UUID FK → users.id,
  type ENUM('fundraising','hiring','growth','partnerships','learning'),
  description TEXT,
  priority INT,
  is_active BOOLEAN,
  created_at TIMESTAMP
)
```

---

### 3.6 Asks

```sql
asks (
  id UUID PK,
  user_id UUID FK → users.id,
  goal_id UUID FK → goals.id NULL,
  description TEXT,
  urgency ENUM('low','medium','high'),
  status ENUM('open','fulfilled','closed'),
  created_at TIMESTAMP
)
```

---

### 3.7 Build-in-Public Posts

```sql
posts (
  id UUID PK,
  user_id UUID FK → users.id,
  type ENUM('progress','learning','milestone','ask'),
  content TEXT,
  is_cross_posted BOOLEAN,
  created_at TIMESTAMP
)
```

---

### 3.8 Introductions

```sql
introductions (
  id UUID PK,
  requester_id UUID FK → users.id,
  target_id UUID FK → users.id,
  agent_initiated BOOLEAN,
  channel ENUM('linkedin','sms','email'),
  rationale TEXT,
  status ENUM('proposed','sent','accepted','declined','successful','failed'),
  created_at TIMESTAMP
)
```

---

### 3.9 Interaction Outcomes

```sql
interaction_outcomes (
  id UUID PK,
  introduction_id UUID FK → introductions.id,
  outcome_type ENUM('meeting','investment','hire','partnership','none'),
  notes TEXT,
  recorded_at TIMESTAMP
)
```

---

## 4. Vector / Semantic Data Model (ZeroDB)

### 4.1 Embedding Collections

Each record references a **relational primary key**.

```
founder_embeddings
company_embeddings
goal_embeddings
ask_embeddings
post_embeddings
introduction_embeddings
interaction_embeddings
agent_memory_embeddings
```

---

### 4.2 Common Vector Schema

```json
{
  "id": "uuid",
  "entity_type": "founder | company | goal | ask | post | intro | interaction",
  "source_id": "relational_uuid",
  "embedding": [float],
  "metadata": {
    "user_id": "uuid",
    "stage": "seed",
    "industry": "fintech",
    "goal_type": "fundraising",
    "timestamp": "ISO-8601"
  }
}
```

---

### 4.3 Founder Embeddings

**Input Signals:**

* Bio + headline
* Current company context
* Goals + asks
* Posting history
* Outcome history

**Use Cases:**

* Founder similarity
* Investor / advisor matching
* Content relevance

---

### 4.4 Goal & Ask Embeddings

* Explicit intent vectors
* Weighted heavily in matching
* Decay over time if inactive

---

### 4.5 Post Embeddings

* Used for discovery
* Used to infer evolving intent
* Used to suggest intros

---

### 4.6 Introduction & Outcome Embeddings

* Captures *why* an intro was made
* Captures *what happened*
* Feeds reinforcement loop

---

## 5. Agent Memory Model (Vector-First)

Agents do **not** store state in relational tables unless auditable.

### Memory Types

1. **Short-term working memory**
2. **Long-term preference memory**
3. **Outcome-based learning memory**

```json
{
  "agent_id": "uuid",
  "memory_type": "preference | outcome | context",
  "content": "Founder prefers warm intros to operators",
  "embedding": [float],
  "confidence": 0.82,
  "last_updated": "ISO-8601"
}
```

---

## 6. Embedding Lifecycle

### Creation

* On signup
* On profile update
* On post / goal / ask creation

### Updates

* After introductions
* After outcomes
* Scheduled re-embedding

### Decay & Refresh

* Time-based decay
* Outcome-weighted reinforcement

---

## 7. Query Patterns

### Example 1: Find Relevant Intros

1. Query active goal embeddings
2. Semantic search across founder + investor vectors
3. Apply relational filters (stage, consent)
4. Rank by similarity × trust score

### Example 2: Agent Weekly Summary

1. Cluster recent interactions
2. Detect emerging themes
3. Generate recommendations

---

## 8. Guardrails & Auditability

* All **actions** logged relationally
* All **suggestions** traceable to embeddings
* Agent decisions include rationale vectors

---

## 9. Why This Model Works

* Clean separation of truth vs intelligence
* Safe for compliance and audits
* Optimized for agent autonomy
* Zero schema lock-in for matching logic

---

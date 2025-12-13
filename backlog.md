# Agile Product Backlog

**Aligned to:** PRD v2 – Semantic AI Founder Network
**Methodology:** Agile + TDD (Test-Driven Development) + BDD (Behavior-Driven Development)

This backlog is structured so:

* **Epics** align to product capabilities
* **User Stories** express user value
* **BDD scenarios** define behavior
* **TDD notes** define test boundaries

---

## EPIC 1: Identity, Authentication & Trust

### Story 1.1 – LinkedIn OAuth Sign-Up

**As a** founder
**I want** to sign up using LinkedIn
**So that** my identity and professional context are verified

**BDD – Scenarios:**

* Given I am not logged in
  When I click “Sign up with LinkedIn”
  Then I am authenticated via LinkedIn OAuth

* Given OAuth succeeds
  Then my user account is created with LinkedIn data

**TDD – Acceptance Tests:**

* User record is created exactly once
* LinkedIn ID is unique
* Failed OAuth does not create a user

---

### Story 1.2 – Phone Verification (Optional)

**As a** founder
**I want** to verify my phone number
**So that** I can receive SMS-based introductions

**BDD:**

* Given I enter a phone number
  When I receive and confirm a code
  Then my phone number is marked verified

**TDD:**

* Invalid codes fail verification
* Verified numbers are immutable without re-verification

---

## EPIC 2: Founder Profiles (Build-in-Public)

### Story 2.1 – Create Founder Profile

**As a** founder
**I want** an auto-generated profile
**So that** I can start building in public quickly

**BDD:**

* Given I sign up
  Then a founder profile is automatically created

**TDD:**

* Profile is created transactionally with user
* Default visibility is public

---

### Story 2.2 – Edit Profile & Focus

**As a** founder
**I want** to edit my bio and current focus
**So that** my intent is accurately represented

**BDD:**

* When I update my focus
  Then my profile embedding is regenerated

**TDD:**

* Profile update triggers embedding pipeline
* No partial updates allowed

---

## EPIC 3: Goals & Asks (Intent Capture)

### Story 3.1 – Create a Goal

**As a** founder
**I want** to define my current goal
**So that** the system understands my intent

**BDD:**

* Given I create a goal
  Then it appears on my profile

**TDD:**

* Goal is persisted relationally
* Goal embedding is created

---

### Story 3.2 – Create an Ask

**As a** founder
**I want** to post a specific ask
**So that** others (and agents) can help

**BDD:**

* Given an active goal
  When I create an ask
  Then it is linked to that goal

**TDD:**

* Ask cannot exist without a user
* Ask embedding references correct goal

---

## EPIC 4: Build-in-Public Feed

### Story 4.1 – Post an Update

**As a** founder
**I want** to share progress publicly
**So that** others can follow my journey

**BDD:**

* When I publish a post
  Then it appears in the feed

**TDD:**

* Post is stored before embedding
* Failed embedding does not block post

---

### Story 4.2 – Discover Relevant Founders

**As a** founder
**I want** to discover relevant updates
**So that** I can engage meaningfully

**BDD:**

* Given my goals
  When I browse the feed
  Then relevant posts rank higher

**TDD:**

* Semantic ranking is deterministic for same inputs

---

## EPIC 5: Semantic Intelligence (ZeroDB)

### Story 5.1 – Embedding Pipeline

**As a** system
**I want** to embed all meaningful objects
**So that** agents can reason semantically

**BDD:**

* Given new content
  Then an embedding job is queued

**TDD:**

* Embeddings reference relational IDs
* Failed jobs retry safely

---

### Story 5.2 – Semantic Search API

**As an** agent
**I want** to search semantically
**So that** I can find relevant people and content

**BDD:**

* Given a query vector
  Then relevant entities are returned

**TDD:**

* Metadata filters always apply
* Search results are ranked

---

## EPIC 6: Virtual Advisor Agent

### Story 6.1 – Initialize Advisor Agent

**As a** founder
**I want** a persistent advisor agent
**So that** I receive proactive help

**BDD:**

* Given I join the platform
  Then my advisor agent is created

**TDD:**

* Agent has isolated memory
* Agent cannot act without permissions

---

### Story 6.2 – Weekly Opportunity Summary

**As a** founder
**I want** a weekly summary
**So that** I understand opportunities

**BDD:**

* When the week ends
  Then a summary is generated

**TDD:**

* Summary is reproducible for same inputs

---

## EPIC 7: Intelligent Introductions

### Story 7.1 – Suggest an Introduction

**As an** agent
**I want** to suggest an intro
**So that** founders meet relevant people

**BDD:**

* Given high semantic similarity
  Then an intro is proposed

**TDD:**

* Similarity threshold is configurable

---

### Story 7.2 – Execute an Introduction

**As an** agent
**I want** to send an intro message
**So that** connections happen automatically

**BDD:**

* Given approval
  When intro is sent
  Then status updates to sent

**TDD:**

* Messages are idempotent
* Failed sends retry safely

---

## EPIC 8: Outcomes & Learning

### Story 8.1 – Record Intro Outcome

**As a** founder
**I want** to record what happened
**So that** the system learns

**BDD:**

* When an outcome is recorded
  Then embeddings are updated

**TDD:**

* Outcome must reference a valid intro

---

## EPIC 9: Permissions & Safety

### Story 9.1 – Autonomy Controls

**As a** founder
**I want** to control agent autonomy
**So that** I feel safe

**BDD:**

* Given autonomy is set to suggest-only
  Then no intros are auto-sent

**TDD:**

* Agent actions always check autonomy mode

---

## EPIC 10: Observability & Audit

### Story 10.1 – Action Audit Log

**As an** admin
**I want** a full audit log
**So that** agent actions are traceable

**BDD:**

* When an agent acts
  Then an audit record is created

**TDD:**

* Logs are immutable
* Logs reference source embeddings

---

## Delivery Notes

* Each story must have failing tests before implementation (TDD)
* Each story must pass BDD scenarios before acceptance
* Agent stories require simulation tests

---


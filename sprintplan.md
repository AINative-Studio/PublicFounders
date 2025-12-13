# Agile Sprint Plan – PRD v2 Implementation

**Based on:** Agile Backlog – Epics & User Stories (TDD/BDD Aligned)
**Purpose:** Define a detailed sprint plan for building the core of PublicFounders today, in multiple short sprints, with clear priorities, dependencies, and TDD/BDD alignment.

---

## Sprint 0 – Foundation Setup (Day 0)

**Goal:** Establish infrastructure, testing framework, and core relational database schema.

**Stories:**

1. Set up Postgres / relational DB with Users, Profiles, Companies, Roles, Goals, Asks, Posts, Introductions, Outcomes.
2. Set up ZeroDB Vector Store, embedding pipeline, and semantic search APIs.
3. Configure CI/CD, TDD framework, BDD harness.
4. Define API contracts for agent interactions.

**Deliverables:**

* Fully functioning development environment
* Empty schema + collections
* Test harness ready

**TDD/BDD:**

* Tests for database migrations
* Embedding creation pipeline test stubs

---

## Sprint 1 – Authentication & Profile Management (Day 1)

**Goal:** Enable founder signup, LinkedIn OAuth, phone verification, and profile creation.

**Stories:**

* LinkedIn OAuth signup
* Phone verification optional flow
* Auto-generated founder profile on signup
* Profile edit functionality with embedding trigger

**Dependencies:**

* Sprint 0 infra setup
* LinkedIn developer API credentials

**Deliverables:**

* Sign-up / login flow fully functional
* Editable profile with embedding trigger

**TDD/BDD:**

* OAuth success/failure test
* Phone verification tests
* Profile creation + update tests

---

## Sprint 2 – Goals, Asks & Posts (Day 1-2)

**Goal:** Capture founder intent and generate initial vector intelligence.

**Stories:**

* Create/Edit goals
* Create/Edit asks linked to goals
* Post progress updates, learnings, milestones, asks

**Dependencies:**

* Sprint 1 profiles
* ZeroDB embedding pipeline

**Deliverables:**

* Goals, asks, posts relationally stored and embedded
* Initial semantic search test working

**TDD/BDD:**

* Goal CRUD tests
* Ask CRUD tests
* Post creation + embedding tests

---

## Sprint 3 – Semantic Intelligence & Agent Initialization (Day 2)

**Goal:** Enable vector intelligence and agent reasoning foundation.

**Stories:**

* Generate embeddings for all relational objects
* Agent memory initialization
* Semantic search API ready

**Dependencies:**

* Sprint 2 content creation
* ZeroDB pipeline

**Deliverables:**

* Embeddings generated for all objects
* Agent memory ready for first interactions
* Search API functional

**TDD/BDD:**

* Embedding correctness test
* Semantic search returns expected results
* Agent memory read/write test

---

## Sprint 4 – Virtual Advisor & Intro Suggestions (Day 2-3)

**Goal:** Enable agent-driven suggestions for intros and content prompts.

**Stories:**

* Advisor agent initialization per founder
* Suggest introductions based on semantic similarity
* Suggest content/actions for engagement

**Dependencies:**

* Sprint 3 embeddings and agent memory

**Deliverables:**

* Advisor agent can suggest intros and posts
* First scenario BDD tests passing

**TDD/BDD:**

* Intro suggestion correctness
* Content suggestion tests
* Agent autonomy modes verified

---

## Sprint 5 – Introduction Execution & Outcome Tracking (Day 3-4)

**Goal:** Automate intro execution and record outcomes.

**Stories:**

* Send LinkedIn/SMS introductions (manual approve or auto)
* Record introduction outcomes
* Re-embed based on outcomes

**Dependencies:**

* Sprint 4 agent suggestions
* LinkedIn/SMS APIs

**Deliverables:**

* Automated intro sending pipeline
* Outcome recording and embedding refresh
* Feedback loop functional

**TDD/BDD:**

* Intro execution success/failure
* Outcome embedding refresh tests
* Autonomy mode enforcement tests

---

## Sprint 6 – Feed & Discovery (Day 4-5)

**Goal:** Enable founder discovery and build-in-public feed.

**Stories:**

* Feed aggregation from posts, goals, asks
* Semantic ranking for relevant content
* Cross-posting to LinkedIn

**Dependencies:**

* Sprint 5 introductions and embeddings

**Deliverables:**

* Feed populated and ranked semantically
* Engagement triggers working
* Cross-post functional

**TDD/BDD:**

* Feed ranking correctness
* Cross-post verification
* Privacy & visibility rules tests

---

## Sprint 7 – Permissions, Audit & Safety (Day 5)

**Goal:** Ensure compliance, auditability, and agent safety.

**Stories:**

* Autonomy mode controls for agents
* Audit logging for all agent actions
* Privacy settings for public visibility

**Dependencies:**

* All prior sprints

**Deliverables:**

* Full audit trail available
* Autonomy enforcement working
* Privacy settings functional

**TDD/BDD:**

* Agent action audit tests
* Autonomy enforcement tests
* Visibility filter tests

---

## Sprint 8 – KPI Tracking & Reporting (Day 5-6)

**Goal:** Track success metrics and provide founder insights.

**Stories:**

* Intro acceptance rate computation
* Response rate computation
* Engagement analytics
* Weekly summary generation for founders

**Dependencies:**

* Sprint 5 introductions
* Sprint 6 feed

**Deliverables:**

* KPI dashboard (developer view)
* Weekly automated summary ready

**TDD/BDD:**

* Metrics correctness tests
* Summary generation tests
* Data refresh tests

---

## Sprint Notes

* **Duration:** 1-week intensive sprints (8 sprints, overlapping as possible)
* **TDD/BDD:** Every feature begins with failing tests; scenarios executed continuously.
* **Dependencies:** Later sprints rely on earlier embeddings, relational truth, and agent memory.
* **Deliverables:** Production-ready MVP capable of: sign-up → profile → goals/asks → semantic suggestions → intro execution → feed → KPI tracking.

**Status:** Sprint Plan Ready for Execution

# Product Requirements Document (PRD v2)

## Product Name

**PublicFounders**

## One‑Line Description

A build‑in‑public founder network powered by LinkedIn data, AI‑native agents, and ZeroDB’s embedding, vector, and semantic search APIs to create intelligent introductions and autonomous growth.

---

## 1. Vision & Purpose

PublicFounders is a **semantic social network** designed for founders who build in public and grow through relationships, not reach.

Instead of a static social graph, the platform uses **intent embeddings** and **agent reasoning** to understand what founders are building, what they need, and who can help—then actively facilitates those connections.

The system is designed so AI agents are not assistants, but **participants** in the network.

---

## 2. Core Thesis

Traditional social networks rely on:

* Followers
* Connections
* Hard‑coded graphs

PublicFounders relies on:

* Meaning
* Intent
* Outcomes

Relationships are **inferred dynamically** via embeddings and semantic similarity, continuously improving as founders interact and outcomes are observed.

---

## 3. Target Users

### Primary

* Early‑stage founders (pre‑seed → Series A)
* Solo and technical founders
* Founders building in public as a growth strategy

### Secondary

* Angels and early‑stage investors
* Advisors and operators
* Recruiters hiring early teams

---

## 4. Core Use Cases

1. Founder documents progress, goals, and asks publicly
2. Platform embeds all activity into intent vectors
3. AI agents identify high‑quality matches semantically
4. Agent facilitates warm introductions via LinkedIn or SMS
5. Outcomes feed back into the system to improve future matches

---

## 5. Product Principles

* **Intent over popularity**
* **Embeddings over graphs**
* **Agents over dashboards**
* **Trust through verified identity and outcomes**

---

## 6. Authentication & Data Ingestion

### LinkedIn Integration (Mandatory)

**OAuth‑based sign‑up**

**Permitted Data Ingestion:**

* Name, headline, profile photo
* Current and past roles
* Companies
* Education
* Skills
* Location
* Public activity signals

All ingested data is:

* User‑consented
* Embedded (not mirrored)
* Used to seed semantic understanding

---

## 7. Founder Build‑in‑Public Profile

### Core Sections

* Auto‑generated + editable bio
* Current startup(s)
* What I’m building now
* Current goals (fundraising, hiring, partnerships, growth)
* Open asks
* Public timeline / journal

### AI Enhancements

* Founder narrative summary
* Goal clarity suggestions
* Ask optimization prompts

---

## 8. Build‑in‑Public Feed

### Content Types

* Progress updates
* Learnings & failures
* Milestones
* Explicit asks

### Feed Logic

* Chronological by default
* Semantic relevance for discovery
* No ads
* No engagement‑bait ranking

### AI Support

* Draft suggestions
* Cross‑posting to LinkedIn
* Cadence recommendations

---

## 9. Virtual Advisor Agent

### Role

A persistent AI agent representing the founder’s interests inside the network.

### Responsibilities

* Understand founder intent and goals
* Monitor semantic network activity
* Identify relevant people and opportunities
* Propose and execute introductions

### Autonomy Modes

* Suggest‑only
* Approve‑before‑intro
* Autonomous (with guardrails)

---

## 10. Intelligent Introductions

### Intro Sources

* PublicFounders users
* LinkedIn 1st‑degree connections
* Approved 2nd‑degree LinkedIn discovery

### Channels

* LinkedIn DM
* SMS (phone‑verified)
* Email (optional)

### Intro Flow

1. Semantic match detected via embeddings
2. Agent explains rationale to founder
3. Consent check (if required)
4. Personalized intro sent
5. Outcome tracked and embedded

---

## 11. Data & Intelligence Layer (ZeroDB)

### Stack

* ZeroDB Embedding API
* ZeroDB Vector Database
* ZeroDB Semantic Search APIs

### Embedded Objects

* Founders
* Companies
* Goals and asks
* Content and updates
* Introductions and outcomes
* Interaction summaries

### Semantic Relationships

Derived dynamically via similarity and clustering:

* Founder ↔ Founder (stage, goals, domain)
* Founder ↔ Investor (thesis alignment)
* Founder ↔ Advisor (experience overlap)

### Advantages

* No rigid schemas
* Strong cold‑start performance
* Continuous learning from outcomes
* Agent‑friendly reasoning layer

---

## 12. AI‑Native Agents API Integration

### Agent Types

* Founder Advisor Agent
* Network Growth Agent
* Content Strategy Agent
* Intro Quality Guard Agent

### Core APIs

* Embedding creation & updates
* Semantic search across entities
* Vector‑based agent memory
* Action execution (intros, drafts)
* Feedback ingestion

### Learning Loop

* Outcome‑weighted re‑embedding
* Similarity threshold tuning
* Personalized trust calibration

---

## 13. Permissions & Privacy

### User Controls

* Public vs private data
* Intro autonomy level
* Allowed communication channels
* Do‑not‑intro lists

### Compliance

* LinkedIn API policies
* GDPR / CCPA
* Explicit agent consent model

---

## 14. Success Metrics (KPIs)

### Network Health

* Intro acceptance rate
* Response rate
* Successful outcome ratio

### User Value

* Time to first meaningful intro
* Weekly active founders
* Retention by cohort

### Growth

* Agent‑initiated introductions
* Invite acceptance rate

---

## 15. MVP Scope

### Phase 1 – Semantic Foundation

* LinkedIn OAuth
* Founder profiles
* Build‑in‑public feed
* ZeroDB embeddings + vector search
* Human‑in‑the‑loop AI suggestions

### Phase 2 – Agent Execution

* Persistent advisor agent
* Semantic intro matching
* LinkedIn + SMS execution

### Phase 3 – Network Effects

* Multi‑agent collaboration
* Investor and advisor layers
* Monetization

---

## 16. Risks & Mitigations

| Risk                  | Mitigation                                  |
| --------------------- | ------------------------------------------- |
| Poor semantic matches | Human review + adaptive thresholds          |
| Agent overreach       | Autonomy controls + audit logs              |
| LinkedIn constraints  | Consent‑driven ingestion + user context     |
| Vector drift          | Scheduled re‑embedding + outcome correction |

---

## 17. Strategic Advantage

* Semantic network vs social graph
* AI agents as first‑class users
* Faster iteration than graph‑based systems
* Designed for autonomous growth

---

**Status:** Final Draft v2

**Owner:** Product

**Last Updated:** TBD

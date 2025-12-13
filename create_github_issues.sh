#!/bin/bash

# Script to create GitHub issues from PublicFounders backlog
# Repository: AINative-Studio/PublicFounders

REPO="AINative-Studio/PublicFounders"

echo "Creating GitHub issues for PublicFounders backlog..."
echo "Repository: $REPO"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. Install it with: brew install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

# EPIC 1: Identity, Authentication & Trust
echo "Creating EPIC 1: Identity, Authentication & Trust..."
gh issue create --repo "$REPO" \
  --title "EPIC 1: Identity, Authentication & Trust" \
  --label "epic,authentication" \
  --body "## Epic Overview
Build the foundation for user identity and trust through LinkedIn OAuth and optional phone verification.

## User Stories
- [ ] Story 1.1: LinkedIn OAuth Sign-Up
- [ ] Story 1.2: Phone Verification (Optional)

## Acceptance Criteria
- LinkedIn OAuth integration working
- User accounts created with verified LinkedIn identity
- Optional SMS verification for introductions
- TDD/BDD tests passing

## Technical Notes
- LinkedIn API integration required
- Twilio/SMS provider for phone verification
- Database schema: users, founder_profiles tables"

# Story 1.1
echo "Creating Story 1.1: LinkedIn OAuth Sign-Up..."
gh issue create --repo "$REPO" \
  --title "Story 1.1: LinkedIn OAuth Sign-Up" \
  --label "user-story,authentication,sprint-1" \
  --body "## User Story
**As a** founder
**I want** to sign up using LinkedIn
**So that** my identity and professional context are verified

## BDD Scenarios
\`\`\`gherkin
Given I am not logged in
When I click \"Sign up with LinkedIn\"
Then I am authenticated via LinkedIn OAuth
\`\`\`

## TDD Acceptance Tests
- [ ] User record is created exactly once
- [ ] LinkedIn ID is unique
- [ ] Failed OAuth does not create a user

## Technical Implementation
- LinkedIn OAuth 2.0 flow
- Store: name, headline, profile_photo_url, location, linkedin_id
- Database: users table"

# Story 1.2
echo "Creating Story 1.2: Phone Verification..."
gh issue create --repo "$REPO" \
  --title "Story 1.2: Phone Verification (Optional)" \
  --label "user-story,authentication,sprint-1" \
  --body "## User Story
**As a** founder
**I want** to verify my phone number
**So that** I can receive SMS-based introductions

## BDD Scenarios
\`\`\`gherkin
Given I enter a phone number
When I receive and confirm a code
Then my phone number is marked verified
\`\`\`

## TDD Acceptance Tests
- [ ] Invalid codes fail verification
- [ ] Verified numbers are immutable without re-verification"

# EPIC 2
echo "Creating EPIC 2: Founder Profiles..."
gh issue create --repo "$REPO" \
  --title "EPIC 2: Founder Profiles (Build-in-Public)" \
  --label "epic,profiles" \
  --body "## Epic Overview
Enable founders to create and manage their build-in-public profiles.

## User Stories
- [ ] Story 2.1: Create Founder Profile
- [ ] Story 2.2: Edit Profile & Focus

## Technical Notes
- Database: founder_profiles table
- ZeroDB: founder_embeddings collection"

# Story 2.1
gh issue create --repo "$REPO" \
  --title "Story 2.1: Create Founder Profile" \
  --label "user-story,profiles,sprint-1" \
  --body "## User Story
**As a** founder
**I want** an auto-generated profile
**So that** I can start building in public quickly

## TDD Acceptance Tests
- [ ] Profile is created transactionally with user
- [ ] Default visibility is public"

# Story 2.2
gh issue create --repo "$REPO" \
  --title "Story 2.2: Edit Profile & Focus" \
  --label "user-story,profiles,sprint-2,embeddings" \
  --body "## User Story
**As a** founder
**I want** to edit my bio and current focus
**So that** my intent is accurately represented

## TDD Acceptance Tests
- [ ] Profile update triggers embedding pipeline
- [ ] No partial updates allowed"

# EPIC 3
echo "Creating EPIC 3: Goals & Asks..."
gh issue create --repo "$REPO" \
  --title "EPIC 3: Goals & Asks (Intent Capture)" \
  --label "epic,intent" \
  --body "## Epic Overview
Capture founder intent through structured goals and asks.

## User Stories
- [ ] Story 3.1: Create a Goal
- [ ] Story 3.2: Create an Ask

## Technical Notes
- Database: goals, asks tables
- ZeroDB: goal_embeddings, ask_embeddings"

# Story 3.1
gh issue create --repo "$REPO" \
  --title "Story 3.1: Create a Goal" \
  --label "user-story,intent,sprint-2,embeddings" \
  --body "## User Story
**As a** founder
**I want** to define my current goal
**So that** the system understands my intent

## TDD Acceptance Tests
- [ ] Goal is persisted relationally
- [ ] Goal embedding is created"

# Story 3.2
gh issue create --repo "$REPO" \
  --title "Story 3.2: Create an Ask" \
  --label "user-story,intent,sprint-2,embeddings" \
  --body "## User Story
**As a** founder
**I want** to post a specific ask
**So that** others (and agents) can help

## TDD Acceptance Tests
- [ ] Ask cannot exist without a user
- [ ] Ask embedding references correct goal"

# Continue with more epics...
echo "Creating remaining epics..."

# EPIC 4
gh issue create --repo "$REPO" \
  --title "EPIC 4: Build-in-Public Feed" \
  --label "epic,feed" \
  --body "## Epic Overview
Enable founders to share progress and discover relevant content.

## User Stories
- [ ] Story 4.1: Post an Update
- [ ] Story 4.2: Discover Relevant Founders"

# EPIC 5
gh issue create --repo "$REPO" \
  --title "EPIC 5: Semantic Intelligence (ZeroDB)" \
  --label "epic,embeddings,semantic-search" \
  --body "## Epic Overview
Build the core semantic intelligence layer using ZeroDB.

## User Stories
- [ ] Story 5.1: Embedding Pipeline
- [ ] Story 5.2: Semantic Search API"

# EPIC 6
gh issue create --repo "$REPO" \
  --title "EPIC 6: Virtual Advisor Agent" \
  --label "epic,agents,ai" \
  --body "## Epic Overview
Create persistent AI advisor agents for each founder.

## User Stories
- [ ] Story 6.1: Initialize Advisor Agent
- [ ] Story 6.2: Weekly Opportunity Summary"

# EPIC 7
gh issue create --repo "$REPO" \
  --title "EPIC 7: Intelligent Introductions" \
  --label "epic,introductions,ai" \
  --body "## Epic Overview
Enable AI agents to suggest and execute intelligent introductions.

## User Stories
- [ ] Story 7.1: Suggest an Introduction
- [ ] Story 7.2: Execute an Introduction"

# EPIC 8
gh issue create --repo "$REPO" \
  --title "EPIC 8: Outcomes & Learning" \
  --label "epic,outcomes,learning" \
  --body "## Epic Overview
Track introduction outcomes and improve through RLHF.

## User Stories
- [ ] Story 8.1: Record Intro Outcome"

# EPIC 9
gh issue create --repo "$REPO" \
  --title "EPIC 9: Permissions & Safety" \
  --label "epic,permissions,safety" \
  --body "## Epic Overview
Implement comprehensive permission controls for agent autonomy.

## User Stories
- [ ] Story 9.1: Autonomy Controls"

# EPIC 10
gh issue create --repo "$REPO" \
  --title "EPIC 10: Observability & Audit" \
  --label "epic,audit,observability" \
  --body "## Epic Overview
Comprehensive audit logging for all agent actions.

## User Stories
- [ ] Story 10.1: Action Audit Log"

echo ""
echo "✅ Successfully created all GitHub issues!"
echo "View them at: https://github.com/$REPO/issues"

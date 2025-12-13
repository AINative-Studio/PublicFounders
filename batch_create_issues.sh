#!/bin/bash
REPO="AINative-Studio/PublicFounders"

# Story 1.1
gh issue create --repo "$REPO" --title "Story 1.1: LinkedIn OAuth Sign-Up" --body "## User Story
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

**Labels:** user-story, authentication, sprint-1, tdd, bdd"

# Story 1.2
gh issue create --repo "$REPO" --title "Story 1.2: Phone Verification (Optional)" --body "## User Story
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
- [ ] Verified numbers are immutable without re-verification

**Labels:** user-story, authentication, sprint-1"

# EPIC 2
gh issue create --repo "$REPO" --title "EPIC 2: Founder Profiles (Build-in-Public)" --body "## Epic Overview
Enable founders to create and manage their build-in-public profiles.

## User Stories
- [ ] Story 2.1: Create Founder Profile
- [ ] Story 2.2: Edit Profile & Focus

**Labels:** epic, profiles, sprint-1"

# Story 2.1
gh issue create --repo "$REPO" --title "Story 2.1: Create Founder Profile" --body "## User Story
**As a** founder  
**I want** an auto-generated profile  
**So that** I can start building in public quickly

## TDD Acceptance Tests
- [ ] Profile is created transactionally with user
- [ ] Default visibility is public

**Labels:** user-story, profiles, sprint-1"

# Story 2.2
gh issue create --repo "$REPO" --title "Story 2.2: Edit Profile & Focus" --body "## User Story
**As a** founder  
**I want** to edit my bio and current focus  
**So that** my intent is accurately represented

## TDD Acceptance Tests
- [ ] Profile update triggers embedding pipeline
- [ ] No partial updates allowed

**Labels:** user-story, profiles, sprint-2, embeddings"

echo "Created 5 issues so far..."

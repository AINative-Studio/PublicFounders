Feature: Build-in-public posts
  As a founder
  I want to share progress publicly
  So that others can follow my journey

  Background:
    Given I am an authenticated founder

  Scenario: Create post with async embedding
    When I create a post "Just shipped our MVP!"
    Then the post is stored before embedding
    And the embedding status is "pending"
    And I receive a successful response immediately
    And the embedding is created asynchronously

  Scenario: Failed embedding does not block post
    Given the embedding service is unavailable
    When I create a post "Making progress"
    Then the post is saved successfully
    And the embedding status is "failed"
    And the error is recorded

  Scenario: Post types are distinguished
    When I create a milestone post "Reached 1000 users"
    Then the post type is "milestone"
    And the embedding includes type prefix

  Scenario: Chronological feed shows newest first
    Given I created a post yesterday
    And I created a post one hour ago
    And I created a post just now
    When I view the feed
    Then the newest post appears first
    And posts are in reverse chronological order

  Scenario: Discover relevant posts based on goals
    Given I have a goal "Raise seed funding"
    And another founder posted "Just closed our seed round"
    And another founder posted "Tips for fundraising"
    When I use the discover feed
    Then I see posts relevant to my goals
    And posts are ranked by semantic similarity
    And recent posts are weighted higher

  Scenario: Cross-posting flag is respected
    When I create a post with cross-posting enabled
    Then the is_cross_posted flag is true
    And the post is marked for LinkedIn sharing

  Scenario: Update post content regenerates embedding async
    Given I have a post "Working on feature X"
    When I update the content to "Completed feature X, starting Y"
    Then the post content is updated
    And embedding regeneration is queued
    And I receive immediate response

  Scenario: Semantic discovery with recency weighting
    Given I have goals about "AI and machine learning"
    And there is a recent post about "ML model deployment"
    And there is an old post about "ML fundamentals"
    When I discover posts with 30% recency weight
    Then the recent post ranks higher
    And similarity and recency are combined

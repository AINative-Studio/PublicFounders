Feature: Create and manage goals
  As a founder
  I want to define my goals
  So that the system understands my intent

  Background:
    Given I am an authenticated founder

  Scenario: Create goal triggers embedding
    When I create a goal "Raise $1M seed round"
    Then the goal is saved in database
    And an embedding is created in ZeroDB
    And the goal appears on my profile

  Scenario: Create goal with all fields
    When I create a fundraising goal "Raise Series A funding" with priority 10
    Then the goal is saved with type "fundraising"
    And the goal has priority 10
    And the goal is active by default

  Scenario: List my active goals
    Given I have 3 active goals
    And I have 2 inactive goals
    When I list my active goals
    Then I see 3 goals in the response
    And all goals are marked as active

  Scenario: Update goal description regenerates embedding
    Given I have a goal "Hire engineers"
    When I update the goal description to "Hire senior backend engineers with AI experience"
    Then the goal description is updated
    And a new embedding is created

  Scenario: Delete goal removes embedding
    Given I have a goal "Learn Python"
    When I delete the goal
    Then the goal is removed from database
    And the embedding is deleted from ZeroDB

  Scenario: Goals are ordered by priority
    Given I have a goal "Fundraising" with priority 10
    And I have a goal "Hiring" with priority 5
    And I have a goal "Growth" with priority 8
    When I list my goals
    Then "Fundraising" appears first
    And "Growth" appears second
    And "Hiring" appears third

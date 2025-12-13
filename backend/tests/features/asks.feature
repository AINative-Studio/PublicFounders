Feature: Create and manage asks
  As a founder
  I want to post specific asks
  So that others and agents can help me

  Background:
    Given I am an authenticated founder

  Scenario: Create ask without goal
    When I create an ask "Need introductions to VCs"
    Then the ask is saved in database
    And the ask has no linked goal
    And an embedding is created for the ask

  Scenario: Create ask linked to goal
    Given I have an active goal "Raise funding"
    When I create an ask "Need warm intros to tier 1 VCs" linked to that goal
    Then the ask is saved in database
    And the ask embedding references correct goal
    And the ask appears under my goal

  Scenario: Ask urgency affects embedding
    When I create a high urgency ask "Need legal counsel ASAP"
    Then the embedding content includes urgency marker
    And the ask is marked as high urgency

  Scenario: Mark ask as fulfilled
    Given I have an open ask "Looking for beta testers"
    When I mark the ask as fulfilled
    Then the ask status is "fulfilled"
    And the fulfilled_at timestamp is set

  Scenario: List open asks only
    Given I have 2 open asks
    And I have 1 fulfilled ask
    And I have 1 closed ask
    When I list asks with status filter "open"
    Then I see 2 asks in the response
    And all asks have status "open"

  Scenario: Cannot create ask for someone else's goal
    Given another founder has a goal
    When I try to create an ask linked to their goal
    Then I receive a 400 error
    And the ask is not created

  Scenario: Ask status lifecycle
    Given I have an open ask
    When I mark it as fulfilled
    Then the status changes from "open" to "fulfilled"
    And the fulfilled_at timestamp is recorded

Feature: Pydantic Models
  As a developer
  I want validated request/response models
  So that API contracts are enforced

  Scenario: SqlQuery accepts valid SQL
    When I create a SqlQuery with "SELECT * FROM customers"
    Then the sql field is "SELECT * FROM customers"

  Scenario: SqlQuery accepts empty SQL
    When I create a SqlQuery with empty string
    Then the sql field is empty

  Scenario: TableSearchQuery uses defaults
    When I create a TableSearchQuery with text "customers"
    Then the text is "customers" and limit is 10

  Scenario: TableSearchQuery accepts custom limit
    When I create a TableSearchQuery with text "orders" and limit 5
    Then the limit is 5

  Scenario: TableResponse from DataFrame
    Given a sample DataFrame
    When I create a TableResponse from the sample DataFrame
    Then columns are ["id", "name", "country"]
    And row_count is 3

  Scenario: TableResponse from empty DataFrame
    When I create a TableResponse from an empty DataFrame
    Then row_count is 0

Feature: SQL Service Operations
  As a data analyst
  I want to explore tables, count rows, find distinct values and top values
  So that I can understand the data

  Scenario: Explore table with default limit
    Given a SQL service with mock data
    When I explore the table "customers" with default limit
    Then the last SQL query contains "select * from customers"
    And the last SQL query contains "limit 100"

  Scenario: Explore table with custom limit
    Given a SQL service with mock data
    When I explore the table "customers" with limit 10
    Then the last SQL query contains "limit 10"

  Scenario: Count rows in a table
    Given a SQL service with mock data
    When I count rows in table "customers"
    Then the last SQL query contains "select count(*) as count from customers"

  Scenario: Get distinct values
    Given a SQL service with mock data
    When I get distinct values of column "country" in table "customers"
    Then the last SQL query contains "select distinct country"

  Scenario: Get top values
    Given a SQL service with mock data
    When I get top 5 values of column "country" in table "customers"
    Then the last SQL query contains "group by country"
    And the last SQL query contains "limit 5"

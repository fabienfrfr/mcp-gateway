Feature: FastAPI Endpoints
  As an API consumer
  I want to query, explore, count, distinct and top via HTTP
  So that I can access data through REST

  Scenario: POST /query returns data
    Given a FastAPI test client with mock service
    When I POST to "/query" with sql "SELECT * FROM customers"
    Then the response status is 200
    And the response has "columns", "rows" and "row_count"

  Scenario: POST /query rejects forbidden SQL
    Given a FastAPI test client with mock service
    When I POST to "/query" with sql "DELETE FROM customers"
    Then the response status is 400

  Scenario: GET /explore returns data
    Given a FastAPI test client with mock service
    When I GET "/explore/customers?limit=10"
    Then the response status is 200
    And the row_count is 3

  Scenario: GET /count returns count
    Given a FastAPI test client with count mock
    When I GET "/count/customers"
    Then the response status is 200
    And the response contains column "count"

  Scenario: GET /distinct returns distinct values
    Given a FastAPI test client with mock service
    When I GET "/distinct/customers/country"
    Then the response status is 200
    And the response contains column "country"

  Scenario: GET /top returns top values
    Given a FastAPI test client with mock service
    When I GET "/top/customers/country?limit=5"
    Then the response status is 200
    And the row_count is 3

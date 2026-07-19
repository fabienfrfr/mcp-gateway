Feature: SQL Portal Client
  As a gateway developer
  I want the client to parse JSON and CSV responses
  So that different SQL portal formats are supported

  Scenario: Parse JSON response
    Given a SQL portal client
    When the portal returns JSON '[{"id": 1, "name": "Alice"}]'
    Then the result has 1 rows

  Scenario: Parse CSV fallback
    Given a SQL portal client
    When the portal returns CSV "id,name\n1,Alice\n2,Bob"
    Then the result has 2 rows

  Scenario: Raise error on unparseable response
    Given a SQL portal client
    When the portal returns unparseable content
    Then a RuntimeError is raised with message "Unable to parse SQL portal response"

  Scenario: Authentication is set when login provided
    Given a SQL portal client with login "admin" and password "secret"
    Then the session auth matches

  Scenario: No authentication when login is None
    Given a SQL portal client without credentials
    Then the session has no auth

  Scenario: SSL verification is disabled by default
    Given a SQL portal client without credentials
    Then SSL verification is disabled

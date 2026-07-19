Feature: SQL Query Security
  As a gateway administrator
  I want to prevent destructive SQL operations
  So that the database remains read-only

  Scenario Outline: Forbidden SQL keywords are blocked
    Given a SQL service
    When I execute the query "<sql>"
    Then a forbidden keyword error is raised for "<keyword>"

    Examples:
      | sql                                      | keyword  |
      | INSERT INTO customers VALUES (1, 'test') | insert   |
      | UPDATE customers SET name='test'         | update   |
      | DELETE FROM customers                    | delete   |
      | DROP TABLE customers                     | drop     |
      | ALTER TABLE customers ADD col INT        | alter    |
      | TRUNCATE TABLE customers                 | truncate |
      | CREATE TABLE test (id INT)               | create   |
      | GRANT ALL ON customers TO user           | grant    |
      | REVOKE ALL ON customers FROM user        | revoke   |

  Scenario: SQL keyword check is case-insensitive
    Given a SQL service
    When I execute the query "INSERT INTO customers VALUES (1)"
    Then a forbidden keyword error is raised for "insert"

  Scenario: Forbidden keywords in subqueries are blocked
    Given a SQL service
    When I execute the query "SELECT * FROM (DELETE FROM customers) sub"
    Then the query is rejected

  Scenario: SELECT queries are allowed
    Given a SQL service with mock data
    When I execute the query "SELECT * FROM customers"
    Then the query returns 3 rows

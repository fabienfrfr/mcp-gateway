Feature: Metadata Semantic Search
  As a data analyst
  I want to search tables by semantic similarity
  So that I can find relevant tables without knowing exact names

  Scenario: Metadata without table_name raises error
    Given a metadata dataframe without "table_name" column
    When I initialize the metadata search service
    Then a ValueError is raised for "table_name"

  Scenario: Search returns results sorted by score
    Given a metadata search service with sample data
    When I search for "customer" with limit 2
    Then 2 results are returned
    And results have "table_name" and "score" fields
    And results are sorted by descending score

  Scenario: Empty descriptions are handled gracefully
    Given a metadata search service with empty descriptions
    When I search for "important" with limit 2
    Then 2 results are returned

  Scenario: Embeddings have correct shape
    Given a metadata search service with sample data
    Then the embeddings matrix has 3 rows

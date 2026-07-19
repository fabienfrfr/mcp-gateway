import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from main import SqlService

scenarios("features/sql_service.feature")
scenarios("features/sql_operations.feature")


@pytest.fixture
def executed_query():
    return {"sql": None, "error": None}


@pytest.fixture
def last_query():
    return {"sql": None}


@given("a SQL service", target_fixture="sql_svc")
def sql_service_only(mocker):
    client = mocker.MagicMock()
    return SqlService(client)


@given("a SQL service with mock data", target_fixture="sql_svc")
def sql_service_with_data(mocker):
    client = mocker.MagicMock()
    client.execute_sql.return_value = pd.DataFrame(
        [
            {"id": 1, "name": "Alice", "country": "FR"},
            {"id": 2, "name": "Bob", "country": "US"},
            {"id": 3, "name": "Charlie", "country": "FR"},
        ]
    )
    return SqlService(client)


@when(parsers.parse('I execute the query "{sql}"'))
def execute_query(sql_svc, executed_query, sql):
    executed_query["sql"] = sql
    try:
        sql_svc.query(sql)
    except ValueError as e:
        executed_query["error"] = e


@when(parsers.parse('I explore the table "{table}" with default limit'))
def explore_default(sql_svc, last_query):
    sql_svc.explore("customers")
    last_query["sql"] = sql_svc.client.execute_sql.call_args[0][0]


@when(parsers.parse('I explore the table "{table}" with limit {limit:d}'))
def explore_custom(sql_svc, last_query):
    sql_svc.explore("customers", limit=10)
    last_query["sql"] = sql_svc.client.execute_sql.call_args[0][0]


@when(parsers.parse('I count rows in table "{table}"'))
def count_rows(sql_svc, last_query):
    sql_svc.count("customers")
    last_query["sql"] = sql_svc.client.execute_sql.call_args[0][0]


@when(parsers.parse('I get distinct values of column "{column}" in table "{table}"'))
def distinct_values(sql_svc, last_query):
    sql_svc.distinct("customers", "country")
    last_query["sql"] = sql_svc.client.execute_sql.call_args[0][0]


@when(parsers.parse('I get top {limit:d} values of column "{column}" in table "{table}"'))
def top_values(sql_svc, last_query):
    sql_svc.top("customers", "country", limit=5)
    last_query["sql"] = sql_svc.client.execute_sql.call_args[0][0]


@then(parsers.parse('a forbidden keyword error is raised for "{keyword}"'))
def check_forbidden(executed_query, keyword):
    assert executed_query["error"] is not None
    assert "Forbidden SQL keyword" in str(executed_query["error"])
    assert keyword in str(executed_query["error"])


@then("the query is rejected")
def check_rejected(executed_query):
    assert executed_query["error"] is not None


@then("the query returns 3 rows")
def check_rows(executed_query):
    assert executed_query["error"] is None


@then(parsers.parse('the last SQL query contains "{fragment}"'))
def check_sql_fragment(last_query, fragment):
    assert fragment.lower() in last_query["sql"].lower()

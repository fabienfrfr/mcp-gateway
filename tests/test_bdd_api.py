import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from main import app

scenarios("features/api.feature")


def _make_mock_client(mocker, df=None):
    from fastapi.testclient import TestClient

    client = TestClient(app, raise_server_exceptions=False)
    mock_client = mocker.MagicMock()
    mock_client.execute_sql.return_value = df if df is not None else pd.DataFrame(
        [
            {"id": 1, "name": "Alice", "country": "FR"},
            {"id": 2, "name": "Bob", "country": "US"},
            {"id": 3, "name": "Charlie", "country": "FR"},
        ]
    )
    client.app.state.sql_client = mock_client
    return {"client": client, "response": None}


@given("a FastAPI test client with mock service", target_fixture="api_ctx")
def setup_client(mocker):
    return _make_mock_client(mocker)


@given("a FastAPI test client with count mock", target_fixture="api_ctx")
def setup_count_client(mocker):
    return _make_mock_client(mocker, df=pd.DataFrame({"count": [3]}))


@when(parsers.parse('I POST to "{path}" with sql "{sql}"'))
def post_query(api_ctx, path, sql):
    api_ctx["response"] = api_ctx["client"].post(path, json={"sql": sql})


@when(parsers.parse('I GET "{path}"'))
def get_path(api_ctx, path):
    api_ctx["response"] = api_ctx["client"].get(path)


@then(parsers.parse("the response status is {status:d}"))
def check_status(api_ctx, status):
    assert api_ctx["response"].status_code == status


@then('the response has "columns", "rows" and "row_count"')
def check_response_fields(api_ctx):
    data = api_ctx["response"].json()
    assert "columns" in data
    assert "rows" in data
    assert "row_count" in data


@then(parsers.parse("the row_count is {count:d}"))
def check_row_count(api_ctx, count):
    assert api_ctx["response"].json()["row_count"] == count


@then(parsers.parse('the response contains column "{col}"'))
def check_column(api_ctx, col):
    data = api_ctx["response"].json()
    assert col in data["columns"]

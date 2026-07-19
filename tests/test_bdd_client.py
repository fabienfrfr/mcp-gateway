import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from main import SqlPortalClient

scenarios("features/client.feature")


@pytest.fixture
def parse_result():
    return {"result": None, "error": None}


@given("a SQL portal client", target_fixture="pc")
def make_portal_client():
    return SqlPortalClient(url="http://fake/api")


@given(parsers.parse('a SQL portal client with login "{login}" and password "{password}"'), target_fixture="pc")
def make_portal_client_auth(login, password):
    return SqlPortalClient(url="http://fake/api", login=login, password=password)


@given("a SQL portal client without credentials", target_fixture="pc")
def make_portal_client_no_auth():
    return SqlPortalClient(url="http://fake/api")


@when(parsers.parse("the portal returns JSON '{json_data}'"))
def returns_json(pc, parse_result, json_data, mocker):
    mock_response = mocker.MagicMock()
    mock_response.text = json_data
    mock_response.raise_for_status = mocker.MagicMock()
    mocker.patch.object(pc.session, "get", return_value=mock_response)
    parse_result["result"] = pc.execute_sql("SELECT * FROM t")


@when(parsers.parse('the portal returns CSV "{csv_data}"'))
def returns_csv(pc, parse_result, csv_data, mocker):
    mock_response = mocker.MagicMock()
    mock_response.text = csv_data.replace("\\n", "\n")
    mock_response.raise_for_status = mocker.MagicMock()
    mocker.patch.object(pc.session, "get", return_value=mock_response)
    parse_result["result"] = pc.execute_sql("SELECT * FROM t")


@when("the portal returns unparseable content")
def returns_bad(pc, parse_result, mocker):
    mock_response = mocker.MagicMock()
    mock_response.text = "???broken???"
    mock_response.raise_for_status = mocker.MagicMock()
    mocker.patch.object(pc.session, "get", return_value=mock_response)
    mocker.patch("main.pd.read_json", side_effect=ValueError("bad json"))
    mocker.patch("main.pd.read_csv", side_effect=ValueError("bad csv"))
    try:
        pc.execute_sql("SELECT * FROM t")
    except RuntimeError as e:
        parse_result["error"] = e


@then(parsers.parse("the result has {count:d} rows"))
def check_row_count(parse_result, count):
    assert len(parse_result["result"]) == count


@then('a RuntimeError is raised with message "Unable to parse SQL portal response"')
def check_runtime_error(parse_result):
    assert parse_result["error"] is not None
    assert "Unable to parse SQL portal response" in str(parse_result["error"])


@then("the session auth matches")
def check_auth(pc):
    assert pc.session.auth == ("admin", "secret")


@then("the session has no auth")
def check_no_auth(pc):
    assert pc.session.auth is None


@then("SSL verification is disabled")
def check_ssl(pc):
    assert pc.verify_ssl is False

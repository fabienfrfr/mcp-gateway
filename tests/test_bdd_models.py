import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from main import SqlQuery, TableResponse, TableSearchQuery

scenarios("features/models.feature")


@pytest.fixture
def model_result():
    return {"obj": None}


@when(parsers.parse('I create a SqlQuery with "{sql}"'))
def create_sql_query(model_result, sql):
    model_result["obj"] = SqlQuery(sql=sql)


@when("I create a SqlQuery with empty string")
def create_sql_query_empty(model_result):
    model_result["obj"] = SqlQuery(sql="")


@when(parsers.parse('I create a TableSearchQuery with text "{text}"'))
def create_search_default(model_result, text):
    model_result["obj"] = TableSearchQuery(text=text)


@when(parsers.parse('I create a TableSearchQuery with text "{text}" and limit {limit:d}'))
def create_search_custom(model_result, text, limit):
    model_result["obj"] = TableSearchQuery(text=text, limit=limit)


@when("I create a TableResponse from the sample DataFrame")
def create_response_from_sample(model_result):
    model_result["obj"] = TableResponse.from_dataframe(
        pd.DataFrame(
            [
                {"id": 1, "name": "Alice", "country": "FR"},
                {"id": 2, "name": "Bob", "country": "US"},
                {"id": 3, "name": "Charlie", "country": "FR"},
            ]
        )
    )


@when("I create a TableResponse from an empty DataFrame")
def create_response_empty(model_result):
    model_result["obj"] = TableResponse.from_dataframe(pd.DataFrame(columns=["a", "b"]))


@then(parsers.parse('the sql field is "{expected}"'))
def check_sql_field(model_result, expected):
    assert model_result["obj"].sql == expected


@then("the sql field is empty")
def check_sql_field_empty(model_result):
    assert model_result["obj"].sql == ""


@then(parsers.parse('the text is "{text}" and limit is {limit:d}'))
def check_search_default(model_result, text, limit):
    assert model_result["obj"].text == text
    assert model_result["obj"].limit == limit


@then(parsers.parse("the limit is {limit:d}"))
def check_limit(model_result, limit):
    assert model_result["obj"].limit == limit


@then(parsers.parse('columns are ["{c1}", "{c2}", "{c3}"]'))
def check_columns(model_result, c1, c2, c3):
    assert model_result["obj"].columns == [c1, c2, c3]


@then(parsers.parse("row_count is {count:d}"))
def check_row_count(model_result, count):
    assert model_result["obj"].row_count == count


@given("a sample DataFrame")
def sample_df():
    pass

import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from main import MetadataSearchService

scenarios("features/metadata_search.feature")


@pytest.fixture
def meta_ctx():
    return {"service": None, "results": None, "error": None}


@given('a metadata dataframe without "table_name" column', target_fixture="bad_df")
def df_without_table_name():
    return pd.DataFrame({"description": ["test"]})


@given("a metadata search service with sample data", target_fixture="meta_svc")
def make_search_service():
    df = pd.DataFrame(
        [
            {"table_name": "customers", "description": "Customer master data"},
            {"table_name": "orders", "description": "Customer orders"},
            {"table_name": "products", "description": "Product catalog"},
        ]
    )
    return MetadataSearchService(df)


@given("a metadata search service with empty descriptions", target_fixture="meta_svc")
def make_search_service_empty():
    df = pd.DataFrame(
        [
            {"table_name": "a", "description": ""},
            {"table_name": "b", "description": "important data"},
        ]
    )
    return MetadataSearchService(df)


@when("I initialize the metadata search service")
def init_service(meta_ctx, bad_df):
    try:
        meta_ctx["service"] = MetadataSearchService(bad_df)
    except ValueError as e:
        meta_ctx["error"] = e


@when(parsers.parse('I search for "{query}" with limit {limit:d}'))
def do_search(meta_ctx, meta_svc, query, limit):
    meta_ctx["service"] = meta_svc
    meta_ctx["results"] = meta_svc.search(query, limit=limit)


@then('a ValueError is raised for "table_name"')
def check_value_error(meta_ctx):
    assert meta_ctx["error"] is not None
    assert "table_name" in str(meta_ctx["error"])


@then(parsers.parse("{count:d} results are returned"))
def check_result_count(meta_ctx, count):
    assert len(meta_ctx["results"]) == count


@then('results have "table_name" and "score" fields')
def check_fields(meta_ctx):
    for r in meta_ctx["results"]:
        assert "table_name" in r
        assert "score" in r


@then("results are sorted by descending score")
def check_sorted(meta_ctx):
    scores = [r["score"] for r in meta_ctx["results"]]
    assert scores == sorted(scores, reverse=True)


@then(parsers.parse("the embeddings matrix has {count:d} rows"))
def check_embeddings(meta_svc, count):
    assert meta_svc.embeddings.shape == (count, meta_svc.embeddings.shape[1])

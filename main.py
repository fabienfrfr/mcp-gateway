from __future__ import annotations

import os
from contextlib import asynccontextmanager

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Request
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SQL_PORTAL_URL = os.getenv("SQL_PORTAL_URL", "")
SQL_PORTAL_LOGIN = os.getenv("SQL_PORTAL_LOGIN", "")
SQL_PORTAL_PASSWORD = os.getenv("SQL_PORTAL_PASSWORD", "")
VERIFY_SSL = os.getenv("SQL_PORTAL_VERIFY_SSL", "false").lower() == "true"


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------


class SqlQuery(BaseModel):
    sql: str


class TableResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "TableResponse":
        return cls(
            columns=list(df.columns),
            rows=df.to_dict(orient="records"),
            row_count=len(df),
        )


# -----------------------------------------------------------------------------
# Client
# -----------------------------------------------------------------------------


class SqlPortalClient:
    """
    Generic HTTP client for a SQL portal.

    Assumes a GET endpoint receiving:
        ?sql=<query>

    Adapt execute_sql() if your portal expects another format.
    """

    def __init__(
        self,
        url: str,
        login: str | None = None,
        password: str | None = None,
        verify_ssl: bool = False,
    ) -> None:
        self.url = url
        self.session = requests.Session()
        self.verify_ssl = verify_ssl

        if login:
            self.session.auth = (login, password or "")

    def execute_sql(self, sql: str) -> pd.DataFrame:
        response = self.session.get(
            self.url,
            params={"sql": sql},
            verify=self.verify_ssl,
            timeout=300,
        )

        response.raise_for_status()

        try:
            return pd.read_json(response.text)
        except Exception:
            try:
                from io import StringIO

                return pd.read_csv(StringIO(response.text))
            except Exception as exc:
                raise RuntimeError("Unable to parse portal response") from exc


# -----------------------------------------------------------------------------
# Service
# -----------------------------------------------------------------------------


class SqlService:
    FORBIDDEN = {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "create",
        "grant",
        "revoke",
    }

    def __init__(self, client: SqlPortalClient):
        self.client = client

    def query(self, sql: str) -> pd.DataFrame:
        lowered = sql.lower()

        for keyword in self.FORBIDDEN:
            if keyword in lowered:
                raise ValueError(f"Forbidden SQL keyword detected: {keyword}")

        return self.client.execute_sql(sql)

    def explore(self, table: str, limit: int = 100) -> pd.DataFrame:
        return self.query(f"select * from {table} limit {int(limit)}")

    def count(self, table: str) -> pd.DataFrame:
        return self.query(f"select count(*) as count from {table}")

    def distinct(self, table: str, column: str) -> pd.DataFrame:
        return self.query(f"select distinct {column} from {table} order by {column}")

    def top(
        self,
        table: str,
        column: str,
        limit: int = 10,
    ) -> pd.DataFrame:
        return self.query(
            f"select {column}, count(*) as count from {table} group by {column} order by count desc limit {int(limit)}"
        )


# -----------------------------------------------------------------------------
# Lifespan
# -----------------------------------------------------------------------------


@asynccontextmanager
async def portal_lifespan(app: FastAPI):
    app.state.sql_client = SqlPortalClient(
        url=SQL_PORTAL_URL,
        login=SQL_PORTAL_LOGIN,
        password=SQL_PORTAL_PASSWORD,
        verify_ssl=VERIFY_SSL,
    )

    yield


# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------

app = FastAPI(title="SQL MCP Gateway")


def get_service(request: Request) -> SqlService:
    return SqlService(request.app.state.sql_client)


@app.post(
    "/query",
    operation_id="query_sql",
    response_model=TableResponse,
)
def query_sql(
    query: SqlQuery,
    request: Request,
) -> TableResponse:
    """
    Execute a read-only SQL query.
    """
    try:
        df = get_service(request).query(query.sql)
        return TableResponse.from_dataframe(df)

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get(
    "/explore/{table}",
    operation_id="explore_table",
    response_model=TableResponse,
)
def explore_table(
    table: str,
    request: Request,
    limit: int = 100,
) -> TableResponse:
    """
    Return sample rows from a table.
    """
    df = get_service(request).explore(table, limit)
    return TableResponse.from_dataframe(df)


@app.get(
    "/count/{table}",
    operation_id="count_rows",
    response_model=TableResponse,
)
def count_rows(
    table: str,
    request: Request,
) -> TableResponse:
    """
    Count rows in a table.
    """
    df = get_service(request).count(table)
    return TableResponse.from_dataframe(df)


@app.get(
    "/distinct/{table}/{column}",
    operation_id="distinct_values",
    response_model=TableResponse,
)
def distinct_values(
    table: str,
    column: str,
    request: Request,
) -> TableResponse:
    """
    Return distinct values from a column.
    """
    df = get_service(request).distinct(table, column)
    return TableResponse.from_dataframe(df)


@app.get(
    "/top/{table}/{column}",
    operation_id="top_values",
    response_model=TableResponse,
)
def top_values(
    table: str,
    column: str,
    request: Request,
    limit: int = 10,
) -> TableResponse:
    """
    Return most frequent values.
    """
    df = get_service(request).top(
        table,
        column,
        limit,
    )

    return TableResponse.from_dataframe(df)


# -----------------------------------------------------------------------------
# MCP
# -----------------------------------------------------------------------------

mcp = FastMCP.from_fastapi(
    app=app,
    name="SQL Gateway",
)

mcp_app = mcp.http_app(path="/")

app.router.lifespan_context = combine_lifespans(
    portal_lifespan,
    mcp_app.lifespan,
)

app.mount("/mcp", mcp_app)

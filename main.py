from __future__ import annotations

import os
from contextlib import asynccontextmanager
from io import StringIO

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastembed import TextEmbedding
from fastmcp import FastMCP
from fastmcp.utilities.lifespan import combine_lifespans
from pydantic import BaseModel

from pathlib import Path
from sqlalchemy import create_engine

load_dotenv()


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SQL_PORTAL_URL = os.getenv("SQL_PORTAL_URL", "")
SQL_PORTAL_LOGIN = os.getenv("SQL_PORTAL_LOGIN", "")
SQL_PORTAL_PASSWORD = os.getenv("SQL_PORTAL_PASSWORD", "")

VERIFY_SSL = os.getenv("SQL_PORTAL_VERIFY_SSL", "false").lower() == "true"

METADATA_SQL = os.getenv(
    "SQL_METADATA_SQL",
    """
    select
        table_name,
        description
    from metadata_tables
    """,
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------


class SqlQuery(BaseModel):
    sql: str


class TableSearchQuery(BaseModel):
    text: str
    limit: int = 10


class TableResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "TableResponse":
        return cls(columns=list(df.columns), rows=df.to_dict(orient="records"), row_count=len(df))


# -----------------------------------------------------------------------------
# Client
# -----------------------------------------------------------------------------


class SqlPortalClient:
    """Generic HTTP SQL portal client.

    Assumes:

        GET ?sql=<query>

    Adapt if needed.
    """

    def __init__(
        self, url: str, login: str | None = None, password: str | None = None, verify_ssl: bool = False
    ) -> None:
        self.url = url
        self.verify_ssl = verify_ssl

        self.session = requests.Session()

        if login:
            self.session.auth = (login, password or "")

    def execute_sql(self, sql: str) -> pd.DataFrame:
        response = self.session.get(self.url, params={"sql": sql}, verify=self.verify_ssl, timeout=300)

        response.raise_for_status()

        try:
            return pd.read_json(StringIO(response.text))
        except Exception:
            try:
                return pd.read_csv(StringIO(response.text))
            except Exception as exc:
                raise RuntimeError("Unable to parse SQL portal response") from exc


# -----------------------------------------------------------------------------
# Semantic Metadata Search
# -----------------------------------------------------------------------------


class MetadataSearchService:
    def __init__(self, metadata: pd.DataFrame) -> None:
        self.metadata = metadata.copy()

        if "table_name" not in self.metadata.columns:
            raise ValueError("Metadata must contain table_name")

        if "description" not in self.metadata.columns:
            self.metadata["description"] = ""

        self.model = TextEmbedding(model_name=EMBEDDING_MODEL)

        texts = (
            self.metadata["table_name"].fillna("").astype(str)
            + ". "
            + self.metadata["description"].fillna("").astype(str)
        ).tolist()

        self.embeddings = np.vstack(list(self.model.embed(texts)))

    def search(self, query: str, limit: int = 10) -> list:
        query_embedding = np.asarray(list(self.model.embed([query]))[0])

        scores = self.embeddings @ query_embedding

        indices = np.argsort(scores)[::-1][:limit]

        results = []

        for idx in indices:
            row = self.metadata.iloc[idx]

            results.append(
                {"table_name": row["table_name"], "description": row["description"], "score": float(scores[idx])}
            )

        return results


# -----------------------------------------------------------------------------
# SQL Service
# -----------------------------------------------------------------------------


class SqlService:
    FORBIDDEN = {"insert", "update", "delete", "drop", "alter", "truncate", "create", "grant", "revoke"}

    def __init__(self, client: SqlPortalClient):
        self.client = client

    def query(self, sql: str) -> pd.DataFrame:
        lowered = sql.lower()

        for keyword in self.FORBIDDEN:
            if keyword in lowered:
                raise ValueError(f"Forbidden SQL keyword: {keyword}")

        return self.client.execute_sql(sql)

    def explore(self, table: str, limit: int = 100) -> pd.DataFrame:
        return self.query(f"select * from {table} limit {int(limit)}")

    def count(self, table: str) -> pd.DataFrame:
        return self.query(f"select count(*) as count from {table}")

    def distinct(self, table: str, column: str) -> pd.DataFrame:
        return self.query(f"select distinct {column} from {table} order by {column}")

    def top(self, table: str, column: str, limit: int = 10) -> pd.DataFrame:
        return self.query(
            f"select {column}, count(*) as count from {table} group by {column} order by count desc limit {int(limit)}"
        )


# -----------------------------------------------------------------------------
# Lifespan
# -----------------------------------------------------------------------------

@asynccontextmanager
async def portal_lifespan(app: FastAPI):
    if SQL_PORTAL_URL:
        client = SqlPortalClient(
            url=SQL_PORTAL_URL,
            login=SQL_PORTAL_LOGIN,
            password=SQL_PORTAL_PASSWORD,
            verify_ssl=VERIFY_SSL,
        )

        app.state.sql_client = client

        metadata_df = client.execute_sql(METADATA_SQL)
        app.state.metadata_search = MetadataSearchService(metadata_df)

    else:
        # ---------------------------------------------------------------------
        # Local SQLite fallback
        # ---------------------------------------------------------------------

        sqlite_path = Path("local.db")

        engine = create_engine(f"sqlite:///{sqlite_path}")

        if not sqlite_path.exists():
            demo_metadata = pd.DataFrame(
                [
                    {
                        "table_name": "customers",
                        "description": "Customer master data",
                    },
                    {
                        "table_name": "orders",
                        "description": "Customer orders",
                    },
                ]
            )

            demo_customers = pd.DataFrame(
                [
                    {"id": 1, "name": "Alice", "country": "FR"},
                    {"id": 2, "name": "Bob", "country": "US"},
                    {"id": 3, "name": "Charlie", "country": "FR"},
                ]
            )

            demo_orders = pd.DataFrame(
                [
                    {"id": 1, "customer_id": 1, "amount": 100},
                    {"id": 2, "customer_id": 1, "amount": 200},
                    {"id": 3, "customer_id": 2, "amount": 150},
                ]
            )

            demo_metadata.to_sql(
                "metadata_tables",
                engine,
                if_exists="replace",
                index=False,
            )

            demo_customers.to_sql(
                "customers",
                engine,
                if_exists="replace",
                index=False,
            )

            demo_orders.to_sql(
                "orders",
                engine,
                if_exists="replace",
                index=False,
            )

        class SQLiteClient:
            def __init__(self, engine):
                self.engine = engine

            def execute_sql(self, sql: str) -> pd.DataFrame:
                return pd.read_sql_query(sql, self.engine)

        client = SQLiteClient(engine)

        app.state.sql_client = client

        metadata_df = client.execute_sql(
            """
            select
                table_name,
                description
            from metadata_tables
            """
        )

        app.state.metadata_search = MetadataSearchService(metadata_df)

        print("Using local SQLite fallback database")

    yield

# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------

app = FastAPI(title="SQL MCP Gateway")


def get_service(request: Request) -> SqlService:
    return SqlService(request.app.state.sql_client)


@app.post("/query", operation_id="query_sql", response_model=TableResponse)
def query_sql(query: SqlQuery, request: Request) -> TableResponse:
    """Execute a read-only SQL query."""
    try:
        df = get_service(request).query(query.sql)

        return TableResponse.from_dataframe(df)

    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/search-tables", operation_id="search_tables")
def search_tables(query: TableSearchQuery, request: Request):
    """Semantic table search."""
    search_service = request.app.state.metadata_search

    return search_service.search(query=query.text, limit=query.limit)


@app.get("/explore/{table}", operation_id="explore_table", response_model=TableResponse)
def explore_table(table: str, request: Request, limit: int = 100):
    """Return sample rows."""
    df = get_service(request).explore(table=table, limit=limit)

    return TableResponse.from_dataframe(df)


@app.get("/count/{table}", operation_id="count_rows", response_model=TableResponse)
def count_rows(table: str, request: Request):
    """Count rows."""
    df = get_service(request).count(table)

    return TableResponse.from_dataframe(df)


@app.get("/distinct/{table}/{column}", operation_id="distinct_values", response_model=TableResponse)
def distinct_values(table: str, column: str, request: Request):
    """Distinct values."""
    df = get_service(request).distinct(table, column)

    return TableResponse.from_dataframe(df)


@app.get("/top/{table}/{column}", operation_id="top_values", response_model=TableResponse)
def top_values(table: str, column: str, request: Request, limit: int = 10):
    """Most frequent values."""
    df = get_service(request).top(table=table, column=column, limit=limit)

    return TableResponse.from_dataframe(df)


# -----------------------------------------------------------------------------
# MCP
# -----------------------------------------------------------------------------

mcp = FastMCP.from_fastapi(app=app, name="SQL Gateway")

mcp_app = mcp.http_app(path="/")
app.router.lifespan_context = combine_lifespans(portal_lifespan, mcp_app.lifespan)

app.mount("/mcp", mcp_app)


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )

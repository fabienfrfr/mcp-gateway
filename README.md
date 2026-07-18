# MCP Gateway

A generic, semantic MCP gateway exposing any HTTP-based SQL portal as both LLM-friendly MCP tools and standard REST endpoints. Designed from the ground up to serve human users (via UI/API) and AI agents simultaneously.

```bash
uv run main.py
uv run chainlit run chatbot.py -w
```

## Architecture

```text
                  +------------------+
                  |    Human User    |
                  +--------+---------+
                           |
                           | HTTP / REST
                           v
+---------+  MCP  +------------------+  HTTP  +------------------+
|   AI    +------>|   FastAPI App    +------>| SQL HTTP Portal  |
| (Agent) |       | (Semantic Layer) | (SQL) |                  |
+---------+       +--------+---------+       +------------------+
    ^                      |
    |                      |
    +--- from_fastapi() ---+
    (FastMCP Auto-maps tools)

```

## Core Design Principles (LLM & Human Best Practices)

1. **Semantic Layer Abstraction:** No raw CRUD endpoints. Expose high-level intent routes (`/search-tables`, `/top`, `/explore`) to reduce LLM cognitive load and simplify frontend code.
2. **Strict Explict Identification:** Every route enforces a clean, action-oriented `operation_id` (`query_sql`, `search_tables`). FastMCP maps these directly into clear tool names for the LLM.
3. **Intent-Driven Documentation:** Docstrings explicitly declare **when** and **why** to use the endpoint (`"""Semantic table search."""`), acting directly as LLM prompt steering.
4. **Strict Typing via Enums:** Restrict input options using Pydantic Enums to eliminate LLM parameter hallucinations.
5. **Server-Side Data Aggregation:** Compute metrics and perform table joins inside Python to save LLM context window tokens and prevent API call chaining.

---

## Pros & Cons

### Advantages

* **DRY Codebase:** Single source of truth. One FastAPI setup automatically serves both humans (REST) and AI (MCP).
* **AI-First Performance:** Fastembed vector search and server-side constraints (`FORBIDDEN` keywords, limits) keep the LLM fast, secure, and accurate.
* **Low Footprint:** No heavy local database or native drivers required; works over standard HTTP.

### Disadvantages

* **Path Parameter Blindness:** Complex dynamic routes like `/distinct/{table}/{column}` require the LLM to successfully call `/search-tables` first to discover valid values.
* **Tight Coupling:** Aligning REST routes to serve both human UX and LLM token-efficiency can require design trade-offs for heavily nested data.

## AI

```
# if : full python agent
uv tool install aider-chat --python 3.12 --force
uv tool install specify-cli
specify init mcp-gateway --integration claude --ignore-agent-tools

# else : npm agent (like claude code)
sudo apt update && sudo apt install -y nodejs npm
sudo npm install -g @opencode/cli
sudo npm install -g @fission-ai/openspec@latest
openspec init
```
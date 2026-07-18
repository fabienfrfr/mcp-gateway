"""Minimal chat UI for testing LLMs with MCP tools.

Architecture:

    Browser (Chainlit UI)
            |
            v
    app.py --(litellm.acompletion, OpenAI-compatible)--> LLM Gateway
       |                                                   |
       | (MCP client built into Chainlit)                  v
       v                                              Hosted LLM
    MCP Servers

This application is an MCP client. It can connect to any MCP-compatible server and dynamically expose its tools to the language model.

Connect MCP servers directly from the chat UI (🔌 icon). No code changes are required to add or remove servers.
"""

from __future__ import annotations

import json
import os

import chainlit as cl
import litellm
from dotenv import load_dotenv


load_dotenv()

MODEL = os.environ.get("AI_MODEL", "gpt-5")  # ex: enterprise compliance model
BASE_URL = os.environ.get("AI_BASE_URL", "http://localhost:4000/v1")
API_KEY = os.environ.get("AI_APIKEY", "dummy")

SYSTEM_PROMPT = (
    "You are an AI assistant with access to connected MCP tools. "
    "Use available tools whenever they can help answer the user's "
    "questions with accurate and up-to-date information."
)

MAX_TOOL_ROUNDS = 10





def _tool_to_openai_schema(tool) -> dict:
    """Convert an MCP tool description into OpenAI tool format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
        },
    }


def _available_tools() -> tuple[list[dict], dict[str, str]]:
    """Collect tools from all connected MCP servers."""
    mcp_tools: dict[str, list] = cl.user_session.get("mcp_tools", {})

    schemas: list[dict] = []
    tool_to_connection: dict[str, str] = {}

    for connection_name, tools in mcp_tools.items():
        for tool in tools:
            schemas.append(_tool_to_openai_schema(tool))
            tool_to_connection[tool.name] = connection_name

    return schemas, tool_to_connection


async def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool on the MCP server that exposes it."""
    _, tool_to_connection = _available_tools()

    connection_name = tool_to_connection.get(tool_name)

    if connection_name is None:
        return f"Error: tool '{tool_name}' is no longer available."

    try:
        mcp_session, _ = cl.context.session.mcp_sessions.get(connection_name)
        result = await mcp_session.call_tool(tool_name, arguments)

        return "\n".join(block.text for block in result.content if hasattr(block, "text"))
    except Exception as exc:
        return f"Tool execution failed: {exc}"


@cl.on_mcp_connect
async def on_mcp_connect(connection, session) -> None:
    """Store tools when an MCP server connects."""
    result = await session.list_tools()

    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = result.tools

    cl.user_session.set("mcp_tools", mcp_tools)

    tool_names = ", ".join(t.name for t in result.tools) or "no tools"

    await cl.Message(content=f"Connected to **{connection.name}**: {tool_names}").send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session) -> None:
    """Remove tools when an MCP server disconnects."""
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools.pop(name, None)

    cl.user_session.set("mcp_tools", mcp_tools)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize chat session."""
    cl.user_session.set("messages", [{"role": "system", "content": SYSTEM_PROMPT}])

    cl.user_session.set("mcp_tools", {})

    await cl.Message(
        content=(
            "Click the 🔌 icon to connect an MCP server "
            "(for example `http://localhost:8080/mcp/`), "
            "then start chatting."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle user messages and tool-calling loop."""
    messages: list[dict] = cl.user_session.get("messages")

    messages.append({"role": "user", "content": message.content})

    tools, _ = _available_tools()

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = await litellm.acompletion(
                model=MODEL, base_url=BASE_URL, api_key=API_KEY, messages=messages, tools=tools or None
            )
        except Exception as exc:
            await cl.Message(content=f"LLM request failed: {exc}").send()
            return

        choice = response.choices[0].message

        messages.append(choice.model_dump())

        if not choice.tool_calls:
            await cl.Message(content=choice.content or "").send()
            break

        for tool_call in choice.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}

            async with cl.Step(name=tool_call.function.name, type="tool") as step:
                step.input = arguments

                tool_result = await _call_mcp_tool(tool_call.function.name, arguments)

                step.output = tool_result

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
    else:
        await cl.Message(content="Maximum tool-calling iterations reached.").send()

    cl.user_session.set("messages", messages)

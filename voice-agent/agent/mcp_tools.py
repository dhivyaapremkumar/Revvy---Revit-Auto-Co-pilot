"""Connects to the RevitMCP server over stdio and loads its tools for LangGraph.

Spawns its own instance of RevitMCP.extension/main.py exactly the way
Claude Desktop's own claude_desktop_config.json does (`uv run --with
mcp[cli]==1.28.1 --with httpx==0.28.1 mcp run <main.py>`) -- this can run
alongside Claude Desktop's own copy without conflict, since both are just
stateless stdio wrappers around the same underlying Revit-side HTTP bridge
on 127.0.0.1:48884.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from agent.config import Settings


def build_mcp_client(settings: Settings) -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "revit": {
                "transport": "stdio",
                "command": settings.revit_mcp_uv_path,
                "args": [
                    "run",
                    "--with",
                    "mcp[cli]==1.28.1",
                    "--with",
                    "httpx==0.28.1",
                    "mcp",
                    "run",
                    settings.revit_mcp_path,
                ],
            }
        }
    )


@asynccontextmanager
async def open_revit_tools(settings: Settings) -> AsyncIterator[list[BaseTool]]:
    """Open ONE stdio connection to RevitMCP and yield tools bound to that
    single persistent session, kept alive for the life of this context.

    `MultiServerMCPClient.get_tools()` (the library's own convenience
    method -- what this used to call) creates a BRAND NEW subprocess
    connection for every single tool call: a fresh `uv run --with
    mcp[cli]... mcp run <path>` process, from scratch, every time. That
    subprocess spin-up (Python startup + uv resolution + RevitMCP server
    init) was the dominant cost behind every voice-agent tool call being
    slow -- even a trivial local Revit HTTP read took 2+ seconds -- and
    since RevitMCP's ask_building_code tool caches its REVVY backend login
    token in that subprocess's own module state, a fresh subprocess per
    call meant a fresh, wasted re-login every single time too. Opening the
    session once here and reusing it for the whole voice-agent process
    lifetime removes both costs.
    """
    client = build_mcp_client(settings)
    async with client.session("revit") as session:
        tools = await load_mcp_tools(session)
        yield tools

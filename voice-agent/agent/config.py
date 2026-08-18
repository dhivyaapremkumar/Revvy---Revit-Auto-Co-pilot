"""Environment configuration for the voice agent."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set -- copy voice-agent/.env.example to voice-agent/.env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    revit_mcp_path: str
    revit_mcp_uv_path: str
    wake_word_model: str
    agent_model: str
    revvy_backend_url: str
    # Optional: without these, the agent still works end-to-end -- it just
    # skips logging conversations to REVVY's chat history (see
    # agent/revvy_client.py). Your own REVVY account, not a shared one.
    revvy_email: str | None
    revvy_password: str | None
    # The window now shows the real web dashboard (React) instead of the
    # standalone orb.html -- same Python backend, same evaluate_js bridge
    # (see ui/window.py), just a different page loaded into it.
    dashboard_url: str


def get_settings() -> Settings:
    return Settings(
        openai_api_key=_require("OPENAI_API_KEY"),
        revit_mcp_path=_require("REVIT_MCP_PATH"),
        revit_mcp_uv_path=_require("REVIT_MCP_UV_PATH"),
        wake_word_model=os.environ.get("WAKE_WORD_MODEL", "hey_jarvis"),
        agent_model=os.environ.get("AGENT_MODEL", "gpt-realtime-mini"),
        revvy_backend_url=os.environ.get("REVVY_BACKEND_URL", "http://localhost:8000"),
        revvy_email=os.environ.get("REVVY_EMAIL") or None,
        revvy_password=os.environ.get("REVVY_PASSWORD") or None,
        dashboard_url=os.environ.get("DASHBOARD_URL", "http://localhost:5173"),
    )

"""Logs voice-agent conversations into REVVY's own chat history.

Reuses the same `chat_sessions`/`chat_messages` tables the web dashboard's
AskBar writes to, via the log-only endpoint (`/messages/log`) -- NOT the
normal `/messages` endpoint, which would generate its own second, different
LLM reply instead of just recording the one the voice agent already spoke.
One session per process "sitting" (created lazily on the first thing
actually said, reused for every turn until the agent exits).
"""
from __future__ import annotations

from datetime import datetime

import httpx

from agent.config import Settings

_ROLE_MAP = {"you": "user", "agent": "assistant"}


class RevvyClientError(Exception):
    """Raised when REVVY's backend can't be reached or rejects a request."""


class RevvyVoiceClient:
    def __init__(self, settings: Settings) -> None:
        self._backend_url = settings.revvy_backend_url
        self._email = settings.revvy_email
        self._password = settings.revvy_password
        self._token: str | None = None
        self._session_id: int | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._email and self._password)

    async def _login(self) -> str:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "{0}/api/v1/auth/login".format(self._backend_url),
                json={"email": self._email, "password": self._password},
            )
        if response.status_code != 200:
            raise RevvyClientError(
                "REVVY login failed ({0}): {1}".format(response.status_code, response.text)
            )
        self._token = response.json()["access_token"]
        return self._token

    async def _post(self, path: str, json_body: dict) -> dict:
        for attempt in range(2):
            token = self._token or await self._login()
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "{0}{1}".format(self._backend_url, path),
                    json=json_body,
                    headers={"Authorization": "Bearer {0}".format(token)},
                )
            if response.status_code in (401, 403) and attempt == 0:
                self._token = None
                continue
            if response.status_code >= 400:
                raise RevvyClientError(
                    "REVVY backend {0} failed ({1}): {2}".format(
                        path, response.status_code, response.text
                    )
                )
            return response.json()
        raise RevvyClientError("REVVY backend {0} failed after re-auth retry".format(path))

    async def log_turn(self, role: str, text: str) -> None:
        """Record one turn ("you" or "agent") -- creates this sitting's session
        on first use. Blank/whitespace-only text (VAD false-triggers with
        nothing actually said) is silently skipped."""
        content = text.strip()
        if not content or not self.enabled:
            return

        if self._session_id is None:
            data = await self._post(
                "/api/v1/chat/sessions",
                {"title": "Voice session -- {0:%b %d, %H:%M}".format(datetime.now())},
            )
            self._session_id = data["id"]

        await self._post(
            "/api/v1/chat/sessions/{0}/messages/log".format(self._session_id),
            {"role": _ROLE_MAP.get(role, role), "content": content},
        )

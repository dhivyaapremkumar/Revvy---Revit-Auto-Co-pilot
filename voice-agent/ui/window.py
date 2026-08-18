"""Reactive agent window: a pywebview wrapper around REVVY's own web dashboard.

pywebview's GUI event loop must own the main thread (required by the
edgechromium backend on Windows), so the actual voice-agent work runs in a
background thread that `webview.start(func=...)` spawns once the window is
ready -- see `run_with_window()`.

This used to load the standalone orb.html (still in this folder, kept as
reference/fallback -- pass its file:// path as `url` to go back to it). The
dashboard's React app defines the same `window.setAgentState` /
`appendTranscriptLine` / etc. global functions orb.html used to (see
frontend/src/hooks/usePywebviewBridge.ts), so every `evaluate_js` call below
is unchanged.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable

import webview

# pywebview defaults to `private_mode=True` (no persistent profile) -- fine
# for a throwaway browser, wrong for an app whose dashboard needs a login.
# Without this, every close/reopen of the window would force signing into
# REVVY again. Kept next to the venv rather than a system temp dir so it
# survives reboots and isn't swept by temp-file cleanup.
_STORAGE_PATH = str(Path(__file__).resolve().parent.parent / ".webview_storage")

_window: webview.Window | None = None
_loaded = threading.Event()


class _JsApi:
    """Exposed to the loaded page as `pywebview.api.*` -- lets the dashboard's
    Ask bar forward text into the audio process without that code touching webview."""

    def __init__(
        self,
        on_text_submit: Callable[[str], None] | None,
        on_mode_change: Callable[[str], None] | None = None,
    ) -> None:
        self._on_text_submit = on_text_submit
        self._on_mode_change = on_mode_change

    def submit_text(self, text: str) -> None:
        if self._on_text_submit and text and text.strip():
            self._on_text_submit(text.strip())

    def set_mode(self, mode: str) -> None:
        if self._on_mode_change:
            self._on_mode_change(mode)


def _on_loaded() -> None:
    _loaded.set()
    # The window has repeatedly ended up minimized right after launch (seen
    # live 2026-08-18) with no code anywhere that minimizes it -- almost
    # certainly Windows' foreground-activation restriction: a window created
    # by a process that isn't the current foreground process (true here,
    # since this is launched from a terminal/background task) can get
    # denied focus and left in whatever state the OS defaults to. Forcing
    # restore+show once the page has actually finished loading makes this
    # self-healing instead of requiring a manual Alt-Tab/taskkill fix every
    # time.
    if _window is not None:
        _window.restore()
        _window.show()


def _call(function_name: str, *args: object) -> None:
    """Best-effort call into a `window.<function_name>` the page may or may
    not have defined yet -- e.g. the dashboard only registers its bridge
    functions once its top-level provider mounts (see
    frontend/src/context/VoiceAgentBridgeContext.tsx), which can race a
    fast-firing pywebview "loaded" event, and registers nothing at all on
    the login page. A missing function must never throw here: that would
    kill this whole relay thread (and every future UI update this session)
    over what's just a page that hasn't caught up yet.
    """
    if _window is None:
        return
    _loaded.wait(timeout=5)
    serialized_args = ", ".join(json.dumps(a) for a in args)
    _window.evaluate_js(
        f"if (typeof window.{function_name} === 'function') {{ "
        f"window.{function_name}({serialized_args}); }}"
    )


def set_state(state: str) -> None:
    """state: one of 'idle', 'listening', 'thinking', 'speaking'."""
    _call("setAgentState", state)


def append_transcript(role: str, text: str) -> None:
    """role: 'you' or 'agent'."""
    _call("appendTranscriptLine", role, text)


def set_system_status(status: dict) -> None:
    """status keys: revit_mcp, building_code, wake_word (see audio_worker.SYSTEM_MSG)."""
    _call("setSystemStatus", status)


def set_last_query(tool_name: str, preview: str) -> None:
    _call("setLastQuery", tool_name, preview)


def toggle_graph() -> None:
    _call("toggleGraph")


def run_with_window(
    worker: Callable[[], None],
    url: str,
    on_text_submit: Callable[[str], None] | None = None,
    on_mode_change: Callable[[str], None] | None = None,
    on_closed: Callable[[], None] | None = None,
) -> None:
    """Show the window (loading `url`) and run `worker` (sync, blocking) in a
    background thread.

    `on_closed`, if given, fires when the window closes (X button or
    otherwise) -- use it to tear down anything `worker` started, since
    nothing else will once the window is gone.
    """
    global _window
    _window = webview.create_window(
        "REVVY Voice Agent",
        url,
        width=1440,
        height=900,
        background_color="#05070d",
        js_api=_JsApi(on_text_submit, on_mode_change),
    )
    _window.events.loaded += _on_loaded
    if on_closed is not None:
        _window.events.closed += lambda *args: on_closed()
    webview.start(worker, gui="edgechromium", private_mode=False, storage_path=_STORAGE_PATH)

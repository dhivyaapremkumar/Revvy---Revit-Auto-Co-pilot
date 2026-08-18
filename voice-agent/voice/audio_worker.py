"""Runs wake-word listening + the realtime voice session in a SEPARATE PROCESS.

sounddevice's WASAPI-backed audio streams appear to conflict with
pywebview's edgechromium (WebView2) renderer when both run in the same
process on Windows -- opening an audio stream reliably breaks the webview
to a black screen, almost certainly a COM apartment-model clash (WebView2
needs an STA message pump; PortAudio's internal audio threads don't share
it cleanly). Isolating ALL audio-touching code (wake word AND the
realtime session's mic/speaker streams) in its own process sidesteps the
conflict entirely -- this process also loads its own independent RevitMCP
connection, since the tools it calls (execute_revit_code, place_family,
ask_building_code, run_model_qa, ...) are needed here, not in the UI
process.
"""
from __future__ import annotations

import asyncio
import multiprocessing as mp
import queue
import subprocess
import sys

from openai import AsyncOpenAI

from agent.config import Settings, get_settings
from agent.mcp_tools import open_revit_tools
from agent.revit_tools import build_revit_tools
from agent.revvy_client import RevvyVoiceClient
from voice import realtime_session
from voice.wake_word import MODE_SWITCH, load_wake_word_model, wait_for_trigger

STATE_MSG = "state"
TRANSCRIPT_MSG = "transcript"
SYSTEM_MSG = "system"
LAST_QUERY_MSG = "last_query"
GRAPH_MSG = "graph"

_ARG_PREVIEW_CHARS = 70

# How often standby (text-mode, no mic) re-checks mode_queue for a switch
# back to voice while waiting for typed input -- keeps the toggle feeling
# immediate without busy-looping.
_TEXT_STANDBY_POLL_SECONDS = 0.3


def _wait_text_only(text_queue: "mp.Queue", mode_queue: "mp.Queue | None"):
    """Text-mode standby: block for typed input with no mic opened at all.
    Returns the typed text, or MODE_SWITCH if `mode_queue` reports a switch
    back to voice mode first."""
    while True:
        try:
            return text_queue.get(timeout=_TEXT_STANDBY_POLL_SECONDS)
        except queue.Empty:
            pass
        if mode_queue is not None:
            try:
                if mode_queue.get_nowait() == "voice":
                    return MODE_SWITCH
            except queue.Empty:
                pass


async def _run(
    settings: Settings, to_ui: "mp.Queue", to_worker: "mp.Queue", mode_queue: "mp.Queue | None" = None
) -> None:
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    # Kept in a named variable (NOT `await open_revit_tools(settings).__aenter__()`
    # inline) -- with nothing else referencing the context-manager object
    # itself, CPython garbage-collects that still-suspended async generator
    # almost immediately, and its cleanup then runs from whatever arbitrary
    # task the GC happens to fire on rather than the task that opened it.
    # anyio's task-group-based cancel scopes require exiting from the same
    # task they were entered in, so that mismatched cleanup crashed the
    # whole MCP session (and took this entire subprocess down with it --
    # the "no response to the wake word" symptom was this process being
    # dead, not the mic or the wake-word model). Keeping this reference
    # alive for `_run`'s whole lifetime (it never returns) prevents that.
    #
    # Entered without a matching __aexit__: this process runs `_run`'s while
    # loop forever, torn down only by `stop()`'s `taskkill /T /F` on the
    # whole process tree (which kills the RevitMCP subprocess this session
    # owns right along with it) -- there's no graceful-shutdown path here to
    # hang a `async with` block off of. See open_revit_tools' docstring for
    # why this needs to be ONE persistent session, not the ephemeral
    # per-call ones `MultiServerMCPClient.get_tools()` used to create.
    _revit_tools_cm = open_revit_tools(settings)
    tools = await _revit_tools_cm.__aenter__()
    # Structured wall/level/room tools (agent/revit_tools.py) sit alongside
    # the raw MCP tools, not in place of them -- execute_revit_code stays
    # available as a fallback for anything the structured set doesn't cover
    # yet (doors, windows, floors, ...).
    execute_code = next(t for t in tools if t.name == "execute_revit_code")
    tools = tools + build_revit_tools(execute_code)
    wake_model = load_wake_word_model(settings.wake_word_model)

    revvy = RevvyVoiceClient(settings)
    if not revvy.enabled:
        print(
            "REVVY_EMAIL / REVVY_PASSWORD not set -- voice conversations won't "
            "appear in the web dashboard's chat history this session."
        )
    # Fire-and-forget logging tasks -- kept referenced so they aren't GC'd
    # mid-flight, discarded once done. A logging failure (backend down,
    # etc.) must never interrupt the actual conversation.
    _log_tasks: set[asyncio.Task] = set()

    def _log_turn(role: str, text: str) -> None:
        if not revvy.enabled:
            return

        async def _do_log() -> None:
            try:
                await revvy.log_turn(role, text)
            except Exception as exc:  # noqa: BLE001 - logging must never break the live conversation
                print("Could not log voice turn to REVVY backend:", exc)

        task = asyncio.create_task(_do_log())
        _log_tasks.add(task)
        task.add_done_callback(_log_tasks.discard)

    # Reported once tools actually loaded -- "connected"/"indexed" here
    # reflect that RevitMCP's tool list (including ask_building_code) came
    # back successfully, not a live re-check of the DB on every message.
    to_ui.put(
        (
            SYSTEM_MSG,
            {
                "revit_mcp": "connected",
                "building_code": "indexed",
                "wake_word": settings.wake_word_model,
            },
        )
    )

    def on_state(state: str) -> None:
        to_ui.put((STATE_MSG, state))

    def on_transcript(role: str, text: str) -> None:
        to_ui.put((TRANSCRIPT_MSG, role, text))
        _log_turn(role, text)

    def on_tool_call(name: str, args: dict) -> None:
        # Show whatever the first argument's value is (e.g. ask_building_code's
        # "question") as a quick preview -- good enough for a status line,
        # not meant to be a full call log.
        preview = next(iter(args.values()), "") if args else ""
        preview = str(preview).replace("\n", " ")
        if len(preview) > _ARG_PREVIEW_CHARS:
            preview = preview[: _ARG_PREVIEW_CHARS - 1] + "…"
        to_ui.put((LAST_QUERY_MSG, name, preview))

    def on_show_graph() -> None:
        to_ui.put((GRAPH_MSG,))

    # "voice": mic listens for the wake word between conversations, replies
    # are spoken. "text": mic is off entirely (no wake-word listening, no
    # mic capture during the conversation either) -- typed input only,
    # replies come back as text. Starts in voice mode; the dashboard's
    # toggle can switch it any time via mode_queue, applied the next time
    # this loop is between conversations (see MODE_SWITCH handling below).
    current_mode = "voice"
    while True:
        to_ui.put((STATE_MSG, "idle"))
        to_ui.put((SYSTEM_MSG, {"mode": current_mode}))
        # Wake word (voice mode) or a typed message (either mode, submitted
        # from the UI's text box while idle) starts a conversation -- a
        # typed opener carries that text as the first turn.
        if current_mode == "voice":
            typed_trigger = wait_for_trigger(wake_model, settings.wake_word_model, to_worker, mode_queue=mode_queue)
        else:
            typed_trigger = _wait_text_only(to_worker, mode_queue)

        if typed_trigger is MODE_SWITCH:
            current_mode = "text" if current_mode == "voice" else "voice"
            continue

        to_ui.put((SYSTEM_MSG, {"error": None}))  # clear any stale error from a previous failed attempt
        try:
            await realtime_session.run_conversation(
                openai_client,
                settings.agent_model,
                tools,
                text_queue=to_worker,
                initial_text=typed_trigger,
                text_only=(current_mode == "text"),
                on_state=on_state,
                on_transcript=on_transcript,
                on_tool_call=on_tool_call,
                on_show_graph=on_show_graph,
            )
        except Exception as exc:  # noqa: BLE001 - keep listening across a single bad conversation
            message = str(exc)
            # The most common real-world cause of "it just doesn't respond"
            # -- OpenAI account out of credits. Previously this only ever
            # showed as one easy-to-miss transcript line; now it also drives
            # a persistent, visible status so it can't be silently missed.
            if "insufficient_quota" in message or "credit_balance_exhausted" in message:
                friendly = "OpenAI account is out of credits -- add credits, then just say the wake word again."
                to_ui.put((TRANSCRIPT_MSG, "agent", friendly))
                to_ui.put((SYSTEM_MSG, {"error": friendly}))
            else:
                to_ui.put((TRANSCRIPT_MSG, "agent", "Error during that conversation: {0}".format(message)))
                to_ui.put((SYSTEM_MSG, {"error": "Last conversation hit an error -- see transcript."}))


def _worker(
    settings: Settings, to_ui: "mp.Queue", to_worker: "mp.Queue", mode_queue: "mp.Queue"
) -> None:
    # This is a fresh interpreter (spawned process) -- main.py's own
    # line_buffering fix doesn't reach it. Without this, prints from here
    # (wake-word scores, tool-call logging errors) sit unflushed instead of
    # showing up in real time.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(line_buffering=True)
    asyncio.run(_run(settings, to_ui, to_worker, mode_queue=mode_queue))


def start(
    settings: Settings | None = None,
    to_worker: "mp.Queue | None" = None,
    mode_queue: "mp.Queue | None" = None,
) -> "tuple[mp.Queue, mp.process.BaseProcess]":
    """Spawn the audio subprocess. Returns (queue it publishes state/transcript
    to, the process itself -- pass the latter to `stop()` on shutdown).

    `to_worker` (optional): a queue the caller can also write typed text
    into, delivered as user turns inside the audio process. If not given,
    one is created but the caller has no way to feed it -- pass your own
    when you want the typed-input box to work.

    `mode_queue` (optional): a queue the caller can write "voice"/"text"
    into to toggle input mode. If not given, one is created but the caller
    has no way to feed it -- pass your own when you want the dashboard's
    mode toggle to work.
    """
    settings = settings or get_settings()
    ctx = mp.get_context("spawn")
    to_ui: "mp.Queue" = ctx.Queue()
    if to_worker is None:
        to_worker = ctx.Queue()
    if mode_queue is None:
        mode_queue = ctx.Queue()
    process = ctx.Process(target=_worker, args=(settings, to_ui, to_worker, mode_queue), daemon=True)
    process.start()
    return to_ui, process


def stop(process: "mp.process.BaseProcess | None") -> None:
    """Kill the audio subprocess AND its descendants (the RevitMCP `uv run`
    stdio server it spawns, and that command's own child process).

    `daemon=True` alone only guarantees cleanup when this process's own
    interpreter exits *normally* -- if the whole app is killed forcefully
    (or, on Windows, since child processes are never auto-reaped when a
    parent dies), the audio process and its RevitMCP grandchild are left
    running as orphans. `taskkill /T` kills the whole process tree, which
    is the only reliable way to take all of them down together on Windows.
    """
    if process is None or process.pid is None or not process.is_alive():
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
    else:
        process.terminate()

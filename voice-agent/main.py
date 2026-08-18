"""Voice-controlled REVVY agent: wake word -> realtime streaming session (RevitMCP tools) -> spoken response.

Run: .venv/Scripts/python.exe main.py

The reactive orb window (ui/orb.html via pywebview) owns the main thread
(required by its edgechromium backend on Windows). All audio-touching
work (wake word + the realtime session's mic/speaker streams) runs in a
SEPARATE PROCESS -- see voice/audio_worker.py for why -- and reports back
over a multiprocessing.Queue that this process relays to the UI.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import sys
import time

# WebView2's GPU compositor frequently fails to initialize over Remote
# Desktop / low-GPU sessions, leaving create_window() produce a live,
# focusable HWND that never actually paints anything -- invisible but
# fully functional otherwise (audio/mic/replies all work). --use-gl=swiftshader
# forces the software (CPU) GL rasterizer instead. Do NOT also pass
# --disable-software-rasterizer -- that disables the swiftshader fallback
# itself, which combined with a disabled GPU leaves no rendering path at
# all (this was tried and reproduced the exact same blank-window symptom).
# Must be set before ui.window imports webview, since that import is what
# stands up the WebView2 environment.
os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "--use-gl=swiftshader")

from agent.config import get_settings
from ui.window import (
    append_transcript,
    run_with_window,
    set_last_query,
    set_state,
    set_system_status,
    toggle_graph,
)
from voice import audio_worker

# Windows' console defaults to a legacy codepage (e.g. cp1252) that can't
# encode arbitrary spoken-response text (smart quotes, em-dashes, etc.) --
# an uncaught UnicodeEncodeError here would silently kill this whole
# thread, breaking every future UI update for the rest of the session.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        # line_buffering=True: without it, prints sit in Python's internal
        # buffer instead of reaching a redirected/piped console immediately
        # -- made diagnosing a "why isn't it responding" report needlessly
        # hard, since "Listening for wake word..." and the per-turn
        # Heard/Reply lines weren't actually visible in real time.
        _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def main() -> None:
    # Created here (not inside _relay_worker) so on_text_submit -- wired
    # into the window's JS bridge before the window even loads -- has
    # somewhere to write typed text once the audio process starts reading
    # from this same queue.
    ctx = mp.get_context("spawn")
    to_worker: "mp.Queue" = ctx.Queue()
    mode_queue: "mp.Queue" = ctx.Queue()
    # Set once _relay_worker actually spawns the audio process -- read by
    # _on_closed, which runs on the main thread after the window is gone.
    audio_process_holder: dict = {"process": None}

    def _on_text_submit(text: str) -> None:
        to_worker.put(text)

    def _on_mode_change(mode: str) -> None:
        if mode in ("voice", "text"):
            mode_queue.put(mode)

    def _on_closed() -> None:
        # webview.start() only returns once the window is gone; the relay
        # thread below is still blocked on to_ui.get() at that point (it's
        # not daemonic), which would keep this whole process alive doing
        # nothing visible. Kill the audio process tree (it and the
        # RevitMCP stdio subprocess it spawned) and force the interpreter
        # to exit rather than wait for a message that will never come.
        audio_worker.stop(audio_process_holder["process"])
        os._exit(0)

    def _relay_worker() -> None:
        """Sync entry point pywebview runs in a background thread: spawn the
        audio process and relay its messages to the UI until it exits."""
        settings = get_settings()
        print("Starting audio process (wake word: {0}, model: {1})...".format(
            settings.wake_word_model, settings.agent_model
        ))
        to_ui, process = audio_worker.start(settings, to_worker=to_worker, mode_queue=mode_queue)
        audio_process_holder["process"] = process
        print(
            "Ready. Say '{0}' or type a question to start.".format(
                settings.wake_word_model.replace("_", " ")
            )
        )

        set_state("idle")
        while True:
            kind, *payload = to_ui.get()
            try:
                if kind == audio_worker.STATE_MSG:
                    (state,) = payload
                    set_state(state)
                    if state == "idle":
                        print("\nListening for wake word...")
                    elif state == "listening":
                        print("Wake word detected / listening...")
                elif kind == audio_worker.TRANSCRIPT_MSG:
                    role, text = payload
                    print("{0}: {1}".format("Heard" if role == "you" else "Reply", text))
                    append_transcript(role, text)
                elif kind == audio_worker.SYSTEM_MSG:
                    (status,) = payload
                    set_system_status(status)
                elif kind == audio_worker.LAST_QUERY_MSG:
                    tool_name, preview = payload
                    set_last_query(tool_name, preview)
                elif kind == audio_worker.GRAPH_MSG:
                    toggle_graph()
            except Exception as exc:  # noqa: BLE001 - one bad message must not kill UI updates for the rest of the session
                print("Error relaying message to UI:", exc)

    # The persistent WebView2 profile (.webview_storage, kept so login
    # survives restarts) has repeatedly served stale, out-of-date content on
    # launch -- confirmed live 2026-08-18: the window showed a nav tab that
    # doesn't exist anywhere in the current frontend source, and nginx's
    # access log showed ZERO real requests from the window's own client
    # across a full relaunch, meaning it never even asked the server. Most
    # likely cause: this process has been force-killed (taskkill /T /F) many
    # times during development, which is exactly the kind of unclean
    # shutdown that makes Chromium-based engines restore a previous session
    # instead of navigating fresh. A cache-busting query param makes the
    # requested URL different every launch, which no cached or restored
    # entry for the OLD url can satisfy -- forces a real navigation every
    # time. React Router matches on pathname only, so this doesn't affect
    # in-app routing.
    dashboard_url = "{0}?_cb={1}".format(get_settings().dashboard_url, int(time.time()))
    run_with_window(
        _relay_worker,
        url=dashboard_url,
        on_text_submit=_on_text_submit,
        on_mode_change=_on_mode_change,
        on_closed=_on_closed,
    )


if __name__ == "__main__":
    mp.freeze_support()
    main()

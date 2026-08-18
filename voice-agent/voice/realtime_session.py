"""One voice-agent conversation over OpenAI's Realtime API (streaming audio-to-audio).

Replaces the old wake-word -> record -> Whisper -> GPT-4o -> TTS cascade's
per-turn latency (each a separate network round trip) with a single
streaming websocket session: the model transcribes, reasons, calls tools,
and speaks back continuously as audio arrives, instead of waiting for each
stage to fully finish before starting the next.

One wake-word trigger (or one typed message) opens the connection; it then
keeps taking turns -- by voice or by typed text -- without needing the wake
word again, until the user goes quiet for a while (see _IDLE_TIMEOUT_SECONDS),
at which point the connection closes and the caller goes back to standby.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import queue
import threading
import time
from typing import Callable

import numpy as np
import sounddevice as sd
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from openai import AsyncOpenAI

SAMPLE_RATE = 24000
_CHUNK_SAMPLES = 2400  # 100ms, matches record.py's chunking convention

# How long to wait, after a response finishes, for the user to either speak
# or type again before ending the conversation and going back to standby
# (needing the wake word again). The mic stream keeps running -- and
# billing as input audio tokens -- for this entire window even in total
# silence, since the connection has to stay open to catch a follow-up at
# all. Raised from 10s to cover a long working session (e.g. building a
# house step-by-step, then querying it) without repeating the wake word
# between nearly every turn -- still bounded rather than infinite, so
# walking away for good eventually still falls back to the cheap
# wake-word-only standby instead of billing forever.
_IDLE_TIMEOUT_SECONDS = 300

# Bounds worst-case cost growth within one session. Every new turn re-sends
# the FULL accumulated conversation (including prior audio, far pricier per
# token than text) as input context, so cost compounds across a long
# back-and-forth rather than growing linearly. Raised from 6 -- a full
# build-a-house-then-query-it session legitimately needs more turns than
# that -- but still capped rather than unbounded, so one very long session
# can't silently run the context (and cost) up forever.
_MAX_TURNS_PER_SESSION = 40

# Extra safety margin added on top of the estimated audio-drain time before
# the mic re-arms (see speaking_until in run_conversation) -- output device
# buffering and any room reverb tail mean "the last sample was written to
# output_stream" doesn't mean "the speaker has gone silent" quite yet.
_ECHO_TAIL_MARGIN_MS = 300

# Bounds cost/runaway responses. Spoken answers self-regulate to be short
# (see _INSTRUCTIONS' "1-3 short sentences" rule) so this cap rarely matters
# for them -- it exists mainly for execute_revit_code turns, whose function
# arguments (a real IronPython script: imports, a transaction, several
# element-creation calls) can legitimately run past a few hundred tokens.
# Previously capped at 400: a wall-creation call's generated code kept
# getting cut off mid-argument by that limit, producing truncated/invalid
# JSON for the tool call (or a syntactically broken script), which then
# failed near-instantly (~0.00s "tool call" durations in the logs) and
# looked like a Revit-side error rather than a token-budget one.
_MAX_OUTPUT_TOKENS = 1500

# Neither server_vad nor semantic_vad has a volume/amplitude floor for
# semantic_vad, and even server_vad's threshold couldn't fully stop short
# ambient blips (a cough, a chair creak) from registering as "speech" and
# getting a real reply. This filters purely on burst duration, client-side,
# regardless of which server-side VAD mode is active.
_MIN_SPEECH_MS = 350

# Same idea as _MIN_SPEECH_MS but for loudness instead of duration: without
# an amplitude floor, semantic_vad happily treats a long, sustained ambient
# sound (a video/music playing near the mic in another window, someone
# talking in the background) as a real, minutes-long "utterance" -- it gets
# transcribed faithfully (that's not a bug in the transcription) and REVVY
# replies to whatever it actually heard, which was never directed at it.
# RMS of the int16 samples (0-32767 scale); a person speaking at normal
# volume directly into a laptop mic runs well above this, while
# speaker-to-mic bleed of background media is typically much quieter.
# Tune using the peak_rms value the speech_stopped log line prints.
_MIN_SPEECH_RMS = 300

# Extra client-side patience on top of semantic_vad's own "low" eagerness
# (already the most patient built-in setting -- there's no further knob to
# turn there). When the server decides speech has stopped, wait this long
# before actually committing to a reply; a new speech_started arriving
# inside the window cancels it, so a mid-sentence breath/pause doesn't get
# treated as "done talking."
_TURN_END_GRACE_MS = 700

# Checked against the input transcript verbatim (not a substring match --
# "the setback should stop at 3m" must NOT trigger this) so saying "stop"
# is a hard, immediate interrupt: cancel whatever's in flight, cut audio
# output dead, go idle. This bypasses the model entirely rather than
# waiting for it to hear "stop", decide to acknowledge, speak that
# acknowledgement, and only then call end_conversation -- which is what
# end_conversation via the LLM tool call actually cost before this, and
# reads as sluggish for something that should be instant.
_STOP_PHRASES = frozenset(
    {
        "stop",
        "stop listening",
        "pause",
        "go idle",
        "cancel",
        "cancel that",
        "never mind",
        "nevermind",
        "that's all",
        "thats all",
        "goodbye",
        "bye",
    }
)


def _is_stop_command(transcript: str) -> bool:
    normalized = transcript.strip().lower().rstrip(".!? ")
    return normalized in _STOP_PHRASES

_INSTRUCTIONS = (
    "You are REVVY's voice-controlled Revit assistant, continuing an ongoing "
    "conversation (no need to re-greet every turn). Tools: get_levels, "
    "get_wall_types, get_walls, get_rooms, create_wall, create_door, "
    "create_window, and create_room are pre-tested structured tools for "
    "those exact operations -- ALWAYS use them instead of execute_revit_code "
    "or place_family when a request is just reading levels/wall types/walls/"
    "rooms, or creating a wall/door/window/room, since they already handle "
    "this project's Revit-API quirks and validate names (level, wall type, "
    "family/type, host wall) against the real model before creating "
    "anything. Never use place_family for a door or window -- it only "
    "supports free-standing placement, not hosting a door/window inside a "
    "wall, so create_door/create_window exist specifically for that. "
    "Wall/door/window type names in this project often contain a literal "
    "inch-mark character as part of the exact name, e.g. 36\" x 84\" -- "
    "when the user describes a size out loud (\"36 by 84\") there's no way "
    "to hear whether quote marks belong in the name, so NEVER compose a "
    "type name yourself from a spoken description. Always take the exact "
    "string from a previous tool result instead -- get_wall_types/"
    "list_families's output, or the available_wall_types/available_types "
    "list an error already gave you -- and reuse it verbatim. If a "
    "create_door/create_window/create_wall call returns 'type not found' or "
    "'wall_type not found', don't just guess a slightly different string "
    "next -- copy one exact entry from that error's available list. "
    "create_room's result always includes area_sqft -- if it's 0, the room "
    "was placed but isn't enclosed by walls yet (Revit only computes a real "
    "area once a room is surrounded by a closed wall loop), so say that "
    "plainly rather than claiming the room was created normally. "
    "create_property_line sets the plot boundary (call it before "
    "check_setbacks -- there's nothing to measure against otherwise). "
    "check_setbacks returns ONLY the actual distances from the building to "
    "the plot boundary -- it never says whether that complies with TNCDBR. "
    "For any setback compliance question, ALWAYS call check_setbacks AND "
    "ask_building_code (for the actual required setback in this case) and "
    "compare them yourself in your reply -- never assert compliance from "
    "just one of them, and never assert compliance if check_setbacks has no "
    "plot boundary/walls yet or ask_building_code found nothing relevant; "
    "say so plainly instead. ALWAYS state check_setbacks' actual numbers "
    "(front/rear/left/right in feet) in your reply, even if ask_building_code "
    "found no specific TNCDBR requirement to compare them against -- the "
    "measured distances are useful on their own and must never be silently "
    "dropped just because the compliance comparison itself came up empty. "
    "If any side comes back 0 or negative, say so explicitly (it means that "
    "wall sits on or past the plot boundary) rather than passing over it. "
    "For corrections to something already in the model -- move it, delete "
    "it, change a wall's type/height/endpoints, rename/renumber a room -- "
    "use get_element_location, get_element_geometry, move_element, "
    "delete_element, modify_wall, or modify_room instead of deleting and "
    "recreating it from scratch. If you don't already know the element's id "
    "from earlier in the conversation, get it first via get_walls/get_rooms/"
    "etc. "
    "For multi-room requests (\"design a 3BHK\", \"create this floor plan\"), "
    "decide the room layout yourself -- each room's corner (x, y) and "
    "width_ft/depth_ft -- using the plot boundary and any adjacency/"
    "orientation the user gave, then call create_floor_plan ONCE with the "
    "full room list, instead of calling create_wall/create_room repeatedly "
    "per room. It builds walls + rooms only (no doors/windows) and returns "
    "each room's wall_ids -- add doors/windows afterward with create_door/"
    "create_window using those ids. Rooms aren't wall-deduplicated -- two "
    "adjacent rooms sharing an edge each get their own walls there, so keep "
    "that in mind rather than promising perfectly shared walls. "
    "RevitMCP model tools "
    "(view/model info, placing free-standing families, executing Revit API "
    "code for anything the structured tools don't cover yet -- floors, "
    "stairs, ... -- opening/saving documents), ask_building_code (search the ingested "
    "Tamil Nadu Building Code, TNCDBR, for a cited answer or compliance "
    "check), and run_model_qa (fixed check for naming issues, missing tags, "
    "stray CAD links, unresolved warnings). For compliance/QA questions "
    "always use those tools -- never assert a TNCDBR clause or QA result "
    "you haven't actually retrieved. ask_building_code also answers GENERIC "
    "code questions with no project specifics (e.g. 'what is the FSI "
    "rule?') -- call it directly with what the user asked, verbatim, rather "
    "than asking for plot size/road width/occupancy first. Only ask a "
    "clarifying question if the tool's own answer says it depends on "
    "something unspecified. ask_building_code and run_model_qa can take "
    "several seconds to come back -- say a brief filler like 'Let me check "
    "that' or 'One moment' in the SAME turn BEFORE calling either of them, "
    "so the wait doesn't sound like silence. Keep replies to 1-3 short "
    "sentences, no markdown, since you're speaking out loud. If the user asks you to "
    "pause, stop listening, go idle, or end the conversation, briefly "
    "acknowledge it and call end_conversation. If the user asks to see the "
    "graph, the architecture, or how you're connected to your tools, "
    "briefly acknowledge it and call show_architecture_graph -- the same "
    "call also closes it if it's already open and they ask to hide/close it. "
    "When writing execute_revit_code for this Revit 2027 environment: "
    "element.Name raises AttributeError on ANY element (Level, WallType, "
    "any instance or type) -- the ONE pattern that reliably works for all "
    "of them is DB.Element.Name.__get__(element). Do not use "
    "get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM) or "
    "LookupParameter('Name') for this -- each only works on some element "
    "kinds and silently returns nothing useful on others (e.g. "
    "SYMBOL_NAME_PARAM works on WallType but not Level; LookupParameter "
    "works on Level but not WallType), which is what caused repeated "
    "wall/level lookup failures before. ElementId.IntegerValue no longer "
    "exists -- use str(element.Id) instead. When a user names a level, "
    "wall type, or family type, match it against the actual names in the "
    "model (via DB.Element.Name.__get__) rather than guessing or "
    "hardcoding a name that may not exist in this project. Keep generated "
    "code compact (no unnecessary comments or blank lines) so a multi-"
    "element script doesn't risk hitting the output-length limit "
    "mid-script."
)

# Handled locally, never sent to RevitMCP -- lets the user end the
# conversation by voice ("pause", "go idle", "stop listening") instead of
# only via the silence timeout.
_END_CONVERSATION_TOOL_NAME = "end_conversation"
_END_CONVERSATION_TOOL = {
    "type": "function",
    "name": _END_CONVERSATION_TOOL_NAME,
    "description": (
        "Call this when the user asks you to stop listening, pause, go "
        "idle, or end the conversation (e.g. 'stop listening', 'go idle', "
        "'pause', 'that's all', 'goodbye'). Say a brief acknowledgement in "
        "the same turn, then call this."
    ),
    "parameters": {"type": "object", "properties": {}},
}

# Also handled locally -- toggles the animated architecture-diagram overlay
# in the UI on/off. Doesn't touch the conversation flow at all.
_SHOW_GRAPH_TOOL_NAME = "show_architecture_graph"
_SHOW_GRAPH_TOOL = {
    "type": "function",
    "name": _SHOW_GRAPH_TOOL_NAME,
    "description": (
        "Call this when the user asks to see the graph, the architecture, "
        "or how you're connected to your tools/RevitMCP/the building code "
        "search -- and again if they ask to hide or close it. Briefly "
        "acknowledge it in the same turn, then call this."
    ),
    "parameters": {"type": "object", "properties": {}},
}

OnState = Callable[[str], None]
OnTranscript = Callable[[str, str], None]
OnToolCall = Callable[[str, dict], None]
OnShowGraph = Callable[[], None]


def _tools_to_realtime_format(tools: list[BaseTool]) -> list[dict]:
    formatted = []
    for tool in tools:
        openai_tool = convert_to_openai_tool(tool)["function"]
        formatted.append(
            {
                "type": "function",
                "name": openai_tool["name"],
                "description": openai_tool.get("description", ""),
                "parameters": openai_tool.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    formatted.append(_END_CONVERSATION_TOOL)
    formatted.append(_SHOW_GRAPH_TOOL)
    return formatted


def _stringify_tool_result(result) -> str:
    """MCP tools return a list of content blocks (`[{"type": "text", "text": "..."}]`)."""
    if isinstance(result, list):
        texts = [block.get("text", "") for block in result if isinstance(block, dict)]
        return "\n".join(t for t in texts if t) or str(result)
    return str(result)


async def run_conversation(
    client: AsyncOpenAI,
    model: str,
    tools: list[BaseTool],
    *,
    text_queue=None,
    initial_text: str | None = None,
    text_only: bool = False,
    on_state: OnState | None = None,
    on_transcript: OnTranscript | None = None,
    on_tool_call: OnToolCall | None = None,
    on_show_graph: OnShowGraph | None = None,
) -> None:
    """Run one conversation over a single realtime connection.

    One wake-word trigger (or one typed message, via `initial_text`) starts
    it; it then keeps taking turns -- by voice or by typed text arriving on
    `text_queue` -- without needing the wake word again, until the user goes
    quiet (no speech, no typed text) for `_IDLE_TIMEOUT_SECONDS`, at which
    point the connection closes and the caller goes back to standby.

    `text_only`: skip the mic and speaker entirely and get/give text-only
    replies (no audio tokens either direction) -- for Text mode, where the
    user has explicitly opted out of voice for this session.
    """
    tools_by_name = {tool.name: tool for tool in tools}
    realtime_tools = _tools_to_realtime_format(tools)
    # Measures the wake-word-trigger-to-mic-actually-capturing gap, purely
    # for logging -- the mic itself now starts capturing (see mic_stream.start()
    # below) BEFORE the websocket connect + session.update round trip, so
    # this should stay near-zero. It used to measure the connect round trip
    # instead (mic opened only after connecting), during which anything the
    # user said straight after the wake word (e.g. "hey jarvis, what's the
    # FSI...") was silently lost before capture even started.
    conversation_entered_at = time.monotonic()
    loop = asyncio.get_running_loop()

    output_stream = None
    if not text_only:
        output_stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16")
        output_stream.start()

    def _emit_state(state: str) -> None:
        if on_state:
            on_state(state)

    # Must be bound BEFORE the mic stream can start calling _mic_callback --
    # that callback runs on PortAudio's own real-time thread and can fire
    # within milliseconds of the stream starting. Reading an unassigned
    # local from that thread raises UnboundLocalError inside the callback,
    # sounddevice silently aborts the whole input stream, and every mic
    # chunk for the rest of that conversation is lost -- surfacing as "it's
    # not hearing me" with no error anywhere.
    response_pending = False
    # See _mic_callback -- monotonic() timestamp of when the currently-
    # buffered playback audio will finish draining out of the speaker.
    speaking_until = 0.0
    # False until the realtime connection is up AND session.update has been
    # acknowledged -- while False, _mic_callback buffers raw chunks locally
    # instead of trying to send them (there's no `conn` to send to yet).
    # Guarded by mic_state_lock so the flip-to-live moment (see the flush
    # below) can't race a callback invocation into either double-sending or
    # silently dropping a chunk caught mid-transition.
    mic_live = False
    mic_state_lock = threading.Lock()
    pre_buffer: list[bytes] = []
    # Bound once the connection is established, below -- pre-declared here
    # (same UnboundLocalError reasoning as response_pending) since the mic
    # can start calling back before that happens.
    conn = None
    # Running peak RMS of the current speech burst -- see _MIN_SPEECH_RMS.
    # Reset to 0.0 at each speech_started, read (and acted on) at the
    # matching speech_stopped. Pre-declared here for the same
    # UnboundLocalError reason as the other mic-callback state above.
    burst_peak_rms = 0.0

    def _mic_callback(indata, frames, time_info, status):  # noqa: ARG001
        nonlocal burst_peak_rms
        if response_pending or time.monotonic() < speaking_until + _ECHO_TAIL_MARGIN_MS / 1000:
            # response_pending: a response is being generated right now.
            # speaking_until: the SERVER already finished generating, but
            # the SPEAKER hasn't finished physically playing the buffered
            # reply back yet -- output_stream.write() queues audio that
            # drains over real time, so response_pending going False
            # doesn't mean REVVY has actually stopped talking. Without this
            # second check, the mic re-arms while the tail of REVVY's own
            # reply is still audibly playing, no acoustic echo cancellation
            # exists on a laptop mic/speaker, and that trailing audio gets
            # captured and sent right back to OpenAI as if it were the user
            # speaking -- surfacing as nonsense/blank transcripts and
            # phantom extra turns that can eat the user's actual next
            # question. interrupt_response is off either way, so none of
            # this audio could barge in usefully -- streaming it would only
            # add billed input-audio tokens (or worse, a fake turn) for no
            # benefit. Drop it; the mic picks back up the moment REVVY has
            # actually finished talking.
            return
        channel = indata[:, 0]
        rms = float(np.sqrt(np.mean(channel.astype(np.float64) ** 2)))
        if rms > burst_peak_rms:
            burst_peak_rms = rms
        chunk_bytes = channel.tobytes()
        with mic_state_lock:
            if not mic_live:
                pre_buffer.append(chunk_bytes)
                return
        encoded = base64.b64encode(chunk_bytes).decode("ascii")
        event = {"type": "input_audio_buffer.append", "audio": encoded}
        # sounddevice's callback runs on PortAudio's own internal thread,
        # not the asyncio loop's thread -- conn.send() is a coroutine, so
        # it must be scheduled onto the loop rather than awaited directly
        # here.
        asyncio.run_coroutine_threadsafe(conn.send(event), loop)

    mic_stream = (
        contextlib.nullcontext()
        if text_only
        else sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=_CHUNK_SAMPLES,
            callback=_mic_callback,
        )
    )
    if not text_only:
        # Started BEFORE connecting -- see conversation_entered_at's
        # comment above. Anything said between now and the connection
        # being ready lands in pre_buffer and gets flushed in order once
        # session.update is acknowledged, instead of being lost.
        mic_stream.start()

    try:
        async with client.realtime.connect(
            model=model,
            # Tool calls (e.g. ask_building_code) can take 5-8s; the default
            # ping_timeout is tight enough that a slow tool call has
            # previously tripped a spurious "keepalive ping timeout" and
            # killed the whole session mid-answer. Give it more headroom.
            websocket_connection_options={"ping_interval": 20, "ping_timeout": 45},
        ) as conn:
            session_config: dict = {
                "type": "realtime",
                "instructions": _INSTRUCTIONS,
                "max_output_tokens": _MAX_OUTPUT_TOKENS,
                "tools": realtime_tools,
            }
            if text_only:
                # No mic, no speaker -- text in, text out. Skips audio
                # tokens (both directions, and audio input tokens are the
                # pricier side) entirely, and there's no VAD to configure
                # since no audio ever gets appended to the input buffer.
                session_config["output_modalities"] = ["text"]
            else:
                session_config["output_modalities"] = ["audio"]
                session_config["audio"] = {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        "turn_detection": {
                            # server_vad's fixed silence_duration_ms
                            # kept cutting people off mid-instruction
                            # (e.g. multi-part "add a window on the
                            # ... south wall ... at 3m") no matter how
                            # high the window was pushed -- semantic_vad
                            # instead waits until the utterance sounds
                            # actually finished (not just quiet),
                            # using its own end-of-turn model rather
                            # than a stopwatch. "low" eagerness biases
                            # it toward waiting longer over cutting in.
                            #
                            # Trade-off: this mode has no amplitude
                            # "threshold" knob (unlike server_vad), so
                            # if ambient room noise starts spawning
                            # false turns again, that's the tell to
                            # switch back and re-tune silence_duration_ms
                            # instead.
                            "type": "semantic_vad",
                            "eagerness": "low",
                            # Manual response creation (see
                            # response_pending below) -- tool calls
                            # here (e.g. ask_building_code) can take
                            # 4-8s, and with create_response=true any
                            # ambient noise picked up during that
                            # wait auto-starts a COMPETING new
                            # response, confusing which response.done
                            # is actually this turn's end and
                            # abandoning the real tool-backed answer
                            # before it's ever spoken.
                            "create_response": False,
                            "interrupt_response": False,
                        },
                        # Cheaper than whisper-1 for the same job.
                        "transcription": {"model": "gpt-4o-mini-transcribe"},
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        "voice": "alloy",
                    },
                }
            await conn.send({"type": "session.update", "session": session_config})

            if not text_only:
                # Flip to live streaming and hand off whatever was captured
                # while connecting, in order, before any new live chunk can
                # be sent -- see mic_state_lock's docstring above for why
                # this needs the lock rather than just flipping mic_live
                # and reading pre_buffer as two separate steps.
                with mic_state_lock:
                    buffered, pre_buffer[:] = list(pre_buffer), []
                    mic_live = True
                for chunk_bytes in buffered:
                    encoded = base64.b64encode(chunk_bytes).decode("ascii")
                    await conn.send({"type": "input_audio_buffer.append", "audio": encoded})
                print(
                    "Mic ready {0:.2f}s after wake word ({1} chunk(s) "
                    "captured before the connection was up, now "
                    "flushed)".format(time.monotonic() - conversation_entered_at, len(buffered)),
                    flush=True,
                )

            _emit_state("listening")
            # A response that includes a tool call finishes its own
            # response.done BEFORE the tool has actually run -- the
            # model can't proceed until we send function_call_output +
            # a follow-up response.create, which starts a SEPARATE
            # response with its own response.done. Only the response
            # that made no tool call is the actual end of a turn.
            tool_call_pending = False
            # create_response is off (see session config above) -- we
            # trigger the response for each turn manually (on
            # speech_stopped or on typed text), and only when no
            # response is already in flight, so a phantom/ambient
            # speech segment picked up during a tool call's wait can't
            # spawn a second competing response.
            # Set when the user asks (by voice or text) to pause/go
            # idle -- checked once the acknowledgement response
            # finishes, to end the conversation early instead of
            # waiting out the full idle timeout.
            end_requested = False
            speech_started_at: float | None = None
            # See the speech_started/speech_stopped handlers below --
            # true when a noise blip cancelled an already-legitimate
            # utterance's grace timer, so that blip's own (too-short)
            # burst doesn't get treated as "nothing worth replying to."
            had_real_utterance = False
            # Real, billed numbers (response.usage corresponds directly
            # to billing per the API's own docs) rather than guessing
            # whether a change actually reduced cost.
            session_tokens_total = 0
            # See _MAX_TURNS_PER_SESSION -- counts completed turns
            # (a tool-call round-trip doesn't count as its own turn).
            turn_count = 0
            # See _TURN_END_GRACE_MS -- holds the delayed "actually
            # commit to a reply" task so a new speech_started can
            # cancel it (the user was just pausing, not finished).
            pending_response_task: asyncio.Task | None = None
            # Set right before every response.create -- logged against
            # the first bit of actual reply content that comes back, so
            # "it feels slow" has a real number instead of a guess.
            response_requested_at: float | None = None

            async def _send_user_text(text: str) -> None:
                nonlocal response_pending, response_requested_at
                await conn.send(
                    {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": text}],
                        },
                    }
                )
                if on_transcript:
                    on_transcript("you", text)
                if not response_pending:
                    response_pending = True
                    response_requested_at = time.monotonic()
                    _emit_state("thinking")
                    await conn.send({"type": "response.create"})

            async def _create_response_after_grace() -> None:
                nonlocal response_pending, response_requested_at
                await asyncio.sleep(_TURN_END_GRACE_MS / 1000)
                if not response_pending:
                    response_pending = True
                    response_requested_at = time.monotonic()
                    _emit_state("thinking")
                    await conn.send({"type": "response.create"})

            async def _stop_now() -> None:
                """Hard interrupt: cancel/cut everything and go idle immediately."""
                nonlocal response_pending, speaking_until, end_requested, pending_response_task
                if pending_response_task is not None and not pending_response_task.done():
                    pending_response_task.cancel()
                if response_pending:
                    try:
                        await conn.send({"type": "response.cancel"})
                    except Exception:  # noqa: BLE001 - best-effort; we're going idle regardless
                        pass
                if output_stream is not None:
                    output_stream.abort()  # discard buffered audio now, not once it finishes playing
                response_pending = False
                speaking_until = 0.0  # abort() just discarded it -- nothing left draining
                end_requested = True
                if on_transcript:
                    on_transcript("agent", "(stopped)")
                _emit_state("idle")

            typed_queue: "asyncio.Queue[str]" = asyncio.Queue()

            async def _bridge_typed_input() -> None:
                """Forward typed text from the (blocking, cross-process)
                text_queue into an in-process asyncio.Queue, without
                blocking the event loop. Polls with a short timeout so a
                cancellation doesn't leave a thread blocked indefinitely."""
                if text_queue is None:
                    return
                while True:
                    try:
                        text = await loop.run_in_executor(None, text_queue.get, True, 1.0)
                    except queue.Empty:
                        continue
                    await typed_queue.put(text)

            bridge_task = asyncio.create_task(_bridge_typed_input())

            if initial_text:
                await _send_user_text(initial_text)

            recv_task = asyncio.create_task(conn.recv())
            text_task = asyncio.create_task(typed_queue.get())
            try:
                while True:
                    # The idle clock shouldn't start counting down the
                    # user's silence until REVVY has actually finished
                    # talking -- response.done (the last recv_task event
                    # for a turn) fires as soon as the server finishes
                    # GENERATING, which for a long reply (near the
                    # _MAX_OUTPUT_TOKENS cap, ~16s of audio) is well
                    # before the speaker finishes physically PLAYING it
                    # back. Without this, a long reply's own remaining
                    # playback time ate into the user's 10s response
                    # window, sometimes ending the conversation before
                    # they could even get a word in.
                    wait_timeout = _IDLE_TIMEOUT_SECONDS + max(0.0, speaking_until - time.monotonic())
                    done, _pending = await asyncio.wait(
                        {recv_task, text_task},
                        timeout=wait_timeout,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if not done:
                        break  # no voice or typed input for a while -- end the conversation

                    if text_task in done:
                        text = text_task.result()
                        text_task = asyncio.create_task(typed_queue.get())
                        if _is_stop_command(text):
                            await _stop_now()
                            break
                        await _send_user_text(text)

                    if recv_task in done:
                        event = recv_task.result()
                        recv_task = asyncio.create_task(conn.recv())

                        if event.type == "response.created":
                            tool_call_pending = False
                        elif event.type == "input_audio_buffer.speech_started":
                            print("speech_started", flush=True)
                            speech_started_at = time.monotonic()
                            burst_peak_rms = 0.0
                            if pending_response_task is not None and not pending_response_task.done():
                                # They're still talking -- that "done" a
                                # moment ago was just a breath/pause, not
                                # the end of the turn. Remember that a
                                # real reply was already queued so a
                                # noise blip below can't silently eat it.
                                pending_response_task.cancel()
                                had_real_utterance = True
                            _emit_state("listening")
                        elif event.type == "input_audio_buffer.speech_stopped":
                            burst_ms = (
                                (time.monotonic() - speech_started_at) * 1000
                                if speech_started_at is not None
                                else _MIN_SPEECH_MS
                            )
                            speech_started_at = None
                            print(
                                "speech_stopped, burst_ms={0:.0f}, peak_rms={1:.0f}".format(
                                    burst_ms, burst_peak_rms
                                ),
                                flush=True,
                            )
                            too_quiet = burst_peak_rms < _MIN_SPEECH_RMS
                            if (burst_ms < _MIN_SPEECH_MS or too_quiet) and not had_real_utterance:
                                # Too short, or too quiet to be real speech
                                # directed at the mic (e.g. background
                                # media/voices bleeding in) -- ignore it (a
                                # transcript may still show up separately;
                                # it just won't get a reply).
                                _emit_state("listening")
                            elif not response_pending:
                                # Either a real burst, or a trailing
                                # noise blip (cough, room echo) that
                                # cancelled an already-legitimate
                                # utterance's grace timer above -- either
                                # way there's real speech to reply to, so
                                # don't drop the turn on the floor.
                                had_real_utterance = False
                                # Stay in "listening" -- _TURN_END_GRACE_MS
                                # gives them a beat to keep talking before
                                # this actually commits to a reply.
                                pending_response_task = asyncio.create_task(_create_response_after_grace())
                        elif event.type == "response.output_audio.delta":
                            if response_requested_at is not None:
                                print(
                                    "Time to first audio: {0:.2f}s".format(
                                        time.monotonic() - response_requested_at
                                    ),
                                    flush=True,
                                )
                                response_requested_at = None
                            _emit_state("speaking")
                            pcm = np.frombuffer(base64.b64decode(event.delta), dtype=np.int16)
                            output_stream.write(pcm)
                            # This chunk queues up to play AFTER whatever
                            # is already buffered (or starting now, if
                            # the buffer's already empty) -- extends the
                            # mic's re-arm gate to cover it too. The
                            # _ECHO_TAIL_MARGIN_MS safety margin is
                            # applied ONCE, at comparison time in
                            # _mic_callback -- NOT added here per chunk,
                            # which would pile up several extra seconds
                            # on a long, many-chunk reply and gate the
                            # mic well past when REVVY actually stopped
                            # talking, silently eating the user's next
                            # turn (speech_started fires, but the mic is
                            # still dropped, so speech_stopped never
                            # arrives and the conversation just times out).
                            chunk_seconds = len(pcm) / SAMPLE_RATE
                            speaking_until = max(speaking_until, time.monotonic()) + chunk_seconds
                        elif event.type == "conversation.item.input_audio_transcription.completed":
                            if on_transcript:
                                on_transcript("you", event.transcript)
                            if _is_stop_command(event.transcript):
                                await _stop_now()
                                break
                        elif event.type == "conversation.item.input_audio_transcription.failed":
                            print("Input transcription failed:", event.error)
                            if on_transcript:
                                on_transcript("you", "(could not transcribe what was said)")
                        elif event.type == "response.output_audio_transcript.done":
                            if on_transcript:
                                on_transcript("agent", event.transcript)
                        elif event.type == "response.output_text.done":
                            if response_requested_at is not None:
                                print(
                                    "Time to reply (text mode): {0:.2f}s".format(
                                        time.monotonic() - response_requested_at
                                    ),
                                    flush=True,
                                )
                                response_requested_at = None
                            if on_transcript:
                                on_transcript("agent", event.text)
                        elif event.type == "error":
                            print("Realtime API error:", event.error)
                            if on_transcript:
                                on_transcript("agent", "Error: {0}".format(event.error.message))
                        elif event.type == "response.function_call_arguments.done":
                            tool_call_pending = True
                            _emit_state("thinking")
                            try:
                                args = json.loads(event.arguments)
                            except json.JSONDecodeError:
                                args = {}
                            if event.name == _END_CONVERSATION_TOOL_NAME:
                                end_requested = True
                                output_text = "Acknowledged -- going idle."
                            elif event.name == _SHOW_GRAPH_TOOL_NAME:
                                if on_show_graph:
                                    on_show_graph()
                                output_text = "Toggled the architecture graph."
                            else:
                                tool = tools_by_name.get(event.name)
                                if tool is None:
                                    output_text = "Unknown tool: {0}".format(event.name)
                                else:
                                    if on_tool_call:
                                        on_tool_call(event.name, args)
                                    # Previously only logged name+duration -- when a tool call
                                    # "doesn't work" over several retries, the model's own
                                    # spoken narration of why is unreliable (paraphrases,
                                    # sometimes just wrong), so debugging required guessing
                                    # instead of just reading what was actually sent/returned.
                                    print("Tool call {0} args: {1}".format(event.name, args), flush=True)
                                    tool_started_at = time.monotonic()
                                    try:
                                        result = await tool.ainvoke(args)
                                        output_text = _stringify_tool_result(result)
                                    except Exception as exc:  # noqa: BLE001 - surface it to the model as a normal tool result, not a crashed session
                                        output_text = "Tool error: {0}".format(exc)
                                    print(
                                        "Tool call {0} took {1:.2f}s, result: {2}".format(
                                            event.name,
                                            time.monotonic() - tool_started_at,
                                            output_text[:500],
                                        ),
                                        flush=True,
                                    )
                            await conn.send(
                                {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": event.call_id,
                                        "output": output_text,
                                    },
                                }
                            )
                            response_requested_at = time.monotonic()
                            await conn.send({"type": "response.create"})
                        elif event.type == "response.done":
                            usage = event.response.usage
                            if usage is not None:
                                session_tokens_total += usage.total_tokens or 0
                                print(
                                    "Tokens this reply: {0} in / {1} out / {2} total -- session so far: {3}".format(
                                        usage.input_tokens,
                                        usage.output_tokens,
                                        usage.total_tokens,
                                        session_tokens_total,
                                    ),
                                    flush=True,
                                )
                            if not tool_call_pending:
                                response_pending = False
                                turn_count += 1
                                if end_requested:
                                    _emit_state("idle")
                                    break
                                if turn_count >= _MAX_TURNS_PER_SESSION:
                                    if on_transcript:
                                        on_transcript(
                                            "agent",
                                            "(session limit reached -- say the wake word to keep going)",
                                        )
                                    _emit_state("idle")
                                    break
                                _emit_state("listening")
            finally:
                recv_task.cancel()
                text_task.cancel()
                bridge_task.cancel()
                cleanup_tasks = [recv_task, text_task, bridge_task]
                if pending_response_task is not None:
                    pending_response_task.cancel()
                    cleanup_tasks.append(pending_response_task)
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    finally:
        if not text_only:
            mic_stream.stop()
            mic_stream.close()
        if output_stream is not None:
            output_stream.stop()
            output_stream.close()

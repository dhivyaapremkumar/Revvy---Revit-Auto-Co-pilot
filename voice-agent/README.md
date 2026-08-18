# REVVY Voice Agent

Voice-controlled Revit assistant: say the wake word, speak a command, and
the agent (OpenAI GPT-4o via LangGraph) acts on the currently open Revit
model through RevitMCP's tools -- including `ask_building_code` (TNCDBR
Q&A/compliance, backed by REVVY's own Code-RAG) and `run_model_qa`
(naming/tags/stray-CAD-links/warnings), both added to
`RevitMCP.extension/tools/`.

## Architecture

```
mic --wake word (openWakeWord)--> record until silence --> Whisper STT
  --> LangGraph agent (GPT-4o + RevitMCP tools, agent<->tools loop)
  --> OpenAI TTS --> speaker
```

The reactive orb window (`ui/orb.html` via pywebview) shows agent state
(idle/listening/thinking/speaking) and a live transcript. See
`agent/graph.py` for the LangGraph `StateGraph` definition --
`graph.get_graph().draw_mermaid()` prints its structure.

## Setup

1. `py -3.12 -m venv .venv` (openWakeWord/onnxruntime lag behind the
   newest Python releases -- 3.12 has the best wheel support today)
2. `.venv/Scripts/pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` (same key as
   `backend/.env`), plus the paths to `uv.exe` and
   `RevitMCP.extension/main.py`.
4. Download the wake-word model once:
   `.venv/Scripts/python -c "from openwakeword.utils import download_models; download_models(['hey_rhasspy'])"`
   (swap `hey_rhasspy` for another of openWakeWord's bundled models --
   `alexa`, `hey_mycroft`, `hey_jarvis`, `hey_rhasspy` -- via
   `WAKE_WORD_MODEL` in `.env` if you'd rather use a different one; a
   fully custom wake word like "Phoenix" needs either training a custom
   openWakeWord model or switching to Picovoice Porcupine, neither of
   which is wired up here yet.)

## Run

- Revit must be open with the REVVY-modified `RevitMCP.extension` and
  pyRevit's routes API reachable at `127.0.0.1:48884` (same requirement
  as Claude Desktop's own "Revit Connector" MCP config).
- The REVVY backend must be running at `http://localhost:8000` (used by
  `ask_building_code` via `RevitMCP.extension/tools/revvy_client.py`'s dev
  login).
- `.venv/Scripts/python main.py`

## Known tuning needed

Wake-word detection threshold (`_DETECTION_THRESHOLD` in
`voice/wake_word.py`, default 0.5) and the silence-detection RMS
threshold (`_SILENCE_RMS_THRESHOLD` in `voice/record.py`, default 300)
were only verified against synthetic TTS audio and haven't been tuned
against a real voice/room -- expect to adjust both after some live use.

"""Wake-word listener using openWakeWord.

Blocks the calling thread until either the configured wake word (default:
"hey jarvis") is detected in the default microphone's audio, or a typed
message arrives on `text_queue` -- whichever happens first. Runs on plain
16kHz mono int16 PCM chunks, openWakeWord's expected format.
"""
from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

_SAMPLE_RATE = 16000
_CHUNK_SAMPLES = 1280  # 80ms per openWakeWord's expected chunk size
_DETECTION_THRESHOLD = 0.4
_DEBUG_SCORE_FLOOR = 0.15  # print scores above this so near-misses are visible for tuning

# Sentinel returned by wait_for_trigger when `mode_queue` reports the user
# switched to Text mode mid-standby -- distinct from both the wake-word
# return (None) and a typed-text return (str), so the caller can tell "stop
# listening on the mic, re-enter standby in text mode" apart from an actual
# trigger.
MODE_SWITCH = object()


def load_wake_word_model(model_name: str) -> Model:
    return Model(wakeword_models=[model_name], inference_framework="onnx")


def wait_for_trigger(
    model: Model, model_name: str, text_queue, mode_queue=None, on_listening=None
) -> "str | None | object":
    """Block until `model_name` is detected in the mic input, typed text
    arrives on `text_queue`, or (if given) `mode_queue` reports a switch away
    from voice mode. Returns the typed text if that's what triggered it,
    None for the wake word, or MODE_SWITCH."""
    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

    def _callback(indata, frames, time_info, status):  # noqa: ARG001 - sounddevice callback signature
        audio_queue.put(indata[:, 0].copy())

    if on_listening:
        on_listening()

    with sd.InputStream(
        samplerate=_SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=_CHUNK_SAMPLES,
        callback=_callback,
    ):
        while True:
            if mode_queue is not None:
                try:
                    if mode_queue.get_nowait() == "text":
                        return MODE_SWITCH
                except queue.Empty:
                    pass
            try:
                return text_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                chunk = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            prediction = model.predict(chunk)
            score = prediction.get(model_name, 0.0)
            if score > _DEBUG_SCORE_FLOOR:
                print("wake word score: {0:.2f}".format(score), flush=True)
            if score > _DETECTION_THRESHOLD:
                model.reset()
                return None

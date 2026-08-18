"""Records a spoken command from the mic until silence, for STT."""
from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
_CHUNK_SAMPLES = 1600  # 100ms chunks
_SILENCE_RMS_THRESHOLD = 300  # int16 RMS; tune against your mic's noise floor
_SILENCE_CHUNKS_TO_STOP = 7  # ~0.7s of silence ends the recording
_MAX_RECORD_SECONDS = 20


def _rms(chunk: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(chunk.astype(np.float64)))))


def record_command() -> np.ndarray:
    """Record from the mic until ~1.2s of silence (or a 20s cap), return int16 mono PCM."""
    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

    def _callback(indata, frames, time_info, status):  # noqa: ARG001 - sounddevice callback signature
        audio_queue.put(indata[:, 0].copy())

    chunks: list[np.ndarray] = []
    silence_run = 0
    speech_started = False
    max_chunks = int(_MAX_RECORD_SECONDS * SAMPLE_RATE / _CHUNK_SAMPLES)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=_CHUNK_SAMPLES,
        callback=_callback,
    ):
        for _ in range(max_chunks):
            chunk = audio_queue.get()
            chunks.append(chunk)
            loud = _rms(chunk) > _SILENCE_RMS_THRESHOLD
            if loud:
                speech_started = True
                silence_run = 0
            elif speech_started:
                silence_run += 1
                if silence_run >= _SILENCE_CHUNKS_TO_STOP:
                    break

    return np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)

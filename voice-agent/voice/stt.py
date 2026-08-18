"""Speech-to-text via OpenAI's Whisper API."""
from __future__ import annotations

import io

import numpy as np
import soundfile as sf
from openai import AsyncOpenAI

async def transcribe(client: AsyncOpenAI, audio: np.ndarray, sample_rate: int) -> str:
    """Transcribe int16 mono PCM audio to text. `sample_rate` must match `audio`'s actual rate."""
    if audio.size == 0:
        return ""
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    buffer.seek(0)
    buffer.name = "command.wav"  # the SDK reads this for the multipart filename/content-type

    response = await client.audio.transcriptions.create(model="whisper-1", file=buffer)
    return response.text.strip()

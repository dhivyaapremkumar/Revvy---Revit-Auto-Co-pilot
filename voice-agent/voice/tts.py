"""Text-to-speech via OpenAI's TTS API, with playback."""
from __future__ import annotations

import io

import sounddevice as sd
import soundfile as sf
from openai import AsyncOpenAI

_VOICE = "alloy"
_MODEL = "tts-1"


async def synthesize(client: AsyncOpenAI, text: str) -> bytes:
    """Return WAV bytes for `text`."""
    response = await client.audio.speech.create(
        model=_MODEL, voice=_VOICE, input=text, response_format="wav"
    )
    return response.read()


def play(wav_bytes: bytes) -> None:
    """Blocking playback of WAV bytes through the default output device."""
    data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
    sd.play(data, samplerate)
    sd.wait()


async def speak(client: AsyncOpenAI, text: str) -> None:
    wav_bytes = await synthesize(client, text)
    play(wav_bytes)

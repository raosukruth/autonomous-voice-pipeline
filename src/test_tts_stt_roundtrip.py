# Live TTS -> iiSTT round-trip fidelity test (optional).
import asyncio
import os
import re

import pytest

from src.stt.deepgram_stt import DeepgramSTT
from src.tts.deepgram_tts import DeepgramTTS


# Source text samples that stress common medical-office phone intents.
FULL_ROUNDTRIP_CASES = [
    (
        "Hello, I would like to schedule an appointment for next Tuesday afternoon.",
        0.65,
    ),
    (
        "I am a returning patient and I need to reschedule my visit from April tenth to April twelfth.",
        0.60,
    ),
    (
        "Please cancel my appointment for Monday at two thirty p m.",
        0.65,
    ),
    (
        "My date of birth is January fifteenth nineteen ninety two.",
        0.60,
    ),
    (
        "My phone number is five five five, one two three, four nine eight seven.",
        0.55,
    ),
    (
        "I need a refill for lisinopril ten milligrams once daily.",
        0.60,
    ),
    (
        "Do you accept Blue Cross Blue Shield p p o insurance?",
        0.60,
    ),
    (
        "Could you repeat the office address and parking instructions slowly?",
        0.65,
    ),
    (
        "I am feeling anxious about my lab results and I need to speak with a nurse.",
        0.65,
    ),
    (
        "My last name is O Connor, spelled O apostrophe C O N N O R.",
        0.50,
    ),
]

# Small, subset suitable for CI smoke runs.
SMOKE_ROUNDTRIP_CASES = FULL_ROUNDTRIP_CASES[:3]


def normalize_text(text: str) -> list[str]:
    # Lowercase and keep only alphanumeric tokens for stable comparison.
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return [t for t in cleaned.split() if t]


def word_recall(reference: str, hypothesis: str) -> float:
    # Fraction of unique reference words found in hypothesis words.
    ref_words = set(normalize_text(reference))
    hyp_words = set(normalize_text(hypothesis))
    if not ref_words:
        return 1.0
    return len(ref_words & hyp_words) / len(ref_words)


async def transcribe_mulaw_bytes(stt: DeepgramSTT, audio: bytes) -> str:
    # Stream mulaw audio to STT and return concatenated final transcripts.
    transcripts: list[str] = []
    done = asyncio.Event()

    async def on_transcript(text: str, is_final: bool) -> None:
        if text.strip():
            transcripts.append(text.strip())
            done.set()

    await stt.start_stream(on_transcript)
    for idx in range(0, len(audio), 160):
        await stt.send_audio(audio[idx:idx + 160])
        await asyncio.sleep(0.02)

    # Add brief silence so endpointing can flush a final transcript.
    silence = b"\xff" * 1600
    for idx in range(0, len(silence), 160):
        await stt.send_audio(silence[idx:idx + 160])
        await asyncio.sleep(0.02)

    try:
        await asyncio.wait_for(done.wait(), timeout=10)
    except asyncio.TimeoutError:
        pass

    # Give listener a moment to process any final buffered messages.
    await asyncio.sleep(0.5)
    await stt.stop_stream()
    return " ".join(transcripts)


async def run_case_set(api_key: str, cases: list[tuple[str, float]]) -> None:
    # Run a case set and fail if any sample drops below its recall threshold.
    tts = DeepgramTTS(api_key=api_key)
    failures: list[str] = []

    for source_text, min_recall in cases:
        stt = DeepgramSTT(api_key=api_key, sample_rate=8000, encoding="mulaw")
        mulaw_audio = await tts.synthesize_to_mulaw(source_text)
        heard_text = await transcribe_mulaw_bytes(stt, mulaw_audio)
        recall = word_recall(source_text, heard_text)
        if recall < min_recall:
            failures.append(
                f"recall={recall:.2f} < {min_recall:.2f} | source={source_text} | heard={heard_text}"
            )

    assert not failures, "Low-fidelity cases:\n" + "\n".join(failures)


async def test_tts_stt_roundtrip_smoke_live():
    # Fast smoke test for CI: a few representative utterances.
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key or os.getenv("RUN_LIVE_AUDIO_TESTS") != "1":
        pytest.skip("Set DEEPGRAM_API_KEY and RUN_LIVE_AUDIO_TESTS=1 to run")
    await run_case_set(api_key, SMOKE_ROUNDTRIP_CASES)


async def test_tts_stt_roundtrip_full_live():
    # Full suite for deeper fidelity checks (enable separately from CI smoke).
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key or os.getenv("RUN_LIVE_AUDIO_FULL") != "1":
        pytest.skip("Set DEEPGRAM_API_KEY and RUN_LIVE_AUDIO_FULL=1 to run")
    await run_case_set(api_key, FULL_ROUNDTRIP_CASES)

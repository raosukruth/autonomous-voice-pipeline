# AGENTS.md — Autonomous Build Instructions for PGAI Voice Bot

## Purpose

Build a voice bot that calls Pretty Good AI's test line (+1-805-439-8008), simulates realistic patient conversations, records them, and identifies bugs. The bot must produce at minimum 10 full MP3 call recordings with transcripts.

---

## CRITICAL RULES FOR THE AGENT

1. **Build component by component.** Never start a new module until the current one is fully functional with all unit tests passing.
2. **Incremental development.** Within each module, develop one function/class at a time, write its tests, run them, and only then proceed to the next piece.
3. **Test-first mindset.** After writing each incremental piece, run `pytest src/<component>/test_<file>.py -v` (or `pytest src/test_<file>.py -v` for root-level modules). ALL tests for that component must pass before proceeding.
4. **Failure protocol:** If a test fails, attempt to fix it (max 5 attempts). On each attempt, read the error, reason about the root cause, and make a targeted fix (not a hack). If after 5 attempts it still fails, update STATUS.md with the failure details and move to the next step. If >80% of tests in a module are failing, stop work on that module, update STATUS.md, and move to the next module.
5. **Status reporting.** After completing each step (success or failure), update STATUS.md.
6. **No secrets in code.** All API keys go in `.env`. Never hardcode keys.
7. **Short functions.** Every function or method should be ≤30 lines. If longer, refactor into helpers.
8. **Do not generate the entire module at once.** Follow the step-by-step order defined below.

---

## HIGH-LEVEL ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                       │
│  Instantiates components, manages call lifecycle,    │
│  saves recordings/transcripts, runs scenarios        │
├──────────┬──────────┬──────────┬────────────────────┤
│   TTS    │   STT    │  PATIENT │      VoIP          │
│ (text →  │ (audio → │ (LLM    │  (Twilio calls +   │
│  audio)  │  text)   │  agent)  │   media streams)   │
├──────────┴──────────┴──────────┴────────────────────┤
│                  UTILITIES                           │
│  Config, AudioUtils, Logging, CallRecorder           │
└─────────────────────────────────────────────────────┘
```

### Data Flow During a Call

```
Pretty Good AI Phone ←→ Twilio ←→ WebSocket Server ←→ Pipeline
                                                         │
                        ┌────────────────────────────────┘
                        ▼
              Incoming audio (mulaw 8kHz)
                        │
                        ▼
                 STT (Deepgram streaming)
                        │
                        ▼
                  Transcribed text
                        │
                        ▼
              LLM Patient Agent (OpenAI)
                        │
                        ▼
                  Response text
                        │
                        ▼
                TTS (Deepgram streaming)
                        │
                        ▼
              Outgoing audio (mulaw 8kHz)
                        │
                        ▼
              WebSocket → Twilio → Phone
```

### Recording Pipeline (parallel)

```
All audio chunks (in + out) → CallRecorder → WAV → MP3
All transcribed turns → TranscriptWriter → JSON + TXT
```

---

## PROJECT STRUCTURE

```
pgai-voice-bot/
├── AGENTS.md                    # This file
├── STATUS.md                    # Auto-updated build status
├── README.md                    # Setup and run instructions
├── .env.example                 # Required environment variables
├── requirements.txt             # Python dependencies
├── conftest.py                  # Root conftest: shared fixtures (sample audio, env, scenario)
├── main.py                      # Entry point
├── src/
│   ├── __init__.py
│   ├── config.py                # Module 1: Config management
│   ├── test_config.py           # Tests for config
│   ├── audio_utils.py           # Module 1: Audio format conversion
│   ├── test_audio_utils.py      # Tests for audio_utils
│   ├── logger.py                # Module 1: Structured logging
│   ├── test_logger.py           # Tests for logger
│   ├── call_recorder.py         # Module 1: Call recording to MP3
│   ├── test_call_recorder.py    # Tests for call_recorder
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── conftest.py          # TTS-specific fixtures (mock aiohttp)
│   │   ├── base.py              # Module 2: Abstract TTS interface
│   │   ├── test_base.py         # Tests for base TTS
│   │   ├── deepgram_tts.py      # Module 2: Deepgram TTS
│   │   └── test_deepgram_tts.py # Tests for Deepgram TTS
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── conftest.py          # STT-specific fixtures (mock websocket)
│   │   ├── base.py              # Module 3: Abstract STT interface
│   │   ├── test_base.py         # Tests for base STT
│   │   ├── deepgram_stt.py      # Module 3: Deepgram streaming STT
│   │   └── test_deepgram_stt.py # Tests for Deepgram STT
│   ├── patient/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Patient-specific fixtures (mock openai)
│   │   ├── scenarios.py         # Module 4: Scenario definitions
│   │   ├── test_scenarios.py    # Tests for scenarios
│   │   ├── agent.py             # Module 4: LLM patient agent
│   │   └── test_agent.py        # Tests for agent
│   ├── voip/
│   │   ├── __init__.py
│   │   ├── conftest.py          # VoIP-specific fixtures (mock twilio)
│   │   ├── twilio_client.py     # Module 5: Twilio outbound calls
│   │   ├── test_twilio_client.py# Tests for Twilio client
│   │   ├── media_stream.py      # Module 5: WebSocket media handler
│   │   └── test_media_stream.py # Tests for media stream
│   ├── orchestrator.py          # Module 6: Main orchestrator
│   └── test_orchestrator.py     # Tests for orchestrator
├── test_main.py                 # Tests for main.py (co-located at root)
├── output/
│   ├── recordings/              # MP3 files go here
│   └── transcripts/             # Transcript files go here
└── scenarios/
    └── patient_scenarios.json   # Scenario definitions
```

---

## ENVIRONMENT VARIABLES (.env.example)

```bash
# Twilio (VoIP)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

# Deepgram (TTS + STT)
DEEPGRAM_API_KEY=your_deepgram_api_key

# OpenAI (LLM Patient Agent)
OPENAI_API_KEY=your_openai_api_key

# Target
TARGET_PHONE_NUMBER=+18054398008

# Server
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
NGROK_AUTH_TOKEN=your_ngrok_auth_token
```

---

## REQUIREMENTS.TXT

```
twilio>=9.0.0
deepgram-sdk>=3.5.0
openai>=1.40.0
websockets>=12.0
fastapi>=0.110.0
uvicorn>=0.29.0
pyngrok>=7.1.0
pydub>=0.25.1
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-mock>=3.12.0
aiohttp>=3.9.0
numpy>=1.26.0
```

---

## PYTEST CONFIGURATION

Since tests live alongside source files inside `src/`, pytest needs to be told where to find them. Create this `pyproject.toml` at the project root **before writing any tests**:

```toml
[tool.pytest.ini_options]
testpaths = ["src", "."]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

Also create a root-level `conftest.py` (NOT inside `src/`) for shared fixtures that all test files can access. Pytest automatically discovers `conftest.py` files in parent directories.

---

## DEPENDENCIES INSTALLATION

Before starting any module, run:

```bash
pip install twilio deepgram-sdk openai websockets fastapi uvicorn pyngrok pydub python-dotenv pytest pytest-asyncio pytest-mock aiohttp numpy
apt-get update && apt-get install -y ffmpeg
```

`ffmpeg` is required by `pydub` for MP3 encoding.

---

## STATUS.MD TEMPLATE

Create this file at project start and update after every step:

```markdown
# STATUS.md — Build Progress

## Overall Status: IN_PROGRESS

## Module 1: Utilities
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 1.1  | Config      | NOT_STARTED | -      |       |
| 1.2  | AudioUtils  | NOT_STARTED | -      |       |
| 1.3  | Logger      | NOT_STARTED | -      |       |
| 1.4  | CallRecorder| NOT_STARTED | -      |       |

## Module 2: TTS
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 2.1  | Base class  | NOT_STARTED | -      |       |
| 2.2  | Deepgram TTS| NOT_STARTED | -      |       |

## Module 3: STT
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 3.1  | Base class  | NOT_STARTED | -      |       |
| 3.2  | Deepgram STT| NOT_STARTED | -      |       |

## Module 4: Patient Agent
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 4.1  | Scenarios   | NOT_STARTED | -      |       |
| 4.2  | Agent       | NOT_STARTED | -      |       |

## Module 5: VoIP
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 5.1  | TwilioClient| NOT_STARTED | -      |       |
| 5.2  | MediaStream | NOT_STARTED | -      |       |

## Module 6: Orchestrator
| Step | Description | Status | Tests Pass | Notes |
|------|-------------|--------|------------|-------|
| 6.1  | Orchestrator| NOT_STARTED | -      |       |
| 6.2  | End-to-end  | NOT_STARTED | -      |       |

## Failures Log
| Module | Step | Error | Attempts | Resolution |
|--------|------|-------|----------|------------|
```

---

## MODULE 1: UTILITIES

### Design

Four utility classes that all other modules depend on. No external API calls needed for testing (pure logic).

#### 1.1 Config (`src/config.py`)

**Purpose:** Load and validate environment variables from `.env`.

**API:**
```python
class Config:
    """Singleton configuration manager."""

    def __init__(self, env_path: str = ".env"):
        """Load .env file and populate attributes."""

    # Attributes (set during __init__):
    # twilio_account_sid: str
    # twilio_auth_token: str
    # twilio_phone_number: str
    # deepgram_api_key: str
    # openai_api_key: str
    # target_phone_number: str  (default: +18054398008)
    # websocket_host: str       (default: 0.0.0.0)
    # websocket_port: int       (default: 8765)
    # ngrok_auth_token: str

    def validate(self) -> list[str]:
        """Return list of missing required env vars. Empty list = all valid."""

    @classmethod
    def from_env(cls) -> "Config":
        """Factory that loads from default .env location."""
```

**Implementation steps:**

**Step 1.1a:** Create `pyproject.toml` (pytest config), `conftest.py` (root shared fixtures), `src/__init__.py` (empty), `src/config.py` with `Config.__init__` and `validate`, and `src/test_config.py`.

Tests for 1.1a:
- `test_config_loads_from_env_file` — Create a temp .env file, load it, assert attributes are set.
- `test_config_validate_returns_missing_vars` — Create config with missing keys, assert validate returns their names.
- `test_config_validate_returns_empty_when_valid` — All keys present, validate returns `[]`.
- `test_config_default_values` — Assert target_phone_number defaults to `+18054398008`, websocket_port defaults to 8765.

Run: `pytest src/test_config.py -v`

---

#### 1.2 AudioUtils (`src/audio_utils.py`)

**Purpose:** Convert between audio formats needed by the pipeline.

**API:**
```python
class AudioUtils:
    """Static methods for audio format conversion."""

    @staticmethod
    def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
        """Convert mulaw-encoded bytes to 16-bit PCM. Twilio sends mulaw 8kHz."""

    @staticmethod
    def pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
        """Convert 16-bit PCM bytes to mulaw encoding. For sending to Twilio."""

    @staticmethod
    def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 8000, channels: int = 1) -> bytes:
        """Wrap raw PCM in a WAV container with proper headers."""

    @staticmethod
    def wav_to_mp3(wav_bytes: bytes) -> bytes:
        """Convert WAV bytes to MP3 using pydub+ffmpeg."""

    @staticmethod
    def resample_pcm(pcm_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample 16-bit PCM audio from one sample rate to another using linear interpolation."""

    @staticmethod
    def mix_audio_streams(stream_a: bytes, stream_b: bytes, sample_rate: int = 8000) -> bytes:
        """Mix two PCM audio streams (same sample rate) into one. Zero-pad the shorter one."""

    @staticmethod
    def base64_to_bytes(b64_string: str) -> bytes:
        """Decode base64 string to raw bytes. Twilio sends audio as base64."""

    @staticmethod
    def bytes_to_base64(raw_bytes: bytes) -> str:
        """Encode raw bytes to base64 string. For sending audio to Twilio."""
```

**Implementation steps:**

**Step 1.2a:** Implement `mulaw_to_pcm`, `pcm_to_mulaw`, `base64_to_bytes`, `bytes_to_base64`. Use the `audioop` module (Python stdlib) for mulaw conversion. If `audioop` is removed (Python 3.13+), use a lookup-table approach.

Note: In Python 3.13+, `audioop` was removed. Check the Python version first:
```python
import sys
if sys.version_info >= (3, 13):
    # Use manual mulaw lookup tables
else:
    import audioop
```

For manual mulaw implementation without audioop, use numpy:
```python
import numpy as np

MULAW_BIAS = 33
MULAW_MAX = 0x1FFF

def _mulaw_encode_sample(sample: int) -> int:
    """Encode a single 16-bit PCM sample to 8-bit mulaw."""
    sign = (sample >> 8) & 0x80
    if sign:
        sample = -sample
    sample = min(sample + MULAW_BIAS, 32767)
    exponent = 7
    for exp_val in [0x4000, 0x2000, 0x1000, 0x0800, 0x0400, 0x0200, 0x0100]:
        if sample >= exp_val:
            break
        exponent -= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF
```

Tests for 1.2a:
- `test_mulaw_to_pcm_returns_bytes` — Convert known mulaw bytes, assert output is bytes and correct length.
- `test_pcm_to_mulaw_returns_bytes` — Convert known PCM, assert output is bytes.
- `test_mulaw_roundtrip` — Encode PCM to mulaw then back; assert values are close (mulaw is lossy but within tolerance).
- `test_base64_roundtrip` — Encode bytes to base64 then decode; assert exact match.

Run: `pytest src/test_audio_utils.py -v -k "mulaw or base64"`

**Step 1.2b:** Implement `pcm_to_wav`, `wav_to_mp3`, `resample_pcm`, `mix_audio_streams`.

Tests for 1.2b:
- `test_pcm_to_wav_has_valid_header` — Assert output starts with `RIFF` and `WAVE` markers.
- `test_pcm_to_wav_correct_params` — Parse WAV header, assert sample rate and channels match input.
- `test_wav_to_mp3_produces_valid_mp3` — Assert output starts with MP3 frame sync bytes or ID3 tag.
- `test_resample_doubles_length` — Resample from 8000 to 16000 Hz, assert output is ~2x length.
- `test_mix_audio_streams_same_length` — Mix two equal-length streams, assert output length matches.
- `test_mix_audio_streams_different_length` — Mix different lengths, assert output length matches longer.

Run: `pytest src/test_audio_utils.py -v`

---

#### 1.3 Logger (`src/logger.py`)

**Purpose:** Structured logging with call context.

**API:**
```python
import logging

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with a structured formatter. Format: [TIMESTAMP] [LEVEL] [NAME] message."""

class CallLogger:
    """Logger with call_id context for per-call log tracking."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self._logger = get_logger(f"call.{call_id}")

    def info(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...
    def warning(self, msg: str, **kwargs) -> None: ...
    def debug(self, msg: str, **kwargs) -> None: ...
```

**Step 1.3a:** Implement both `get_logger` and `CallLogger`.

Tests for 1.3a:
- `test_get_logger_returns_logger` — Assert return type is `logging.Logger`.
- `test_get_logger_has_handler` — Assert logger has at least one handler.
- `test_call_logger_includes_call_id` — Capture log output, assert call_id appears.
- `test_call_logger_levels` — Call info/error/warning/debug, assert no exceptions.

Run: `pytest src/test_logger.py -v`

---

#### 1.4 CallRecorder (`src/call_recorder.py`)

**Purpose:** Accumulate audio chunks during a call and save as MP3. Also save transcripts.

**API:**
```python
class CallRecorder:
    """Records both sides of a call and produces MP3 + transcript files."""

    def __init__(self, call_id: str, output_dir: str = "output"):
        """Initialize with a unique call ID. Creates output subdirectories if needed."""

    def add_inbound_chunk(self, pcm_bytes: bytes) -> None:
        """Append a PCM audio chunk from the remote party (Pretty Good AI agent)."""

    def add_outbound_chunk(self, pcm_bytes: bytes) -> None:
        """Append a PCM audio chunk from our bot (the patient)."""

    def add_transcript_entry(self, speaker: str, text: str, timestamp: float) -> None:
        """Add a transcript line. speaker is 'agent' or 'patient'."""

    def save_recording(self) -> str:
        """Mix inbound+outbound, convert to MP3, save. Returns file path."""

    def save_transcript(self) -> str:
        """Save transcript as JSON and TXT. Returns TXT file path."""

    def get_transcript_text(self) -> str:
        """Return transcript as formatted text string."""
```

**Step 1.4a:** Implement `__init__`, `add_inbound_chunk`, `add_outbound_chunk`, `add_transcript_entry`.

Tests for 1.4a:
- `test_recorder_creates_output_dirs` — Assert directories are created.
- `test_add_inbound_chunk_stores_data` — Add chunks, assert internal buffer grows.
- `test_add_outbound_chunk_stores_data` — Same for outbound.
- `test_add_transcript_entry_stores_entry` — Add entries, assert they're retrievable.

Run: `pytest src/test_call_recorder.py -v -k "step1"`

**Step 1.4b:** Implement `save_recording`, `save_transcript`, `get_transcript_text`.

Tests for 1.4b:
- `test_save_recording_creates_mp3` — Add sample PCM chunks, save, assert MP3 file exists and is non-empty.
- `test_save_transcript_creates_files` — Add transcript entries, save, assert TXT and JSON files exist.
- `test_get_transcript_text_format` — Assert format is `[TIMESTAMP] SPEAKER: text`.
- `test_save_recording_empty_audio_handles_gracefully` — No chunks added, save should not crash (produce silent file or skip).

Run: `pytest src/test_call_recorder.py -v`

Then run ALL Module 1 tests: `pytest src/test_config.py src/test_audio_utils.py src/test_logger.py src/test_call_recorder.py -v`

**Update STATUS.md for Module 1.**

---

## MODULE 2: TEXT-TO-SPEECH (TTS)

### Design

Abstract base class + Deepgram implementation. TTS converts LLM response text into audio bytes suitable for sending over Twilio (mulaw 8kHz).

#### 2.1 Base Class (`src/tts/base.py`)

**API:**
```python
from abc import ABC, abstractmethod

class BaseTTS(ABC):
    """Abstract TTS interface. All TTS providers must implement this."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (PCM 16-bit, specific sample rate).
        Returns raw PCM audio bytes."""
        ...

    @abstractmethod
    async def synthesize_to_mulaw(self, text: str) -> bytes:
        """Convert text to mulaw 8kHz audio bytes ready for Twilio."""
        ...

    @abstractmethod
    def get_sample_rate(self) -> int:
        """Return the native sample rate of this TTS provider."""
        ...
```

**Step 2.1a:** Create `src/tts/__init__.py`, `src/tts/base.py`, `src/tts/conftest.py`, and `src/tts/test_base.py`.

Tests for 2.1a:
- `test_base_tts_cannot_instantiate` — Assert `BaseTTS()` raises `TypeError`.
- `test_base_tts_subclass_must_implement_methods` — Create a partial subclass, assert it also raises `TypeError`.
- `test_base_tts_complete_subclass_works` — Create a mock subclass implementing all methods, instantiate it successfully.

Run: `pytest src/tts/test_base.py -v`

---

#### 2.2 Deepgram TTS (`src/tts/deepgram_tts.py`)

**API:**
```python
from src.tts.base import BaseTTS

class DeepgramTTS(BaseTTS):
    """Deepgram TTS implementation using their REST API."""

    def __init__(self, api_key: str, model: str = "aura-asteria-en", sample_rate: int = 8000):
        """Initialize with Deepgram API key."""

    async def synthesize(self, text: str) -> bytes:
        """Call Deepgram TTS API. Returns PCM audio bytes.
        Uses encoding=linear16 and the configured sample_rate.
        Endpoint: POST https://api.deepgram.com/v1/speak
        Query params: model, encoding=linear16, sample_rate, container=none
        Headers: Authorization: Token <api_key>, Content-Type: application/json
        Body: {"text": text}
        """

    async def synthesize_to_mulaw(self, text: str) -> bytes:
        """Call Deepgram TTS API with mulaw encoding.
        Uses encoding=mulaw and sample_rate=8000.
        This avoids needing to convert PCM→mulaw ourselves.
        Endpoint: POST https://api.deepgram.com/v1/speak
        Query params: model, encoding=mulaw, sample_rate=8000, container=none
        """

    def get_sample_rate(self) -> int:
        return self.sample_rate
```

**Implementation notes:**
- Use `aiohttp` for async HTTP requests to Deepgram's REST API.
- Deepgram TTS endpoint: `https://api.deepgram.com/v1/speak`
- Request body is JSON: `{"text": "Hello world"}`
- Query parameters control output format: `model=aura-asteria-en&encoding=mulaw&sample_rate=8000&container=none`
- Response body is raw audio bytes.
- Handle HTTP errors (401 unauthorized, 429 rate limited, etc.) with clear error messages.

**Step 2.2a:** Implement `DeepgramTTS.__init__` and `synthesize` (basic version with aiohttp POST).

Tests for 2.2a (use mocking for unit tests — no real API calls, write in `src/tts/test_deepgram_tts.py`):
- `test_deepgram_tts_init_stores_config` — Assert api_key, model, sample_rate are stored.
- `test_deepgram_tts_synthesize_calls_api` — Mock aiohttp, assert correct URL and headers.
- `test_deepgram_tts_synthesize_returns_bytes` — Mock response with sample bytes, assert return is bytes.
- `test_deepgram_tts_synthesize_handles_error` — Mock 401 response, assert raises exception.
- `test_deepgram_tts_synthesize_empty_text` — Assert raises ValueError for empty string.

Run: `pytest src/tts/test_deepgram_tts.py -v`

**Step 2.2b:** Implement `synthesize_to_mulaw` and `get_sample_rate`.

Tests for 2.2b:
- `test_deepgram_tts_synthesize_mulaw_uses_correct_params` — Mock aiohttp, assert query params include `encoding=mulaw`.
- `test_deepgram_tts_get_sample_rate` — Assert returns configured sample rate.

Run: `pytest src/tts/ -v`

**Update STATUS.md for Module 2.**

---

## MODULE 3: SPEECH-TO-TEXT (STT)

### Design

Abstract base class + Deepgram streaming implementation. STT receives audio chunks in real-time via WebSocket and emits transcribed text with utterance boundary detection.

#### 3.1 Base Class (`src/stt/base.py`)

**API:**
```python
from abc import ABC, abstractmethod
from typing import Callable, Optional

class BaseSTT(ABC):
    """Abstract STT interface for streaming speech-to-text."""

    @abstractmethod
    async def start_stream(self, on_transcript: Callable[[str, bool], None]) -> None:
        """Open a streaming STT session.
        on_transcript(text, is_final) is called when transcript is available.
        is_final=True means end of utterance (speaker stopped talking).
        """
        ...

    @abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send an audio chunk to the STT stream. Audio must be in the format
        expected by the provider (typically PCM 16-bit at 16kHz or 8kHz)."""
        ...

    @abstractmethod
    async def stop_stream(self) -> None:
        """Close the STT streaming session and release resources."""
        ...
```

**Step 3.1a:** Create `src/stt/__init__.py`, `src/stt/base.py`, `src/stt/conftest.py`, and `src/stt/test_base.py`.

Tests for 3.1a:
- `test_base_stt_cannot_instantiate` — Assert `BaseSTT()` raises `TypeError`.
- `test_base_stt_complete_subclass` — Mock subclass works.

Run: `pytest src/stt/test_base.py -v`

---

#### 3.2 Deepgram Streaming STT (`src/stt/deepgram_stt.py`)

**API:**
```python
from src.stt.base import BaseSTT
from typing import Callable
import asyncio
import json
import websockets

class DeepgramSTT(BaseSTT):
    """Deepgram streaming STT using their WebSocket API."""

    DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str, sample_rate: int = 8000, encoding: str = "mulaw", language: str = "en-US"):
        """Initialize. Does NOT open connection yet."""
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.language = language
        self._ws = None
        self._on_transcript = None
        self._listen_task = None

    async def start_stream(self, on_transcript: Callable[[str, bool], None]) -> None:
        """Connect to Deepgram WebSocket.
        URL: wss://api.deepgram.com/v1/listen?encoding={encoding}&sample_rate={sample_rate}&language={language}&model=nova-2&punctuate=true&interim_results=true&utterance_end_ms=1000&vad_events=true&endpointing=300
        Headers: Authorization: Token <api_key>
        Start a background task to listen for transcription responses.
        """

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Send audio chunk to Deepgram WebSocket as binary message.
        Must call start_stream first."""

    async def stop_stream(self) -> None:
        """Send close message to Deepgram and close WebSocket.
        Close message: JSON {"type": "CloseStream"}
        Cancel the listen task."""

    async def _listen_for_transcripts(self) -> None:
        """Background task: read messages from Deepgram WebSocket.
        Parse JSON messages. For type="Results":
          - Extract channel.alternatives[0].transcript
          - Check is_final and speech_final flags
          - Call self._on_transcript(text, is_final)
        For type="UtteranceEnd":
          - This signals the speaker has stopped. Call on_transcript("", True) as a flush signal.
        Handle connection errors gracefully."""
```

**Implementation notes:**
- Deepgram WebSocket protocol: send binary audio chunks, receive JSON transcription events.
- Key response types: `Results` (with interim/final transcripts), `UtteranceEnd`, `SpeechStarted`.
- `Results` message structure:
  ```json
  {
    "type": "Results",
    "channel": {
      "alternatives": [{"transcript": "hello", "confidence": 0.99}]
    },
    "is_final": true,
    "speech_final": true
  }
  ```
- Use `utterance_end_ms=1000` to detect 1-second silence as end-of-utterance.
- Use `endpointing=300` for faster turn detection (300ms silence).

**Step 3.2a:** Implement `DeepgramSTT.__init__` and `start_stream` (WebSocket connection).

Tests for 3.2a (mock WebSocket, write in `src/stt/test_deepgram_stt.py`):
- `test_deepgram_stt_init_stores_config` — Assert attributes are set.
- `test_deepgram_stt_start_stream_connects` — Mock websockets.connect, assert called with correct URL.
- `test_deepgram_stt_start_stream_stores_callback` — Assert on_transcript is stored.
- `test_deepgram_stt_send_audio_before_start_raises` — Assert raises RuntimeError.

Run: `pytest src/stt/test_deepgram_stt.py -v -k "init or start"`

**Step 3.2b:** Implement `send_audio`, `stop_stream`, and `_listen_for_transcripts`.

Tests for 3.2b:
- `test_deepgram_stt_send_audio_sends_bytes` — Mock ws.send, assert called with bytes.
- `test_deepgram_stt_stop_stream_closes` — Mock ws.close, assert called.
- `test_deepgram_stt_listen_parses_results` — Feed mock JSON messages, assert callback is called with correct text and is_final.
- `test_deepgram_stt_listen_handles_utterance_end` — Feed UtteranceEnd message, assert callback called.

Run: `pytest src/stt/ -v`

**Update STATUS.md for Module 3.**

---

## MODULE 4: LLM PATIENT AGENT

### Design

The patient agent uses an LLM (OpenAI GPT-4o-mini) to generate realistic patient responses based on a scenario. It maintains conversation history and produces contextually appropriate responses.

#### 4.1 Scenarios (`src/patient/scenarios.py`)

**API:**
```python
from dataclasses import dataclass, field

@dataclass
class PatientScenario:
    """Defines a patient persona and their reason for calling."""
    id: str                        # Unique scenario ID, e.g. "scheduling_new"
    name: str                      # Patient name, e.g. "Sarah Johnson"
    description: str               # Scenario summary for logging
    system_prompt: str             # Full system prompt for the LLM
    opening_line: str              # What the patient says first
    tags: list[str] = field(default_factory=list)  # e.g. ["scheduling", "simple"]

def get_default_scenarios() -> list[PatientScenario]:
    """Return a list of 12+ predefined patient scenarios covering all required categories:
    1.  Simple appointment scheduling (new patient)
    2.  Appointment scheduling (returning patient)
    3.  Rescheduling an existing appointment
    4.  Canceling an appointment
    5.  Medication refill request (simple)
    6.  Medication refill request (controlled substance — edge case)
    7.  Question about office hours
    8.  Question about location/directions
    9.  Question about accepted insurance
    10. Interruption / unclear request (edge case)
    11. Non-English speaker / heavy accent simulation (edge case)
    12. Multiple requests in one call (scheduling + refill)
    13. Emotional/anxious patient (edge case)
    14. Wrong number / confused patient (edge case)
    """

def load_scenarios_from_file(filepath: str) -> list[PatientScenario]:
    """Load scenarios from a JSON file."""

def save_scenarios_to_file(scenarios: list[PatientScenario], filepath: str) -> None:
    """Save scenarios to a JSON file."""
```

**System prompt template for each scenario:**
```
You are {name}, a patient calling a medical office. You are calling to {reason}.

PERSONALITY:
{personality_traits}

RULES:
- Speak naturally and conversationally, as a real person would on the phone.
- Keep responses short (1-3 sentences). Real patients don't give speeches.
- If asked for information you don't have in your persona, improvise realistically.
- React to what the agent says — don't just robotically follow a script.
- If the agent asks you to hold, say "sure" or "okay" and wait.
- If the agent says something confusing or wrong, ask for clarification.
- When the call's purpose is fulfilled, thank them and say goodbye.
- Use filler words occasionally (um, uh, well, so) to sound natural.

YOUR DETAILS:
- Name: {name}
- Date of birth: {dob}
- Phone number: {phone}
- Reason for calling: {reason}
{additional_details}
```

**Step 4.1a:** Create `src/patient/__init__.py`, `src/patient/scenarios.py`, `src/patient/conftest.py`, and `src/patient/test_scenarios.py`. Implement `PatientScenario` dataclass and `get_default_scenarios` with at least 12 scenarios.

Tests for 4.1a:
- `test_patient_scenario_creation` — Create a scenario, assert all fields are set.
- `test_get_default_scenarios_returns_list` — Assert returns non-empty list.
- `test_get_default_scenarios_minimum_count` — Assert >= 12 scenarios.
- `test_get_default_scenarios_all_have_required_fields` — Assert every scenario has non-empty id, name, system_prompt, opening_line.
- `test_get_default_scenarios_covers_categories` — Assert tags cover: scheduling, rescheduling, canceling, refill, office_hours, location, insurance, edge_case.
- `test_scenario_serialization_roundtrip` — Save to JSON and load back, assert equality.

Run: `pytest src/patient/test_scenarios.py -v`

---

#### 4.2 Patient Agent (`src/patient/agent.py`)

**API:**
```python
from openai import AsyncOpenAI

class PatientAgent:
    """LLM-powered patient that generates conversational responses."""

    def __init__(self, api_key: str, scenario: PatientScenario, model: str = "gpt-4o-mini"):
        """Initialize with OpenAI key and a patient scenario."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.scenario = scenario
        self.model = model
        self.conversation_history: list[dict] = []
        self._system_message = {"role": "system", "content": scenario.system_prompt}

    async def get_opening_line(self) -> str:
        """Return the scenario's opening line and add it to history."""

    async def generate_response(self, agent_utterance: str) -> str:
        """Given what the PGAI agent just said, generate the patient's response.
        1. Add agent_utterance to history as 'user' role (from the patient's perspective,
           the office agent is the 'user' asking questions).
           Actually, let's use proper role mapping:
           - system: patient persona prompt
           - assistant: patient's previous responses
           - user: what the PGAI agent said (the input to respond to)
        2. Call OpenAI API with full conversation history.
        3. Extract response text.
        4. Add response to history as 'assistant'.
        5. Return response text.
        """

    async def should_hang_up(self, agent_utterance: str) -> bool:
        """Determine if the conversation has naturally concluded.
        Check for goodbye patterns in the agent's utterance AND the patient's last response.
        Simple heuristic: both sides have said goodbye/thank you/have a good day."""

    def get_conversation_history(self) -> list[dict]:
        """Return full conversation history for transcript generation."""

    def reset(self) -> None:
        """Clear conversation history for reuse with same scenario."""
```

**Step 4.2a:** Implement `PatientAgent.__init__`, `get_opening_line`, and `reset`. Write tests in `src/patient/test_agent.py`.

Tests for 4.2a:
- `test_patient_agent_init` — Assert client, scenario, model, empty history.
- `test_patient_agent_opening_line` — Assert returns scenario's opening_line and adds to history.
- `test_patient_agent_reset_clears_history` — Add entries, reset, assert empty.

Run: `pytest src/patient/test_agent.py -v -k "init or opening or reset"`

**Step 4.2b:** Implement `generate_response` and `should_hang_up`.

Tests for 4.2b (mock OpenAI API):
- `test_generate_response_calls_openai` — Mock AsyncOpenAI, assert `chat.completions.create` is called.
- `test_generate_response_includes_history` — Assert messages include system prompt + full history.
- `test_generate_response_adds_to_history` — After call, history has new entries.
- `test_generate_response_returns_string` — Assert return type is str.
- `test_should_hang_up_detects_goodbye` — Feed goodbye phrases, assert returns True.
- `test_should_hang_up_returns_false_for_normal_speech` — Feed normal text, assert False.

Run: `pytest src/patient/ -v`

**Update STATUS.md for Module 4.**

---

## MODULE 5: VoIP (TWILIO + WEBSOCKET)

### Design

This is the most complex module. It has two parts:
1. **TwilioClient** — makes outbound calls via Twilio REST API.
2. **MediaStreamHandler** — handles the bidirectional WebSocket connection for real-time audio.

#### 5.1 TwilioClient (`src/voip/twilio_client.py`)

**API:**
```python
from twilio.rest import Client

class TwilioClient:
    """Manages outbound calls via Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """Initialize Twilio client."""
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def make_call(self, to_number: str, websocket_url: str) -> str:
        """Initiate an outbound call that connects to our WebSocket for media streaming.
        Uses TwiML:
          <Response>
            <Connect>
              <Stream url="{websocket_url}" />
            </Connect>
          </Response>
        Returns the call SID.
        """

    def get_call_status(self, call_sid: str) -> str:
        """Get current status of a call (queued, ringing, in-progress, completed, etc.)."""

    def end_call(self, call_sid: str) -> None:
        """Terminate a call by updating its status to 'completed'."""
```

**Step 5.1a:** Create `src/voip/__init__.py`, `src/voip/twilio_client.py`, `src/voip/conftest.py`, and `src/voip/test_twilio_client.py`. Implement all three methods.

Tests for 5.1a (mock Twilio client):
- `test_twilio_client_init` — Assert client and from_number are stored.
- `test_make_call_creates_call` — Mock `client.calls.create`, assert called with correct TwiML and numbers.
- `test_make_call_returns_sid` — Assert returns a string SID.
- `test_get_call_status_fetches` — Mock `client.calls().fetch`, assert returns status string.
- `test_end_call_updates_status` — Mock `client.calls().update`, assert called with `status='completed'`.

Run: `pytest src/voip/test_twilio_client.py -v`

---

#### 5.2 MediaStreamHandler (`src/voip/media_stream.py`)

**API:**
```python
import asyncio
import json
import websockets
from typing import Callable, Optional

class MediaStreamHandler:
    """Handles Twilio Media Stream WebSocket connections.

    Twilio Media Streams protocol:
    - 'connected' event: WebSocket connected
    - 'start' event: Stream started, includes streamSid and metadata
    - 'media' event: Audio chunk (base64-encoded mulaw), includes payload and timestamp
    - 'stop' event: Stream ended

    To send audio back to the caller:
    Send JSON: {"event": "media", "streamSid": "...", "media": {"payload": "<base64 mulaw audio>"}}
    """

    def __init__(self):
        self.stream_sid: Optional[str] = None
        self._on_audio_received: Optional[Callable] = None
        self._ws = None
        self._is_connected = False

    async def handle_connection(self, websocket, on_audio_received: Callable[[bytes], None]) -> None:
        """Main handler for an incoming WebSocket connection from Twilio.
        1. Store the websocket and callback.
        2. Listen for messages in a loop.
        3. Dispatch to appropriate handler based on event type.
        4. Continue until 'stop' event or connection closes.
        """

    async def _handle_event(self, message: str) -> None:
        """Parse JSON message and dispatch:
        - 'connected': log it, set _is_connected = True
        - 'start': extract and store streamSid from msg['start']['streamSid']
        - 'media': decode base64 audio from msg['media']['payload'],
                   call self._on_audio_received(decoded_bytes)
        - 'stop': log it, set _is_connected = False
        """

    async def send_audio(self, mulaw_audio_bytes: bytes) -> None:
        """Send audio back to Twilio through the media stream.
        1. Base64-encode the mulaw audio.
        2. Send JSON: {"event": "media", "streamSid": self.stream_sid, "media": {"payload": b64_audio}}
        Must chunk audio into segments of 20ms (160 bytes at 8kHz mulaw) for smooth playback.
        """

    async def send_clear(self) -> None:
        """Send a clear event to stop any queued audio on Twilio's side.
        JSON: {"event": "clear", "streamSid": self.stream_sid}
        Use this when the bot is interrupted (barge-in)."""

    def is_connected(self) -> bool:
        return self._is_connected
```

**Step 5.2a:** Create `src/voip/media_stream.py` and `src/voip/test_media_stream.py`. Implement `__init__`, `handle_connection`, `_handle_event`.

Tests for 5.2a:
- `test_media_stream_init` — Assert initial state (stream_sid is None, not connected).
- `test_handle_event_connected` — Feed connected event JSON, assert _is_connected is True.
- `test_handle_event_start` — Feed start event JSON with streamSid, assert stored.
- `test_handle_event_media` — Feed media event with base64 payload, assert callback called with decoded bytes.
- `test_handle_event_stop` — Feed stop event, assert _is_connected is False.
- `test_handle_event_unknown_event` — Feed unknown event type, assert no crash.

Run: `pytest src/voip/test_media_stream.py -v`

**Step 5.2b:** Implement `send_audio` and `send_clear`.

Tests for 5.2b:
- `test_send_audio_sends_json` — Mock websocket.send, assert JSON has correct structure.
- `test_send_audio_chunks_correctly` — Send 640 bytes (80ms), assert 4 messages sent (20ms each = 160 bytes).
- `test_send_clear_sends_clear_event` — Assert JSON has event=clear and correct streamSid.
- `test_send_audio_when_not_connected_raises` — Assert raises RuntimeError.

Run: `pytest src/voip/ -v`

**Update STATUS.md for Module 5.**

---

## MODULE 6: ORCHESTRATOR

### Design

The orchestrator ties everything together. It manages the full lifecycle of a call: starts the WebSocket server, establishes the Twilio call, pipes audio through STT → LLM → TTS, records everything, and saves output.

#### 6.1 Orchestrator (`src/orchestrator.py`)

**API:**
```python
import asyncio

class CallPipeline:
    """Manages the real-time audio pipeline for a single call."""

    def __init__(self, config, scenario, call_id: str):
        """Instantiate TTS, STT, PatientAgent, CallRecorder for this call."""

    async def start(self, media_handler: MediaStreamHandler) -> None:
        """Begin the pipeline:
        1. Start STT stream with _on_transcript callback.
        2. Wait for a brief pause after connection (1-2 seconds) for the PGAI agent greeting.
        3. Pipeline runs until call ends or timeout.
        """

    async def _on_transcript(self, text: str, is_final: bool) -> None:
        """Called when STT produces a transcript.
        If is_final and text is non-empty:
          1. Log the agent's utterance.
          2. Record transcript entry.
          3. Check if should_hang_up.
          4. Generate patient response via LLM.
          5. Synthesize response via TTS.
          6. Send audio to media stream.
          7. Record transcript entry for patient.
        """

    async def _on_audio_received(self, audio_bytes: bytes) -> None:
        """Called when audio is received from Twilio.
        1. Record inbound chunk.
        2. Forward to STT.
        """

    async def stop(self) -> None:
        """Clean up: stop STT, save recording and transcript."""


class Orchestrator:
    """Top-level controller that runs multiple calls."""

    def __init__(self, config):
        """Initialize with config. Create TwilioClient."""

    async def run_call(self, scenario: PatientScenario) -> dict:
        """Execute a single call with the given scenario.
        1. Generate unique call_id.
        2. Start WebSocket server (on config.websocket_port).
        3. Start ngrok tunnel to expose WebSocket server.
        4. Make Twilio outbound call pointing to ngrok WebSocket URL.
        5. Wait for WebSocket connection from Twilio.
        6. Create and start CallPipeline.
        7. Wait for call to complete (natural end or timeout after 180 seconds).
        8. Save recording and transcript.
        9. Return call metadata (call_id, duration, transcript_path, recording_path).
        """

    async def run_all_scenarios(self, scenarios: list[PatientScenario], delay_between_calls: int = 10) -> list[dict]:
        """Run calls for all scenarios sequentially.
        Add a delay between calls to avoid rate limiting.
        Return list of call metadata dicts.
        """

    async def generate_bug_report(self, call_results: list[dict]) -> str:
        """After all calls complete, use LLM to analyze transcripts and
        identify bugs/issues in the PGAI agent's responses.
        Save to output/bug_report.md.
        Return the report content.
        """
```

**Implementation notes for the WebSocket server:**
```python
import websockets
from pyngrok import ngrok

async def _start_websocket_server(self, pipeline):
    """Start WebSocket server and return the server object."""
    async def handler(websocket, path):
        media_handler = MediaStreamHandler()
        # Connect pipeline's audio callback to media handler
        await media_handler.handle_connection(
            websocket,
            on_audio_received=pipeline._on_audio_received
        )
    server = await websockets.serve(handler, self.config.websocket_host, self.config.websocket_port)
    return server

def _start_ngrok(self):
    """Start ngrok tunnel and return the public WebSocket URL."""
    ngrok.set_auth_token(self.config.ngrok_auth_token)
    tunnel = ngrok.connect(self.config.websocket_port, "tcp")
    # Convert tcp://host:port to wss://host:port
    public_url = tunnel.public_url.replace("tcp://", "wss://")
    return public_url
```

**Important timing considerations:**
- After Twilio connects the call, the PGAI agent will greet first ("Thank you for calling...").
- The bot should wait and listen to the full greeting before responding.
- Use the STT `is_final` / `utterance_end` signals to detect when the agent stops talking.
- After the agent's greeting, send the patient's opening line via TTS.
- Then enter the conversational loop.

**Step 6.1a:** Create `src/test_orchestrator.py`. Implement `CallPipeline.__init__`, `_on_audio_received`, and `_on_transcript` skeleton.

Tests for 6.1a (heavily mocked):
- `test_call_pipeline_init_creates_components` — Assert TTS, STT, PatientAgent, CallRecorder are created.
- `test_on_audio_received_records_and_forwards` — Mock recorder and STT, assert both called.
- `test_on_transcript_triggers_response_flow` — Mock agent and TTS, feed final transcript, assert response generated.

Run: `pytest src/test_orchestrator.py -v -k "pipeline"`

**Step 6.1b:** Implement `Orchestrator.__init__`, `run_call`, `run_all_scenarios`.

Tests for 6.1b:
- `test_orchestrator_init` — Assert config and twilio_client are set.
- `test_run_call_returns_metadata` — Mock all components, assert returns dict with call_id, duration, paths.
- `test_run_all_scenarios_runs_sequentially` — Mock run_call, feed 3 scenarios, assert called 3 times.

Run: `pytest src/test_orchestrator.py -v`

**Step 6.1c:** Implement `generate_bug_report`.

Tests for 6.1c:
- `test_generate_bug_report_creates_file` — Mock OpenAI, assert output/bug_report.md is created.
- `test_generate_bug_report_includes_transcripts` — Assert all transcripts are included in the LLM prompt.

Run: `pytest src/test_orchestrator.py -v`

**Update STATUS.md for Module 6.**

---

## MODULE 7: MAIN ENTRY POINT AND FINAL INTEGRATION

### 7.1 Main Script (`main.py`)

```python
"""Main entry point. Run: python main.py"""
import asyncio
from src.config import Config
from src.patient.scenarios import get_default_scenarios
from src.orchestrator import Orchestrator

async def main():
    config = Config.from_env()
    missing = config.validate()
    if missing:
        print(f"Missing environment variables: {missing}")
        return

    orchestrator = Orchestrator(config)
    scenarios = get_default_scenarios()

    # Run first 2 calls as a quick test, then all 12+
    print(f"Running {len(scenarios)} call scenarios...")
    results = await orchestrator.run_all_scenarios(scenarios)

    print(f"\nCompleted {len(results)} calls.")
    for r in results:
        print(f"  Call {r['call_id']}: {r.get('status', 'unknown')} - {r.get('duration', 0):.1f}s")

    # Generate bug report
    report = await orchestrator.generate_bug_report(results)
    print(f"\nBug report saved to output/bug_report.md")

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 7.1a:** Create `main.py` and `test_main.py` (at project root, co-located with main.py).

Tests for 7.1a:
- `test_main_validates_config` — Mock Config with missing vars, assert prints error.
- `test_main_runs_orchestrator` — Mock everything, assert orchestrator.run_all_scenarios is called.

Run: `pytest test_main.py -v`

Then run the FULL test suite across all components: `pytest src/ . -v`

---

## MODULE 8: README AND DOCUMENTATION

### 8.1 README.md

Create `README.md` with:

```markdown
# PGAI Voice Bot — Patient Simulator

A voice bot that calls Pretty Good AI's test line, simulates realistic patient
conversations, and identifies bugs in their AI agent.

## Quick Start

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   apt-get install -y ffmpeg  # Required for MP3 encoding
   ```

2. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

## Required API Keys
- **Twilio**: Account SID, Auth Token, Phone Number (for making calls)
- **Deepgram**: API Key (for speech-to-text and text-to-speech)
- **OpenAI**: API Key (for LLM patient agent)
- **ngrok**: Auth Token (for exposing WebSocket server)

## Architecture

The bot uses a pipeline architecture with six components:

1. **VoIP (Twilio)** — Makes outbound calls and streams audio via WebSocket
2. **STT (Deepgram)** — Real-time streaming speech-to-text
3. **Patient Agent (OpenAI)** — LLM-powered patient persona
4. **TTS (Deepgram)** — Converts patient responses to speech
5. **Call Recorder** — Captures full call audio as MP3 + transcripts
6. **Orchestrator** — Manages the call lifecycle and scenario rotation

The real-time pipeline receives audio from Twilio's Media Streams via WebSocket,
transcribes it with Deepgram's streaming STT, generates responses with GPT-4o-mini,
synthesizes speech with Deepgram TTS, and sends it back through the WebSocket.

## Output
- `output/recordings/` — MP3 files for each call
- `output/transcripts/` — Text transcripts for each call
- `output/bug_report.md` — Analysis of issues found
```

### 8.2 Architecture Doc

Create `ARCHITECTURE.md` (1-2 paragraphs as required by the challenge):

```markdown
# Architecture

This voice bot uses a streaming pipeline architecture to conduct real-time phone
conversations. Twilio handles telephony: an outbound call is placed via REST API, and
bidirectional audio flows through Twilio Media Streams over a WebSocket connection,
exposed publicly via ngrok. Incoming audio (mulaw 8kHz from Twilio) is streamed to
Deepgram's WebSocket-based STT service for real-time transcription with utterance
boundary detection. When the remote agent finishes speaking, the transcribed text is
sent to an OpenAI GPT-4o-mini powered patient agent that maintains conversation context
and generates natural responses. The response text is then synthesized to speech via
Deepgram's TTS API (mulaw 8kHz output) and sent back through the Twilio WebSocket as
chunked base64-encoded media events.

I chose this architecture for three reasons: (1) streaming STT + TTS minimizes latency
compared to batch processing, keeping the conversation natural; (2) Deepgram handles
both STT and TTS with native mulaw support, eliminating audio format conversion
overhead; (3) the component-based design with abstract interfaces allows swapping
providers without changing the pipeline logic. The patient agent uses structured
scenarios with detailed personas to produce varied, realistic conversations that
stress-test different aspects of the PGAI system. Each call is recorded in full
(both sides mixed to MP3) with timestamped transcripts, and a post-run LLM analysis
identifies bugs and quality issues across all calls.
```

---

## DEVELOPMENT ORDER SUMMARY

Execute modules in this exact order. Never skip ahead.

| Order | Module | Steps | Depends On |
|-------|--------|-------|------------|
| 1     | Utilities (Config, AudioUtils, Logger, CallRecorder) | 1.1a → 1.2a → 1.2b → 1.3a → 1.4a → 1.4b | Nothing |
| 2     | TTS | 2.1a → 2.2a → 2.2b | Module 1 |
| 3     | STT | 3.1a → 3.2a → 3.2b | Module 1 |
| 4     | Patient Agent | 4.1a → 4.2a → 4.2b | Module 1 |
| 5     | VoIP | 5.1a → 5.2a → 5.2b | Module 1 |
| 6     | Orchestrator | 6.1a → 6.1b → 6.1c | Modules 1-5 |
| 7     | Main + Integration | 7.1a | Module 6 |
| 8     | README + Docs | 8.1 → 8.2 | All modules |

---

## TESTING STRATEGY

### Co-Located Test Layout

Tests live alongside their source files inside `src/`. Each subpackage has its own `conftest.py` for component-specific fixtures. A root-level `conftest.py` (at the project root, outside `src/`) provides shared fixtures available to all tests.

```
pgai-voice-bot/
├── conftest.py                  # ROOT: shared fixtures (sample audio, env, scenario)
├── pyproject.toml               # pytest config: testpaths = ["src", "."]
├── test_main.py                 # Tests for main.py
├── src/
│   ├── config.py
│   ├── test_config.py           # Tests right next to config.py
│   ├── audio_utils.py
│   ├── test_audio_utils.py      # Tests right next to audio_utils.py
│   ├── logger.py
│   ├── test_logger.py
│   ├── call_recorder.py
│   ├── test_call_recorder.py
│   ├── orchestrator.py
│   ├── test_orchestrator.py
│   ├── tts/
│   │   ├── conftest.py          # TTS mock fixtures (mock aiohttp)
│   │   ├── base.py
│   │   ├── test_base.py
│   │   ├── deepgram_tts.py
│   │   └── test_deepgram_tts.py
│   ├── stt/
│   │   ├── conftest.py          # STT mock fixtures (mock websocket)
│   │   ├── base.py
│   │   ├── test_base.py
│   │   ├── deepgram_stt.py
│   │   └── test_deepgram_stt.py
│   ├── patient/
│   │   ├── conftest.py          # Patient mock fixtures (mock openai)
│   │   ├── scenarios.py
│   │   ├── test_scenarios.py
│   │   ├── agent.py
│   │   └── test_agent.py
│   └── voip/
│       ├── conftest.py          # VoIP mock fixtures (mock twilio)
│       ├── twilio_client.py
│       ├── test_twilio_client.py
│       ├── media_stream.py
│       └── test_media_stream.py
```

### Root Fixtures (`conftest.py` at project root)

These are shared across ALL test files. Pytest auto-discovers `conftest.py` in parent directories.

```python
import pytest
import os
import tempfile

@pytest.fixture
def sample_env_file():
    """Create a temporary .env file with all required variables."""
    content = """
TWILIO_ACCOUNT_SID=test_sid
TWILIO_AUTH_TOKEN=test_token
TWILIO_PHONE_NUMBER=+11234567890
DEEPGRAM_API_KEY=test_deepgram_key
OPENAI_API_KEY=test_openai_key
TARGET_PHONE_NUMBER=+18054398008
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
NGROK_AUTH_TOKEN=test_ngrok_token
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def sample_pcm_audio():
    """Generate 1 second of silent PCM audio (16-bit, 8kHz, mono)."""
    import numpy as np
    samples = np.zeros(8000, dtype=np.int16)
    return samples.tobytes()

@pytest.fixture
def sample_mulaw_audio():
    """Generate 1 second of silent mulaw audio (8kHz)."""
    return b'\\xff' * 8000  # 0xFF is mulaw silence

@pytest.fixture
def sample_scenario():
    """Return a simple test scenario."""
    from src.patient.scenarios import PatientScenario
    return PatientScenario(
        id="test_scheduling",
        name="Test Patient",
        description="Test scenario for scheduling",
        system_prompt="You are Test Patient. You want to schedule an appointment for next Tuesday.",
        opening_line="Hi, I'd like to schedule an appointment please.",
        tags=["scheduling", "simple"]
    )

@pytest.fixture
def mock_config(sample_env_file):
    """Return a Config loaded from sample env."""
    from src.config import Config
    return Config(env_path=sample_env_file)
```

### Component-Specific Fixtures

**`src/tts/conftest.py` — Mocking aiohttp for Deepgram TTS:**
```python
import pytest

@pytest.fixture
def mock_aiohttp_session(mocker):
    mock_response = mocker.AsyncMock()
    mock_response.status = 200
    mock_response.read = mocker.AsyncMock(return_value=b'\x00' * 1600)
    mock_response.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = mocker.AsyncMock(return_value=False)

    mock_session = mocker.AsyncMock()
    mock_session.post = mocker.MagicMock(return_value=mock_response)
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=False)

    mocker.patch('aiohttp.ClientSession', return_value=mock_session)
    return mock_session
```

**`src/stt/conftest.py` — Mocking WebSocket for Deepgram STT:**
```python
import pytest
import json

@pytest.fixture
def mock_websocket(mocker):
    ws = mocker.AsyncMock()
    ws.send = mocker.AsyncMock()
    ws.close = mocker.AsyncMock()
    # Simulate receiving a transcript message then closing
    ws.__aiter__ = mocker.MagicMock(return_value=iter([
        json.dumps({
            "type": "Results",
            "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.99}]},
            "is_final": True,
            "speech_final": True
        })
    ]))
    mocker.patch('websockets.connect', return_value=ws)
    return ws
```

**`src/voip/conftest.py` — Mocking Twilio:**
```python
import pytest

@pytest.fixture
def mock_twilio(mocker):
    mock_client = mocker.MagicMock()
    mock_call = mocker.MagicMock()
    mock_call.sid = "CA1234567890"
    mock_call.status = "in-progress"
    mock_client.calls.create.return_value = mock_call
    mocker.patch('twilio.rest.Client', return_value=mock_client)
    return mock_client
```

**`src/patient/conftest.py` — Mocking OpenAI:**
```python
import pytest

@pytest.fixture
def mock_openai(mocker):
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "Sure, I'd like to schedule for Tuesday please."

    mock_client = mocker.AsyncMock()
    mock_client.chat.completions.create = mocker.AsyncMock(return_value=mock_response)
    mocker.patch('openai.AsyncOpenAI', return_value=mock_client)
    return mock_client
```

**Orchestrator tests (`src/test_orchestrator.py`)** use inline fixtures or import from other conftest files since the orchestrator depends on all components:
```python
import pytest

@pytest.fixture
def mock_all_components(mocker):
    """Mock TTS, STT, PatientAgent, CallRecorder, TwilioClient for orchestrator tests."""
    mocks = {}
    mocks['tts'] = mocker.AsyncMock()
    mocks['tts'].synthesize_to_mulaw = mocker.AsyncMock(return_value=b'\x00' * 1600)
    mocks['stt'] = mocker.AsyncMock()
    mocks['agent'] = mocker.AsyncMock()
    mocks['agent'].get_opening_line = mocker.AsyncMock(return_value="Hi, I need an appointment.")
    mocks['agent'].generate_response = mocker.AsyncMock(return_value="Yes, Tuesday works.")
    mocks['agent'].should_hang_up = mocker.AsyncMock(return_value=False)
    mocks['recorder'] = mocker.MagicMock()
    mocks['recorder'].save_recording = mocker.MagicMock(return_value="/output/recordings/test.mp3")
    mocks['recorder'].save_transcript = mocker.MagicMock(return_value="/output/transcripts/test.txt")
    mocks['twilio'] = mocker.MagicMock()
    mocks['twilio'].make_call = mocker.MagicMock(return_value="CA1234567890")
    return mocks
```

### Running Tests

After each step, run the co-located test file:
```bash
pytest src/test_config.py -v                          # root-level module
pytest src/tts/test_deepgram_tts.py -v                # subpackage module
pytest src/tts/test_deepgram_tts.py -v -k "init"      # specific tests
```

After completing a component, run all tests in that directory:
```bash
pytest src/tts/ -v                                     # all TTS tests
pytest src/voip/ -v                                    # all VoIP tests
```

After completing all modules, run the full suite:
```bash
pytest src/ . -v                                       # everything
```

---

## FAILURE HANDLING PROTOCOL

At every test step, follow this protocol:

```
1. Run tests.
2. If ALL PASS → update STATUS.md with DONE, proceed to next step.
3. If ANY FAIL:
   a. Read the error message and traceback carefully.
   b. Identify the root cause (not the symptom).
   c. Make a targeted fix to the source code.
   d. Run tests again.
   e. Repeat up to 5 times total.
   f. If still failing after 5 attempts:
      - Update STATUS.md: status=FAILED, note the error and all 5 attempts.
      - If >80% of module tests are failing: STOP this module, move to next.
      - If <80% failing: continue to next step in same module.
4. NEVER hack a test to make it pass (e.g., no try/except that swallows errors,
   no asserting True unconditionally, no deleting failing tests).
5. NEVER skip writing tests. Every step must have tests.
```

---

## POST-DEVELOPMENT CHECKLIST

After all modules are complete:

1. [ ] All test files exist and have been run.
2. [ ] STATUS.md is fully updated with all step statuses.
3. [ ] `.env.example` exists with all required variables listed.
4. [ ] `requirements.txt` includes all dependencies.
5. [ ] `README.md` has clear setup and run instructions.
6. [ ] `ARCHITECTURE.md` has 1-2 paragraph architecture description.
7. [ ] `output/` directory structure exists.
8. [ ] `main.py` is runnable with `python main.py`.
9. [ ] `scenarios/patient_scenarios.json` has 12+ scenarios.
10. [ ] No API keys are hardcoded anywhere in the source code.

---

## NOTES ON SPECIFIC IMPLEMENTATION DETAILS

### Twilio Media Streams Audio Format
- Twilio sends: mulaw encoding, 8000 Hz sample rate, single channel
- Audio chunks arrive as base64-encoded strings in the `media.payload` field
- Each chunk is ~20ms of audio (160 bytes of mulaw)
- To send audio back: base64-encode mulaw audio, send as JSON media event

### Deepgram TTS Output Format
- Request mulaw encoding directly: `encoding=mulaw&sample_rate=8000&container=none`
- This avoids needing to convert between formats
- The response body is raw mulaw audio bytes

### Deepgram STT Input Format
- Send mulaw 8kHz audio directly (no conversion needed)
- URL params: `encoding=mulaw&sample_rate=8000`
- Audio is sent as binary WebSocket messages

### Conversation Flow State Machine
```
STATES:
  WAITING_FOR_GREETING  → Agent speaks first, bot listens
  LISTENING             → Bot is listening to agent speak
  PROCESSING            → STT got final transcript, LLM is generating response
  SPEAKING              → TTS audio is being sent to Twilio
  CALL_ENDING           → Goodbye detected, finishing up
  CALL_ENDED            → Call complete, saving recordings

TRANSITIONS:
  WAITING_FOR_GREETING → LISTENING     (when first STT transcript arrives)
  LISTENING → PROCESSING               (when is_final=True from STT)
  PROCESSING → SPEAKING                (when TTS audio is ready)
  SPEAKING → LISTENING                 (when all TTS audio chunks sent)
  LISTENING → CALL_ENDING              (when should_hang_up returns True)
  CALL_ENDING → CALL_ENDED             (after farewell audio sent)
```

### Call Timeout
- Set a maximum call duration of 180 seconds (3 minutes).
- If the call exceeds this, gracefully end it:
  1. Generate a closing line: "Thank you, I need to go now. Goodbye!"
  2. Send it through TTS.
  3. Wait 2 seconds.
  4. End the call via Twilio API.

### ngrok Tunnel
- Use `pyngrok` to programmatically create an ngrok tunnel.
- The tunnel exposes the local WebSocket server.
- Twilio's `<Stream>` connects to this public URL.
- Note: ngrok free tier may have limitations. If ngrok fails, log the error clearly.
- The ngrok URL format for WebSocket: replace `tcp://` with `wss://` in the tunnel URL.

### Audio Chunking for Twilio
- Twilio expects audio in small chunks (recommended 20ms per message).
- At 8kHz mulaw (1 byte per sample): 20ms = 160 bytes per chunk.
- When sending TTS audio back, chunk it into 160-byte segments.
- Add a small delay (~20ms) between chunks to match real-time playback.

### Handling Barge-In (Interruption)
- If new STT transcripts arrive while the bot is speaking (SPEAKING state):
  1. Send a `clear` event to Twilio to stop queued audio.
  2. Transition to PROCESSING with the new transcript.
  3. Generate a new response.
- This handles the case where the PGAI agent interrupts the patient.

---

## FINAL REMINDERS

1. **Start with Module 1.** Do not jump to VoIP or Orchestrator first.
2. **One step at a time.** Generate code for ONE step, write tests, run them, fix them.
3. **Update STATUS.md** after every single step — success or failure.
4. **Functions ≤ 30 lines.** Refactor aggressively.
5. **No hardcoded keys.** Everything comes from `.env` through Config.
6. **When stuck:** Update STATUS.md, move on. Do not spin endlessly.
7. **The goal:** Working code that makes real phone calls and records them. Quality over perfection.

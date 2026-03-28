# PGAI Voice Bot/Patient Simulator

A voice bot that calls Pretty Good AI's test line, simulates realistic patient
conversations, and identifies bugs in their AI agent.

## Quick Start

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   brew install ffmpeg  # macOS — required for MP3 encoding
   # or: apt-get install -y ffmpeg  # Linux
   ```

2. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

3. Run the bot:
   ```bash
   python main.py
   ```

4. Run the automated pipeline script (tests + program + snapshot + round ranking):
   ```bash
   bash run_tests_and_program.sh
   ```

## Required API Keys

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Twilio authentication token |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number |
| `DEEPGRAM_API_KEY` | Deepgram API key (STT + TTS) |
| `OPENAI_API_KEY` | OpenAI API key (LLM patient agent) |
| `NGROK_AUTH_TOKEN` | ngrok auth token (exposes local WebSocket) |
| `TARGET_PHONE_NUMBER` | Number to call (default: +18054398008) |

## Architecture

The bot uses a streaming pipeline with six components:

1. **VoIP (Twilio)** — Makes outbound calls and streams audio via WebSocket
2. **STT (Deepgram)** — Real-time streaming speech-to-text
3. **Patient Agent (OpenAI)** — LLM-powered patient persona
4. **TTS (Deepgram)** — Converts patient responses to speech
5. **Call Recorder** — Captures full call audio as MP3 + transcripts
6. **Orchestrator** — Manages the call lifecycle and scenario rotation

## Output

- `output/recordings/` — MP3 files (one per call)
- `output/transcripts/` — JSON + TXT transcripts for each call
- `output/bug_report.md` — LLM analysis of issues found

## Running Tests

```bash
pytest src/ . -v         
pytest src/patient/ -v   
```

Or use the project script:

```bash
bash run_tests_and_program.sh
```

## Scenarios

The bot ships includes 14 patient scenarios covering:
- New and returning patient scheduling
- Rescheduling and cancellations
- Simple and medication refills
- Office hours, location, insurance questions
- Edge cases: interruptions, language barriers, wrong numbers, multiple requests, emotional patient/speaker

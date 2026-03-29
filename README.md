# PGAI Voice Bot/Patient Simulator

A voice bot that calls Pretty Good AI's test line, simulates realistic patient
conversations, and identifies bugs in their AI agent.

The repository contains both the active app and archived run snapshots. The
live program writes its current run outputs under `output/`, and the helper
script snapshots each completed run under `rounds/round-N/output/` for later
comparison.

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

   A direct run writes the current bug report and any generated call artifacts
   into `output/`.

4. Run the automated pipeline script (tests + program + snapshot + round ranking):
   ```bash
   bash run_tests_and_program.sh
   ```

   This script:
   - runs tests
   - runs the program
   - copies the current `output/` directory into a new `rounds/round-N/output/`
     snapshot
   - generates `rounds/round_ranking.md`

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

Current-run files:
- `output/bug_report.md` — latest bug report
- `output/recordings/` — current run MP3 files when a run produces fresh call audio
- `output/transcripts/` — current run JSON + TXT transcripts when a run produces fresh transcripts

Archived snapshots:
- `rounds/round-N/output/recordings/` — MP3 files captured for that archived round
- `rounds/round-N/output/transcripts/` — JSON + TXT transcripts for that archived round
- `rounds/round-N/output/bug_report.md` — bug report generated for that round
- `rounds/round_ranking.md` — cross-round comparison report

If you are inspecting historical results already committed in the repo, the most
complete artifacts are typically under `rounds/` rather than the top-level
`output/` directory.

## Running Tests

```bash
pytest src/ . -v         
pytest src/patient/ -v   
```

Or use the project script:

```bash
bash run_tests_and_program.sh
```

## Repository Layout

```text
.
├── main.py
├── src/                     # application code and tests
├── scenarios/               # scenario JSON input
├── output/                  # latest run reports and call artifacts
├── rounds/                  # archived run snapshots and ranking report
├── STATUS.md
├── ARCHITECTURE.md
└── run_tests_and_program.sh
```

## Scenarios

The bot ships with 14 patient scenarios covering:
- New and returning patient scheduling
- Rescheduling and cancellations
- Simple and medication refills
- Office hours, location, insurance questions
- Edge cases: interruptions, language barriers, wrong numbers, multiple requests, emotional patient/speaker

Loom recording in loom-workflow.mp4

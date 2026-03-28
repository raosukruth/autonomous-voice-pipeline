# Orchestrator: ties all components together for a single call and multi-call runs.
import asyncio
import logging
import os
import time
import uuid
from typing import Optional

from openai import AsyncOpenAI

from src.call_recorder import CallRecorder
from src.config import Config
from src.patient.agent import PatientAgent
from src.patient.scenarios import PatientScenario
from src.stt.deepgram_stt import DeepgramSTT
from src.tts.deepgram_tts import DeepgramTTS
from src.voip.media_stream import MediaStreamHandler
from src.voip.twilio_client import TwilioClient

logger = logging.getLogger(__name__)

MAX_CALL_DURATION = 180  # seconds


class CallState:
    WAITING = "waiting"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ENDING = "ending"
    ENDED = "ended"


class CallPipeline:
    # Manages the real-time audio pipeline for a single call.

    def __init__(self, config: Config, scenario: PatientScenario, call_id: str):
        self.call_id = call_id
        self.config = config
        self.tts = DeepgramTTS(api_key=config.deepgram_api_key)
        self.stt = DeepgramSTT(api_key=config.deepgram_api_key)
        self.agent = PatientAgent(api_key=config.openai_api_key, scenario=scenario)
        self.recorder = CallRecorder(call_id=call_id)
        self.state = CallState.WAITING
        self.media_handler: Optional[MediaStreamHandler] = None
        self.start_time: float = 0.0
        self.recording_path: str = ""
        self.transcript_path: str = ""

    async def start(self, media_handler: MediaStreamHandler) -> None:
        # Begin the pipeline.
        self.media_handler = media_handler
        self.start_time = time.time()
        await self.stt.start_stream(on_transcript=self.on_transcript)
        self.state = CallState.LISTENING
        logger.info("[%s] Pipeline started", self.call_id)

    async def on_transcript(self, text: str, is_final: bool) -> None:
        # Handle a transcript from STT.
        if not is_final or not text.strip():
            return
        if self.state not in (CallState.LISTENING, CallState.WAITING):
            return

        logger.info("[%s] Agent: %s", self.call_id, text)
        self.recorder.add_transcript_entry("agent", text, time.time())
        self.state = CallState.PROCESSING

        if await self.agent.should_hang_up(text):
            await self.finish_call()
            return

        response = await self.agent.generate_response(text)
        logger.info("[%s] Patient: %s", self.call_id, response)
        self.recorder.add_transcript_entry("patient", response, time.time())

        await self.send_tts(response)
        self.state = CallState.LISTENING

    async def on_audio_received(self, audio_bytes: bytes) -> None:
        # Called when audio is received from Twilio.
        self.recorder.add_inbound_chunk(audio_bytes)
        await self.stt.send_audio(audio_bytes)

    async def send_tts(self, text: str) -> None:
        # Synthesize text and send audio over the media stream.
        self.state = CallState.SPEAKING
        mulaw_audio = await self.tts.synthesize_to_mulaw(text)
        self.recorder.add_outbound_chunk(mulaw_audio)
        if self.media_handler:
            await self.media_handler.send_audio(mulaw_audio)

    async def finish_call(self) -> None:
        # Send farewell and clean up.
        self.state = CallState.ENDING
        farewell = "Thank you, take care. Goodbye!"
        await self.send_tts(farewell)
        self.recorder.add_transcript_entry("patient", farewell, time.time())
        await self.stop()

    async def stop(self) -> tuple:
        # Clean up: stop STT, save recording and transcript.
        self.state = CallState.ENDED
        await self.stt.stop_stream()
        self.recording_path = self.recorder.save_recording()
        self.transcript_path = self.recorder.save_transcript()
        return self.recording_path, self.transcript_path


class Orchestrator:
    # Top-level controller that runs multiple calls.

    def __init__(self, config: Config):
        self.config = config
        self.twilio = TwilioClient(
            account_sid=config.twilio_account_sid,
            auth_token=config.twilio_auth_token,
            from_number=config.twilio_phone_number,
        )
        self._server = None
        self._tunnel = None
        self._ws_url = None
        self._current_pipeline: Optional[CallPipeline] = None

    async def _start_infrastructure(self):
        # Start the WebSocket server and ngrok tunnel once for all calls.
        import websockets
        from pyngrok import ngrok

        async def ws_handler(websocket, path=""):
            if self._current_pipeline is None:
                return
            pipeline = self._current_pipeline
            media_handler = MediaStreamHandler()
            try:
                await pipeline.start(media_handler)
                pipeline._connection_event.set()
                await media_handler.handle_connection(websocket, pipeline.on_audio_received)
            except Exception as exc:
                logger.warning("WebSocket handler ended for %s: %s", pipeline.call_id, exc)
            finally:
                if pipeline.state != CallState.ENDED:
                    try:
                        await pipeline.stop()
                    except Exception as stop_exc:
                        logger.warning("Pipeline stop failed for %s: %s", pipeline.call_id, stop_exc)

        self._server = await websockets.serve(
            ws_handler, self.config.websocket_host, self.config.websocket_port
        )
        ngrok.set_auth_token(self.config.ngrok_auth_token)
        self._tunnel = ngrok.connect(self.config.websocket_port, "http")
        public_url = self._tunnel.public_url
        self._ws_url = public_url.replace("https://", "wss://").replace("http://", "ws://")
        logger.info("WebSocket server + ngrok ready: %s", self._ws_url)

    def _stop_infrastructure(self):
        from pyngrok import ngrok as _ngrok
        if self._server:
            try:
                self._server.close()
            except Exception as exc:
                logger.warning("WebSocket server close failed: %s", exc)
        if self._tunnel:
            try:
                _ngrok.disconnect(self._tunnel.public_url)
            except Exception as exc:
                logger.warning("ngrok disconnect failed (safe to ignore): %s", exc)
        self._server = None
        self._tunnel = None

    async def run_call(self, scenario: PatientScenario) -> dict:
        # Execute a single call with the given scenario.
        call_id = str(uuid.uuid4())[:8]
        logger.info("Starting call %s: %s", call_id, scenario.description)
        start_time = time.time()

        pipeline = CallPipeline(self.config, scenario, call_id)
        pipeline._connection_event = asyncio.Event()
        self._current_pipeline = pipeline

        call_sid = None
        try:
            call_sid = self.twilio.make_call(self.config.target_phone_number, self._ws_url)
            logger.info("Call SID: %s", call_sid)
            try:
                await asyncio.wait_for(pipeline._connection_event.wait(), timeout=30)
                await asyncio.wait_for(
                    self.wait_for_call_end(pipeline), timeout=MAX_CALL_DURATION
                )
            except asyncio.TimeoutError:
                logger.warning("Call %s timed out", call_id)
                await self.handle_timeout(pipeline, call_sid)
        except Exception as exc:
            logger.error("Error during call %s: %s", call_id, exc)
        finally:
            self._current_pipeline = None

        if pipeline.state != CallState.ENDED:
            try:
                if call_sid:
                    try:
                        self.twilio.end_call(call_sid)
                    except Exception:
                        pass
                await pipeline.stop()
            except Exception as e:
                logger.error("Failed to stop pipeline %s: %s", call_id, e)

        duration = time.time() - start_time
        return {
            "call_id": call_id,
            "call_sid": call_sid,
            "scenario_id": scenario.id,
            "duration": duration,
            "recording_path": pipeline.recording_path,
            "transcript_path": pipeline.transcript_path,
            "status": "completed" if pipeline.recording_path else "partial",
        }

    async def wait_for_call_end(self, pipeline: CallPipeline) -> None:
        # Poll until pipeline reaches ENDED state.
        while pipeline.state != CallState.ENDED:
            await asyncio.sleep(1)

    async def handle_timeout(self, pipeline: CallPipeline, call_sid: str) -> None:
        # End a timed-out call.
        if pipeline.media_handler:
            try:
                await pipeline.send_tts("Thank you, I need to go now. Goodbye!")
                await asyncio.sleep(2)
            except Exception:
                pass
        try:
            self.twilio.end_call(call_sid)
        except Exception:
            pass
        try:
            await pipeline.stop()
        except Exception as e:
            logger.error("Error saving pipeline %s: %s", pipeline.call_id, e)

    async def run_all_scenarios(self, scenarios: list,
                                delay_between_calls: int = 10) -> list:
        # Run calls for all scenarios sequentially.
        await self._start_infrastructure()
        results = []
        try:
            for i, scenario in enumerate(scenarios):
                try:
                    result = await self.run_call(scenario)
                    results.append(result)
                except Exception as exc:
                    logger.error("Call failed for scenario %s: %s", scenario.id, exc)
                    results.append({"scenario_id": scenario.id, "status": "failed", "error": str(exc)})
                if i < len(scenarios) - 1:
                    await asyncio.sleep(delay_between_calls)
        finally:
            self._stop_infrastructure()
        return results

    async def generate_bug_report(self, call_results: list) -> str:
        # Use LLM to analyze transcripts and produce a bug report.
        client = AsyncOpenAI(api_key=self.config.openai_api_key)
        transcript_summaries = build_transcript_summaries(call_results)
        prompt = build_bug_report_prompt(transcript_summaries)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        report = response.choices[0].message.content.strip()
        report_path = os.path.join("output", "bug_report.md")
        os.makedirs("output", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return report


def build_transcript_summaries(call_results: list) -> str:
    # Read transcript files and assemble a summary string.
    # Also scan the transcripts directory for any files not in results.
    transcript_dir = os.path.join("output", "transcripts")
    used_paths = set()
    parts = []
    for r in call_results:
        tx_path = r.get("transcript_path", "")
        scenario_id = r.get("scenario_id", "unknown")
        call_id = r.get("call_id", "")
        content = _read_transcript(tx_path, call_id, transcript_dir)
        if tx_path:
            used_paths.add(os.path.abspath(tx_path))
        if content:
            parts.append(f"## Scenario: {scenario_id}\n{content}\n")

    if os.path.isdir(transcript_dir):
        for fname in sorted(os.listdir(transcript_dir)):
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.abspath(os.path.join(transcript_dir, fname))
            if fpath in used_paths:
                continue
            with open(fpath, encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                parts.append(f"## Extra transcript: {fname}\n{content}\n")
    return "\n".join(parts) if parts else "(no transcripts available)"


def _read_transcript(tx_path: str, call_id: str, transcript_dir: str) -> str:
    # Try the given path, then look for call_id.txt in transcript_dir.
    if tx_path and os.path.exists(tx_path):
        with open(tx_path, encoding="utf-8") as f:
            return f.read().strip()
    if call_id:
        fallback = os.path.join(transcript_dir, f"{call_id}.txt")
        if os.path.exists(fallback):
            with open(fallback, encoding="utf-8") as f:
                return f.read().strip()
    return ""


def build_bug_report_prompt(transcript_summaries: str) -> str:
    return f"""You are a QA engineer reviewing transcripts of an AI phone agent called "Pretty Good AI".
Analyze the transcripts below and identify bugs, issues, or areas where the agent performed poorly.

For each issue found, document:
1. The scenario where it occurred
2. What the agent said or failed to do
3. What the expected behavior should have been
4. Severity (Critical / High / Medium / Low)

Format the output as a Markdown bug report.

TRANSCRIPTS:
{transcript_summaries}
"""

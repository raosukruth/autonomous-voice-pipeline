# Deepgram streaming STT using their WebSocket API.
import asyncio
import json
import websockets
from typing import Callable, Optional
from src.logger import get_logger

logger = get_logger(__name__)


class DeepgramSTT:
    # Deepgram streaming STT using their WebSocket API.

    DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"

    def __init__(self, api_key: str, sample_rate: int = 8000,
                 encoding: str = "mulaw", language: str = "en-US"):
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.language = language
        self.ws = None
        self.on_transcript: Optional[Callable] = None
        self.listen_task: Optional[asyncio.Task] = None

    def build_url(self) -> str:
        # Build the Deepgram WebSocket URL with query parameters.
        params = (
            f"encoding={self.encoding}"
            f"&sample_rate={self.sample_rate}"
            f"&language={self.language}"
            f"&model=nova-2"
            f"&punctuate=true"
            f"&interim_results=true"
            f"&utterance_end_ms=1000"
            f"&vad_events=true"
            f"&endpointing=300"
        )
        return f"{self.DEEPGRAM_WS_URL}?{params}"

    async def start_stream(self, on_transcript: Callable[[str, bool], None]) -> None:
        # Connect to Deepgram WebSocket and start listening.
        self.on_transcript = on_transcript
        url = self.build_url()
        headers = {"Authorization": f"Token {self.api_key}"}
        # websockets.connect can be used as a coroutine (returns connection directly)
        connect_result = websockets.connect(url, additional_headers=headers)
        # Handle both coroutine and context manager forms
        if asyncio.iscoroutine(connect_result):
            self.ws = await connect_result
        else:
            self.ws = await connect_result.__aenter__()
        self.listen_task = asyncio.create_task(self.listen_for_transcripts())

    async def send_audio(self, audio_bytes: bytes) -> None:
        # Send audio chunk to Deepgram WebSocket.
        if self.ws is None:
            return
        try:
            await self.ws.send(audio_bytes)
        except Exception:
            pass  # Ignore closed-connection errors during cleanup

    async def stop_stream(self) -> None:
        # Send close message to Deepgram and close WebSocket.
        if self.ws is None:
            return
        try:
            await self.ws.send(json.dumps({"type": "CloseStream"}))
        except Exception:
            pass
        if self.listen_task and not self.listen_task.done():
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        try:
            await self.ws.close()
        except Exception:
            pass
        self.ws = None

    async def listen_for_transcripts(self) -> None:
        # Background task: read and parse messages from Deepgram WebSocket.
        try:
            async for message in self.ws:
                await self.handle_message(message)
        except Exception as e:
            logger.error(f"Deepgram STT listen error: {e}")

    async def handle_message(self, message: str) -> None:
        # Parse a single Deepgram message and invoke the callback.
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        if msg_type == "Results":
            alternatives = data.get("channel", {}).get("alternatives", [])
            if not alternatives:
                return
            text = alternatives[0].get("transcript", "")
            is_final = data.get("is_final", False) or data.get("speech_final", False)
            if text and self.on_transcript:
                await self.on_transcript(text, is_final)

        elif msg_type == "UtteranceEnd":
            if self.on_transcript:
                await self.on_transcript("", True)

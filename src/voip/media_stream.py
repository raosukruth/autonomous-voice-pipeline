# Twilio Media Stream WebSocket handler.
import asyncio
import base64
import json
import logging
from typing import Callable, Optional
from src.audio_utils import (
    USE_AUDIOOP, mulaw_to_pcm_numpy, pcm_to_mulaw_numpy,
)

logger = logging.getLogger(__name__)

# 20ms of audio at 8kHz mulaw = 160 bytes
CHUNK_SIZE = 160
CHUNK_DURATION_S = 0.02


class MediaStreamHandler:
    # Handles Twilio Media Stream WebSocket connections.

    def __init__(self):
        self.stream_sid: Optional[str] = None
        self.on_audio_received: Optional[Callable] = None
        self.ws = None
        self.connected = False

    async def handle_connection(self, websocket,
                                on_audio_received: Callable[[bytes], None]) -> None:
        # Main handler for an incoming WebSocket connection from Twilio.
        self.ws = websocket
        self.on_audio_received = on_audio_received
        try:
            async for message in websocket:
                await self.handle_event(message)
        except Exception as exc:
            # Remote disconnects are expected in real phone calls and ngrok restarts.
            logger.warning("Media stream connection ended: %s", exc)
        finally:
            self.connected = False

    async def handle_event(self, message: str) -> None:
        # Parse JSON message and dispatch to the appropriate handler.
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON message")
            return

        event = msg.get("event", "")
        if event == "connected":
            self.connected = True
            logger.info("Twilio media stream connected")
        elif event == "start":
            self.stream_sid = msg.get("start", {}).get("streamSid")
            logger.info("Stream started: %s", self.stream_sid)
        elif event == "media":
            payload = msg.get("media", {}).get("payload", "")
            if payload and self.on_audio_received:
                audio_bytes = self.base64_to_bytes(payload)
                await self.on_audio_received(audio_bytes)
        elif event == "stop":
            self.connected = False
            logger.info("Stream stopped")
        else:
            logger.debug("Unknown event type: %s", event)

    async def send_audio(self, mulaw_audio_bytes: bytes) -> None:
        # Send audio back to Twilio in 20ms chunks.
        if not self.ws:
            raise RuntimeError("WebSocket not connected — call handle_connection first")
        for i in range(0, len(mulaw_audio_bytes), CHUNK_SIZE):
            chunk = mulaw_audio_bytes[i:i + CHUNK_SIZE]
            payload = self.bytes_to_base64(chunk)
            message = json.dumps({
                "event": "media",
                "streamSid": self.stream_sid,
                "media": {"payload": payload},
            })
            await self.ws.send(message)
            await asyncio.sleep(CHUNK_DURATION_S)

    async def send_clear(self) -> None:
        # Send a clear event to stop queued audio on Twilio's side (barge-in).
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
        message = json.dumps({"event": "clear", "streamSid": self.stream_sid})
        await self.ws.send(message)

    def is_connected(self) -> bool:
        return self.connected

    def mulaw_to_pcm(self, mulaw_bytes: bytes) -> bytes:
        # Convert mulaw-encoded bytes (from Twilio) to 16-bit PCM.
        if USE_AUDIOOP:
            import warnings, audioop
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                return audioop.ulaw2lin(mulaw_bytes, 2)
        return mulaw_to_pcm_numpy(mulaw_bytes)

    def pcm_to_mulaw(self, pcm_bytes: bytes) -> bytes:
        # Convert 16-bit PCM to mulaw encoding (for sending to Twilio).
        if USE_AUDIOOP:
            import warnings, audioop
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                return audioop.lin2ulaw(pcm_bytes, 2)
        return pcm_to_mulaw_numpy(pcm_bytes)

    def base64_to_bytes(self, b64_string: str) -> bytes:
        # Decode base64 string to raw bytes (Twilio sends audio as base64).
        return base64.b64decode(b64_string)

    def bytes_to_base64(self, raw_bytes: bytes) -> str:
        # Encode raw bytes to base64 string (for sending audio to Twilio).
        return base64.b64encode(raw_bytes).decode("utf-8")

# Tests for MediaStreamHandler.
import asyncio
import base64
import json
import pytest
from src.voip.media_stream import MediaStreamHandler


# ── Helper to build Twilio-style event JSON ────────────────────────────────────

def connected_msg():
    return json.dumps({"event": "connected"})


def start_msg(stream_sid="SS123"):
    return json.dumps({"event": "start", "start": {"streamSid": stream_sid}})


def media_msg(payload_bytes=b"\x00\xff"):
    b64 = base64.b64encode(payload_bytes).decode()
    return json.dumps({"event": "media", "media": {"payload": b64}})


def stop_msg():
    return json.dumps({"event": "stop"})


# ── Step 5.2a tests ────────────────────────────────────────────────────────────

def test_media_stream_init():
    handler = MediaStreamHandler()
    assert handler.stream_sid is None
    assert handler.is_connected() is False
    assert handler.ws is None


async def test_handle_event_connected():
    handler = MediaStreamHandler()
    await handler.handle_event(connected_msg())
    assert handler.is_connected() is True


async def test_handle_event_start():
    handler = MediaStreamHandler()
    await handler.handle_event(start_msg("SS_TEST"))
    assert handler.stream_sid == "SS_TEST"


async def test_handle_event_media():
    received = []

    async def on_audio(data: bytes):
        received.append(data)

    handler = MediaStreamHandler()
    handler.on_audio_received = on_audio
    await handler.handle_event(media_msg(b"\x01\x02\x03"))
    assert len(received) == 1
    assert received[0] == b"\x01\x02\x03"


async def test_handle_event_stop():
    handler = MediaStreamHandler()
    await handler.handle_event(connected_msg())
    assert handler.is_connected() is True
    await handler.handle_event(stop_msg())
    assert handler.is_connected() is False


async def test_handle_event_unknown_event():
    handler = MediaStreamHandler()
    # Should not raise
    await handler.handle_event(json.dumps({"event": "mystery"}))


# ── Step 5.2b tests ────────────────────────────────────────────────────────────

async def test_send_audio_sends_json(mocker):
    handler = MediaStreamHandler()
    mock_ws = mocker.AsyncMock()
    handler.ws = mock_ws
    handler.stream_sid = "SS123"
    await handler.send_audio(b"\x00" * 160)
    mock_ws.send.assert_called_once()
    payload = json.loads(mock_ws.send.call_args.args[0])
    assert payload["event"] == "media"
    assert payload["streamSid"] == "SS123"
    assert "payload" in payload["media"]


async def test_send_audio_chunks_correctly(mocker):
    # 640 bytes at 160 bytes/chunk = 4 messages.
    handler = MediaStreamHandler()
    mock_ws = mocker.AsyncMock()
    handler.ws = mock_ws
    handler.stream_sid = "SS123"
    # Patch asyncio.sleep to avoid real delays
    mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)
    await handler.send_audio(b"\x00" * 640)
    assert mock_ws.send.call_count == 4


async def test_send_clear_sends_clear_event(mocker):
    handler = MediaStreamHandler()
    mock_ws = mocker.AsyncMock()
    handler.ws = mock_ws
    handler.stream_sid = "SS123"
    await handler.send_clear()
    mock_ws.send.assert_called_once()
    payload = json.loads(mock_ws.send.call_args.args[0])
    assert payload["event"] == "clear"
    assert payload["streamSid"] == "SS123"


async def test_send_audio_when_not_connected_raises():
    handler = MediaStreamHandler()
    with pytest.raises(RuntimeError):
        await handler.send_audio(b"\x00" * 160)


class FailingSocket:
    # Async iterable websocket stub that raises while streaming.
    def __aiter__(self):
        return self

    async def __anext__(self):
        raise RuntimeError("connection dropped")


async def test_handle_connection_disconnect_is_graceful():
    received = []

    async def on_audio(data: bytes):
        received.append(data)

    handler = MediaStreamHandler()
    await handler.handle_connection(FailingSocket(), on_audio)
    assert handler.is_connected() is False
    assert received == []

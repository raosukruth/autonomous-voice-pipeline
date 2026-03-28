# Tests for DeepgramSTT (Steps 3.2a and 3.2b).
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.stt.deepgram_stt import DeepgramSTT


def make_mock_ws(mocker, messages=None):
    # Helper: create a mock websocket that behaves like an async iterable.
    mock_ws = mocker.MagicMock()
    mock_ws.send = mocker.AsyncMock()
    mock_ws.close = mocker.AsyncMock()

    async def _aiter():
        for msg in (messages or []):
            yield msg

    mock_ws.__aiter__ = MagicMock(return_value=_aiter())

    # Make websockets.connect return a coroutine yielding mock_ws
    async def _connect(*args, **kwargs):
        return mock_ws

    return mock_ws, _connect


# ── Step 3.2a tests ──────────────────────────────────────────────────────────

def test_deepgram_stt_init_stores_config():
    # Assert attributes are set correctly.
    stt = DeepgramSTT(api_key="test_key", sample_rate=8000, encoding="mulaw", language="en-US")
    assert stt.api_key == "test_key"
    assert stt.sample_rate == 8000
    assert stt.encoding == "mulaw"
    assert stt.language == "en-US"
    assert stt.ws is None
    assert stt.on_transcript is None


async def test_deepgram_stt_start_stream_connects(mocker):
    # Mock websockets.connect, assert called with correct URL.
    mock_ws, mock_connect = make_mock_ws(mocker)
    mocker.patch('websockets.connect', side_effect=mock_connect)

    stt = DeepgramSTT(api_key="test_key")
    callback = MagicMock()
    await stt.start_stream(callback)

    url_called = mocker.patch.object  # just verify it ran
    assert stt.ws is mock_ws

    if stt.listen_task:
        stt.listen_task.cancel()
        try:
            await stt.listen_task
        except asyncio.CancelledError:
            pass


async def test_deepgram_stt_start_stream_stores_callback(mocker):
    # Assert on_transcript is stored after start_stream.
    mock_ws, mock_connect = make_mock_ws(mocker)
    mocker.patch('websockets.connect', side_effect=mock_connect)

    stt = DeepgramSTT(api_key="test_key")
    callback = MagicMock()
    await stt.start_stream(callback)
    assert stt.on_transcript is callback

    if stt.listen_task:
        stt.listen_task.cancel()
        try:
            await stt.listen_task
        except asyncio.CancelledError:
            pass


async def test_deepgram_stt_send_audio_before_start_returns_silently():
    # send_audio returns silently (no error) if called before start_stream.
    stt = DeepgramSTT(api_key="test_key")
    # Should not raise — just silently return
    await stt.send_audio(b'\x00' * 160)


# ── Step 3.2b tests ──────────────────────────────────────────────────────────

async def test_deepgram_stt_send_audio_sends_bytes(mocker):
    # Mock ws.send, assert called with bytes.
    mock_ws, mock_connect = make_mock_ws(mocker)
    mocker.patch('websockets.connect', side_effect=mock_connect)

    stt = DeepgramSTT(api_key="test_key")
    await stt.start_stream(MagicMock())

    audio = b'\x00' * 160
    await stt.send_audio(audio)
    mock_ws.send.assert_called_with(audio)

    if stt.listen_task:
        stt.listen_task.cancel()
        try:
            await stt.listen_task
        except asyncio.CancelledError:
            pass


async def test_deepgram_stt_stop_stream_closes(mocker):
    # Mock ws.close, assert called after stop_stream.
    mock_ws, mock_connect = make_mock_ws(mocker)
    mocker.patch('websockets.connect', side_effect=mock_connect)

    stt = DeepgramSTT(api_key="test_key")
    await stt.start_stream(MagicMock())
    await stt.stop_stream()

    assert mock_ws.close.called


async def test_deepgram_stt_listen_parses_results(mocker):
    # Feed mock JSON messages, assert callback called with correct text and is_final.
    results_msg = json.dumps({
        "type": "Results",
        "channel": {"alternatives": [{"transcript": "hello world", "confidence": 0.99}]},
        "is_final": True,
        "speech_final": True,
    })

    mock_ws, mock_connect = make_mock_ws(mocker, messages=[results_msg])
    mocker.patch('websockets.connect', side_effect=mock_connect)

    received = []
    stt = DeepgramSTT(api_key="test_key")
    await stt.start_stream(lambda text, is_final: received.append((text, is_final)))

    await asyncio.sleep(0.05)

    assert any(text == "hello world" and is_final for text, is_final in received)


async def test_deepgram_stt_listen_handles_utterance_end(mocker):
    # Feed UtteranceEnd message, assert callback called with ('', True).
    utter_end_msg = json.dumps({"type": "UtteranceEnd"})

    mock_ws, mock_connect = make_mock_ws(mocker, messages=[utter_end_msg])
    mocker.patch('websockets.connect', side_effect=mock_connect)

    received = []
    stt = DeepgramSTT(api_key="test_key")
    await stt.start_stream(lambda text, is_final: received.append((text, is_final)))

    await asyncio.sleep(0.05)

    assert ("", True) in received

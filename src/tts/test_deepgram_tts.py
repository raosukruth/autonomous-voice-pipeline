# Tests for DeepgramTTS (Steps 2.2a and 2.2b).
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tts.deepgram_tts import DeepgramTTS


# ── Step 2.2a tests ──────────────────────────────────────────────────────────

def test_deepgram_tts_init_stores_config():
    # Assert api_key, model, sample_rate are stored.
    tts = DeepgramTTS(api_key="test_key", model="aura-asteria-en", sample_rate=8000)
    assert tts.api_key == "test_key"
    assert tts.model == "aura-asteria-en"
    assert tts.sample_rate == 8000


async def test_deepgram_tts_synthesize_calls_api(mock_aiohttp_session):
    # Mock aiohttp, assert correct URL and authorization header.
    tts = DeepgramTTS(api_key="test_key")
    result = await tts.synthesize("Hello world")
    assert mock_aiohttp_session.post.called
    call_kwargs = mock_aiohttp_session.post.call_args
    url = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("url", call_kwargs[0][0] if call_kwargs[0] else "")
    # Check URL is correct
    assert "api.deepgram.com/v1/speak" in str(call_kwargs)
    # Check auth header
    assert "test_key" in str(call_kwargs)


async def test_deepgram_tts_synthesize_returns_bytes(mock_aiohttp_session):
    # Mock response with sample bytes, assert return is bytes.
    tts = DeepgramTTS(api_key="test_key")
    result = await tts.synthesize("Hello world")
    assert isinstance(result, bytes)
    assert len(result) > 0


async def test_deepgram_tts_synthesize_handles_error(mocker):
    # Mock 401 response, assert raises PermissionError.
    mock_response = mocker.AsyncMock()
    mock_response.status = 401
    mock_response.__aenter__ = mocker.AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = mocker.AsyncMock(return_value=False)

    mock_session = mocker.AsyncMock()
    mock_session.post = mocker.MagicMock(return_value=mock_response)
    mock_session.__aenter__ = mocker.AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = mocker.AsyncMock(return_value=False)

    mocker.patch('aiohttp.ClientSession', return_value=mock_session)

    tts = DeepgramTTS(api_key="bad_key")
    with pytest.raises(PermissionError):
        await tts.synthesize("Hello")


async def test_deepgram_tts_synthesize_empty_text():
    # Assert raises ValueError for empty string.
    tts = DeepgramTTS(api_key="test_key")
    with pytest.raises(ValueError):
        await tts.synthesize("")


# ── Step 2.2b tests ──────────────────────────────────────────────────────────

async def test_deepgram_tts_synthesize_mulaw_uses_correct_params(mock_aiohttp_session):
    # Mock aiohttp, assert query params include encoding=mulaw.
    tts = DeepgramTTS(api_key="test_key")
    await tts.synthesize_to_mulaw("Hello world")
    call_args = str(mock_aiohttp_session.post.call_args)
    assert "mulaw" in call_args


def test_deepgram_tts_get_sample_rate():
    # Assert returns configured sample rate.
    tts = DeepgramTTS(api_key="test_key", sample_rate=16000)
    assert tts.get_sample_rate() == 16000

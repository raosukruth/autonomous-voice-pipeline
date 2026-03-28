# STT-specific fixtures: mock websocket for Deepgram STT tests.
import pytest
import json


@pytest.fixture
def mock_websocket(mocker):
    ws = mocker.AsyncMock()
    ws.send = mocker.AsyncMock()
    ws.close = mocker.AsyncMock()
    ws.__aiter__ = mocker.MagicMock(return_value=iter([
        json.dumps({
            "type": "Results",
            "channel": {"alternatives": [{"transcript": "hello", "confidence": 0.99}]},
            "is_final": True,
            "speech_final": True,
        })
    ]))
    mocker.patch('websockets.connect', return_value=ws)
    return ws

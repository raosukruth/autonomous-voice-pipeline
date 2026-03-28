# TTS-specific fixtures: mock aiohttp for Deepgram TTS tests.
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

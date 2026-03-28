# VoIP-specific fixtures.
import pytest


@pytest.fixture
def mock_twilio(mocker):
    mock_call = mocker.MagicMock()
    mock_call.sid = "CA1234567890"
    mock_call.status = "in-progress"

    mock_client = mocker.MagicMock()
    mock_client.calls.create.return_value = mock_call
    mock_client.calls.return_value.fetch.return_value = mock_call
    mock_client.calls.return_value.update.return_value = mock_call

    mocker.patch("src.voip.twilio_client.Client", return_value=mock_client)
    return mock_client

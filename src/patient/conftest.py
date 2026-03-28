# Fixtures for patient agent tests.
import pytest


@pytest.fixture
def mock_openai(mocker):
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "Sure, Tuesday works for me."

    mock_client = mocker.AsyncMock()
    mock_client.chat = mocker.MagicMock()
    mock_client.chat.completions = mocker.MagicMock()
    mock_client.chat.completions.create = mocker.AsyncMock(return_value=mock_response)

    mocker.patch("src.patient.agent.AsyncOpenAI", return_value=mock_client)
    return mock_client

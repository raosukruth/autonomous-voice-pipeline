# Tests for TwilioClient.
import pytest
from src.voip.twilio_client import TwilioClient


def test_twilio_client_init(mock_twilio):
    client = TwilioClient("ACtest", "authtoken", "+11234567890")
    assert client.from_number == "+11234567890"


def test_make_call_creates_call(mock_twilio):
    client = TwilioClient("ACtest", "authtoken", "+11234567890")
    client.make_call("+18054398008", "wss://example.ngrok.io/ws")
    mock_twilio.calls.create.assert_called_once()
    kwargs = mock_twilio.calls.create.call_args.kwargs
    assert kwargs["to"] == "+18054398008"
    assert kwargs["from_"] == "+11234567890"
    assert "wss://example.ngrok.io/ws" in kwargs["twiml"]


def test_make_call_returns_sid(mock_twilio):
    client = TwilioClient("ACtest", "authtoken", "+11234567890")
    sid = client.make_call("+18054398008", "wss://example.ngrok.io/ws")
    assert isinstance(sid, str)
    assert sid == "CA1234567890"


def test_get_call_status_fetches(mock_twilio):
    client = TwilioClient("ACtest", "authtoken", "+11234567890")
    status = client.get_call_status("CA1234567890")
    mock_twilio.calls.assert_called_with("CA1234567890")
    assert status == "in-progress"


def test_end_call_updates_status(mock_twilio):
    client = TwilioClient("ACtest", "authtoken", "+11234567890")
    client.end_call("CA1234567890")
    mock_twilio.calls.assert_called_with("CA1234567890")
    mock_twilio.calls.return_value.update.assert_called_once_with(status="completed")

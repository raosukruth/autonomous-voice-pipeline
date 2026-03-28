# Tests for Config module (Step 1.1a).
import os
import tempfile
import pytest
from src.config import Config


def test_config_loads_from_env_file(sample_env_file):
    # Create a temp .env file, load it, assert attributes are set.
    config = Config(env_path=sample_env_file)
    assert config.twilio_account_sid == "test_sid"
    assert config.twilio_auth_token == "test_token"
    assert config.twilio_phone_number == "+11234567890"
    assert config.deepgram_api_key == "test_deepgram_key"
    assert config.openai_api_key == "test_openai_key"
    assert config.ngrok_auth_token == "test_ngrok_token"


def test_config_validate_returns_missing_vars():
    # Create config with missing keys, assert validate returns their names.
    required_keys = [
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER",
        "DEEPGRAM_API_KEY", "OPENAI_API_KEY", "NGROK_AUTH_TOKEN",
    ]
    # Backup and clear all required env vars so they don't leak from other tests
    backup = {k: os.environ.pop(k, None) for k in required_keys}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("TWILIO_ACCOUNT_SID=test_sid\n")
        f.flush()
        env_path = f.name
    try:
        config = Config(env_path=env_path)
        missing = config.validate()
        assert "TWILIO_AUTH_TOKEN" in missing
        assert "DEEPGRAM_API_KEY" in missing
        assert "OPENAI_API_KEY" in missing
    finally:
        os.unlink(env_path)
        for k, v in backup.items():
            if v is not None:
                os.environ[k] = v


def test_config_validate_returns_empty_when_valid(sample_env_file):
    # All keys present, validate returns [].
    config = Config(env_path=sample_env_file)
    missing = config.validate()
    assert missing == []


def test_config_default_values():
    # Assert target_phone_number defaults to +18054398008, websocket_port defaults to 8765.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("")
        f.flush()
        env_path = f.name
    try:
        # Clear potentially polluting env vars
        env_backup = {}
        for key in ["TARGET_PHONE_NUMBER", "WEBSOCKET_PORT", "WEBSOCKET_HOST"]:
            env_backup[key] = os.environ.pop(key, None)

        config = Config(env_path=env_path)
        assert config.target_phone_number == "+18054398008"
        assert config.websocket_port == 8765
        assert config.websocket_host == "0.0.0.0"
    finally:
        os.unlink(env_path)
        for key, val in env_backup.items():
            if val is not None:
                os.environ[key] = val

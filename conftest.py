import pytest
import os
import tempfile


@pytest.fixture
def sample_env_file():
    # Create a temporary .env file with all required variables.
    content = """
TWILIO_ACCOUNT_SID=test_sid
TWILIO_AUTH_TOKEN=test_token
TWILIO_PHONE_NUMBER=+11234567890
DEEPGRAM_API_KEY=test_deepgram_key
OPENAI_API_KEY=test_openai_key
TARGET_PHONE_NUMBER=+18054398008
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
NGROK_AUTH_TOKEN=test_ngrok_token
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_pcm_audio():
    # Generate 1 second of silent PCM audio (16-bit, 8kHz, mono).
    import numpy as np
    samples = np.zeros(8000, dtype=np.int16)
    return samples.tobytes()


@pytest.fixture
def sample_mulaw_audio():
    # Generate 1 second of silent mulaw audio (8kHz).
    return b'\xff' * 8000  # 0xFF is mulaw silence


@pytest.fixture
def sample_scenario():
    # Return a simple test scenario.
    from src.patient.scenarios import PatientScenario
    return PatientScenario(
        id="test_scheduling",
        name="Test Patient",
        description="Test scenario for scheduling",
        system_prompt="You are Test Patient. You want to schedule an appointment for next Tuesday.",
        opening_line="Hi, I'd like to schedule an appointment please.",
        tags=["scheduling", "simple"]
    )


@pytest.fixture
def mock_config(sample_env_file):
    # Return a Config loaded from sample env.
    from src.config import Config
    return Config(env_path=sample_env_file)

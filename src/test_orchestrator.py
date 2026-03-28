# Tests for Orchestrator and CallPipeline.
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.orchestrator import CallPipeline, CallState, Orchestrator
from src.patient.scenarios import PatientScenario


@pytest.fixture
def scenario():
    return PatientScenario(
        id="test_sched",
        name="Test Patient",
        description="Test scheduling",
        system_prompt="You are a patient calling to schedule an appointment.",
        opening_line="Hi, I need an appointment.",
        tags=["scheduling"],
    )


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.deepgram_api_key = "dg_test"
    cfg.openai_api_key = "openai_test"
    cfg.twilio_account_sid = "ACtest"
    cfg.twilio_auth_token = "authtest"
    cfg.twilio_phone_number = "+11234567890"
    cfg.target_phone_number = "+18054398008"
    cfg.websocket_host = "0.0.0.0"
    cfg.websocket_port = 8765
    cfg.ngrok_auth_token = "ngrok_test"
    return cfg


@pytest.fixture
def mock_all_components(mocker):
    mocks = {}
    tts = mocker.AsyncMock()
    tts.synthesize_to_mulaw = mocker.AsyncMock(return_value=b"\x00" * 320)
    mocker.patch("src.orchestrator.DeepgramTTS", return_value=tts)
    mocks["tts"] = tts

    stt = mocker.AsyncMock()
    stt.start_stream = mocker.AsyncMock()
    stt.send_audio = mocker.AsyncMock()
    stt.stop_stream = mocker.AsyncMock()
    mocker.patch("src.orchestrator.DeepgramSTT", return_value=stt)
    mocks["stt"] = stt

    agent = mocker.AsyncMock()
    agent.get_opening_line = mocker.AsyncMock(return_value="Hi, I need an appointment.")
    agent.generate_response = mocker.AsyncMock(return_value="Yes, Tuesday works.")
    agent.should_hang_up = mocker.AsyncMock(return_value=False)
    mocker.patch("src.orchestrator.PatientAgent", return_value=agent)
    mocks["agent"] = agent

    recorder = mocker.MagicMock()
    recorder.save_recording = mocker.MagicMock(return_value="output/recordings/test.mp3")
    recorder.save_transcript = mocker.MagicMock(return_value="output/transcripts/test.txt")
    mocker.patch("src.orchestrator.CallRecorder", return_value=recorder)
    mocks["recorder"] = recorder

    twilio = mocker.MagicMock()
    twilio.make_call = mocker.MagicMock(return_value="CA1234567890")
    twilio.end_call = mocker.MagicMock()
    mocker.patch("src.orchestrator.TwilioClient", return_value=twilio)
    mocks["twilio"] = twilio

    return mocks


# ── Step 6.1a: CallPipeline ────────────────────────────────────────────────────

def test_call_pipeline_init_creates_components(mock_config, scenario, mock_all_components):
    pipeline = CallPipeline(mock_config, scenario, "call001")
    assert pipeline.call_id == "call001"
    assert pipeline.tts is not None
    assert pipeline.stt is not None
    assert pipeline.agent is not None
    assert pipeline.recorder is not None
    assert pipeline.state == CallState.WAITING


async def test_on_audio_received_records_and_forwards(mock_config, scenario, mock_all_components):
    pipeline = CallPipeline(mock_config, scenario, "call002")
    await pipeline.on_audio_received(b"\x00" * 160)
    mock_all_components["recorder"].add_inbound_chunk.assert_called_once()
    mock_all_components["stt"].send_audio.assert_called_once_with(b"\x00" * 160)


async def test_on_transcript_triggers_response_flow(mock_config, scenario, mock_all_components):
    pipeline = CallPipeline(mock_config, scenario, "call003")
    pipeline.state = CallState.LISTENING
    media_handler = MagicMock()
    media_handler.send_audio = AsyncMock()
    pipeline.media_handler = media_handler

    await pipeline.on_transcript("How can I help you?", is_final=True)

    mock_all_components["agent"].generate_response.assert_called_once()
    mock_all_components["tts"].synthesize_to_mulaw.assert_called_once()


# ── Step 6.1b: Orchestrator ────────────────────────────────────────────────────

def test_orchestrator_init(mock_config, mock_all_components):
    orch = Orchestrator(mock_config)
    assert orch.config is mock_config
    assert orch.twilio is not None


async def test_run_all_scenarios_runs_sequentially(mock_config, scenario, mock_all_components, mocker):
    orch = Orchestrator(mock_config)
    mock_run_call = mocker.AsyncMock(return_value={"call_id": "x", "status": "completed"})
    orch.run_call = mock_run_call
    mocker.patch.object(orch, "_start_infrastructure", new=mocker.AsyncMock())
    mocker.patch.object(orch, "_stop_infrastructure", new=mocker.MagicMock())
    mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)
    scenarios = [scenario, scenario, scenario]
    results = await orch.run_all_scenarios(scenarios, delay_between_calls=0)
    assert mock_run_call.call_count == 3
    assert len(results) == 3


# ── Step 6.1c: Bug report ──────────────────────────────────────────────────────

async def test_generate_bug_report_creates_file(mock_config, mock_all_components, tmp_path, mocker):
    orch = Orchestrator(mock_config)
    mocker.patch("os.makedirs")

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "# Bug Report\n\nNo bugs found."
    mock_openai_client = mocker.AsyncMock()
    mock_openai_client.chat.completions.create = mocker.AsyncMock(return_value=mock_completion)
    mocker.patch("src.orchestrator.AsyncOpenAI", return_value=mock_openai_client)

    mock_open = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)

    call_results = [{"scenario_id": "test", "transcript_path": "", "status": "completed"}]
    report = await orch.generate_bug_report(call_results)
    assert "Bug Report" in report


async def test_generate_bug_report_includes_transcripts(mock_config, mock_all_components, tmp_path, mocker):
    orch = Orchestrator(mock_config)

    transcript_content = "[0.0] agent: How can I help you?\n[1.0] patient: I need an appointment.\n"
    tx_file = tmp_path / "test_transcript.txt"
    tx_file.write_text(transcript_content)

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "# Bug Report\n\nFound issues."
    mock_openai_client = mocker.AsyncMock()
    captured_prompt = {}

    async def capture_create(**kwargs):
        captured_prompt["messages"] = kwargs["messages"]
        return mock_completion

    mock_openai_client.chat.completions.create = capture_create
    mocker.patch("src.orchestrator.AsyncOpenAI", return_value=mock_openai_client)
    mocker.patch("os.makedirs")
    mocker.patch("builtins.open", mocker.mock_open())

    call_results = [{
        "call_id": "abc123",
        "scenario_id": "s1",
        "transcript_path": str(tx_file),
        "status": "completed",
    }]
    mocker.patch("builtins.open", mocker.mock_open(read_data="Agent: Hello\nPatient: Hi"))
    await orch.generate_bug_report(call_results)
    prompt_text = captured_prompt["messages"][0]["content"]
    assert "s1" in prompt_text


def test_stop_infrastructure_ignores_ngrok_disconnect_errors(mock_config, mock_all_components, mocker):
    orch = Orchestrator(mock_config)
    orch._server = MagicMock()
    server = orch._server
    orch._tunnel = MagicMock()
    orch._tunnel.public_url = "https://example.ngrok-free.dev"

    mock_disconnect = mocker.patch(
        "pyngrok.ngrok.disconnect", side_effect=RuntimeError("session closed")
    )

    orch._stop_infrastructure()

    server.close.assert_called_once()
    mock_disconnect.assert_called_once_with("https://example.ngrok-free.dev")
    assert orch._server is None
    assert orch._tunnel is None

# Tests for main.py entry point.
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def test_main_validates_config(capsys, mocker):
    # If env vars are missing, main() prints an error and returns early.
    mock_cfg = MagicMock()
    mock_cfg.validate.return_value = ["OPENAI_API_KEY", "TWILIO_AUTH_TOKEN"]
    mocker.patch("main.Config.from_env", return_value=mock_cfg)

    from main import main
    await main()

    captured = capsys.readouterr()
    assert "Missing environment variables" in captured.out
    assert "OPENAI_API_KEY" in captured.out


async def test_main_runs_orchestrator(mocker):
    # When config is valid, main() calls run_all_scenarios and generate_bug_report.
    mock_cfg = MagicMock()
    mock_cfg.validate.return_value = []
    mocker.patch("main.Config.from_env", return_value=mock_cfg)

    call_result = {
        "call_id": "abc123",
        "status": "completed",
        "duration": 45.2,
        "recording_path": "output/recordings/abc123.mp3",
        "transcript_path": "output/transcripts/abc123.txt",
    }
    mock_orch = MagicMock()
    mock_orch.run_all_scenarios = AsyncMock(return_value=[call_result])
    mock_orch.generate_bug_report = AsyncMock(return_value="# Bug Report")
    mocker.patch("main.Orchestrator", return_value=mock_orch)

    from main import main
    await main()

    mock_orch.run_all_scenarios.assert_called_once()
    mock_orch.generate_bug_report.assert_called_once()

# Tests for CallRecorder module (Steps 1.4a and 1.4b).
import os
import json
import tempfile
import pytest
import numpy as np
from src.call_recorder import CallRecorder


@pytest.fixture
def recorder(tmp_path):
    # Create a CallRecorder using a temporary output directory.
    return CallRecorder(call_id="test-call-001", output_dir=str(tmp_path))


@pytest.fixture
def sample_pcm():
    # Generate 0.1 second of silent PCM (16-bit, 8kHz, mono).
    return np.zeros(800, dtype=np.int16).tobytes()


# ── Step 1.4a tests ─────────────────────────────────────────────────────────

def test_recorder_creates_output_dirs(tmp_path):
    # Assert recordings and transcripts directories are created.
    CallRecorder(call_id="dir-test", output_dir=str(tmp_path))
    assert os.path.isdir(os.path.join(str(tmp_path), "recordings"))
    assert os.path.isdir(os.path.join(str(tmp_path), "transcripts"))


def test_add_inbound_chunk_stores_data(recorder, sample_pcm):
    # Add chunks, assert internal buffer grows.
    assert len(recorder.inbound_chunks) == 0
    recorder.add_inbound_chunk(sample_pcm)
    recorder.add_inbound_chunk(sample_pcm)
    assert len(recorder.inbound_chunks) == 2


def test_add_outbound_chunk_stores_data(recorder, sample_pcm):
    # Same for outbound.
    assert len(recorder.outbound_chunks) == 0
    recorder.add_outbound_chunk(sample_pcm)
    assert len(recorder.outbound_chunks) == 1


def test_add_transcript_entry_stores_entry(recorder):
    # Add entries, assert they're retrievable.
    recorder.add_transcript_entry("agent", "Hello, how can I help?", 0.5)
    recorder.add_transcript_entry("patient", "I'd like an appointment.", 2.3)
    assert len(recorder.transcript_entries) == 2
    assert recorder.transcript_entries[0]["speaker"] == "agent"
    assert recorder.transcript_entries[1]["text"] == "I'd like an appointment."


# ── Step 1.4b tests ─────────────────────────────────────────────────────────

def test_save_recording_creates_mp3(recorder, sample_pcm):
    # Add sample PCM chunks, save, assert MP3 file exists and is non-empty.
    recorder.add_inbound_chunk(sample_pcm)
    recorder.add_outbound_chunk(sample_pcm)
    path = recorder.save_recording()
    assert os.path.isfile(path)
    assert path.endswith(".mp3")
    assert os.path.getsize(path) > 0


def test_save_transcript_creates_files(recorder):
    # Add transcript entries, save, assert TXT and JSON files exist.
    recorder.add_transcript_entry("agent", "Hello!", 0.0)
    recorder.add_transcript_entry("patient", "Hi there!", 1.5)
    txt_path = recorder.save_transcript()
    assert os.path.isfile(txt_path)
    assert txt_path.endswith(".txt")
    json_path = txt_path.replace(".txt", ".json")
    assert os.path.isfile(json_path)


def test_get_transcript_text_format(recorder):
    # Assert format is [TIMESTAMP] SPEAKER: text.
    recorder.add_transcript_entry("agent", "Hello!", 0.0)
    recorder.add_transcript_entry("patient", "Hi there!", 1.5)
    text = recorder.get_transcript_text()
    assert "[0.00] AGENT: Hello!" in text
    assert "[1.50] PATIENT: Hi there!" in text


def test_save_recording_empty_audio_handles_gracefully(recorder):
    # No chunks added, save should not crash.
    path = recorder.save_recording()
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0

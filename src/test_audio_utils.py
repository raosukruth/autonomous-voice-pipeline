# Tests for audio conversion methods now on MediaStreamHandler and CallRecorder.
import pytest
import numpy as np
from src.voip.media_stream import MediaStreamHandler
from src.call_recorder import CallRecorder


# ── Step 1.2a tests: mulaw and base64 (now on MediaStreamHandler) ──────────────

def test_mulaw_to_pcm_returns_bytes():
    # Convert known mulaw bytes, assert output is bytes and correct length.
    handler = MediaStreamHandler()
    mulaw_input = b'\xff' * 160  # 160 bytes of mulaw silence
    result = handler.mulaw_to_pcm(mulaw_input)
    assert isinstance(result, bytes)
    # mulaw to 16-bit PCM: 1 byte → 2 bytes
    assert len(result) == len(mulaw_input) * 2


def test_pcm_to_mulaw_returns_bytes():
    # Convert known PCM, assert output is bytes.
    handler = MediaStreamHandler()
    pcm_input = b'\x00\x00' * 160  # 160 samples of silence
    result = handler.pcm_to_mulaw(pcm_input)
    assert isinstance(result, bytes)
    assert len(result) == 160


def test_mulaw_roundtrip():
    # Encode PCM to mulaw then back; values close within tolerance (mulaw is lossy).
    handler = MediaStreamHandler()
    samples = np.array([0, 1000, -1000, 5000, -5000, 16000, -16000], dtype=np.int16)
    pcm_bytes = samples.tobytes()
    mulaw_bytes = handler.pcm_to_mulaw(pcm_bytes)
    pcm_back = handler.mulaw_to_pcm(mulaw_bytes)
    samples_back = np.frombuffer(pcm_back, dtype=np.int16)
    # mulaw is lossy; allow 5% relative error or 500 absolute
    for orig, recovered in zip(samples, samples_back):
        tolerance = max(500, abs(int(orig)) * 0.1)
        assert abs(int(orig) - int(recovered)) <= tolerance, \
            f"Round-trip mismatch: {orig} → {recovered}"


def test_base64_roundtrip():
    # Encode bytes to base64 then decode; assert exact match.
    handler = MediaStreamHandler()
    original = b'\x00\x01\x02\xFE\xFF' * 100
    b64 = handler.bytes_to_base64(original)
    assert isinstance(b64, str)
    recovered = handler.base64_to_bytes(b64)
    assert recovered == original


# ── Step 1.2b tests: wav, mp3, resample, mix (now on CallRecorder) ────────────

def test_pcm_to_wav_has_valid_header(sample_pcm_audio, tmp_path):
    # Assert output starts with RIFF and WAVE markers.
    recorder = CallRecorder("test_wav", output_dir=str(tmp_path))
    wav_bytes = recorder.pcm_to_wav(sample_pcm_audio)
    assert wav_bytes[:4] == b'RIFF'
    assert wav_bytes[8:12] == b'WAVE'


def test_pcm_to_wav_correct_params(sample_pcm_audio, tmp_path):
    # Parse WAV header, assert sample rate and channels match input.
    import wave, io
    recorder = CallRecorder("test_wav_params", output_dir=str(tmp_path), sample_rate=8000)
    wav_bytes = recorder.pcm_to_wav(sample_pcm_audio, channels=1)
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
        assert wf.getframerate() == 8000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


def test_wav_to_mp3_produces_valid_mp3(sample_pcm_audio, tmp_path):
    # Assert output starts with MP3 frame sync bytes or ID3 tag.
    recorder = CallRecorder("test_mp3", output_dir=str(tmp_path))
    wav_bytes = recorder.pcm_to_wav(sample_pcm_audio)
    mp3_bytes = recorder.wav_to_mp3(wav_bytes)
    assert len(mp3_bytes) > 0
    # MP3 files start with ID3 tag (b'ID3') or sync word (0xFF 0xFB / 0xFF 0xF3 etc.)
    is_id3 = mp3_bytes[:3] == b'ID3'
    is_sync = (mp3_bytes[0] == 0xFF and mp3_bytes[1] & 0xE0 == 0xE0)
    assert is_id3 or is_sync, f"Not a valid MP3: first bytes={mp3_bytes[:4].hex()}"


def test_resample_doubles_length(tmp_path):
    # Resample from 8000 to 16000 Hz, assert output is ~2x length.
    recorder = CallRecorder("test_resample", output_dir=str(tmp_path))
    pcm = np.zeros(8000, dtype=np.int16).tobytes()
    result = recorder.resample_pcm(pcm, from_rate=8000, to_rate=16000)
    original_samples = len(pcm) // 2
    result_samples = len(result) // 2
    assert abs(result_samples - original_samples * 2) <= 2


def test_mix_audio_streams_same_length(tmp_path):
    # Mix two equal-length streams, assert output length matches.
    recorder = CallRecorder("test_mix_same", output_dir=str(tmp_path))
    pcm_a = np.zeros(8000, dtype=np.int16).tobytes()
    pcm_b = np.zeros(8000, dtype=np.int16).tobytes()
    result = recorder.mix_audio_streams(pcm_a, pcm_b)
    assert len(result) == len(pcm_a)


def test_mix_audio_streams_different_length(tmp_path):
    # Mix different lengths, assert output length matches longer stream.
    recorder = CallRecorder("test_mix_diff", output_dir=str(tmp_path))
    pcm_a = np.zeros(8000, dtype=np.int16).tobytes()
    pcm_b = np.zeros(4000, dtype=np.int16).tobytes()
    result = recorder.mix_audio_streams(pcm_a, pcm_b)
    assert len(result) == len(pcm_a)

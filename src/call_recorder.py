# Call recorder: accumulates audio chunks and saves as MP3 + transcripts.
import io
import os
import json
import sys
import time
import wave
from typing import List, Dict
import numpy as np
from src.logger import get_logger

# mulaw → linear PCM decoding (audioop or numpy fallback)
def _mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    if not mulaw_bytes:
        return b""
    if sys.version_info < (3, 13):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import audioop
        return audioop.ulaw2lin(mulaw_bytes, 2)
    # numpy fallback for Python 3.13+
    table = []
    for i in range(256):
        byte = ~i & 0xFF
        sign = byte & 0x80
        exp = (byte >> 4) & 0x07
        mant = byte & 0x0F
        sample = (((mant << 1) | 0x21) << exp) - 33
        table.append(-sample if sign else sample)
    arr = np.array([table[b] for b in mulaw_bytes], dtype=np.int16)
    return arr.tobytes()

logger = get_logger(__name__)


class CallRecorder:
    # Records both sides of a call and produces MP3 + transcript files.

    def __init__(self, call_id: str, output_dir: str = "output", sample_rate: int = 8000):
        # Initialize with a unique call ID. Creates output subdirectories.
        self.call_id = call_id
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.recordings_dir = os.path.join(output_dir, "recordings")
        self.transcripts_dir = os.path.join(output_dir, "transcripts")
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)

        self.inbound_chunks: List[bytes] = []
        self.outbound_chunks: List[bytes] = []
        self.transcript_entries: List[Dict] = []

    def add_inbound_chunk(self, mulaw_bytes: bytes) -> None:
        # Inbound audio from Twilio is mulaw-encoded; decode to linear PCM.
        self.inbound_chunks.append(_mulaw_to_pcm(mulaw_bytes))

    def add_outbound_chunk(self, mulaw_bytes: bytes) -> None:
        # Outbound TTS audio is mulaw-encoded; decode to linear PCM.
        self.outbound_chunks.append(_mulaw_to_pcm(mulaw_bytes))

    def add_transcript_entry(self, speaker: str, text: str, timestamp: float) -> None:
        # Add a transcript line. speaker is 'agent' or 'patient'.
        self.transcript_entries.append({
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp,
        })

    def save_recording(self) -> str:
        # Mix inbound+outbound, convert to MP3, save. Returns file path.
        inbound_pcm = b"".join(self.inbound_chunks)
        outbound_pcm = b"".join(self.outbound_chunks)

        if not inbound_pcm and not outbound_pcm:
            # Produce a short silent recording rather than crashing
            silent = b"\x00\x00" * 8000
            mixed_pcm = silent
        elif not inbound_pcm:
            mixed_pcm = outbound_pcm
        elif not outbound_pcm:
            mixed_pcm = inbound_pcm
        else:
            mixed_pcm = self.mix_audio_streams(inbound_pcm, outbound_pcm)

        wav_bytes = self.pcm_to_wav(mixed_pcm)
        mp3_bytes = self.wav_to_mp3(wav_bytes)

        mp3_path = os.path.join(self.recordings_dir, f"{self.call_id}.mp3")
        with open(mp3_path, "wb") as f:
            f.write(mp3_bytes)

        logger.info(f"Saved recording: {mp3_path}")
        return mp3_path

    def save_transcript(self) -> str:
        # Save transcript as JSON and TXT. Returns TXT file path.
        base = os.path.join(self.transcripts_dir, self.call_id)

        json_path = f"{base}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.transcript_entries, f, indent=2)

        txt_path = f"{base}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.get_transcript_text())

        logger.info(f"Saved transcript: {txt_path}")
        return txt_path

    def get_transcript_text(self) -> str:
        # Return transcript as formatted text string.
        lines = []
        for entry in self.transcript_entries:
            ts = entry["timestamp"]
            speaker = entry["speaker"].upper()
            text = entry["text"]
            lines.append(f"[{ts:.2f}] {speaker}: {text}")
        return "\n".join(lines)

    # ── Audio conversion methods ───────────────────────────────────────────────

    def pcm_to_wav(self, pcm_bytes: bytes, channels: int = 1) -> bytes:
        # Wrap raw PCM in a WAV container using this recorder's sample rate.
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    def wav_to_mp3(self, wav_bytes: bytes) -> bytes:
        # Convert WAV bytes to MP3 using pydub+ffmpeg.
        from pydub import AudioSegment
        wav_io = io.BytesIO(wav_bytes)
        segment = AudioSegment.from_wav(wav_io)
        mp3_io = io.BytesIO()
        segment.export(mp3_io, format="mp3")
        return mp3_io.getvalue()

    def mix_audio_streams(self, stream_a: bytes, stream_b: bytes) -> bytes:
        # Mix two PCM streams of this recorder's sample rate. Zero-pads shorter.
        a = np.frombuffer(stream_a, dtype=np.int16).astype(np.int32)
        b = np.frombuffer(stream_b, dtype=np.int16).astype(np.int32)
        max_len = max(len(a), len(b))
        a = np.pad(a, (0, max_len - len(a)))
        b = np.pad(b, (0, max_len - len(b)))
        mixed = (a + b).clip(-32768, 32767).astype(np.int16)
        return mixed.tobytes()

    def resample_pcm(self, pcm_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        # Resample 16-bit PCM from from_rate to to_rate using linear interpolation.
        samples = np.frombuffer(pcm_bytes, dtype=np.int16)
        num_out = int(len(samples) * to_rate / from_rate)
        indices = np.linspace(0, len(samples) - 1, num_out)
        resampled = np.interp(indices, np.arange(len(samples)), samples)
        return resampled.astype(np.int16).tobytes()

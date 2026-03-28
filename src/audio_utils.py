# Audio format utilities for the voice bot pipeline.
import sys
import base64
import struct
import io
import wave
import numpy as np
from pydub import AudioSegment



# Use audioop if available (Python < 3.13), otherwise use numpy-based fallback
USE_AUDIOOP = sys.version_info < (3, 13)

if USE_AUDIOOP:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import audioop


# ── mulaw lookup tables for Python 3.13+ fallback ─────────────────────────────

MULAW_DECODE_TABLE = None
MULAW_ENCODE_TABLE = None


def build_mulaw_tables():
    # Build mulaw encode/decode lookup tables.
    global MULAW_DECODE_TABLE, MULAW_ENCODE_TABLE

    # Decode table: 256 entries, mulaw byte → 16-bit PCM sample
    decode = []
    for i in range(256):
        byte = ~i & 0xFF
        sign = byte & 0x80
        exponent = (byte >> 4) & 0x07
        mantissa = byte & 0x0F
        sample = ((mantissa << 1) | 0x21) << exponent
        sample -= 33
        if sign:
            sample = -sample
        decode.append(sample)
    MULAW_DECODE_TABLE = decode

    # Encode table: build by inverting the decode
    encode = [0] * 65536  # indexed by (sample + 32768) as uint16
    for mulaw_byte in range(256):
        pcm = decode[mulaw_byte]
        idx = pcm + 32768
        if 0 <= idx < 65536:
            encode[idx] = mulaw_byte
    # Fill gaps by nearest-neighbour
    for i in range(1, 65536):
        if encode[i] == 0 and encode[i - 1] != 0:
            encode[i] = encode[i - 1]
    MULAW_ENCODE_TABLE = encode


def mulaw_to_pcm_numpy(mulaw_bytes: bytes) -> bytes:
    # Convert mulaw bytes to signed 16-bit PCM using lookup table.
    global MULAW_DECODE_TABLE
    if MULAW_DECODE_TABLE is None:
        build_mulaw_tables()
    arr = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    pcm = np.array([MULAW_DECODE_TABLE[b] for b in arr], dtype=np.int16)
    return pcm.tobytes()


def pcm_to_mulaw_numpy(pcm_bytes: bytes) -> bytes:
    # Convert signed 16-bit PCM to mulaw bytes using lookup table.
    global MULAW_ENCODE_TABLE
    if MULAW_ENCODE_TABLE is None:
        build_mulaw_tables()
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    indices = (samples.astype(np.int32) + 32768).clip(0, 65535)
    mulaw = np.array([MULAW_ENCODE_TABLE[i] for i in indices], dtype=np.uint8)
    return mulaw.tobytes()

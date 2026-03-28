# Deepgram TTS implementation using Deepgram REST API.
import aiohttp

DEEPGRAM_SPEAK_URL = "https://api.deepgram.com/v1/speak"


class DeepgramTTS:
    # Deepgram TTS implementation using their REST API.

    def __init__(self, api_key: str, model: str = "aura-asteria-en", sample_rate: int = 8000):
        # Initialize with Deepgram API key.
        self.api_key = api_key
        self.model = model
        self.sample_rate = sample_rate

    async def synthesize(self, text: str) -> bytes:
        # Call Deepgram TTS API. Returns PCM audio bytes (linear16 encoding).
        if not text:
            raise ValueError("Text cannot be empty")

        params = {
            "model": self.model,
            "encoding": "linear16",
            "sample_rate": self.sample_rate,
            "container": "none",
        }
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {"text": text}

        return await self.post_deepgram(params, headers, body)

    async def synthesize_to_mulaw(self, text: str) -> bytes:
        # Call Deepgram TTS API with mulaw encoding (ready for Twilio).
        if not text:
            raise ValueError("Text cannot be empty")

        params = {
            "model": self.model,
            "encoding": "mulaw",
            "sample_rate": 8000,
            "container": "none",
        }
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {"text": text}

        return await self.post_deepgram(params, headers, body)

    async def post_deepgram(self, params: dict, headers: dict, body: dict) -> bytes:
        # Shared HTTP POST helper for Deepgram TTS endpoint.
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPGRAM_SPEAK_URL, params=params, headers=headers, json=body) as resp:
                if resp.status == 401:
                    raise PermissionError("Deepgram API key is invalid or unauthorized")
                if resp.status == 429:
                    raise RuntimeError("Deepgram rate limit exceeded")
                if resp.status != 200:
                    raise RuntimeError(f"Deepgram TTS request failed with status {resp.status}")
                return await resp.read()

    def get_sample_rate(self) -> int:
        return self.sample_rate

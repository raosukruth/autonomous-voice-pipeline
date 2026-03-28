# Configuration management: load and validate environment variables from .env.
import os
from dotenv import load_dotenv


class Config:
    # Singleton configuration manager.

    def __init__(self, env_path: str = ".env"):
        # Load .env file and populate attributes.
        load_dotenv(dotenv_path=env_path, override=True)

        self.twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.target_phone_number: str = os.getenv("TARGET_PHONE_NUMBER", "+18054398008")
        self.websocket_host: str = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        self.websocket_port: int = int(os.getenv("WEBSOCKET_PORT", "8765"))
        self.ngrok_auth_token: str = os.getenv("NGROK_AUTH_TOKEN", "")

    def validate(self) -> list:
        # Return list of missing required env vars. Empty list = all valid.
        required = [
            "twilio_account_sid",
            "twilio_auth_token",
            "twilio_phone_number",
            "deepgram_api_key",
            "openai_api_key",
            "ngrok_auth_token",
        ]
        missing = []
        for attr in required:
            value = getattr(self, attr, "")
            if not value:
                env_var = attr.upper()
                missing.append(env_var)
        return missing

    @classmethod
    def from_env(cls) -> "Config":
        # Factory that loads from default .env location.
        return cls(env_path=".env")

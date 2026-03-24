from typing import Optional
from pydantic import SecretStr, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TOKEN: SecretStr
    TELEGRAM_SECRET: SecretStr

    STATISTICS_HEARTBEAT_URL: AnyUrl

    UPTIME_API_TOKEN: SecretStr
    UPTIME_MONITOR_ID: SecretStr

    NGROK_AUTHTOKEN: SecretStr
    UKRAINEALARM_TOKEN: SecretStr

    ADMINS_CHAT_ID: int = 1568892912
    ADMINS_MODERATION_THREAD_ID: Optional[int]
    ADMINS_BUGS_THREAD_ID: Optional[int]
    ADMINS_FEEDBACK_THREAD_ID: Optional[int]
    ADMINS_STREAM_THREAD_ID: Optional[int]
    ADMINS: Optional[list[int]] = None

    BASE_URL: AnyUrl = AnyUrl("http://localhost:8000")

    SPOTIPY_CLIENT_ID: SecretStr
    SPOTIPY_CLIENT_SECRET: SecretStr

    COOKIES_PATH: Optional[str] = None

    @property
    def WEBHOOK_URL(self) -> str:
        return f"{self.BASE_URL}webhook"

    model_config = SettingsConfigDict(env_file=("stack.env", ".env"), extra="ignore")


settings = Settings()

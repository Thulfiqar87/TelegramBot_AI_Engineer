import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    OPENAI_API_KEY: str          # Required — bot cannot function without AI
    OPENPROJECT_URL: str
    OPENPROJECT_API_KEY: str
    OPENWEATHER_API_KEY: str
    OPENWEATHER_LAT: float = 24.7136
    OPENWEATHER_LON: float = 46.6753
    DATA_DIR: str = "data"
    ADMIN_IDS: list[int] = [5029080143]

    @property
    def LOGS_DIR(self) -> str:
        return os.path.join(self.DATA_DIR, "logs")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate(self):
        # Pydantic validates required fields on instantiation
        pass

# Instantiate global settings
try:
    Config = Settings()
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
except Exception as e:
    print(f"Configuration Error: {e}")
    raise

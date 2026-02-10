import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    GOOGLE_API_KEY: str = "deprecated" # Keeping to avoid breaking if .env still has it, but unused
    DASHSCOPE_API_KEY: str
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
        # Pydantic validates on instantiation
        pass

# Instantiate global settings
try:
    Config = Settings()
    # Create logs dir
    os.makedirs(Config.LOGS_DIR, exist_ok=True)
except Exception as e:
    # We allow import failure to not crash immediately if env is missing during test, 
    # but strictly we should. For now, let's print.
    print(f"Configuration Error: {e}")
    # We must ensure Config is available or re-raise
    # To avoid 'name Config is not defined' in other modules if this fails:
    raise e

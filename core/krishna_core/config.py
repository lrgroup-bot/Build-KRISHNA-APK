from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("KRISHNA_HOST", "0.0.0.0")
    port: int = int(os.getenv("KRISHNA_PORT", "8766"))
    db_path: str = os.getenv("KRISHNA_DB", "krishna_core.db")
    ollama_url: str = os.getenv("KRISHNA_OLLAMA_URL", "http://127.0.0.1:11434")
    cloud_api_url: str = os.getenv("KRISHNA_CLOUD_API_URL", "")
    cloud_api_key: str = os.getenv("KRISHNA_CLOUD_API_KEY", "")
    allow_actions: bool = os.getenv("KRISHNA_ALLOW_ACTIONS", "0") == "1"

settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./visaguard.db"
    storage_root: str = "./storage"
    encryption_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_timeout_seconds: int = 60

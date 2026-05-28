from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./visaguard.db"
    storage_root: str = "./storage"
    encryption_key: str = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_timeout_seconds: int = 180
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    policy_data_root: str = "./data/policy"
    policy_index_path: str = "./data/policy/index/policy_index.json"
    dso_index_path: str = "./data/dso/index"
    dso_school_aliases_path: str = "./app/services/dso_agent/data/school_aliases.json"
    langgraph_checkpointer_path: str = "./langgraph.sqlite"

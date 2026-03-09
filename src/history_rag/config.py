from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    dashscope_api_key: str = ""
    embedding_model: str = "text-embedding-v4"
    embedding_provider: str = "dashscope"  # "dashscope" or "local"
    llm_model: str = "claude-sonnet-4-20250514"
    chroma_persist_dir: str = str(PROJECT_ROOT / "data" / "chroma_db")
    data_raw_dir: str = str(PROJECT_ROOT / "data" / "raw")
    prompts_dir: str = str(PROJECT_ROOT / "prompts")
    chunk_max_chars: int = 500
    chunk_overlap_sentences: int = 2
    retrieval_top_k: int = 10

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()

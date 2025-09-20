from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    env: Literal["dev","prod"] = "dev"
    llm_backend: Literal["lmstudio","openai"] = "lmstudio"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    openai_api_key: str | None = None
    vector_db: Literal["chromadb","faiss"] = "chromadb"

    class Config:
        env_file = ".env"

def load_settings() -> Settings:
    return Settings()

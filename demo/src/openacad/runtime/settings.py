from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: this file is src/openacad/runtime/settings.py.
# Four `.parent` calls climb to the repo root that holds .env, data/, scripts/, apps/.
DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── LLM provider ────────────────────────────────────────
    llm_provider: Literal["anthropic", "openai", "openrouter", "deepseek"] = "anthropic"

    anthropic_api_key: str = ""
    anthropic_extraction_model: str = "claude-haiku-4-5-20251001"
    anthropic_synthesis_model: str = "claude-sonnet-4-6"

    openai_api_key: str = ""
    openai_extraction_model: str = "gpt-4o-mini"
    openai_synthesis_model: str = "gpt-4o"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_extraction_model: str = "anthropic/claude-haiku-4.5"
    openrouter_synthesis_model: str = "anthropic/claude-haiku-4.5"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # ── embeddings (local) ──────────────────────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── paths ───────────────────────────────────────────────
    vault_dir: Path = Field(default_factory=lambda: DEMO_ROOT / "vault")
    data_dir: Path = Field(default_factory=lambda: DEMO_ROOT / "data")
    embeddings_dir: Path = Field(default_factory=lambda: DEMO_ROOT / "data" / "embeddings")
    tinydb_path: Path = Field(default_factory=lambda: DEMO_ROOT / "data" / "state.json")
    prompts_dir: Path = Field(default_factory=lambda: DEMO_ROOT / "api" / "prompts")

    # ── thresholds ──────────────────────────────────────────
    prompt_regen_threshold: int = 10
    registry_promote_threshold: int = 3

    # ── server ──────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def extraction_model(self) -> str:
        return {
            "anthropic": self.anthropic_extraction_model,
            "openai": self.openai_extraction_model,
            "openrouter": self.openrouter_extraction_model,
            "deepseek": "deepseek-chat",
        }[self.llm_provider]

    @property
    def synthesis_model(self) -> str:
        return {
            "anthropic": self.anthropic_synthesis_model,
            "openai": self.openai_synthesis_model,
            "openrouter": self.openrouter_synthesis_model,
            "deepseek": "deepseek-chat",
        }[self.llm_provider]


settings = Settings()

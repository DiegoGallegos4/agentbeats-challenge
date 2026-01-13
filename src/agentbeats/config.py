"""Shared configuration models for AgentBeats scaffolding."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from .config_loader import CONFIG_PATH, get_config_value
from .domain.finance import FINANCE_KEYWORDS


class DataPaths(BaseModel):
    predictions: Path = Field(default=Path("data/generated/predictions/latest.jsonl"))
    resolutions: Path = Field(default=Path("data/generated/resolutions/latest.jsonl"))
    events: Path = Field(default=Path("data/generated/events/latest.jsonl"))


class EvaluatorConfig(BaseModel):
    data_paths: DataPaths = Field(default_factory=DataPaths)
    metrics: List[str] = Field(default_factory=lambda: ["accuracy", "brier"])
    run_log_dir: Path = Field(default=Path("data/generated/runs"))


class IngestionConfig(BaseModel):
    fixture_events: Path = Field(default=Path("data/fixtures/resolutions/sample_events.jsonl"))
    default_output: Path = Field(default=Path("data/generated/events/latest.jsonl"))
    source: str = Field(default="polymarket")
    polymarket_limit: int = Field(default=10)
    include_active: bool = Field(default=True)
    finance_keywords: List[str] = Field(default_factory=lambda: list(FINANCE_KEYWORDS.keys()))


class PredictorConfig(BaseModel):
    events_snapshot: Path = Field(default=Path("data/generated/events/latest.jsonl"))
    fallback_events: Path = Field(default=Path("data/fixtures/resolutions/sample_events.jsonl"))
    news_fixtures: Optional[Path] = Field(default=None)
    fixture_predictions: Path = Field(default=Path("data/fixtures/predictions/sample_predictions.jsonl"))
    default_output: Path = Field(default=Path("data/generated/predictions/latest.jsonl"))
    tool_log_dir: Path = Field(default=Path("data/generated/tool_logs"))
    alpha_vantage_api_key: Optional[str] = Field(
        default_factory=lambda: get_config_value(["tools", "alpha_vantage", "api_key"], env_fallback="ALPHAVANTAGE_API_KEY")
    )
    alpha_vantage_cache_dir: Path = Field(
        default_factory=lambda: Path(
            get_config_value(
                ["tools", "alpha_vantage", "cache_dir"],
                default="data/generated/tool_cache/alpha_vantage",
            )
        )
    )
    edgar_user_agent: str = Field(
        default_factory=lambda: get_config_value(
            ["tools", "edgar", "user_agent"],
            default="agentbeats/0.1 (contact: your-email@example.com)",
            env_fallback="SEC_USER_AGENT",
        )
    )
    edgar_cache_dir: Path = Field(
        default_factory=lambda: Path(
            get_config_value(
                ["tools", "edgar", "cache_dir"],
                default="data/generated/tool_cache/edgar",
            )
        )
    )

class LLMConfig(BaseModel):
    provider: str = Field(default_factory=lambda: get_config_value(["llm", "provider"], default="ollama"))
    model: str = Field(default_factory=lambda: get_config_value(["llm", "model"], default="llama3"))
    endpoint: str = Field(default_factory=lambda: get_config_value(["llm", "endpoint"], default="http://localhost:11434"))
    temperature: float = Field(default_factory=lambda: float(get_config_value(["llm", "temperature"], default=0.0)))


def config_path() -> Path:
    """Expose the resolved config path for messaging."""
    return CONFIG_PATH

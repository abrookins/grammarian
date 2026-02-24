"""Configuration management for Proseq."""

from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from pydantic import BaseModel, Field


class MetricConfig(BaseModel):
    """Configuration for a single metric."""

    enabled: bool = True
    weight: float = Field(default=1.0, ge=0.0)
    options: dict[str, Any] = Field(default_factory=dict)


class ProfileConfig(BaseModel):
    """Configuration for a writing style profile."""

    name: str
    description: str = ""
    target_grade: int = Field(default=10, ge=1, le=20)
    max_sentence_words: int = Field(default=30, ge=10, le=100)
    check_passive: bool = True
    check_weasel: bool = True
    custom_words: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    """Configuration for LLM integration."""

    enabled: bool = False
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    context: str = ""  # Additional context about writing style/audience


class RedpenConfig(BaseModel):
    """Main configuration model."""

    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    default_profile: str = "default"
    metrics: dict[str, MetricConfig] = Field(default_factory=dict)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    extensions: list[str] = Field(default_factory=lambda: [".md", ".txt", ".rst"])

    @classmethod
    def load(cls, path: Path | None = None) -> "RedpenConfig":
        """Load configuration from file."""
        if path is None:
            path = cls._find_config()
        if path is None or not path.exists():
            return cls()
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    @classmethod
    def _find_config(cls) -> Path | None:
        """Find config file in current or parent directories."""
        names = [".redpen.toml", "redpen.toml", "pyproject.toml"]
        cwd = Path.cwd()
        for parent in [cwd, *cwd.parents]:
            for name in names:
                path = parent / name
                if path.exists():
                    if name == "pyproject.toml":
                        # Check if it has [tool.redpen] section
                        with open(path, "rb") as f:
                            data = tomllib.load(f)
                        if "tool" in data and "redpen" in data["tool"]:
                            return path
                    else:
                        return path
        return None

    def get_profile(self, name: str | None = None) -> ProfileConfig:
        """Get a profile by name, or the default profile."""
        name = name or self.default_profile
        if name in self.profiles:
            return self.profiles[name]
        # Return default profile
        return ProfileConfig(name="default")

    def get_metric_config(self, metric_name: str) -> MetricConfig:
        """Get configuration for a metric."""
        if metric_name.lower() in self.metrics:
            return self.metrics[metric_name.lower()]
        return MetricConfig()


# Default profile definitions
DEFAULT_PROFILES = {
    "default": ProfileConfig(
        name="default",
        description="Balanced settings for general writing",
        target_grade=10,
    ),
    "technical": ProfileConfig(
        name="technical",
        description="Technical documentation style",
        target_grade=12,
        max_sentence_words=35,
        check_passive=False,  # Passive voice is acceptable in technical docs
    ),
    "casual": ProfileConfig(
        name="casual",
        description="Blog posts and casual writing",
        target_grade=8,
        max_sentence_words=25,
        check_weasel=False,  # More relaxed
    ),
    "academic": ProfileConfig(
        name="academic",
        description="Academic and formal writing",
        target_grade=14,
        max_sentence_words=40,
        check_passive=True,
        check_weasel=True,
    ),
}


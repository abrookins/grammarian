"""Tests for configuration management."""

import pytest
from pathlib import Path

from grammarian.config import (
    GrammarianConfig,
    ProfileConfig,
    MetricConfig,
    LLMConfig,
    DEFAULT_PROFILES,
)


class TestProfileConfig:
    """Tests for ProfileConfig."""

    def test_default_values(self) -> None:
        profile = ProfileConfig(name="test")
        assert profile.name == "test"
        assert profile.target_grade == 10
        assert profile.max_sentence_words == 30
        assert profile.check_passive is True
        assert profile.check_weasel is True

    def test_custom_values(self) -> None:
        profile = ProfileConfig(
            name="custom",
            description="Custom profile",
            target_grade=8,
            max_sentence_words=25,
            check_passive=False,
            custom_words=["foo", "bar"],
        )
        assert profile.target_grade == 8
        assert profile.max_sentence_words == 25
        assert profile.check_passive is False
        assert profile.custom_words == ["foo", "bar"]


class TestMetricConfig:
    """Tests for MetricConfig."""

    def test_default_values(self) -> None:
        config = MetricConfig()
        assert config.enabled is True
        assert config.weight == 1.0
        assert config.options == {}

    def test_custom_values(self) -> None:
        config = MetricConfig(enabled=False, weight=2.0, options={"key": "value"})
        assert config.enabled is False
        assert config.weight == 2.0
        assert config.options == {"key": "value"}


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_values(self) -> None:
        config = LLMConfig()
        assert config.enabled is False
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.3

    def test_custom_values(self) -> None:
        config = LLMConfig(enabled=True, model="gpt-4", context="Technical docs")
        assert config.enabled is True
        assert config.model == "gpt-4"
        assert config.context == "Technical docs"


class TestGrammarianConfig:
    """Tests for GrammarianConfig."""

    def test_default_values(self) -> None:
        config = GrammarianConfig()
        assert config.default_profile == "default"
        assert config.profiles == {}
        assert config.metrics == {}
        assert config.extensions == [".md", ".txt", ".rst"]

    def test_get_profile_default(self) -> None:
        config = GrammarianConfig()
        profile = config.get_profile()
        assert profile.name == "default"

    def test_get_profile_custom(self) -> None:
        config = GrammarianConfig(
            profiles={"custom": ProfileConfig(name="custom", target_grade=8)}
        )
        profile = config.get_profile("custom")
        assert profile.name == "custom"
        assert profile.target_grade == 8

    def test_get_profile_unknown_returns_default(self) -> None:
        config = GrammarianConfig()
        profile = config.get_profile("unknown")
        assert profile.name == "default"

    def test_get_metric_config_default(self) -> None:
        config = GrammarianConfig()
        metric_config = config.get_metric_config("spelling")
        assert metric_config.enabled is True
        assert metric_config.weight == 1.0

    def test_get_metric_config_custom(self) -> None:
        config = GrammarianConfig(
            metrics={"spelling": MetricConfig(weight=2.0)}
        )
        metric_config = config.get_metric_config("spelling")
        assert metric_config.weight == 2.0

    def test_load_nonexistent_file(self) -> None:
        config = GrammarianConfig.load(Path("/nonexistent/path.toml"))
        assert config.default_profile == "default"

    def test_load_from_toml(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".grammarian.toml"
        config_file.write_text("""
default_profile = "technical"

[profiles.technical]
name = "technical"
target_grade = 12
""")
        config = GrammarianConfig.load(config_file)
        assert config.default_profile == "technical"
        profile = config.get_profile("technical")
        assert profile.target_grade == 12


class TestDefaultProfiles:
    """Tests for DEFAULT_PROFILES."""

    def test_default_profile_exists(self) -> None:
        assert "default" in DEFAULT_PROFILES
        assert DEFAULT_PROFILES["default"].target_grade == 10

    def test_technical_profile_exists(self) -> None:
        assert "technical" in DEFAULT_PROFILES
        assert DEFAULT_PROFILES["technical"].check_passive is False

    def test_casual_profile_exists(self) -> None:
        assert "casual" in DEFAULT_PROFILES
        assert DEFAULT_PROFILES["casual"].target_grade == 8

    def test_academic_profile_exists(self) -> None:
        assert "academic" in DEFAULT_PROFILES
        assert DEFAULT_PROFILES["academic"].target_grade == 14


class TestConfigFinding:
    """Tests for config file finding."""

    def test_find_config_with_grammarian_toml(self, tmp_path: Path, monkeypatch) -> None:
        """Test finding .grammarian.toml config file."""
        config_file = tmp_path / ".grammarian.toml"
        config_file.write_text('[profiles.test]\nname = "test"\n')

        monkeypatch.chdir(tmp_path)
        found = GrammarianConfig._find_config()
        assert found == config_file

    def test_find_config_pyproject_toml(self, tmp_path: Path, monkeypatch) -> None:
        """Test finding config in pyproject.toml."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.grammarian]
default_profile = "technical"
""")

        monkeypatch.chdir(tmp_path)
        found = GrammarianConfig._find_config()
        assert found == config_file

    def test_find_config_pyproject_no_grammarian(self, tmp_path: Path, monkeypatch) -> None:
        """Test pyproject.toml without grammarian section is ignored."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.black]
line-length = 88
""")

        monkeypatch.chdir(tmp_path)
        found = GrammarianConfig._find_config()
        # Should return None since no grammarian config
        assert found is None

    def test_find_config_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Test when no config file exists."""
        monkeypatch.chdir(tmp_path)
        found = GrammarianConfig._find_config()
        assert found is None


class TestTomliImport:
    """Tests for tomli fallback import."""

    def test_tomllib_import(self) -> None:
        """Verify tomllib is used on Python 3.11+."""
        import sys
        if sys.version_info >= (3, 11):
            import tomllib
            assert tomllib is not None


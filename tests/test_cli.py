"""Tests for the CLI."""

import pytest
from click.testing import CliRunner

from grammarian.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Grammarian" in result.output

    def test_analyze_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--min-score" in result.output
        assert "--diff" in result.output
        assert "--profile" in result.output

    def test_analyze_no_paths(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze"])
        assert "No paths specified" in result.output

    def test_analyze_file(self, runner: CliRunner, tmp_path) -> None:
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("This is a simple test document. It has a few sentences.")

        result = runner.invoke(cli, ["analyze", str(test_file)])
        assert result.exit_code == 0
        assert "Writing Quality Index" in result.output

    def test_analyze_json_format(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Hello world.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--format", "json"])
        assert result.exit_code == 0
        assert "wqi_score" in result.output

    def test_analyze_min_score_pass(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Simple clear text for testing.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--min-score", "0.1"])
        assert result.exit_code == 0

    def test_analyze_min_score_fail(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Txt.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--min-score", "0.99"])
        assert result.exit_code == 1

    def test_analyze_profile(self, runner: CliRunner, tmp_path) -> None:
        test_file = tmp_path / "test.md"
        test_file.write_text("Technical documentation about the API implementation.")

        result = runner.invoke(cli, ["analyze", str(test_file), "--profile", "technical"])
        assert result.exit_code == 0
        assert "Writing Quality Index" in result.output

